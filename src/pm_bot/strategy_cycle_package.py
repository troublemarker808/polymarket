"""Single-package artifact for a full multi-board strategy cycle."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategy_execute_window import StrategyExecutionWindowReport
from pm_bot.strategy_feedback_loop import StrategyFeedbackLoopReport
from pm_bot.strategy_governance import StrategyGovernanceReport
from pm_bot.strategy_governance_decision import StrategyGovernanceDecision
from pm_bot.strategy_loop_decision import StrategyLoopDecision
from pm_bot.strategy_loop_history import StrategyLoopHistoryReport


@dataclass(slots=True, frozen=True)
class StrategyCyclePackage:
    cycle_status: str
    cycle_reason: str
    next_step: str
    governance_action: str | None
    window_action: str | None
    loop_action: str | None
    strategy_mode: str
    primary_board: str | None
    governance_report: StrategyGovernanceReport | None
    governance_decision: StrategyGovernanceDecision | None
    execution_report: StrategyExecutionWindowReport | None
    feedback_report: StrategyFeedbackLoopReport | None
    history_report: StrategyLoopHistoryReport
    loop_decision: StrategyLoopDecision


def build_strategy_cycle_package(
    *,
    governance_report: StrategyGovernanceReport | None = None,
    governance_decision: StrategyGovernanceDecision | None = None,
    execution_report: StrategyExecutionWindowReport | None = None,
    feedback_report: StrategyFeedbackLoopReport | None = None,
    history_report: StrategyLoopHistoryReport,
    loop_decision: StrategyLoopDecision,
) -> StrategyCyclePackage:
    quarantined_boards = (
        tuple(board.board for board in governance_report.boards if board.strategy_state == "quarantined")
        if governance_report is not None
        else ()
    )
    degraded_boards = (
        tuple(board.board for board in governance_report.boards if board.strategy_state == "degraded")
        if governance_report is not None
        else ()
    )
    if quarantined_boards:
        cycle_status = "stabilize"
        cycle_reason = f"quarantined boards remain in the strategy cycle: {', '.join(quarantined_boards)}"
        next_step = "keep quarantined boards blocked, refresh research evidence, and only reopen promotion after clean version comparisons"
    elif (governance_report is not None and governance_report.rollback_boards) or (
        execution_report is not None and execution_report.halted
    ):
        cycle_status = "stabilize"
        cycle_reason = "strategy cycle contains rollback pressure or halted execution"
        next_step = "complete rollback and fresh verification before another promotion window"
    elif (
        feedback_report is not None
        and feedback_report.overall_loop_action == "verify"
    ) or loop_decision.recommended_mode == "verify":
        cycle_status = "verify"
        cycle_reason = "recent strategy applications still require verification closure"
        next_step = "finish verification reports and only then reopen promotion sequencing"
    elif (
        feedback_report is not None
        and feedback_report.overall_loop_action == "learn"
    ) or loop_decision.recommended_mode == "learn":
        cycle_status = "learn"
        cycle_reason = "current evidence still points to tuning and additional experimentation"
        next_step = "refresh experiments on the weakest board and regenerate candidate comparisons"
    elif degraded_boards:
        cycle_status = "learn"
        cycle_reason = f"degraded boards still need learning attention: {', '.join(degraded_boards)}"
        next_step = "keep degraded boards in the experiment queue and avoid applying new presets until version state improves"
    else:
        cycle_status = "advance"
        cycle_reason = "governance, execution, and long-horizon loop all currently support progression"
        next_step = "keep controlled promotion cadence and accumulate another evidence window"

    return StrategyCyclePackage(
        cycle_status=cycle_status,
        cycle_reason=cycle_reason,
        next_step=next_step,
        governance_action=(governance_report.overall_action if governance_report is not None else None),
        window_action=(execution_report.window_action if execution_report is not None else None),
        loop_action=(feedback_report.overall_loop_action if feedback_report is not None else None),
        strategy_mode=loop_decision.recommended_mode,
        primary_board=loop_decision.primary_board,
        governance_report=governance_report,
        governance_decision=governance_decision,
        execution_report=execution_report,
        feedback_report=feedback_report,
        history_report=history_report,
        loop_decision=loop_decision,
    )


def format_strategy_cycle_package(package: StrategyCyclePackage) -> str:
    lines = [
        "# Strategy Cycle Package",
        "",
        f"- cycle_status: {package.cycle_status}",
        f"- cycle_reason: {package.cycle_reason}",
        f"- next_step: {package.next_step}",
        f"- governance_action: {package.governance_action or ''}",
        f"- window_action: {package.window_action or ''}",
        f"- loop_action: {package.loop_action or ''}",
        f"- strategy_mode: {package.strategy_mode}",
        f"- primary_board: {package.primary_board or ''}",
        "",
        "## Board Summary",
        "",
    ]
    if package.governance_report is not None:
        for board in package.governance_report.boards:
            lines.append(
                "- "
                + f"{board.board}:action={board.action}:promotion={board.promotion_decision}:"
                + f"ready={str(board.ready_to_apply).lower()}:verify={board.verification_decision or 'none'}"
            )
    else:
        lines.append("- governance details unavailable in this package; using long-horizon strategy loop artifacts only")
    return "\n".join(lines) + "\n"


def write_strategy_cycle_package(
    *,
    path: str | Path,
    package: StrategyCyclePackage,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_cycle_package(package), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(package)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_strategy_cycle_package(path: str | Path) -> dict[str, object] | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
