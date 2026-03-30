from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategy_execute_window import StrategyExecutionWindowReport, StrategyBoardExecutionResult
from pm_bot.strategy_feedback_loop import build_strategy_feedback_loop_report
from pm_bot.strategy_governance import StrategyGovernanceBoardStatus, StrategyGovernanceReport


def test_build_strategy_feedback_loop_report_requests_verification_when_pending(tmp_path: Path) -> None:
    governance = StrategyGovernanceReport(
        overall_action="apply",
        overall_reason="ready",
        next_step="apply boards",
        apply_ready_boards=("crypto",),
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
    execution = StrategyExecutionWindowReport(
        window_action="apply",
        first_step="apply crypto",
        executed=True,
        halted=False,
        next_step="run verification",
        board_results=(
            StrategyBoardExecutionResult(
                board="crypto",
                planned_action="apply",
                executed_action="apply",
                success=True,
                output_config_path="crypto.applied.toml",
                blockers=(),
                notes=(),
            ),
        ),
    )

    report = build_strategy_feedback_loop_report(
        governance_report=governance,
        execution_report=execution,
    )

    assert report.overall_loop_action == "verify"
    assert report.boards[0].loop_action == "verify"


def test_build_strategy_feedback_loop_report_stabilizes_on_failed_verification(tmp_path: Path) -> None:
    sports_verify = tmp_path / "sports-verify.json"
    sports_verify.write_text(
        json.dumps({"verification_decision": "rollback"}, ensure_ascii=True),
        encoding="utf-8",
    )
    governance = StrategyGovernanceReport(
        overall_action="rollback",
        overall_reason="verification failed",
        next_step="rollback sports",
        apply_ready_boards=(),
        rollback_boards=("sports",),
        boards=(
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
                reason="failed verify",
                warnings=(),
            ),
        ),
        warnings=(),
    )
    execution = StrategyExecutionWindowReport(
        window_action="stabilize",
        first_step="rollback sports",
        executed=True,
        halted=False,
        next_step="re-run verify",
        board_results=(
            StrategyBoardExecutionResult(
                board="sports",
                planned_action="rollback",
                executed_action="rollback",
                success=True,
                output_config_path="sports.rollback.toml",
                blockers=(),
                notes=(),
            ),
        ),
    )

    report = build_strategy_feedback_loop_report(
        governance_report=governance,
        execution_report=execution,
        sports_verify_path=sports_verify,
    )

    assert report.overall_loop_action == "stabilize"
    assert report.boards[0].loop_action == "stabilize"


def test_build_strategy_feedback_loop_report_learns_on_degraded_hold_board() -> None:
    governance = StrategyGovernanceReport(
        overall_action="hold",
        overall_reason="degraded board",
        next_step="collect more evidence",
        apply_ready_boards=(),
        rollback_boards=(),
        boards=(
            StrategyGovernanceBoardStatus(
                board="weather",
                next_working_preset="wx-strip",
                promotion_decision="keep_current",
                ready_to_apply=False,
                apply_mode=None,
                applied=False,
                verification_decision=None,
                rollback_recommended=None,
                action="hold",
                reason="degraded",
                warnings=(),
                strategy_state="degraded",
            ),
        ),
        warnings=(),
    )
    execution = StrategyExecutionWindowReport(
        window_action="hold",
        first_step="collect more evidence",
        executed=False,
        halted=False,
        next_step="rerun experiments",
        board_results=(),
    )

    report = build_strategy_feedback_loop_report(
        governance_report=governance,
        execution_report=execution,
    )

    assert report.overall_loop_action == "learn"
    assert report.boards[0].loop_action == "learn"
