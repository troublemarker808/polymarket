from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.crypto.phase2.auto_experiments import (
    _promotion_decision,
    _promotion_reason,
    _select_winner,
    _winner_reason,
)


def test_select_winner_prefers_lower_loss_when_readiness_is_tied() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        focus="baseline",
        secondary_focus="execution",
        loss_ranking=("execution", "exit"),
        recommended_action="proceed",
        readiness_score=0.8,
        total_profit_loss=0.7,
        filtered_pnl=0.1,
        tuning_priority="execution",
        selection_loss=0.1,
        pricing_loss=0.1,
        execution_loss=0.4,
        exit_loss=0.2,
        sizing_loss=0.1,
        average_loss_trade_pnl=-0.14,
        large_notional_share=0.35,
        target_alignment_score=0,
        targeted_loss_improvement=0.0,
    )
    candidate = SimpleNamespace(
        variant_name="execution_faster_quotes",
        focus="execution",
        secondary_focus="exit",
        loss_ranking=("execution", "exit"),
        recommended_action="proceed",
        readiness_score=0.8,
        total_profit_loss=0.5,
        filtered_pnl=0.08,
        tuning_priority="execution",
        selection_loss=0.1,
        pricing_loss=0.1,
        execution_loss=0.18,
        exit_loss=0.12,
        sizing_loss=0.1,
        average_loss_trade_pnl=-0.06,
        large_notional_share=0.22,
        target_alignment_score=2,
        targeted_loss_improvement=0.15,
    )

    winner = _select_winner(baseline=baseline, candidates=(candidate,))

    assert winner.variant_name == "execution_faster_quotes"
    assert _winner_reason(winner=winner, baseline=baseline).startswith("candidate improved targeted loss components")


def test_promotion_decision_promotes_clear_winner() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        focus="baseline",
        secondary_focus="execution",
        loss_ranking=("execution", "exit"),
        recommended_action="proceed",
        readiness_score=0.75,
        total_profit_loss=0.7,
        filtered_pnl=0.08,
        tuning_priority="execution",
        selection_loss=0.1,
        pricing_loss=0.1,
        execution_loss=0.42,
        exit_loss=0.15,
        sizing_loss=0.1,
        average_loss_trade_pnl=-0.15,
        large_notional_share=0.37,
        target_alignment_score=0,
        targeted_loss_improvement=0.0,
    )
    candidate = SimpleNamespace(
        variant_name="execution_faster_quotes",
        focus="execution",
        secondary_focus="exit",
        loss_ranking=("execution", "exit"),
        recommended_action="proceed",
        readiness_score=0.82,
        total_profit_loss=0.5,
        filtered_pnl=0.12,
        tuning_priority="execution",
        selection_loss=0.1,
        pricing_loss=0.1,
        execution_loss=0.18,
        exit_loss=0.08,
        sizing_loss=0.1,
        average_loss_trade_pnl=-0.07,
        large_notional_share=0.24,
        target_alignment_score=2,
        targeted_loss_improvement=0.155,
    )

    decision = _promotion_decision(winner=candidate, baseline=baseline, candidates=(candidate,))

    assert decision == "promote_candidate"
    assert _promotion_reason(winner=candidate, baseline=baseline, candidates=(candidate,)) == "winner clears current promotion conditions over baseline"


def test_promotion_decision_collects_more_evidence_when_targeted_loss_does_not_improve() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        focus="baseline",
        secondary_focus="pricing",
        loss_ranking=("selection", "pricing"),
        recommended_action="proceed",
        readiness_score=0.8,
        total_profit_loss=0.45,
        filtered_pnl=0.11,
        tuning_priority="selection",
        selection_loss=0.2,
        pricing_loss=0.08,
        execution_loss=0.07,
        exit_loss=0.05,
        sizing_loss=0.05,
        average_loss_trade_pnl=-0.08,
        large_notional_share=0.19,
        target_alignment_score=0,
        targeted_loss_improvement=0.0,
    )
    candidate = SimpleNamespace(
        variant_name="selection_pricing_high_confidence",
        focus="selection+pricing",
        secondary_focus="pricing",
        loss_ranking=("selection", "pricing"),
        recommended_action="proceed",
        readiness_score=0.81,
        total_profit_loss=0.43,
        filtered_pnl=0.1,
        tuning_priority="selection",
        selection_loss=0.19,
        pricing_loss=0.08,
        execution_loss=0.06,
        exit_loss=0.05,
        sizing_loss=0.05,
        average_loss_trade_pnl=-0.09,
        large_notional_share=0.22,
        target_alignment_score=0,
        targeted_loss_improvement=0.01,
    )

    assert _promotion_decision(winner=candidate, baseline=baseline, candidates=(candidate,)) == "collect_more_evidence"
