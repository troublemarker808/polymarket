from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.weather.phase1.auto_experiments import (
    _promotion_decision,
    _promotion_reason,
    _select_winner,
    _winner_reason,
)


def test_select_weather_winner_prefers_higher_readiness() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        recommended_action="proceed",
        readiness_score=0.76,
        total_profit_loss=0.6,
        target_alignment_score=0,
        focus="baseline",
        profit_focus="settlement",
        loss_ranking=("settlement", "selection", "execution"),
        selection_loss=0.15,
        settlement_loss=0.3,
        execution_loss=0.15,
    )
    candidate = SimpleNamespace(
        variant_name="settlement_higher_strip_gate",
        recommended_action="proceed",
        readiness_score=0.83,
        total_profit_loss=0.6,
        target_alignment_score=2,
        focus="settlement",
        profit_focus="settlement",
        loss_ranking=("settlement", "selection", "execution"),
        selection_loss=0.15,
        settlement_loss=0.22,
        execution_loss=0.18,
    )

    winner = _select_winner(baseline=baseline, candidates=(candidate,))

    assert winner.variant_name == "settlement_higher_strip_gate"
    assert _winner_reason(winner=winner, baseline=baseline) == "candidate improved targeted weather loss components by 0.0800"


def test_weather_promotion_decision_collects_more_evidence_on_loss_regression() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        recommended_action="proceed",
        readiness_score=0.8,
        total_profit_loss=0.4,
        target_alignment_score=0,
        focus="baseline",
        profit_focus="execution",
        loss_ranking=("execution", "selection", "settlement"),
        selection_loss=0.1,
        settlement_loss=0.1,
        execution_loss=0.2,
    )
    candidate = SimpleNamespace(
        variant_name="execution_higher_edge_gate",
        recommended_action="proceed",
        readiness_score=0.84,
        total_profit_loss=0.5,
        target_alignment_score=1,
        focus="execution",
        profit_focus="execution",
        loss_ranking=("execution", "selection", "settlement"),
        selection_loss=0.12,
        settlement_loss=0.12,
        execution_loss=0.26,
    )

    decision = _promotion_decision(winner=candidate, baseline=baseline, candidates=(candidate,))

    assert decision == "collect_more_evidence"
    assert _promotion_reason(winner=candidate, baseline=baseline, candidates=(candidate,)) == "winner is promising but does not yet clear targeted weather loss-improvement conditions"
