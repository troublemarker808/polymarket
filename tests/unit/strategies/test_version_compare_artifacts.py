from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.crypto.phase2.version_compare import build_crypto_phase2_version_comparison
from pm_bot.strategies.sports.phase1.version_compare import build_sports_version_comparison
from pm_bot.strategies.weather.phase1.version_compare import build_weather_version_comparison


def test_build_crypto_version_comparison_marks_candidate_when_evidence_is_ready() -> None:
    report = SimpleNamespace(
        promotion_decision="promote_candidate",
        baseline=SimpleNamespace(
            variant_name="baseline",
            recommended_action="proceed",
            readiness_score=0.72,
            total_profit_loss=1.1,
            filtered_pnl=0.12,
            edge_capture_ratio=0.42,
            pnl_per_notional=0.01,
            average_loss_trade_pnl=-0.14,
            large_notional_share=0.38,
            average_trade_execution_drag_bps=22.0,
            average_trade_realized_pnl_bps=-8.0,
            exit_family_balance_score=0.52,
            large_bucket_pnl_per_notional=-0.01,
        ),
        winner=SimpleNamespace(
            variant_name="execution_exit_guard",
            recommended_action="proceed",
            readiness_score=0.8,
            total_profit_loss=0.9,
            filtered_pnl=0.18,
            targeted_loss_improvement=0.07,
            edge_capture_ratio=0.57,
            pnl_per_notional=0.03,
            average_loss_trade_pnl=-0.08,
            large_notional_share=0.24,
            average_trade_execution_drag_bps=12.0,
            average_trade_realized_pnl_bps=6.0,
            exit_family_balance_score=0.68,
            large_bucket_pnl_per_notional=0.012,
        ),
    )
    evidence = SimpleNamespace(ready_to_apply=True)

    comparison = build_crypto_phase2_version_comparison(report=report, evidence=evidence)

    assert comparison.recommendation == "promote"
    assert comparison.strategy_state == "candidate"
    assert comparison.metric_wins["targeted_loss"] == "execution_exit_guard"
    assert comparison.metric_wins["edge_capture"] == "execution_exit_guard"
    assert comparison.metric_wins["exit_asymmetry"] == "execution_exit_guard"
    assert comparison.metric_wins["size_concentration"] == "execution_exit_guard"
    assert comparison.metric_wins["trade_execution_drag"] == "execution_exit_guard"
    assert comparison.metric_wins["trade_realized_pnl_bps"] == "execution_exit_guard"
    assert comparison.edge_capture_delta > 0
    assert comparison.average_loss_trade_pnl_delta > 0


def test_build_sports_version_comparison_marks_degraded_without_enough_targeted_improvement() -> None:
    report = SimpleNamespace(
        promotion_decision="collect_more_evidence",
        baseline=SimpleNamespace(
            variant_name="baseline",
            recommended_action="proceed",
            readiness_score=0.78,
            total_profit_loss=0.9,
            average_clv_bps=4.0,
            actionable_markets=8,
            blocked_markets=2,
        ),
        winner=SimpleNamespace(
            variant_name="selection_pricing_combo",
            recommended_action="proceed",
            readiness_score=0.8,
            total_profit_loss=0.88,
            average_clv_bps=3.5,
            actionable_markets=8,
            blocked_markets=2,
            targeted_loss_improvement=0.01,
        ),
    )

    comparison = build_sports_version_comparison(report=report)

    assert comparison.recommendation == "quarantine"
    assert comparison.strategy_state == "quarantined"


def test_build_weather_version_comparison_marks_quarantine_when_pause_persists() -> None:
    report = SimpleNamespace(
        promotion_decision="keep_baseline",
        baseline=SimpleNamespace(
            variant_name="baseline",
            recommended_action="pause",
            readiness_score=0.4,
            total_profit_loss=1.3,
            average_monotonicity_gap_bps=120.0,
            actionable_markets=7,
            blocked_markets=3,
        ),
        winner=SimpleNamespace(
            variant_name="baseline",
            recommended_action="pause",
            readiness_score=0.4,
            total_profit_loss=1.3,
            average_monotonicity_gap_bps=120.0,
            actionable_markets=7,
            blocked_markets=3,
            targeted_loss_improvement=0.0,
        ),
    )

    comparison = build_weather_version_comparison(report=report)

    assert comparison.recommendation == "quarantine"
    assert comparison.strategy_state == "quarantined"
