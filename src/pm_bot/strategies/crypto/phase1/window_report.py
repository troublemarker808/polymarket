"""Bucketed reporting for crypto window families."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market


@dataclass(slots=True, frozen=True)
class CryptoWindowFamilyBucket:
    underlying: str
    event_family: str
    series_key: str
    unique_markets: int
    snapshot_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    event_counts: dict[str, int]


@dataclass(slots=True, frozen=True)
class CryptoWindowFamilyReport:
    generated_at: datetime
    snapshot_path: str
    event_path: str | None
    summary_path: str
    output_dir: str | None
    normalized_snapshot_count: int
    skipped_snapshot_count: int
    buckets: tuple[CryptoWindowFamilyBucket, ...]


@dataclass(slots=True, frozen=True)
class CryptoFamilyExportResult:
    snapshot_path: str
    event_path: str | None
    filtered_snapshot_path: str
    filtered_event_path: str | None
    summary_path: str
    underlying: str | None
    event_family: str | None
    series_key_contains: str | None
    retained_snapshot_count: int
    retained_market_count: int
    retained_event_count: int


def generate_crypto_window_family_report(
    *,
    snapshot_path: str | Path,
    event_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> CryptoWindowFamilyReport:
    snapshots = load_market_snapshots(snapshot_path)
    normalized_by_market_id: dict[str, tuple[str, str, str]] = {}
    bucket_snapshot_counts: Counter[tuple[str, str, str]] = Counter()
    bucket_market_ids: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    bucket_first_seen: dict[tuple[str, str, str], datetime] = {}
    bucket_last_seen: dict[tuple[str, str, str], datetime] = {}
    skipped_snapshot_count = 0

    for snapshot in snapshots:
        normalized = normalize_crypto_market(snapshot)
        if normalized is None:
            skipped_snapshot_count += 1
            continue
        key = (normalized.underlying, normalized.event_family, normalized.series_key)
        normalized_by_market_id[snapshot.market_id] = key
        bucket_snapshot_counts[key] += 1
        bucket_market_ids[key].add(snapshot.market_id)
        current_first = bucket_first_seen.get(key)
        current_last = bucket_last_seen.get(key)
        if current_first is None or snapshot.timestamp < current_first:
            bucket_first_seen[key] = snapshot.timestamp
        if current_last is None or snapshot.timestamp > current_last:
            bucket_last_seen[key] = snapshot.timestamp

    bucket_event_counts: defaultdict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    if event_path is not None:
        for raw in _load_event_records(event_path):
            payload = raw.get("payload")
            if not isinstance(payload, dict):
                continue
            market_id = str(payload.get("market_id", "")).strip()
            if not market_id:
                continue
            key = normalized_by_market_id.get(market_id)
            if key is None:
                continue
            event_type = str(raw.get("event_type", "")).strip()
            if event_type:
                bucket_event_counts[key][event_type] += 1

    buckets = tuple(
        sorted(
            (
                CryptoWindowFamilyBucket(
                    underlying=underlying,
                    event_family=event_family,
                    series_key=series_key,
                    unique_markets=len(bucket_market_ids[(underlying, event_family, series_key)]),
                    snapshot_count=bucket_snapshot_counts[(underlying, event_family, series_key)],
                    first_seen_at=bucket_first_seen[(underlying, event_family, series_key)],
                    last_seen_at=bucket_last_seen[(underlying, event_family, series_key)],
                    event_counts=dict(sorted(bucket_event_counts[(underlying, event_family, series_key)].items())),
                )
                for underlying, event_family, series_key in bucket_snapshot_counts
            ),
            key=lambda item: (
                -sum(item.event_counts.values()),
                -item.snapshot_count,
                item.underlying,
                item.event_family,
                item.series_key,
            ),
        )
    )

    summary_path = (
        Path(output_dir) / "summary.md"
        if output_dir is not None
        else Path(snapshot_path).with_suffix(".window-family-summary.md")
    )
    report = CryptoWindowFamilyReport(
        generated_at=datetime.now(tz=timezone.utc),
        snapshot_path=str(Path(snapshot_path)),
        event_path=str(Path(event_path)) if event_path is not None else None,
        summary_path=str(summary_path),
        output_dir=str(Path(output_dir)) if output_dir is not None else None,
        normalized_snapshot_count=sum(bucket_snapshot_counts.values()),
        skipped_snapshot_count=skipped_snapshot_count,
        buckets=buckets,
    )
    write_crypto_window_family_report(report, summary_path)
    return report


def format_crypto_window_family_report(report: CryptoWindowFamilyReport) -> str:
    return "\n".join(
        [
            "Crypto Window Family Report",
            f"snapshot_path={report.snapshot_path}",
            f"event_path={report.event_path or ''}",
            f"normalized_snapshot_count={report.normalized_snapshot_count}",
            f"skipped_snapshot_count={report.skipped_snapshot_count}",
            f"bucket_count={len(report.buckets)}",
            "buckets="
            + ",".join(
                f"{bucket.underlying}:{bucket.event_family}:{bucket.unique_markets}m:{sum(bucket.event_counts.values())}e"
                for bucket in report.buckets
            ),
            f"summary_path={report.summary_path}",
        ]
    )


def write_crypto_window_family_report(report: CryptoWindowFamilyReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Crypto Window Family Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- snapshot_path: {report.snapshot_path}",
        f"- event_path: {report.event_path or ''}",
        f"- normalized_snapshot_count: {report.normalized_snapshot_count}",
        f"- skipped_snapshot_count: {report.skipped_snapshot_count}",
        f"- bucket_count: {len(report.buckets)}",
        "",
        "## Buckets",
        "",
    ]
    if not report.buckets:
        lines.append("- none")
    for bucket in report.buckets:
        lines.append(
            f"- {bucket.underlying} {bucket.event_family}: series={bucket.series_key}, "
            f"markets={bucket.unique_markets}, snapshots={bucket.snapshot_count}, "
            f"window={bucket.first_seen_at.isoformat()} -> {bucket.last_seen_at.isoformat()}"
        )
        if bucket.event_counts:
            lines.append(
                "  event_counts: "
                + ",".join(f"{name}:{count}" for name, count in sorted(bucket.event_counts.items()))
            )
    target.write_text("\n".join(lines), encoding="utf-8")


def export_crypto_family_window(
    *,
    snapshot_path: str | Path,
    output_dir: str | Path,
    event_path: str | Path | None = None,
    underlying: str | None = None,
    event_family: str | None = None,
    series_key_contains: str | None = None,
) -> CryptoFamilyExportResult:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    filtered_snapshots: list[object] = []
    retained_market_ids: set[str] = set()
    for snapshot in load_market_snapshots(snapshot_path):
        normalized = normalize_crypto_market(snapshot)
        if normalized is None:
            continue
        if underlying is not None and normalized.underlying != underlying:
            continue
        if event_family is not None and normalized.event_family != event_family:
            continue
        if series_key_contains is not None and series_key_contains not in normalized.series_key:
            continue
        filtered_snapshots.append(snapshot)
        retained_market_ids.add(snapshot.market_id)

    filtered_snapshot_path = output_root / "snapshots.jsonl"
    filtered_snapshot_path.write_text(
        "\n".join(json.dumps(_snapshot_record(snapshot), ensure_ascii=True) for snapshot in filtered_snapshots),
        encoding="utf-8",
    )

    retained_event_count = 0
    filtered_event_path: Path | None = None
    if event_path is not None:
        filtered_event_path = output_root / "events.jsonl"
        filtered_events: list[str] = []
        for raw in _load_event_records(event_path):
            payload = raw.get("payload")
            if not isinstance(payload, dict):
                continue
            market_id = str(payload.get("market_id", "")).strip()
            if market_id and market_id in retained_market_ids:
                filtered_events.append(json.dumps(raw, ensure_ascii=True))
        retained_event_count = len(filtered_events)
        filtered_event_path.write_text("\n".join(filtered_events), encoding="utf-8")

    summary_path = output_root / "summary.md"
    result = CryptoFamilyExportResult(
        snapshot_path=str(Path(snapshot_path)),
        event_path=str(Path(event_path)) if event_path is not None else None,
        filtered_snapshot_path=str(filtered_snapshot_path),
        filtered_event_path=str(filtered_event_path) if filtered_event_path is not None else None,
        summary_path=str(summary_path),
        underlying=underlying,
        event_family=event_family,
        series_key_contains=series_key_contains,
        retained_snapshot_count=len(filtered_snapshots),
        retained_market_count=len(retained_market_ids),
        retained_event_count=retained_event_count,
    )
    write_crypto_family_export_result(result, summary_path)
    return result


def format_crypto_family_export_result(result: CryptoFamilyExportResult) -> str:
    return "\n".join(
        [
            "Crypto Family Export",
            f"snapshot_path={result.snapshot_path}",
            f"event_path={result.event_path or ''}",
            f"filtered_snapshot_path={result.filtered_snapshot_path}",
            f"filtered_event_path={result.filtered_event_path or ''}",
            f"underlying={result.underlying or ''}",
            f"event_family={result.event_family or ''}",
            f"series_key_contains={result.series_key_contains or ''}",
            f"retained_snapshot_count={result.retained_snapshot_count}",
            f"retained_market_count={result.retained_market_count}",
            f"retained_event_count={result.retained_event_count}",
            f"summary_path={result.summary_path}",
        ]
    )


def write_crypto_family_export_result(result: CryptoFamilyExportResult, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Crypto Family Export",
        "",
        f"- snapshot_path: {result.snapshot_path}",
        f"- event_path: {result.event_path or ''}",
        f"- filtered_snapshot_path: {result.filtered_snapshot_path}",
        f"- filtered_event_path: {result.filtered_event_path or ''}",
        f"- underlying: {result.underlying or ''}",
        f"- event_family: {result.event_family or ''}",
        f"- series_key_contains: {result.series_key_contains or ''}",
        f"- retained_snapshot_count: {result.retained_snapshot_count}",
        f"- retained_market_count: {result.retained_market_count}",
        f"- retained_event_count: {result.retained_event_count}",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")


def _load_event_records(path: str | Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if isinstance(raw, dict):
                records.append(raw)
    return records


def _snapshot_record(snapshot) -> dict[str, object]:
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
            "yes_bid_levels": [{"price": level.price, "size": level.size} for level in snapshot.yes_bid_levels],
            "yes_ask_levels": [{"price": level.price, "size": level.size} for level in snapshot.yes_ask_levels],
            "no_bid_levels": [{"price": level.price, "size": level.size} for level in snapshot.no_bid_levels],
            "no_ask_levels": [{"price": level.price, "size": level.size} for level in snapshot.no_ask_levels],
            "liquidity_score": snapshot.liquidity_score,
            "metadata": dict(snapshot.metadata),
        },
    }
