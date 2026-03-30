from __future__ import annotations

from pm_bot.strategy_loop_decision import build_strategy_loop_decision
from pm_bot.strategy_loop_history import StrategyLoopHistoryEntry, StrategyLoopHistoryReport


def test_build_strategy_loop_decision_prefers_recurring_stabilize_board() -> None:
    report = StrategyLoopHistoryReport(
        window_count=3,
        latest_action="stabilize",
        recurring_stabilize_boards=("sports",),
        recurring_learn_boards=("weather",),
        recommended_mode="stabilize",
        next_step="freeze unstable boards",
        entries=(
            StrategyLoopHistoryEntry(
                path="loop-a.json",
                overall_loop_action="stabilize",
                next_step="continue",
                board_actions={"sports": "stabilize"},
            ),
        ),
    )

    decision = build_strategy_loop_decision(report)

    assert decision.recommended_mode == "stabilize"
    assert decision.primary_board == "sports"
