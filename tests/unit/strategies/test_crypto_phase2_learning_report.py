from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.crypto.phase2.learning_report import (
    build_crypto_phase2_learning_report,
    format_crypto_phase2_learning_report,
)


def test_build_crypto_phase2_learning_report_summarizes_recurring_focus(tmp_path: Path) -> None:
    suite_a = tmp_path / "suite-a.json"
    suite_b = tmp_path / "suite-b.json"
    suite_c = tmp_path / "suite-c.json"
    suite_a.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "profit_focus": "execution",
                    "tuning_priority": "execution",
                    "selection_loss": 0.1,
                    "pricing_loss": 0.1,
                    "execution_loss": 0.4,
                    "exit_loss": 0.2,
                    "sizing_loss": 0.15,
                    "edge_capture_ratio": 0.42,
                    "average_signal_edge_bps": 120.0,
                    "average_adverse_fill_bps": 54.0,
                    "pnl_per_notional": -0.012,
                    "average_trade_expected_edge_bps": 120.0,
                    "average_trade_execution_drag_bps": 26.0,
                    "average_trade_realized_pnl_bps": -14.0,
                    "average_fusion_observed_gap_bps": 165.0,
                    "average_barrier_surface_disagreement_bps": 90.0,
                    "average_win_trade_pnl": 0.08,
                    "average_loss_trade_pnl": -0.15,
                    "average_submitted_notional": 5.2,
                    "large_notional_share": 0.42,
                    "dominant_exit_reason": "stop_loss",
                    "stop_loss_exit_share": 0.36,
                    "passive_cleanup_exit_share": 0.22,
                    "exit_family_balance_score": 0.62,
                    "small_bucket_pnl_per_notional": 0.012,
                    "medium_bucket_pnl_per_notional": -0.004,
                    "large_bucket_pnl_per_notional": -0.022,
                    "tuning_actions": [
                        "reduce maker_quote_ttl_seconds or increase maker_aggressiveness for the active preset",
                    ],
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    suite_b.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "profit_focus": "execution",
                    "tuning_priority": "execution",
                    "selection_loss": 0.12,
                    "pricing_loss": 0.09,
                    "execution_loss": 0.35,
                    "exit_loss": 0.18,
                    "sizing_loss": 0.14,
                    "edge_capture_ratio": 0.48,
                    "average_signal_edge_bps": 110.0,
                    "average_adverse_fill_bps": 46.0,
                    "pnl_per_notional": -0.008,
                    "average_trade_expected_edge_bps": 110.0,
                    "average_trade_execution_drag_bps": 22.0,
                    "average_trade_realized_pnl_bps": -10.0,
                    "average_fusion_observed_gap_bps": 150.0,
                    "average_barrier_surface_disagreement_bps": 84.0,
                    "average_win_trade_pnl": 0.07,
                    "average_loss_trade_pnl": -0.13,
                    "average_submitted_notional": 5.1,
                    "large_notional_share": 0.38,
                    "dominant_exit_reason": "stop_loss",
                    "stop_loss_exit_share": 0.31,
                    "passive_cleanup_exit_share": 0.28,
                    "exit_family_balance_score": 0.58,
                    "small_bucket_pnl_per_notional": 0.01,
                    "medium_bucket_pnl_per_notional": -0.002,
                    "large_bucket_pnl_per_notional": -0.018,
                    "tuning_actions": [
                        "reduce maker_quote_ttl_seconds or increase maker_aggressiveness for the active preset",
                        "lower taker_urgency_threshold for families that miss too many fills",
                    ],
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    suite_c.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "profit_focus": "sizing",
                    "tuning_priority": "sizing",
                    "selection_loss": 0.14,
                    "pricing_loss": 0.11,
                    "execution_loss": 0.3,
                    "exit_loss": 0.16,
                    "sizing_loss": 0.2,
                    "edge_capture_ratio": 0.55,
                    "average_signal_edge_bps": 95.0,
                    "average_adverse_fill_bps": 42.0,
                    "pnl_per_notional": -0.004,
                    "average_trade_expected_edge_bps": 95.0,
                    "average_trade_execution_drag_bps": 18.0,
                    "average_trade_realized_pnl_bps": -6.0,
                    "average_fusion_observed_gap_bps": 135.0,
                    "average_barrier_surface_disagreement_bps": 70.0,
                    "average_win_trade_pnl": 0.06,
                    "average_loss_trade_pnl": -0.11,
                    "average_submitted_notional": 4.9,
                    "large_notional_share": 0.31,
                    "dominant_exit_reason": "aging_exit",
                    "stop_loss_exit_share": 0.18,
                    "passive_cleanup_exit_share": 0.41,
                    "exit_family_balance_score": 0.46,
                    "small_bucket_pnl_per_notional": 0.008,
                    "medium_bucket_pnl_per_notional": -0.001,
                    "large_bucket_pnl_per_notional": -0.015,
                    "tuning_actions": [
                        "reduce default_notional for families with negative average trade pnl",
                    ],
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_crypto_phase2_learning_report(
        suite_paths=[suite_a, suite_b, suite_c],
    )

    assert report.run_count == 3
    assert report.recurring_profit_focuses == ("execution",)
    assert report.recurring_tuning_priorities == ("execution",)
    assert report.recommended_next_experiment == "execution"
    assert report.recurring_loss_ranking[0] == "execution"
    assert report.average_component_losses["execution"] > report.average_component_losses["pricing"]
    assert report.average_edge_capture_ratio < 0.5
    assert report.average_pnl_per_notional < 0.0
    assert report.average_trade_execution_drag_bps > 0.0
    assert report.average_trade_realized_pnl_bps < 0.0
    assert report.average_fusion_observed_gap_bps > 100.0
    assert report.average_loss_trade_pnl < 0.0
    assert report.average_large_notional_share >= 0.3
    assert report.dominant_exit_reason in {"stop_loss", "aging_exit"}
    assert report.average_stop_loss_exit_share > 0.0
    assert report.average_passive_cleanup_exit_share > 0.0
    rendered = format_crypto_phase2_learning_report(report)
    assert "recommended_next_experiment: execution" in rendered
    assert "recurring_loss_ranking: execution" in rendered
    assert "average_edge_capture_ratio:" in rendered
    assert "average_trade_execution_drag_bps:" in rendered
    assert "average_trade_realized_pnl_bps:" in rendered
    assert "average_fusion_observed_gap_bps:" in rendered
    assert "average_loss_trade_pnl:" in rendered
    assert "average_large_notional_share:" in rendered
    assert "average_stop_loss_exit_share:" in rendered
    assert "average_passive_cleanup_exit_share:" in rendered
    assert "reduce maker_quote_ttl_seconds" in rendered
