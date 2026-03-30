from __future__ import annotations

from pm_bot.strategy_change_window import StrategyChangeWindow
from pm_bot.strategy_governance import StrategyGovernanceBoardStatus, StrategyGovernanceReport
from pm_bot.strategy_governance_decision import build_strategy_governance_decision


def test_build_strategy_governance_decision_reflects_report_and_window() -> None:
    report = StrategyGovernanceReport(
        overall_action="apply",
        overall_reason="ready for controlled application",
        next_step="apply candidates",
        apply_ready_boards=("crypto", "weather"),
        rollback_boards=(),
        boards=(
            StrategyGovernanceBoardStatus(
                board="crypto",
                next_working_preset="btc-fast",
                promotion_decision="promote_candidate",
                ready_to_apply=True,
                apply_mode="review_then_apply",
                applied=False,
                verification_decision=None,
                rollback_recommended=None,
                action="apply",
                reason="ready",
                warnings=(),
            ),
        ),
        warnings=(),
    )
    window = StrategyChangeWindow(
        window_action="apply",
        first_step="apply crypto",
        apply_order=("crypto", "weather"),
        rollback_order=(),
        observe_order=(),
        steps=("apply crypto change package in a controlled window",),
    )

    decision = build_strategy_governance_decision(report, window)

    assert decision.governance_action == "apply"
    assert decision.first_step == "apply crypto"
    assert decision.apply_ready_boards == ("crypto", "weather")
