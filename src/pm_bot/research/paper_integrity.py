"""Integrity checks for persisted paper-session artifacts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from pm_bot.execution.metrics_report import load_metrics_file
from pm_bot.execution.paper_metrics import PaperExecutionMetrics
from pm_bot.runtime.state import RuntimeState, runtime_state_from_dict

_METRIC_COMPARE_KEYS = (
    "processed_snapshots",
    "paper_days_observed",
    "observed_trading_days",
    "signals_generated",
    "signals_rejected",
    "orders_submitted",
    "orders_rejected",
    "orders_filled",
    "orders_partially_filled",
    "orders_expired",
    "orders_canceled",
    "trades_closed",
    "market_data_failures",
    "market_data_recoveries",
    "filled_shares_total",
    "maker_filled_shares",
    "taker_filled_shares",
    "fill_rate",
    "cancel_rate",
    "avg_time_to_fill_ms",
    "avg_fill_price_vs_mid_bps",
    "maker_fill_share",
    "taker_fill_share",
    "generated_by_strategy",
    "submitted_by_strategy",
)
_FLOAT_TOLERANCE = 1e-9


@dataclass(slots=True, frozen=True)
class IntegrityCheck:
    scope: str
    field: str
    expected: Any
    actual: Any
    passed: bool


@dataclass(slots=True, frozen=True)
class PaperIntegrityDiagnostics:
    event_counts: dict[str, int]
    fill_sources: dict[str, int]
    fill_trade_sides: dict[str, int]
    buy_fill_count: int
    sell_fill_count: int
    buy_fill_notional: float
    sell_fill_notional: float
    closed_trade_net_pnl_total: float
    current_day_closed_trade_net_pnl: float | None
    current_day_submitted_orders: int | None
    latest_snapshot_at: datetime | None
    latest_data_success_at: datetime | None
    final_consecutive_data_failures: int | None
    final_last_data_error: str | None


@dataclass(slots=True, frozen=True)
class PaperIntegrityReport:
    generated_at: datetime
    metrics_path: str
    event_path: str
    state_path: str | None
    passed: bool
    checks: tuple[IntegrityCheck, ...]
    reconstructed_metrics: dict[str, Any]
    diagnostics: PaperIntegrityDiagnostics

    @property
    def failed_checks(self) -> tuple[IntegrityCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)


def generate_paper_integrity_report(
    *,
    metrics_path: str | Path,
    event_path: str | Path,
    state_path: str | Path | None = None,
) -> PaperIntegrityReport:
    metrics = load_metrics_file(metrics_path)
    events = _load_event_log(event_path)
    reconstructed = _replay_metrics_from_events(events).to_dict()
    runtime_state = _load_runtime_state(state_path)
    diagnostics = _summarize_events(events, day_started_at=(runtime_state.day_started_at if runtime_state is not None else None))

    checks: list[IntegrityCheck] = []
    for key in _METRIC_COMPARE_KEYS:
        checks.append(
            IntegrityCheck(
                scope="metrics",
                field=key,
                expected=_normalize_value(reconstructed.get(key)),
                actual=_normalize_value(metrics.get(key)),
                passed=_values_match(metrics.get(key), reconstructed.get(key)),
            )
        )

    if runtime_state is not None:
        checks.extend(_state_checks(runtime_state=runtime_state, diagnostics=diagnostics))

    return PaperIntegrityReport(
        generated_at=datetime.now(tz=timezone.utc),
        metrics_path=str(Path(metrics_path)),
        event_path=str(Path(event_path)),
        state_path=(str(Path(state_path)) if state_path is not None else None),
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
        reconstructed_metrics=reconstructed,
        diagnostics=diagnostics,
    )


def format_paper_integrity_report(report: PaperIntegrityReport) -> str:
    lines = [
        "# Paper Integrity Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- status: {'pass' if report.passed else 'fail'}",
        f"- metrics_path: {report.metrics_path}",
        f"- event_path: {report.event_path}",
        f"- state_path: {report.state_path or ''}",
        f"- checks_passed: {sum(1 for check in report.checks if check.passed)}",
        f"- checks_failed: {sum(1 for check in report.checks if not check.passed)}",
        "",
        "## Diagnostics",
        "",
    ]

    diagnostics = report.diagnostics
    lines.extend(
        [
            f"- closed_trade_net_pnl_total: {diagnostics.closed_trade_net_pnl_total:.6f}",
            (
                f"- current_day_closed_trade_net_pnl: {diagnostics.current_day_closed_trade_net_pnl:.6f}"
                if diagnostics.current_day_closed_trade_net_pnl is not None
                else "- current_day_closed_trade_net_pnl: "
            ),
            (
                f"- current_day_submitted_orders: {diagnostics.current_day_submitted_orders}"
                if diagnostics.current_day_submitted_orders is not None
                else "- current_day_submitted_orders: "
            ),
            f"- buy_fill_count: {diagnostics.buy_fill_count}",
            f"- sell_fill_count: {diagnostics.sell_fill_count}",
            f"- buy_fill_notional: {diagnostics.buy_fill_notional:.6f}",
            f"- sell_fill_notional: {diagnostics.sell_fill_notional:.6f}",
            (
                f"- latest_snapshot_at: {diagnostics.latest_snapshot_at.isoformat()}"
                if diagnostics.latest_snapshot_at is not None
                else "- latest_snapshot_at: "
            ),
            (
                f"- latest_data_success_at: {diagnostics.latest_data_success_at.isoformat()}"
                if diagnostics.latest_data_success_at is not None
                else "- latest_data_success_at: "
            ),
            (
                f"- final_consecutive_data_failures: {diagnostics.final_consecutive_data_failures}"
                if diagnostics.final_consecutive_data_failures is not None
                else "- final_consecutive_data_failures: "
            ),
            f"- final_last_data_error: {diagnostics.final_last_data_error or ''}",
            "",
            "## Fill Sources",
            "",
        ]
    )
    if diagnostics.fill_sources:
        for source, count in sorted(diagnostics.fill_sources.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Fill Trade Sides",
            "",
        ]
    )
    if diagnostics.fill_trade_sides:
        for side, count in sorted(diagnostics.fill_trade_sides.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {side}: {count}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Failed Checks",
            "",
        ]
    )
    failed_checks = report.failed_checks
    if failed_checks:
        for check in failed_checks:
            lines.append(
                f"- {check.scope}.{check.field}: expected={_format_value(check.expected)} actual={_format_value(check.actual)}"
            )
    else:
        lines.append("- none")

    return "\n".join(lines)


def write_paper_integrity_report(report: PaperIntegrityReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_paper_integrity_report(report), encoding="utf-8")


def _load_event_log(path: str | Path) -> tuple[dict[str, Any], ...]:
    event_path = Path(path)
    if not event_path.exists():
        raise FileNotFoundError(event_path)

    events: list[dict[str, Any]] = []
    with event_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Event log lines must decode to JSON objects")
            events.append(payload)
    return tuple(events)


def _load_runtime_state(path: str | Path | None) -> RuntimeState | None:
    if path is None:
        return None
    state_path = Path(path)
    if not state_path.exists():
        raise FileNotFoundError(state_path)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Runtime state payload must be a JSON object")
    return runtime_state_from_dict(payload)


def _replay_metrics_from_events(events: tuple[dict[str, Any], ...]) -> PaperExecutionMetrics:
    metrics = PaperExecutionMetrics()
    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if not event_type or not isinstance(payload, dict):
            continue
        if event_type == "market.snapshot_processed":
            updated_at = _parse_datetime(payload.get("updated_at"))
            if updated_at is not None:
                metrics.note_snapshot(timestamp=updated_at)
        metrics.record_event(event_type=event_type, payload=payload)
    return metrics


def _summarize_events(
    events: tuple[dict[str, Any], ...],
    *,
    day_started_at: datetime | None,
) -> PaperIntegrityDiagnostics:
    event_counts: Counter[str] = Counter()
    fill_sources: Counter[str] = Counter()
    fill_trade_sides: Counter[str] = Counter()
    buy_fill_count = 0
    sell_fill_count = 0
    buy_fill_notional = 0.0
    sell_fill_notional = 0.0
    closed_trade_net_pnl_total = 0.0
    current_day_closed_trade_net_pnl = 0.0 if day_started_at is not None else None
    current_day_submitted_orders = 0 if day_started_at is not None else None
    latest_snapshot_at: datetime | None = None
    latest_data_success_at: datetime | None = None
    consecutive_data_failures = 0 if day_started_at is not None else None
    last_data_error: str | None = None

    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if not event_type or not isinstance(payload, dict):
            continue

        event_counts[event_type] += 1

        if event_type in {"order.filled", "order.partially_filled"}:
            fill_source = str(payload.get("fill_source", "")).strip() or "unknown"
            fill_sources[fill_source] += 1

            trade_side = str(payload.get("trade_side", "")).strip() or "unknown"
            fill_trade_sides[trade_side] += 1

            fill_notional_delta = float(payload.get("fill_notional_delta", 0.0) or 0.0)
            if trade_side == "BUY":
                buy_fill_count += 1
                buy_fill_notional += fill_notional_delta
            elif trade_side == "SELL":
                sell_fill_count += 1
                sell_fill_notional += fill_notional_delta

        if event_type == "trade.closed":
            net_pnl = float(payload.get("net_pnl", 0.0) or 0.0)
            closed_trade_net_pnl_total += net_pnl
            if current_day_closed_trade_net_pnl is not None and day_started_at is not None:
                closed_at = _parse_datetime(payload.get("closed_at"))
                if closed_at is not None and closed_at >= day_started_at:
                    current_day_closed_trade_net_pnl += net_pnl

        if event_type == "order.submitted" and current_day_submitted_orders is not None and day_started_at is not None:
            created_at = _parse_datetime(payload.get("created_at"))
            if created_at is not None and created_at >= day_started_at:
                current_day_submitted_orders += 1

        if event_type == "market.snapshot_processed":
            updated_at = _parse_datetime(payload.get("updated_at"))
            latest_snapshot_at = _max_datetime(latest_snapshot_at, updated_at)
            latest_data_success_at = _max_datetime(latest_data_success_at, updated_at)
            if consecutive_data_failures is not None:
                consecutive_data_failures = 0
                last_data_error = None
        elif event_type == "market_data.recovered":
            updated_at = _parse_datetime(payload.get("updated_at"))
            latest_data_success_at = _max_datetime(latest_data_success_at, updated_at)
            if consecutive_data_failures is not None:
                consecutive_data_failures = 0
                last_data_error = None
        elif event_type == "market_data.failure" and consecutive_data_failures is not None:
            consecutive_data_failures += 1
            last_data_error = str(payload.get("error", "")).strip() or None

    return PaperIntegrityDiagnostics(
        event_counts=dict(sorted(event_counts.items())),
        fill_sources=dict(sorted(fill_sources.items())),
        fill_trade_sides=dict(sorted(fill_trade_sides.items())),
        buy_fill_count=buy_fill_count,
        sell_fill_count=sell_fill_count,
        buy_fill_notional=buy_fill_notional,
        sell_fill_notional=sell_fill_notional,
        closed_trade_net_pnl_total=closed_trade_net_pnl_total,
        current_day_closed_trade_net_pnl=current_day_closed_trade_net_pnl,
        current_day_submitted_orders=current_day_submitted_orders,
        latest_snapshot_at=latest_snapshot_at,
        latest_data_success_at=latest_data_success_at,
        final_consecutive_data_failures=consecutive_data_failures,
        final_last_data_error=last_data_error,
    )


def _state_checks(
    *,
    runtime_state: RuntimeState,
    diagnostics: PaperIntegrityDiagnostics,
) -> list[IntegrityCheck]:
    checks = [
        IntegrityCheck(
            scope="state",
            field="realized_pnl_today",
            expected=(
                round(diagnostics.current_day_closed_trade_net_pnl, 12)
                if diagnostics.current_day_closed_trade_net_pnl is not None
                else None
            ),
            actual=round(runtime_state.realized_pnl_today, 12),
            passed=(
                diagnostics.current_day_closed_trade_net_pnl is not None
                and _values_match(runtime_state.realized_pnl_today, diagnostics.current_day_closed_trade_net_pnl)
            ),
        ),
        IntegrityCheck(
            scope="state",
            field="orders_today",
            expected=diagnostics.current_day_submitted_orders,
            actual=runtime_state.orders_today,
            passed=(
                diagnostics.current_day_submitted_orders is not None
                and runtime_state.orders_today == diagnostics.current_day_submitted_orders
            ),
        ),
        IntegrityCheck(
            scope="state",
            field="last_data_success_at",
            expected=_normalize_value(diagnostics.latest_data_success_at),
            actual=_normalize_value(runtime_state.last_data_success_at),
            passed=_values_match(runtime_state.last_data_success_at, diagnostics.latest_data_success_at),
        ),
        IntegrityCheck(
            scope="state",
            field="consecutive_data_failures",
            expected=diagnostics.final_consecutive_data_failures,
            actual=runtime_state.consecutive_data_failures,
            passed=(
                diagnostics.final_consecutive_data_failures is not None
                and runtime_state.consecutive_data_failures == diagnostics.final_consecutive_data_failures
            ),
        ),
        IntegrityCheck(
            scope="state",
            field="last_data_error",
            expected=diagnostics.final_last_data_error,
            actual=runtime_state.last_data_error,
            passed=runtime_state.last_data_error == diagnostics.final_last_data_error,
        ),
    ]
    return checks


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _max_datetime(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return candidate if candidate > current else current


def _values_match(actual: Any, expected: Any) -> bool:
    if isinstance(actual, datetime) or isinstance(expected, datetime):
        actual_dt = actual if isinstance(actual, datetime) else _parse_datetime(actual)
        expected_dt = expected if isinstance(expected, datetime) else _parse_datetime(expected)
        return actual_dt == expected_dt
    if isinstance(actual, float) or isinstance(expected, float):
        if actual is None or expected is None:
            return actual is expected
        return abs(float(actual) - float(expected)) <= _FLOAT_TOLERANCE
    return bool(_normalize_value(actual) == _normalize_value(expected))


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return tuple(_normalize_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_normalize_value(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _normalize_value(item) for key, item in sorted(value.items())}
    return value


def _format_value(value: Any) -> str:
    normalized = _normalize_value(value)
    if normalized is None:
        return ""
    if isinstance(normalized, float):
        return f"{normalized:.12f}".rstrip("0").rstrip(".")
    return str(normalized)
