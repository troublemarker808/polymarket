"""Determinism checks for replay and backtest artifact generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pm_bot.research.engine import ResearchRunResult, run_backtest as _run_backtest, run_replay as _run_replay
from pm_bot.runtime.state import DashboardState, PendingOrderState, PositionState

_FLOAT_TOLERANCE = 1e-9


@dataclass(slots=True, frozen=True)
class DeterminismCheck:
    name: str
    passed: bool
    mismatch_path: str | None
    first_hash: str
    second_hash: str


@dataclass(slots=True, frozen=True)
class ReplayDeterminismReport:
    generated_at: datetime
    mode: str
    snapshot_path: str
    limit: int | None
    passed: bool
    checks: tuple[DeterminismCheck, ...]
    processed_snapshots: int
    events_recorded: int


async def generate_replay_determinism_report(
    *,
    snapshot_path: str | Path,
    config_dir: str = "configs",
    mode: str = "replay",
    limit: int | None = None,
) -> ReplayDeterminismReport:
    if mode not in {"replay", "backtest"}:
        raise ValueError("mode must be 'replay' or 'backtest'")

    runner = _run_replay if mode == "replay" else _run_backtest
    with TemporaryDirectory(prefix="pm-bot-determinism-") as tempdir:
        tempdir_path = Path(tempdir)
        first_result = await runner(
            snapshot_path=snapshot_path,
            config_dir=config_dir,
            limit=limit,
            recorder_path=tempdir_path / "first.events.jsonl",
            metrics_path=tempdir_path / "first.metrics.json",
        )
        second_result = await runner(
            snapshot_path=snapshot_path,
            config_dir=config_dir,
            limit=limit,
            recorder_path=tempdir_path / "second.events.jsonl",
            metrics_path=tempdir_path / "second.metrics.json",
        )

        first_summary = _research_result_to_dict(first_result)
        second_summary = _research_result_to_dict(second_result)
        first_metrics = _load_json(tempdir_path / "first.metrics.json")
        second_metrics = _load_json(tempdir_path / "second.metrics.json")
        first_events = _load_jsonl(tempdir_path / "first.events.jsonl")
        second_events = _load_jsonl(tempdir_path / "second.events.jsonl")

    checks = (
        _build_check(name="summary", first=first_summary, second=second_summary),
        _build_check(name="metrics", first=first_metrics, second=second_metrics),
        _build_check(name="events", first=first_events, second=second_events),
    )
    return ReplayDeterminismReport(
        generated_at=datetime.now(tz=timezone.utc),
        mode=mode,
        snapshot_path=str(Path(snapshot_path)),
        limit=limit,
        passed=all(check.passed for check in checks),
        checks=checks,
        processed_snapshots=first_result.processed_snapshots,
        events_recorded=first_result.events_recorded,
    )


def format_replay_determinism_report(report: ReplayDeterminismReport) -> str:
    lines = [
        "# Replay Determinism Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- status: {'pass' if report.passed else 'fail'}",
        f"- mode: {report.mode}",
        f"- snapshot_path: {report.snapshot_path}",
        f"- limit: {report.limit if report.limit is not None else ''}",
        f"- processed_snapshots: {report.processed_snapshots}",
        f"- events_recorded: {report.events_recorded}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(
            f"- {check.name}: {'pass' if check.passed else 'fail'}"
            + (f" mismatch_path={check.mismatch_path}" if check.mismatch_path else "")
        )
        lines.append(f"  first_hash={check.first_hash}")
        lines.append(f"  second_hash={check.second_hash}")

    return "\n".join(lines)


def write_replay_determinism_report(report: ReplayDeterminismReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_replay_determinism_report(report), encoding="utf-8")


def _build_check(*, name: str, first: Any, second: Any) -> DeterminismCheck:
    mismatch_path = _find_first_difference(first, second, path="$")
    return DeterminismCheck(
        name=name,
        passed=mismatch_path is None,
        mismatch_path=mismatch_path,
        first_hash=_stable_hash(first),
        second_hash=_stable_hash(second),
    )


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _research_result_to_dict(result: ResearchRunResult) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "processed_snapshots": result.processed_snapshots,
        "signals_generated": result.signals_generated,
        "signals_rejected": result.signals_rejected,
        "orders_rejected": result.orders_rejected,
        "submitted_orders": result.submitted_orders,
        "events_recorded": result.events_recorded,
        "generated_by_strategy": dict(sorted(result.generated_by_strategy.items())),
        "submitted_by_strategy": dict(sorted(result.submitted_by_strategy.items())),
        "dashboard": _dashboard_to_dict(result.dashboard),
    }


def _dashboard_to_dict(dashboard: DashboardState) -> dict[str, Any]:
    return {
        "total_equity": dashboard.total_equity,
        "today_pnl": dashboard.today_pnl,
        "open_positions": [_position_to_dict(position) for position in sorted(dashboard.open_positions, key=_position_key)],
        "pending_orders": [_pending_order_to_dict(order) for order in sorted(dashboard.pending_orders, key=_pending_order_key)],
        "status": dashboard.status.value,
        "halt_reason": dashboard.halt_reason.value,
        "halt_message": dashboard.halt_message,
        "last_alert": dashboard.last_alert,
        "daily_order_count": dashboard.daily_order_count,
        "daily_order_soft_limit_reached": dashboard.daily_order_soft_limit_reached,
        "last_data_success_at": dashboard.last_data_success_at.isoformat() if dashboard.last_data_success_at is not None else None,
        "last_data_error": dashboard.last_data_error,
        "consecutive_data_failures": dashboard.consecutive_data_failures,
        "issue_codes": tuple(dashboard.issue_codes),
    }


def _position_to_dict(position: PositionState) -> dict[str, Any]:
    return {
        "market_id": position.market_id,
        "token_id": position.token_id,
        "category": position.category.value,
        "strategy_id": position.strategy_id,
        "notional": position.notional,
        "shares": position.shares,
        "average_entry_price": position.average_entry_price,
        "mark_price": position.mark_price,
        "unrealized_pnl": position.unrealized_pnl,
        "opened_at": position.opened_at.isoformat(),
    }


def _pending_order_to_dict(order: PendingOrderState) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "market_id": order.market_id,
        "token_id": order.token_id,
        "category": order.category.value,
        "strategy_id": order.strategy_id,
        "side": order.side,
        "limit_price": order.limit_price,
        "requested_shares": order.requested_shares,
        "requested_notional": order.requested_notional,
        "matched_shares": order.matched_shares,
        "matched_notional": order.matched_notional,
        "fees_paid": order.fees_paid,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "quote_ttl_seconds": order.quote_ttl_seconds,
        "signal_edge_bps": order.signal_edge_bps,
    }


def _position_key(position: PositionState) -> tuple[str, str, str]:
    return (position.market_id, position.token_id, position.strategy_id)


def _pending_order_key(order: PendingOrderState) -> tuple[str, str]:
    return (order.order_id, order.market_id)


def _stable_hash(value: Any) -> str:
    payload = json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _find_first_difference(first: Any, second: Any, *, path: str) -> str | None:
    if isinstance(first, datetime) or isinstance(second, datetime):
        first = first.isoformat() if isinstance(first, datetime) else first
        second = second.isoformat() if isinstance(second, datetime) else second

    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        if abs(float(first) - float(second)) <= _FLOAT_TOLERANCE:
            return None
        return path

    if type(first) is not type(second):
        return path

    if isinstance(first, dict):
        first_keys = sorted(first.keys())
        second_keys = sorted(second.keys())
        if first_keys != second_keys:
            return f"{path}.__keys__"
        for key in first_keys:
            mismatch = _find_first_difference(first[key], second[key], path=f"{path}.{key}")
            if mismatch is not None:
                return mismatch
        return None

    if isinstance(first, (list, tuple)):
        if len(first) != len(second):
            return f"{path}.length"
        for index, (left, right) in enumerate(zip(first, second, strict=False)):
            mismatch = _find_first_difference(left, right, path=f"{path}[{index}]")
            if mismatch is not None:
                return mismatch
        return None

    if first != second:
        return path
    return None
