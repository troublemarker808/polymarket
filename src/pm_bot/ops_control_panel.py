"""Operator control-panel rendering for runtime plus multi-board ops state."""

from __future__ import annotations

from dataclasses import dataclass

from pm_bot.ops_history import OpsHistoryReport
from pm_bot.ops_console import UnifiedOpsConsole
from pm_bot.runtime.state import DashboardState
from pm_bot.strategy_loop_decision import StrategyLoopDecision


@dataclass(slots=True, frozen=True)
class OpsControlPanel:
    runtime_action: str
    runtime_decision: str
    triage_action: str
    triage_reason: str
    overall_action: str
    overall_decision: str
    next_step: str
    rollback_target: str | None
    blocker_count: int
    warning_count: int
    checklist_completion_ratio: float
    boards: tuple[str, ...]
    escalation_actions: tuple[str, ...]
    checklist: tuple[str, ...]
    latest_ops_action: str
    recent_ops_actions: tuple[str, ...]
    review_streak: int
    pause_streak: int
    recommended_attention: str
    recurring_issues: tuple[str, ...]
    strategy_mode: str
    strategy_primary_board: str
    strategy_next_step: str
    strategy_cycle_status: str
    strategy_cycle_reason: str
    strategy_cycle_next_step: str


def build_ops_control_panel(
    *,
    dashboard: DashboardState,
    runtime_rendered: str,
    console: UnifiedOpsConsole,
    history: OpsHistoryReport | None = None,
    strategy_loop_decision: StrategyLoopDecision | None = None,
    strategy_cycle_package: dict[str, object] | None = None,
) -> OpsControlPanel:
    runtime_action = _line_value(runtime_rendered, "risk_action")
    runtime_decision = _line_value(runtime_rendered, "risk_decision")
    triage_action, triage_reason = _triage_summary(console=console, history=history)
    boards = tuple(
        f"{board.board}:action={board.action}:decision={board.decision}"
        for board in console.boards
    )
    return OpsControlPanel(
        runtime_action=runtime_action,
        runtime_decision=runtime_decision,
        triage_action=triage_action,
        triage_reason=triage_reason,
        overall_action=console.overall_action,
        overall_decision=console.overall_decision,
        next_step=console.next_step,
        rollback_target=console.rollback_target,
        blocker_count=console.blocker_count,
        warning_count=console.warning_count,
        checklist_completion_ratio=console.checklist_completion_ratio,
        boards=boards,
        escalation_actions=console.escalation_actions,
        checklist=console.checklist,
        latest_ops_action=history.latest_action if history is not None else "",
        recent_ops_actions=history.recent_actions if history is not None else (),
        review_streak=history.review_streak if history is not None else 0,
        pause_streak=history.pause_streak if history is not None else 0,
        recommended_attention=history.recommended_attention if history is not None else "",
        recurring_issues=history.recurring_issues if history is not None else (),
        strategy_mode=(strategy_loop_decision.recommended_mode if strategy_loop_decision is not None else ""),
        strategy_primary_board=(strategy_loop_decision.primary_board or "" if strategy_loop_decision is not None else ""),
        strategy_next_step=(strategy_loop_decision.next_step if strategy_loop_decision is not None else ""),
        strategy_cycle_status=_dict_value(strategy_cycle_package, "cycle_status"),
        strategy_cycle_reason=_dict_value(strategy_cycle_package, "cycle_reason"),
        strategy_cycle_next_step=_dict_value(strategy_cycle_package, "next_step"),
    )


def format_ops_control_panel(panel: OpsControlPanel) -> str:
    lines = [
        "ops_control_panel",
        f"runtime_action={panel.runtime_action}",
        f"runtime_decision={panel.runtime_decision}",
        f"triage_action={panel.triage_action}",
        f"triage_reason={panel.triage_reason}",
        f"overall_action={panel.overall_action}",
        f"overall_decision={panel.overall_decision}",
        f"next_step={panel.next_step}",
        f"rollback_target={panel.rollback_target or ''}",
        f"blockers={panel.blocker_count}",
        f"warnings={panel.warning_count}",
        f"checklist_completion={panel.checklist_completion_ratio:.2f}",
        f"latest_ops_action={panel.latest_ops_action}",
        f"recent_ops_actions={','.join(panel.recent_ops_actions)}",
        f"review_streak={panel.review_streak}",
        f"pause_streak={panel.pause_streak}",
        f"recommended_attention={panel.recommended_attention}",
        f"strategy_mode={panel.strategy_mode}",
        f"strategy_primary_board={panel.strategy_primary_board}",
        f"strategy_next_step={panel.strategy_next_step}",
        f"strategy_cycle_status={panel.strategy_cycle_status}",
        f"strategy_cycle_reason={panel.strategy_cycle_reason}",
        f"strategy_cycle_next_step={panel.strategy_cycle_next_step}",
    ]
    lines.extend(f"board_status={item}" for item in panel.boards)
    lines.extend(f"recurring_issue={item}" for item in panel.recurring_issues[:5])
    lines.extend(f"escalation_action={item}" for item in panel.escalation_actions)
    lines.extend(f"checklist_item={item}" for item in panel.checklist[:5])
    return "\n".join(lines)


def _line_value(rendered: str, key: str) -> str:
    prefix = f"{key}="
    for line in rendered.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


def _triage_summary(
    *,
    console: UnifiedOpsConsole,
    history: OpsHistoryReport | None,
) -> tuple[str, str]:
    if console.overall_action == "pause":
        return "stabilize", f"overall_action={console.overall_action}"
    if history is not None and history.review_streak >= 2 and history.recurring_issues:
        return "escalate", f"recurring_issues={len(history.recurring_issues)}"
    return "monitor", f"overall_action={console.overall_action}"


def _dict_value(payload: dict[str, object] | None, key: str) -> str:
    if payload is None:
        return ""
    value = payload.get(key)
    return "" if value in (None, "") else str(value)
