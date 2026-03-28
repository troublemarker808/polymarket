from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from pm_bot.execution.paper_metrics import PaperExecutionMetrics
from pm_bot.research.paper_integrity import format_paper_integrity_report, generate_paper_integrity_report
from pm_bot.runtime.state import RuntimeState, runtime_state_to_dict


def test_generate_paper_integrity_report_passes_for_matching_artifacts(tmp_path: Path) -> None:
    metrics_path, event_path, state_path = _write_artifacts(tmp_path)

    report = generate_paper_integrity_report(
        metrics_path=metrics_path,
        event_path=event_path,
        state_path=state_path,
    )

    assert report.passed is True
    assert report.failed_checks == ()
    assert report.diagnostics.buy_fill_count == 2
    assert report.diagnostics.sell_fill_count == 0
    assert report.diagnostics.buy_fill_notional == 2.6
    assert report.diagnostics.closed_trade_net_pnl_total == 0.1
    rendered = format_paper_integrity_report(report)
    assert "- status: pass" in rendered
    assert "- none" in rendered


def test_generate_paper_integrity_report_flags_metric_and_state_mismatches(tmp_path: Path) -> None:
    metrics_path, event_path, state_path = _write_artifacts(
        tmp_path,
        metrics_overrides={"orders_filled": 7},
        state_overrides={"orders_today": 2},
    )

    report = generate_paper_integrity_report(
        metrics_path=metrics_path,
        event_path=event_path,
        state_path=state_path,
    )

    assert report.passed is False
    failed = {(check.scope, check.field) for check in report.failed_checks}
    assert ("metrics", "orders_filled") in failed
    assert ("state", "orders_today") in failed


def _write_artifacts(
    tmp_path: Path,
    *,
    metrics_overrides: dict[str, object] | None = None,
    state_overrides: dict[str, object] | None = None,
) -> tuple[Path, Path, Path]:
    started_at = datetime(2026, 3, 26, 5, 35, 0, tzinfo=UTC)
    snapshot_at = started_at + timedelta(minutes=1)
    partial_fill_at = snapshot_at + timedelta(seconds=1)
    full_fill_at = snapshot_at + timedelta(seconds=2)
    close_at = snapshot_at + timedelta(seconds=3)

    events = [
        {
            "event_type": "market.snapshot_processed",
            "payload": {
                "market_id": "m1",
                "processed_snapshots": 1,
                "submitted_orders": 1,
                "stale_orders_cancelled": 0,
                "updated_at": snapshot_at.isoformat(),
            },
        },
        {
            "event_type": "signal.generated",
            "payload": {
                "strategy_id": "crypto.execution_sample",
                "market_id": "m1",
                "token_id": "yes-token",
                "side": "buy_yes",
                "generated_at": snapshot_at.isoformat(),
            },
        },
        {
            "event_type": "order.submitted",
            "payload": {
                "order_id": "paper-1",
                "strategy_id": "crypto.execution_sample",
                "market_id": "m1",
                "token_id": "yes-token",
                "side": "buy_yes",
                "price": 0.52,
                "size": 5.0,
                "notional": 2.6,
                "created_at": snapshot_at.isoformat(),
            },
        },
        {
            "event_type": "order.partially_filled",
            "payload": {
                "order_id": "paper-1",
                "market_id": "m1",
                "token_id": "yes-token",
                "strategy_id": "crypto.execution_sample",
                "trade_side": "BUY",
                "status": "partially_filled",
                "matched_shares": 2.0,
                "matched_notional": 1.0,
                "average_fill_price": 0.5,
                "fill_shares_delta": 2.0,
                "fill_notional_delta": 1.0,
                "fill_source": "maker",
                "mid_price": 0.51,
                "fill_age_ms": 1000.0,
                "updated_at": partial_fill_at.isoformat(),
            },
        },
        {
            "event_type": "order.filled",
            "payload": {
                "order_id": "paper-1",
                "market_id": "m1",
                "token_id": "yes-token",
                "strategy_id": "crypto.execution_sample",
                "trade_side": "BUY",
                "status": "filled",
                "matched_shares": 5.0,
                "matched_notional": 2.6,
                "average_fill_price": 0.52,
                "fill_shares_delta": 3.0,
                "fill_notional_delta": 1.6,
                "fill_source": "taker",
                "mid_price": 0.51,
                "fill_age_ms": 2000.0,
                "updated_at": full_fill_at.isoformat(),
            },
        },
        {
            "event_type": "trade.closed",
            "payload": {
                "market_id": "m1",
                "token_id": "yes-token",
                "strategy_id": "crypto.execution_sample",
                "realized_pnl": 0.11,
                "fees_paid": 0.01,
                "net_pnl": 0.1,
                "closed_at": close_at.isoformat(),
            },
        },
    ]

    metrics = PaperExecutionMetrics()
    metrics.note_snapshot(snapshot_at)
    for event in events[1:]:
        metrics.record_event(event["event_type"], event["payload"])
    metrics_payload = metrics.to_dict()
    if metrics_overrides:
        metrics_payload.update(metrics_overrides)

    state = RuntimeState(
        starting_equity=1000.0,
        day_starting_equity=1000.0,
        realized_pnl_today=0.1,
        unrealized_pnl=0.0,
        orders_today=1,
        day_started_at=started_at,
        updated_at=close_at,
        last_data_success_at=snapshot_at,
    )
    state_payload = runtime_state_to_dict(state)
    if state_overrides:
        state_payload.update(state_overrides)

    metrics_path = tmp_path / "metrics.json"
    event_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "state.json"
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    event_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=True) for event in events) + "\n",
        encoding="utf-8",
    )
    state_path.write_text(json.dumps(state_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return metrics_path, event_path, state_path
