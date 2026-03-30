"""Single-page operator view combining runtime, unified ops, and history."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import json
from pathlib import Path
from typing import Any, cast

from pm_bot.ops_control_panel import OpsControlPanel, build_ops_control_panel, format_ops_control_panel
from pm_bot.ops_followup import OpsFollowUpQueue, format_ops_followup_queue
from pm_bot.ops_history import OpsHistoryReport, format_ops_history_report
from pm_bot.ops_console import UnifiedOpsConsole, format_unified_ops_console
from pm_bot.runtime.state import DashboardState
from pm_bot.strategy_loop_decision import StrategyLoopDecision, format_strategy_loop_decision


@dataclass(slots=True, frozen=True)
class OpsOnePage:
    runtime_rendered: str
    console: UnifiedOpsConsole
    control_panel: OpsControlPanel
    history: OpsHistoryReport | None
    followup_queue: OpsFollowUpQueue | None
    strategy_loop_decision: StrategyLoopDecision | None
    strategy_cycle_package: dict[str, object] | None
    triage_action: str
    triage_reason: str


def build_ops_one_page(
    *,
    dashboard: DashboardState,
    runtime_rendered: str,
    console: UnifiedOpsConsole,
    history: OpsHistoryReport | None = None,
    followup_queue: OpsFollowUpQueue | None = None,
    strategy_loop_decision: StrategyLoopDecision | None = None,
    strategy_cycle_package: object | None = None,
) -> OpsOnePage:
    normalized_cycle_package = _normalize_strategy_cycle_package(strategy_cycle_package)
    triage_action, triage_reason = _triage_decision(
        console=console,
        followup_queue=followup_queue,
    )
    return OpsOnePage(
        runtime_rendered=runtime_rendered,
        console=console,
        control_panel=build_ops_control_panel(
            dashboard=dashboard,
            runtime_rendered=runtime_rendered,
            console=console,
            history=history,
            strategy_loop_decision=strategy_loop_decision,
            strategy_cycle_package=normalized_cycle_package,
        ),
        history=history,
        followup_queue=followup_queue,
        strategy_loop_decision=strategy_loop_decision,
        strategy_cycle_package=normalized_cycle_package,
        triage_action=triage_action,
        triage_reason=triage_reason,
    )


def format_ops_one_page(page: OpsOnePage) -> str:
    lines = [
        "# Ops One Page",
        "",
        "## Runtime",
        "",
        f"triage_action={page.triage_action}",
        f"triage_reason={page.triage_reason}",
        "",
        "```text",
        page.runtime_rendered,
        "```",
        "",
        "## Control Panel",
        "",
        "```text",
        format_ops_control_panel(page.control_panel),
        "```",
        "",
        "## Unified Ops",
        "",
        format_unified_ops_console(page.console).strip(),
    ]
    if page.history is not None:
        lines.extend(
            [
                "",
                "## History",
                "",
                format_ops_history_report(page.history).strip(),
            ]
        )
    if page.strategy_loop_decision is not None:
        lines.extend(
            [
                "",
                "## Strategy Loop",
                "",
                format_strategy_loop_decision(page.strategy_loop_decision).strip(),
            ]
        )
    if page.strategy_cycle_package is not None:
        lines.extend(
            [
                "",
                "## Strategy Cycle",
                "",
                _format_strategy_cycle(page.strategy_cycle_package).strip(),
            ]
        )
    if page.followup_queue is not None:
        lines.extend(
            [
                "",
                "## Follow-Up",
                "",
                format_ops_followup_queue(page.followup_queue).strip(),
            ]
        )
    return "\n".join(lines) + "\n"


def write_ops_one_page(
    *,
    path: str | Path,
    page: OpsOnePage,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_ops_one_page(page), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(page), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_ops_one_page(path: str | Path) -> dict[str, object] | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _normalize(page: OpsOnePage) -> dict[str, object]:
    return {
        "runtime_rendered": page.runtime_rendered,
        "triage_action": page.triage_action,
        "triage_reason": page.triage_reason,
        "console": {
            "overall_action": page.console.overall_action,
            "overall_decision": page.console.overall_decision,
            "next_step": page.console.next_step,
            "rollback_target": page.console.rollback_target,
            "checklist_completion_ratio": page.console.checklist_completion_ratio,
            "blocker_count": page.console.blocker_count,
            "warning_count": page.console.warning_count,
            "boards": [asdict(board) for board in page.console.boards],
            "checklist": list(page.console.checklist),
            "escalation_actions": list(page.console.escalation_actions),
            "generated_reports": list(page.console.generated_reports),
        },
        "control_panel": {
            **asdict(page.control_panel),
            "boards": list(page.control_panel.boards),
            "escalation_actions": list(page.control_panel.escalation_actions),
            "checklist": list(page.control_panel.checklist),
            "recent_ops_actions": list(page.control_panel.recent_ops_actions),
        },
        "strategy_loop_decision": (
            asdict(page.strategy_loop_decision)
            if page.strategy_loop_decision is not None
            else None
        ),
        "strategy_cycle_package": page.strategy_cycle_package,
        "history": (
            {
                **asdict(page.history),
                "recent_actions": list(page.history.recent_actions),
                "board_review_counts": list(page.history.board_review_counts),
                "recent_runs": [
                    {
                        **asdict(run),
                        "board_actions": list(run.board_actions),
                    }
                    for run in page.history.recent_runs
                ],
            }
            if page.history is not None
            else None
        ),
        "followup_queue": (
            {
                "generated_from": page.followup_queue.generated_from,
                "overall_action": page.followup_queue.overall_action,
                "recommended_attention": page.followup_queue.recommended_attention,
                "item_count": page.followup_queue.item_count,
                "lifecycle": {
                    "open_items": list(page.followup_queue.lifecycle.open_items),
                    "escalating_items": list(page.followup_queue.lifecycle.escalating_items),
                    "resolved_items": list(page.followup_queue.lifecycle.resolved_items),
                },
                "items": [asdict(item) for item in page.followup_queue.items],
            }
            if page.followup_queue is not None
            else None
        ),
    }


def _triage_decision(
    *,
    console: UnifiedOpsConsole,
    followup_queue: OpsFollowUpQueue | None,
) -> tuple[str, str]:
    if console.overall_action == "pause":
        return "stabilize", f"overall_action={console.overall_action}"
    if followup_queue is not None:
        if followup_queue.lifecycle.escalating_items:
            return "escalate", f"escalating_issues={len(followup_queue.lifecycle.escalating_items)}"
        if followup_queue.lifecycle.open_items:
            return "monitor", f"open_issues={len(followup_queue.lifecycle.open_items)}"
        if followup_queue.lifecycle.resolved_items:
            return "monitor", f"resolved_issues={len(followup_queue.lifecycle.resolved_items)}"
    if console.overall_action == "review":
        return "monitor", f"overall_action={console.overall_action}"
    return "monitor", "steady_state"


def _normalize_strategy_cycle_package(payload: object | None) -> dict[str, object] | None:
    if payload is None:
        return None
    if is_dataclass(payload):
        normalized = asdict(cast(Any, payload))
        return normalized if isinstance(normalized, dict) else None
    if isinstance(payload, dict):
        return payload
    return None


def _format_strategy_cycle(payload: dict[str, object]) -> str:
    lines = [
        "# Strategy Cycle Package",
        "",
        f"- cycle_status: {payload.get('cycle_status', '')}",
        f"- cycle_reason: {payload.get('cycle_reason', '')}",
        f"- next_step: {payload.get('next_step', '')}",
        f"- strategy_mode: {payload.get('strategy_mode', '')}",
        f"- primary_board: {payload.get('primary_board', '') or ''}",
    ]
    return "\n".join(lines) + "\n"
