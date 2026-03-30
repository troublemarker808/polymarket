from __future__ import annotations

from pathlib import Path

from pm_bot.multi_board_ops import MultiBoardBoardStatus, MultiBoardOpsReport
from pm_bot.ops_followup import build_ops_followup_queue, format_ops_followup_queue, write_ops_followup_queue
from pm_bot.ops_history import OpsHistoryReport, OpsHistoryRun
from pm_bot.promotion_evidence import PromotionEvidenceEntry, PromotionEvidenceReport
from pm_bot.strategy_loop_decision import StrategyLoopDecision


def test_build_ops_followup_queue_turns_review_streak_into_queue_items(tmp_path: Path) -> None:
    queue = build_ops_followup_queue(
        latest_report=MultiBoardOpsReport(
            overall_action="review",
            overall_decision="review:crypto=review,sports=proceed,weather=proceed",
            next_step="review_cross_board_artifacts",
            rollback_target="crypto",
            escalation_actions=("review crypto board scorecard and refresh supporting evidence",),
            blockers=(),
            warnings=("crypto: evidence blocked",),
            boards=(
                MultiBoardBoardStatus("crypto", "review", "review:crypto", "crypto.md", False, 1, 0, ("evidence blocked",)),
            ),
        ),
        history=OpsHistoryReport(
            total_runs=2,
            latest_action="review",
            recent_actions=("review", "review"),
            review_streak=2,
            pause_streak=0,
            proceed_streak=0,
            recommended_attention="escalate_review_streak",
            board_review_counts=("crypto=2",),
            recurring_issues=("crypto: evidence blocked=2",),
            recent_runs=(
                OpsHistoryRun("2026-03-30", "run-001", "review", "review:crypto=review", "crypto", 0, 1, ("crypto=review",), (), ("crypto: evidence blocked",)),
                OpsHistoryRun("2026-03-29", "run-000", "review", "review:crypto=review", "crypto", 0, 1, ("crypto=review",), (), ("crypto: evidence blocked",)),
            ),
        ),
    )

    assert queue.item_count >= 2
    assert queue.recommended_attention == "escalate_review_streak"
    assert queue.lifecycle.escalating_items == ("crypto: evidence blocked",)
    assert "Ops Follow-Up Queue" in format_ops_followup_queue(queue)

    target = write_ops_followup_queue(path=tmp_path / "ops-followup-queue.md", queue=queue)
    assert target.exists()
    assert target.with_suffix(".json").exists()


def test_build_ops_followup_queue_includes_promotion_evidence_items() -> None:
    queue = build_ops_followup_queue(
        latest_report=MultiBoardOpsReport(
            overall_action="proceed",
            overall_decision="proceed:crypto=proceed,sports=proceed,weather=proceed",
            next_step="prepare_unified_ops_window",
            rollback_target=None,
            escalation_actions=("proceed with unified ops window and operator handoff",),
            blockers=(),
            warnings=(),
            boards=(
                MultiBoardBoardStatus("crypto", "proceed", "proceed:crypto", "crypto.md", True, 1, 1, ()),
            ),
        ),
        promotion_evidence=PromotionEvidenceReport(
            stage="small_live_stability",
            ready=False,
            session_count=2,
            blockers=("Not enough operator bundles for stability evidence (3 required).",),
            warnings=("Too many evidence windows ended in review.",),
            checks={"session_count": "blocked:2"},
            entries=(
                PromotionEvidenceEntry(
                    bundle_path="bundle-a.md",
                    session_label="a",
                    overall_action="review",
                    overall_decision="review",
                    next_step="review",
                    alert_count=0,
                    alert_codes=(),
                    orders_submitted=1,
                    orders_filled=1,
                    recommended_route_bias=None,
                ),
            ),
        ),
    )

    reasons = [item.reason for item in queue.items]
    assert any("Not enough operator bundles" in reason for reason in reasons)
    assert any("Too many evidence windows ended in review." in reason for reason in reasons)


def test_build_ops_followup_queue_tracks_resolved_recurring_issues() -> None:
    queue = build_ops_followup_queue(
        latest_report=MultiBoardOpsReport(
            overall_action="proceed",
            overall_decision="proceed:crypto=proceed,sports=proceed,weather=proceed",
            next_step="prepare_unified_ops_window",
            rollback_target=None,
            escalation_actions=("proceed with unified ops window and operator handoff",),
            blockers=(),
            warnings=(),
            boards=(
                MultiBoardBoardStatus("crypto", "proceed", "proceed:crypto", "crypto.md", True, 1, 1, ()),
            ),
        ),
        history=OpsHistoryReport(
            total_runs=3,
            latest_action="proceed",
            recent_actions=("proceed", "review", "review"),
            review_streak=0,
            pause_streak=0,
            proceed_streak=1,
            recommended_attention="collect_more_runs",
            board_review_counts=("crypto=2",),
            recurring_issues=("crypto: evidence blocked=2",),
            recent_runs=(
                OpsHistoryRun("2026-03-31", "run-002", "proceed", "proceed:crypto=proceed", None, 0, 0, ("crypto=proceed",), (), ()),
                OpsHistoryRun("2026-03-30", "run-001", "review", "review:crypto=review", "crypto", 0, 1, ("crypto=review",), (), ("crypto: evidence blocked",)),
                OpsHistoryRun("2026-03-29", "run-000", "review", "review:crypto=review", "crypto", 0, 1, ("crypto=review",), (), ("crypto: evidence blocked",)),
            ),
        ),
    )

    assert queue.lifecycle.resolved_items == ("crypto: evidence blocked",)


def test_build_ops_followup_queue_includes_strategy_loop_items() -> None:
    queue = build_ops_followup_queue(
        latest_report=MultiBoardOpsReport(
            overall_action="proceed",
            overall_decision="proceed:crypto=proceed,sports=proceed,weather=proceed",
            next_step="prepare_unified_ops_window",
            rollback_target=None,
            escalation_actions=("proceed with unified ops window and operator handoff",),
            blockers=(),
            warnings=(),
            boards=(
                MultiBoardBoardStatus("sports", "proceed", "proceed:sports", "sports.md", True, 1, 1, ()),
            ),
        ),
        strategy_loop_decision=StrategyLoopDecision(
            recommended_mode="stabilize",
            latest_action="stabilize",
            primary_board="sports",
            next_step="freeze new strategy promotions on repeatedly unstable boards and re-baseline them",
        ),
    )

    assert queue.recommended_attention == "stabilize_sports"
    assert any(item.owner == "sports" for item in queue.items)
