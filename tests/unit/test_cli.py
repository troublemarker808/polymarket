import runpy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from pm_bot.execution.paper_metrics import PaperExecutionMetrics
from pm_bot.cli import _load_underlying_states
from pm_bot.runtime.state import RuntimeState, runtime_state_to_dict


def test_module_cli_entrypoint_shows_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["pm_bot.cli", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("pm_bot.cli", run_name="__main__")

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Polymarket bot foundation CLI" in captured.out
    assert "run-paper-crypto-session" in captured.out
    assert "run-sync-crypto-session" in captured.out
    assert "check-paper-integrity" in captured.out
    assert "check-replay-determinism" in captured.out
    assert "phase1-replay" in captured.out
    assert "crypto-calibration-report" in captured.out
    assert "crypto-calibration-experiments" in captured.out
    assert "crypto-market-selection-report" in captured.out
    assert "crypto-phase2-replay" in captured.out
    assert "crypto-phase2-suite" in captured.out
    assert "run-paper-crypto-phase2-session" in captured.out
    assert "mine-fixed-windows" in captured.out
    assert "run-fixed-window-experiments" in captured.out
    assert "--board" in captured.out
    assert "--train-snapshot-path" in captured.out
    assert "--validation-snapshot-path" in captured.out
    assert "--holdout-snapshot-path" in captured.out
    assert "--candidate-set" in captured.out
    assert "btc_refined" in captured.out
    assert "--underlying-state-path" in captured.out
    assert "--exclude-bootstrap-from-limit" in captured.out
    assert "--shadow-state-path" in captured.out


def test_module_cli_check_paper_integrity(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    metrics_path, event_path, state_path = _write_integrity_artifacts(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "check-paper-integrity",
            "--metrics-path",
            str(metrics_path),
            "--event-path",
            str(event_path),
            "--state-path",
            str(state_path),
        ],
    )

    runpy.run_module("pm_bot.cli", run_name="__main__")

    captured = capsys.readouterr()
    assert "# Paper Integrity Report" in captured.out
    assert "- status: pass" in captured.out


def test_module_cli_check_replay_determinism(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    snapshot_path.write_text(
        "\n".join(
            [
                json.dumps(
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
                        "metadata": {"reference_yes_probability": "0.56", "no_token_id": "crypto-1-no"},
                    }
                ),
                json.dumps(
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
                        "metadata": {"model_yes_probability": "0.68", "start_time": "2026-03-23T14:00:00Z"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "check-replay-determinism",
            "--snapshot-path",
            str(snapshot_path),
            "--research-mode",
            "replay",
        ],
    )

    runpy.run_module("pm_bot.cli", run_name="__main__")

    captured = capsys.readouterr()
    assert "# Replay Determinism Report" in captured.out
    assert "- status: pass" in captured.out


def test_load_underlying_states_reads_multiple_underlyings(tmp_path: Path) -> None:
    payload_path = tmp_path / "underlying_states.json"
    payload_path.write_text(
        json.dumps(
            [
                {
                    "underlying": "ETH",
                    "as_of": "2026-03-27T15:14:00Z",
                    "spot_price": 1850.0,
                    "daily_return": -0.032,
                    "realized_volatility": 0.62,
                    "implied_volatility": 0.71,
                },
                {
                    "underlying": "BTC",
                    "as_of": "2026-03-27T15:15:00Z",
                    "spot_price": 79000.0,
                    "daily_return": -0.028,
                    "realized_volatility": 0.58,
                    "implied_volatility": 0.66,
                },
            ],
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    states = _load_underlying_states(str(payload_path))

    assert sorted(states) == ["BTC", "ETH"]
    assert states["ETH"].spot_price == pytest.approx(1850.0)
    assert states["BTC"].spot_price == pytest.approx(79000.0)


def _write_integrity_artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    started_at = datetime(2026, 3, 26, 5, 35, 0, tzinfo=UTC)
    snapshot_at = started_at + timedelta(minutes=1)
    fill_at = snapshot_at + timedelta(seconds=2)
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
                "fill_shares_delta": 5.0,
                "fill_notional_delta": 2.6,
                "fill_source": "taker",
                "mid_price": 0.51,
                "fill_age_ms": 2000.0,
                "updated_at": fill_at.isoformat(),
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

    state = RuntimeState(
        starting_equity=1000.0,
        day_starting_equity=1000.0,
        realized_pnl_today=0.1,
        orders_today=1,
        day_started_at=started_at,
        updated_at=close_at,
        last_data_success_at=snapshot_at,
    )

    metrics_path = tmp_path / "metrics.json"
    event_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "state.json"
    metrics_path.write_text(json.dumps(metrics.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
    event_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=True) for event in events) + "\n",
        encoding="utf-8",
    )
    state_path.write_text(json.dumps(runtime_state_to_dict(state), ensure_ascii=True, indent=2), encoding="utf-8")
    return metrics_path, event_path, state_path
