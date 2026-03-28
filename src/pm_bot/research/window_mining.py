"""High-signal window mining for fixed-window experiments."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from pm_bot.core.types import MarketSnapshot, OrderBookLevel
from pm_bot.research.engine import load_market_snapshots

_WEIGHTS = {
    "trade.closed": 30.0,
    "order.filled": 24.0,
    "order.partially_filled": 18.0,
    "order.canceled": 12.0,
    "order.expired": 8.0,
    "order.rejected": 10.0,
    "order.submitted": 2.0,
}
_EVENTFUL_TYPES = frozenset(_WEIGHTS)


@dataclass(slots=True, frozen=True)
class MinedWindow:
    name: str
    score: float
    labels: tuple[str, ...]
    start_at: datetime
    end_at: datetime
    snapshot_count: int
    snapshot_path: str
    event_path: str
    event_counts: dict[str, int]
    rejection_reasons: tuple[tuple[str, int], ...]


@dataclass(slots=True, frozen=True)
class WindowMiningReport:
    generated_at: datetime
    snapshot_path: str
    event_path: str
    output_dir: str
    summary_path: str
    window_snapshot_count: int
    mined_windows: tuple[MinedWindow, ...]


@dataclass(slots=True, frozen=True)
class _EventRecord:
    event_type: str
    timestamp: datetime
    payload: dict[str, Any]
    raw: dict[str, Any]


async def mine_fixed_windows(
    *,
    snapshot_path: str | Path,
    event_path: str | Path,
    output_dir: str | Path | None = None,
    window_snapshots: int = 30,
    top_windows: int = 3,
) -> WindowMiningReport:
    if window_snapshots < 3:
        raise ValueError("window_snapshots must be at least 3")
    if top_windows < 1:
        raise ValueError("top_windows must be at least 1")

    snapshots = _chronological_snapshots(load_market_snapshots(snapshot_path))
    if len(snapshots) < window_snapshots:
        raise ValueError("Snapshot capture is smaller than the requested window size")
    events = _load_eventful_records(event_path)
    if not events:
        raise ValueError("Event log does not contain any eventful records for window mining")

    output_root = _resolve_output_dir(output_dir)
    snapshot_times = [snapshot.timestamp for snapshot in snapshots]
    event_times = [record.timestamp for record in events]
    windows_by_bounds: dict[tuple[int, int], None] = {}
    half_window = window_snapshots // 2
    for record in events:
        center = _nearest_snapshot_index(snapshot_times, record.timestamp)
        start = max(0, center - half_window)
        end = min(len(snapshots), start + window_snapshots)
        start = max(0, end - window_snapshots)
        windows_by_bounds[(start, end)] = None

    ranked_windows: list[tuple[float, int, int, list[_EventRecord]]] = []
    for start, end in windows_by_bounds:
        start_at = snapshots[start].timestamp
        end_at = snapshots[end - 1].timestamp
        left = bisect_left(event_times, start_at)
        right = bisect_right(event_times, end_at)
        window_events = events[left:right]
        score = _window_score(window_events)
        if score <= 0:
            continue
        ranked_windows.append((score, start, end, window_events))
    ranked_windows.sort(key=lambda item: (-item[0], snapshots[item[1]].timestamp, item[1]))

    selected: list[MinedWindow] = []
    selected_bounds: list[tuple[int, int]] = []
    for score, start, end, window_events in ranked_windows:
        bounds = (start, end)
        if any(_overlap_ratio(bounds, existing) > 0.5 for existing in selected_bounds):
            continue
        mined = _write_window_artifacts(
            rank=len(selected) + 1,
            snapshots=snapshots[start:end],
            events=window_events,
            output_dir=output_root,
            score=score,
        )
        selected.append(mined)
        selected_bounds.append(bounds)
        if len(selected) >= top_windows:
            break

    report = WindowMiningReport(
        generated_at=datetime.now(tz=timezone.utc),
        snapshot_path=str(Path(snapshot_path)),
        event_path=str(Path(event_path)),
        output_dir=str(output_root),
        summary_path=str(output_root / "summary.md"),
        window_snapshot_count=window_snapshots,
        mined_windows=tuple(selected),
    )
    write_window_mining_report(report, report.summary_path)
    return report


def format_window_mining_report(report: WindowMiningReport) -> str:
    return "\n".join(
        [
            f"snapshot_path={report.snapshot_path}",
            f"event_path={report.event_path}",
            f"output_dir={report.output_dir}",
            f"window_snapshot_count={report.window_snapshot_count}",
            f"windows_found={len(report.mined_windows)}",
            f"window_scores={','.join(f'{window.name}:{window.score:.2f}' for window in report.mined_windows)}",
            f"summary_path={report.summary_path}",
        ]
    )


def write_window_mining_report(report: WindowMiningReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Window Mining Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- snapshot_path: {report.snapshot_path}",
        f"- event_path: {report.event_path}",
        f"- output_dir: {report.output_dir}",
        f"- window_snapshot_count: {report.window_snapshot_count}",
        f"- windows_found: {len(report.mined_windows)}",
        "",
        "## Windows",
        "",
    ]
    if not report.mined_windows:
        lines.append("- none")
    for window in report.mined_windows:
        lines.append(
            f"- {window.name}: score={window.score:.2f}, labels={','.join(window.labels)}, "
            f"snapshots={window.snapshot_count}, window={window.start_at.isoformat()} -> {window.end_at.isoformat()}"
        )
        lines.append(f"  snapshot_path: {window.snapshot_path}")
        lines.append(f"  event_path: {window.event_path}")
        counts = ",".join(f"{key}:{value}" for key, value in sorted(window.event_counts.items()))
        lines.append(f"  event_counts: {counts}")
        if window.rejection_reasons:
            reasons = ",".join(f"{reason}:{count}" for reason, count in window.rejection_reasons)
            lines.append(f"  rejection_reasons: {reasons}")
    target.write_text("\n".join(lines), encoding="utf-8")


def _load_eventful_records(path: str | Path) -> list[_EventRecord]:
    records: list[_EventRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                continue
            event_type = str(raw.get("event_type", "")).strip()
            if event_type not in _EVENTFUL_TYPES:
                continue
            payload = raw.get("payload")
            if not isinstance(payload, dict):
                continue
            timestamp = _event_timestamp(payload)
            if timestamp is None:
                continue
            records.append(
                _EventRecord(
                    event_type=event_type,
                    timestamp=timestamp,
                    payload=payload,
                    raw={"event_type": event_type, "payload": payload},
                )
            )
    records.sort(key=lambda record: record.timestamp)
    return records


def _event_timestamp(payload: dict[str, Any]) -> datetime | None:
    for key in ("updated_at", "created_at", "generated_at", "timestamp"):
        value = payload.get(key)
        if value in (None, ""):
            continue
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _window_score(events: list[_EventRecord]) -> float:
    total = 0.0
    counts = Counter(record.event_type for record in events)
    for record in events:
        total += _WEIGHTS.get(record.event_type, 0.0)
        if record.event_type == "order.canceled" and record.payload.get("reason") == "open_order_replaced":
            total += 4.0
        if record.event_type == "order.rejected" and record.payload.get("reason"):
            total += 1.0
    if counts.get("trade.closed", 0) > 0:
        total += 20.0
    if counts.get("order.filled", 0) > 0 or counts.get("order.partially_filled", 0) > 0:
        total += 12.0
    only_expiry_like = (
        counts.get("trade.closed", 0) == 0
        and counts.get("order.filled", 0) == 0
        and counts.get("order.partially_filled", 0) == 0
        and counts.get("order.rejected", 0) == 0
        and counts.get("order.canceled", 0) == 0
        and counts.get("order.expired", 0) > 0
    )
    if only_expiry_like:
        total -= 10.0
    return total


def _labels_for_window(events: list[_EventRecord]) -> tuple[str, ...]:
    counts = Counter(record.event_type for record in events)
    labels: list[str] = []
    if counts.get("order.filled", 0) or counts.get("order.partially_filled", 0) or counts.get("trade.closed", 0):
        labels.append("fill-bearing")
    replacement_cancels = sum(
        1
        for record in events
        if record.event_type == "order.canceled" and record.payload.get("reason") == "open_order_replaced"
    )
    if replacement_cancels > 0:
        labels.append("replacement-heavy")
    if counts.get("order.rejected", 0) > 0:
        labels.append("rejection-heavy")
    if counts.get("order.expired", 0) > 0:
        labels.append("expiry-heavy")
    if not labels:
        labels.append("submission-heavy")
    return tuple(labels)


def _write_window_artifacts(
    *,
    rank: int,
    snapshots: list[MarketSnapshot],
    events: list[_EventRecord],
    output_dir: Path,
    score: float,
) -> MinedWindow:
    name = f"window-{rank:02d}"
    snapshot_output = output_dir / f"{name}.snapshots.jsonl"
    event_output = output_dir / f"{name}.events.jsonl"
    snapshot_output.write_text(
        "\n".join(json.dumps(_snapshot_record(snapshot), ensure_ascii=True) for snapshot in snapshots),
        encoding="utf-8",
    )
    event_output.write_text(
        "\n".join(json.dumps(record.raw, ensure_ascii=True) for record in events),
        encoding="utf-8",
    )
    event_counts = Counter(record.event_type for record in events)
    rejection_reasons = Counter(
        str(record.payload.get("reason"))
        for record in events
        if record.event_type == "order.rejected" and record.payload.get("reason")
    )
    return MinedWindow(
        name=name,
        score=score,
        labels=_labels_for_window(events),
        start_at=snapshots[0].timestamp,
        end_at=snapshots[-1].timestamp,
        snapshot_count=len(snapshots),
        snapshot_path=str(snapshot_output),
        event_path=str(event_output),
        event_counts=dict(sorted(event_counts.items())),
        rejection_reasons=tuple(sorted(rejection_reasons.items(), key=lambda item: (-item[1], item[0]))),
    )


def _overlap_ratio(left: tuple[int, int], right: tuple[int, int]) -> float:
    overlap = max(0, min(left[1], right[1]) - max(left[0], right[0]))
    shortest = max(1, min(left[1] - left[0], right[1] - right[0]))
    return overlap / shortest


def _nearest_snapshot_index(timestamps: list[datetime], event_time: datetime) -> int:
    index = bisect_left(timestamps, event_time)
    if index <= 0:
        return 0
    if index >= len(timestamps):
        return len(timestamps) - 1
    before = timestamps[index - 1]
    after = timestamps[index]
    if (event_time - before) <= (after - event_time):
        return index - 1
    return index


def _chronological_snapshots(snapshots: list[MarketSnapshot]) -> list[MarketSnapshot]:
    indexed = list(enumerate(snapshots))
    indexed.sort(key=lambda item: (item[1].timestamp, item[0]))
    return [snapshot for _, snapshot in indexed]


def _resolve_output_dir(path: str | Path | None) -> Path:
    if path is not None:
        target = Path(path)
    else:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = Path("data/runtime") / f"mined-windows-{timestamp}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _snapshot_record(snapshot: MarketSnapshot) -> dict[str, Any]:
    return {
        "event_type": "market.snapshot",
        "payload": {
            "market_id": snapshot.market_id,
            "token_id": snapshot.token_id,
            "slug": snapshot.slug,
            "category": snapshot.category.value,
            "timestamp": snapshot.timestamp.isoformat(),
            "resolution_time": snapshot.resolution_time.isoformat() if snapshot.resolution_time is not None else None,
            "best_bid_yes": snapshot.best_bid_yes,
            "best_ask_yes": snapshot.best_ask_yes,
            "best_bid_no": snapshot.best_bid_no,
            "best_ask_no": snapshot.best_ask_no,
            "best_bid_yes_size": snapshot.best_bid_yes_size,
            "best_ask_yes_size": snapshot.best_ask_yes_size,
            "best_bid_no_size": snapshot.best_bid_no_size,
            "best_ask_no_size": snapshot.best_ask_no_size,
            "tick_size": snapshot.tick_size,
            "min_order_size": snapshot.min_order_size,
            "last_traded_price": snapshot.last_traded_price,
            "last_trade_side": snapshot.last_trade_side,
            "last_trade_size": snapshot.last_trade_size,
            "yes_bid_levels": _level_records(snapshot.yes_bid_levels),
            "yes_ask_levels": _level_records(snapshot.yes_ask_levels),
            "no_bid_levels": _level_records(snapshot.no_bid_levels),
            "no_ask_levels": _level_records(snapshot.no_ask_levels),
            "liquidity_score": snapshot.liquidity_score,
            "metadata": dict(snapshot.metadata),
        },
    }


def _level_records(levels: tuple[OrderBookLevel, ...]) -> list[dict[str, float]]:
    return [{"price": level.price, "size": level.size} for level in levels]
