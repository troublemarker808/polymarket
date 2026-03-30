from __future__ import annotations

from pm_bot.strategy_change_window import build_strategy_change_window
from pm_bot.strategy_governance import StrategyGovernanceBoardStatus, StrategyGovernanceReport


def test_build_strategy_change_window_prioritizes_rollbacks() -> None:
    report = StrategyGovernanceReport(
        overall_action="rollback",
        overall_reason="verification failed",
        next_step="rollback flagged boards",
        apply_ready_boards=("weather",),
        rollback_boards=("sports",),
        boards=(
            StrategyGovernanceBoardStatus(
                board="crypto",
                next_working_preset="btc-fast",
                promotion_decision="promote_candidate",
                ready_to_apply=True,
                apply_mode="review_then_apply",
                applied=True,
                verification_decision="pass",
                rollback_recommended=False,
                action="observe",
                reason="candidate verifies cleanly",
                warnings=(),
            ),
            StrategyGovernanceBoardStatus(
                board="sports",
                next_working_preset="nba-tight",
                promotion_decision="promote_candidate",
                ready_to_apply=True,
                apply_mode="review_then_apply",
                applied=True,
                verification_decision="rollback",
                rollback_recommended=True,
                action="rollback",
                reason="verification requires rollback",
                warnings=(),
            ),
            StrategyGovernanceBoardStatus(
                board="weather",
                next_working_preset="wx-strip",
                promotion_decision="promote_candidate",
                ready_to_apply=True,
                apply_mode="review_then_apply",
                applied=False,
                verification_decision=None,
                rollback_recommended=None,
                action="apply",
                reason="candidate is ready for controlled application",
                warnings=(),
            ),
        ),
        warnings=(),
    )

    window = build_strategy_change_window(report)

    assert window.window_action == "stabilize"
    assert window.first_step == "rollback sports"
    assert window.rollback_order == ("sports",)
    assert "hold remaining apply-ready boards" in " ".join(window.steps)


def test_build_strategy_change_window_stabilizes_quarantined_boards() -> None:
    report = StrategyGovernanceReport(
        overall_action="hold",
        overall_reason="sports quarantined",
        next_step="collect more evidence",
        apply_ready_boards=(),
        rollback_boards=(),
        boards=(
            StrategyGovernanceBoardStatus(
                board="sports",
                next_working_preset="nba-tight",
                promotion_decision="keep_current",
                ready_to_apply=False,
                apply_mode=None,
                applied=False,
                verification_decision=None,
                rollback_recommended=None,
                action="hold",
                reason="quarantined",
                warnings=(),
                strategy_state="quarantined",
            ),
        ),
        warnings=(),
    )

    window = build_strategy_change_window(report)

    assert window.window_action == "stabilize"
    assert window.first_step == "quarantine sports"
