from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from pm_bot.research.replay_determinism import format_replay_determinism_report, generate_replay_determinism_report
from pm_bot.research.engine import ResearchRunResult
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus


def test_generate_replay_determinism_report_passes_for_stable_replay(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    _write_snapshots(snapshot_path)

    report = asyncio.run(
        generate_replay_determinism_report(
            snapshot_path=snapshot_path,
            config_dir="configs",
            mode="replay",
        )
    )

    assert report.passed is True
    assert tuple(check.name for check in report.checks) == ("summary", "metrics", "events")
    assert all(check.passed for check in report.checks)
    rendered = format_replay_determinism_report(report)
    assert "- status: pass" in rendered


def test_generate_replay_determinism_report_flags_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = {"count": 0}

    async def _fake_runner(
        *,
        snapshot_path,
        config_dir="configs",
        limit=None,
        recorder_path=None,
        metrics_path=None,
    ) -> ResearchRunResult:
        calls["count"] += 1
        assert recorder_path is not None
        assert metrics_path is not None
        event_notional = 1.0 if calls["count"] == 1 else 2.0
        metrics_payload = {
            "processed_snapshots": 1,
            "paper_days_observed": 1,
            "observed_trading_days": ["2026-03-23"],
            "signals_generated": 1,
            "signals_rejected": 0,
            "orders_submitted": 1,
            "orders_rejected": 0,
            "orders_filled": 1,
            "orders_partially_filled": 0,
            "orders_expired": 0,
            "orders_canceled": 0,
            "trades_closed": 0,
            "market_data_failures": 0,
            "market_data_recoveries": 0,
            "filled_shares_total": event_notional,
            "maker_filled_shares": 0.0,
            "taker_filled_shares": event_notional,
            "fill_rate": 1.0,
            "cancel_rate": 0.0,
            "avg_time_to_fill_ms": 1000.0,
            "avg_fill_price_vs_mid_bps": 0.0,
            "maker_fill_share": 0.0,
            "taker_fill_share": 1.0,
            "generated_by_strategy": {"crypto.maker": 1},
            "submitted_by_strategy": {"crypto.maker": 1},
            "updated_at": "2026-03-23T12:00:00+00:00",
        }
        Path(metrics_path).write_text(json.dumps(metrics_payload, ensure_ascii=True), encoding="utf-8")
        Path(recorder_path).write_text(
            json.dumps(
                {
                    "event_type": "order.filled",
                    "payload": {"fill_notional_delta": event_notional},
                },
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return ResearchRunResult(
            mode="replay",
            processed_snapshots=1,
            signals_generated=1,
            signals_rejected=0,
            orders_rejected=0,
            submitted_orders=(1 if calls["count"] == 1 else 2),
            events_recorded=1,
            generated_by_strategy={"crypto.maker": 1},
            submitted_by_strategy={"crypto.maker": 1},
            dashboard=_dashboard(),
        )

    monkeypatch.setattr("pm_bot.research.replay_determinism._run_replay", _fake_runner)
    snapshot_path = tmp_path / "snapshots.jsonl"
    snapshot_path.write_text("", encoding="utf-8")

    report = asyncio.run(
        generate_replay_determinism_report(
            snapshot_path=snapshot_path,
            config_dir="configs",
            mode="replay",
        )
    )

    assert report.passed is False
    checks = {check.name: check for check in report.checks}
    assert checks["summary"].passed is False
    assert checks["metrics"].passed is False
    assert checks["events"].passed is False


def _dashboard() -> DashboardState:
    return DashboardState(
        total_equity=1000.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
        last_data_success_at=None,
        last_data_error=None,
        consecutive_data_failures=0,
        issue_codes=(),
    )


def _write_snapshots(path: Path) -> None:
    records = [
        {
            "market_id": "crypto-1",
            "token_id": "crypto-1-yes",
            "slug": "crypto-1",
            "category": "crypto",
            "timestamp": "2026-03-23T12:00:00Z",
            "best_bid_yes": 0.5,
            "best_ask_yes": 0.6,
            "best_bid_no": 0.4,
            "best_ask_no": 0.5,
            "last_traded_price": 0.55,
            "metadata": {
                "reference_yes_probability": "0.56",
                "no_token_id": "crypto-1-no",
            },
        },
        {
            "market_id": "sports-1",
            "token_id": "sports-1-yes",
            "slug": "sports-1",
            "category": "sports",
            "timestamp": "2026-03-23T12:05:00Z",
            "resolution_time": "2026-03-23T16:00:00Z",
            "best_bid_yes": 0.59,
            "best_ask_yes": 0.6,
            "best_bid_no": 0.4,
            "best_ask_no": 0.41,
            "last_traded_price": 0.595,
            "metadata": {
                "model_yes_probability": "0.68",
                "start_time": "2026-03-23T14:00:00Z",
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
