from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.sports.phase1.auto_experiments import (
    _promotion_decision,
    _promotion_reason,
    _select_winner,
    _winner_reason,
)


def test_select_sports_winner_prefers_lower_loss_when_readiness_is_tied() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        recommended_action="proceed",
        readiness_score=0.8,
        total_profit_loss=0.7,
        target_alignment_score=0,
        focus="baseline",
        profit_focus="selection",
        loss_ranking=("selection", "pricing", "execution"),
        selection_loss=0.35,
        pricing_loss=0.2,
        execution_loss=0.15,
    )
    candidate = SimpleNamespace(
        variant_name="selection_higher_edge_gate",
        recommended_action="proceed",
        readiness_score=0.8,
        total_profit_loss=0.5,
        target_alignment_score=2,
        focus="selection",
        profit_focus="selection",
        loss_ranking=("selection", "execution", "pricing"),
        selection_loss=0.2,
        pricing_loss=0.18,
        execution_loss=0.12,
    )

    winner = _select_winner(baseline=baseline, candidates=(candidate,))

    assert winner.variant_name == "selection_higher_edge_gate"
    assert _winner_reason(winner=winner, baseline=baseline) == "candidate improved targeted sports loss components by 0.1500"


def test_sports_promotion_decision_promotes_clear_winner() -> None:
    baseline = SimpleNamespace(
        variant_name="baseline",
        recommended_action="proceed",
        readiness_score=0.75,
        total_profit_loss=0.7,
        target_alignment_score=0,
        focus="baseline",
        profit_focus="selection",
        loss_ranking=("selection", "pricing", "execution"),
        selection_loss=0.4,
        pricing_loss=0.2,
        execution_loss=0.1,
    )
    candidate = SimpleNamespace(
        variant_name="selection_higher_edge_gate",
        recommended_action="proceed",
        readiness_score=0.82,
        total_profit_loss=0.5,
        target_alignment_score=2,
        focus="selection",
        profit_focus="selection",
        loss_ranking=("selection", "pricing", "execution"),
        selection_loss=0.22,
        pricing_loss=0.18,
        execution_loss=0.1,
    )

    decision = _promotion_decision(winner=candidate, baseline=baseline, candidates=(candidate,))

    assert decision == "promote_candidate"
    assert _promotion_reason(winner=candidate, baseline=baseline, candidates=(candidate,)) == "winner clears current sports promotion conditions over baseline"
