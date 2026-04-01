from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase2.suite import run_crypto_phase2_suite


def test_run_crypto_phase2_suite_writes_selection_and_replay_artifacts(tmp_path: Path) -> None:
    result = asyncio.run(
        run_crypto_phase2_suite(
            snapshot_path=Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"),
            underlying_states={
                "BTC": build_underlying_state(
                    underlying="BTC",
                    as_of=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
                    spot_price=79000.0,
                    daily_return=-0.028,
                    realized_volatility=0.58,
                    implied_volatility=0.66,
                )
            },
            output_dir=tmp_path / "crypto-suite",
            run_id="crypto-suite-test",
        )
    )

    suite_json = tmp_path / "crypto-suite" / "suite.json"
    suite_md = tmp_path / "crypto-suite" / "suite.md"
    final_scorecard_md = tmp_path / "crypto-suite" / "final_scorecard.md"
    final_scorecard_json = tmp_path / "crypto-suite" / "final_scorecard.json"
    selection_summary = tmp_path / "crypto-suite" / "selection" / "summary.md"
    unfiltered_metrics = tmp_path / "crypto-suite" / "replay-unfiltered" / "metrics.json"
    filtered_metrics = tmp_path / "crypto-suite" / "replay-filtered" / "metrics.json"

    assert suite_json.exists()
    assert suite_md.exists()
    assert final_scorecard_md.exists()
    assert final_scorecard_json.exists()
    assert selection_summary.exists()
    assert unfiltered_metrics.exists()
    assert filtered_metrics.exists()

    payload = json.loads(suite_json.read_text(encoding="utf-8"))
    assert payload["selection_blocked_series_keys"] == []
    assert payload["filtered_replay"]["signals_generated"] >= 0
    assert payload["unfiltered_replay"]["signals_generated"] >= 0
    assert payload["final_scorecard"]["recommended_action"] in {"proceed", "review", "pause"}
    assert payload["final_scorecard"]["route_stage_acceptance_decision"] in {"proceed", "review", "pause"}
    assert isinstance(payload["final_scorecard"]["route_stage_failed_stages"], list)
    assert isinstance(payload["final_scorecard"]["route_stage_statuses"], dict)
    assert isinstance(payload["final_scorecard"]["route_stage_blockers"], dict)
    assert "dominant_route_stage_blocker" in payload["final_scorecard"]
    assert "next_constrained_action" in payload["final_scorecard"]
    assert payload["final_scorecard"]["promotion_decision"] in {"proceed", "review", "pause"}
    assert payload["final_scorecard"]["promotion_stage_label"] in {"paper available", "shadow validation"}
    assert isinstance(payload["final_scorecard"]["promotion_blocking_reasons"], list)
    assert payload["final_scorecard"]["profit_focus"] in {"selection", "pricing", "execution", "exit", "sizing"}
    assert payload["final_scorecard"]["tuning_priority"] in {"selection", "pricing", "execution", "exit", "sizing"}
    assert 0.0 <= payload["final_scorecard"]["selection_quality_score"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["pricing_quality_score"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["execution_quality_score"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["exit_quality_score"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["sizing_quality_score"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["selection_loss"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["pricing_loss"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["execution_loss"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["exit_loss"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["sizing_loss"] <= 1.0
    assert 0.0 <= payload["final_scorecard"]["total_profit_loss"] <= 5.0
    assert isinstance(payload["final_scorecard"]["tuning_actions"], list)
    assert "component_reasons" in payload["final_scorecard"]
    assert result.selection_blocked_series_keys == ()
    assert 0.0 <= payload["filtered_replay"]["maker_fill_rate"] <= 1.0
    assert 0.0 <= payload["filtered_replay"]["taker_fill_rate"] <= 1.0
    assert 0.0 <= payload["filtered_replay"]["expiration_rate"] <= 1.0
    assert 0.0 <= payload["filtered_replay"]["stop_out_rate"] <= 1.0
    assert payload["filtered_replay"]["submitted_notional"] >= 0.0
    assert payload["filtered_replay"]["average_signal_edge_bps"] >= 0.0
    assert payload["filtered_replay"]["average_adverse_fill_bps"] >= 0.0
    assert payload["filtered_replay"]["expected_edge_capture_bps"] >= 0.0
    assert payload["filtered_replay"]["edge_capture_ratio"] >= 0.0
    assert 0.0 <= payload["filtered_replay"]["winning_trade_rate"] <= 1.0
    assert "average_win_trade_pnl" in payload["filtered_replay"]
    assert "average_loss_trade_pnl" in payload["filtered_replay"]
    assert "average_submitted_notional" in payload["filtered_replay"]
    assert "large_notional_share" in payload["filtered_replay"]
    assert "dominant_exit_reason" in payload["filtered_replay"]
    assert "stop_loss_exit_share" in payload["filtered_replay"]
    assert "passive_cleanup_exit_share" in payload["filtered_replay"]
    assert "average_signal_edge_bps" in payload["final_scorecard"]
    assert "average_adverse_fill_bps" in payload["final_scorecard"]
    assert "expected_edge_capture_bps" in payload["final_scorecard"]
    assert "edge_capture_ratio" in payload["final_scorecard"]
    assert "average_trade_expected_edge_bps" in payload["filtered_replay"]
    assert "average_trade_execution_drag_bps" in payload["filtered_replay"]
    assert "average_trade_realized_pnl_bps" in payload["filtered_replay"]
    assert "average_barrier_observed_gap_bps" in payload["filtered_replay"]
    assert "average_surface_observed_gap_bps" in payload["filtered_replay"]
    assert "average_fusion_observed_gap_bps" in payload["filtered_replay"]
    assert "average_barrier_surface_disagreement_bps" in payload["filtered_replay"]
    assert "submitted_notional" in payload["final_scorecard"]
    assert "pnl_per_notional" in payload["final_scorecard"]
    assert "average_win_trade_pnl" in payload["final_scorecard"]
    assert "average_loss_trade_pnl" in payload["final_scorecard"]
    assert "average_submitted_notional" in payload["final_scorecard"]
    assert "large_notional_share" in payload["final_scorecard"]
    assert "dominant_exit_reason" in payload["final_scorecard"]
    assert "stop_loss_exit_share" in payload["final_scorecard"]
    assert "passive_cleanup_exit_share" in payload["final_scorecard"]
    assert "exit_family_balance_score" in payload["final_scorecard"]
    assert "small_bucket_pnl_per_notional" in payload["final_scorecard"]
    assert "medium_bucket_pnl_per_notional" in payload["final_scorecard"]
    assert "large_bucket_pnl_per_notional" in payload["final_scorecard"]
    assert "average_fusion_observed_gap_bps" in payload["final_scorecard"]
    assert "average_barrier_surface_disagreement_bps" in payload["final_scorecard"]
    assert "top_loss_trades" in payload["filtered_replay"]
    assert "top_loss_market_breakdown" in payload["filtered_replay"]
    assert "top_loss_signature_breakdown" in payload["filtered_replay"]
    assert "top_loss_trades" in payload["final_scorecard"]
    assert "top_loss_market_breakdown" in payload["final_scorecard"]
    assert "top_loss_signature_breakdown" in payload["final_scorecard"]

    final_rendered = final_scorecard_md.read_text(encoding="utf-8")
    assert "## Profit Components" in final_rendered
    assert "## Route Stage Gates" in final_rendered
    assert "next_constrained_action:" in final_rendered
    assert "## Profit Loss Decomposition" in final_rendered
    assert "## Top Loss Attribution" in final_rendered
    assert "## Tuning Actions" in final_rendered
    assert "- profit_focus:" in final_rendered
