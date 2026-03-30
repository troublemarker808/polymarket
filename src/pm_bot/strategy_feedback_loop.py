"""Feedback-loop summary after a controlled strategy execution window."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategy_execute_window import StrategyExecutionWindowReport
from pm_bot.strategy_governance import StrategyGovernanceReport


@dataclass(slots=True, frozen=True)
class StrategyFeedbackBoardStatus:
    board: str
    strategy_state: str
    execution_state: str
    verification_state: str
    loop_action: str
    reason: str


@dataclass(slots=True, frozen=True)
class StrategyFeedbackLoopReport:
    overall_loop_action: str
    overall_reason: str
    next_step: str
    boards: tuple[StrategyFeedbackBoardStatus, ...]


def build_strategy_feedback_loop_report(
    *,
    governance_report: StrategyGovernanceReport,
    execution_report: StrategyExecutionWindowReport,
    crypto_verify_path: str | Path | None = None,
    sports_verify_path: str | Path | None = None,
    weather_verify_path: str | Path | None = None,
) -> StrategyFeedbackLoopReport:
    execution_by_board = {item.board: item for item in execution_report.board_results}
    verify_payloads = {
        "crypto": _load_json(crypto_verify_path),
        "sports": _load_json(sports_verify_path),
        "weather": _load_json(weather_verify_path),
    }

    boards: list[StrategyFeedbackBoardStatus] = []
    for board in governance_report.boards:
        execution = execution_by_board.get(board.board)
        verification_state = str(verify_payloads[board.board].get("verification_decision", "pending"))
        execution_state = execution.executed_action if execution is not None else "pending"
        if board.strategy_state == "quarantined":
            loop_action = "stabilize"
            reason = "board remains quarantined and cannot re-enter the promotion cycle"
        elif board.strategy_state == "degraded" and board.action == "hold":
            loop_action = "learn"
            reason = "board remains degraded and should stay in the experiment queue"
        elif verification_state == "rollback":
            loop_action = "stabilize"
            reason = "verification failed after execution"
        elif execution_state == "apply" and verification_state == "pass":
            loop_action = "observe"
            reason = "candidate applied and verification passed"
        elif execution_state in {"apply", "rollback"} and verification_state == "pending":
            loop_action = "verify"
            reason = "execution finished and verification is still pending"
        elif board.action == "hold":
            loop_action = "learn"
            reason = "board still needs more evidence before the next attempt"
        else:
            loop_action = "observe"
            reason = "board remains in observation state"
        boards.append(
            StrategyFeedbackBoardStatus(
                board=board.board,
                strategy_state=board.strategy_state,
                execution_state=execution_state,
                verification_state=verification_state,
                loop_action=loop_action,
                reason=reason,
            )
        )

    if any(item.loop_action == "stabilize" for item in boards):
        overall_loop_action = "stabilize"
        overall_reason = "at least one board failed verification after execution"
        next_step = "rollback failed boards, refresh evidence, and reopen the next window only after re-verification"
    elif any(item.loop_action == "verify" for item in boards):
        overall_loop_action = "verify"
        overall_reason = "one or more boards finished execution without a completed verification result"
        next_step = "run the missing verification reports before taking another promotion step"
    elif any(item.loop_action == "learn" for item in boards):
        overall_loop_action = "learn"
        overall_reason = "one or more boards still need additional evidence before promotion"
        next_step = "collect another experiment window and refresh candidate comparisons"
    else:
        overall_loop_action = "observe"
        overall_reason = "all executed boards currently verify cleanly"
        next_step = "continue observation and accumulate another evidence window before the next promotion attempt"

    return StrategyFeedbackLoopReport(
        overall_loop_action=overall_loop_action,
        overall_reason=overall_reason,
        next_step=next_step,
        boards=tuple(boards),
    )


def format_strategy_feedback_loop_report(report: StrategyFeedbackLoopReport) -> str:
    lines = [
        "# Strategy Feedback Loop Report",
        "",
        f"- overall_loop_action: {report.overall_loop_action}",
        f"- overall_reason: {report.overall_reason}",
        f"- next_step: {report.next_step}",
        "",
        "## Boards",
        "",
    ]
    for board in report.boards:
        lines.append(
            "- "
            + f"{board.board}:execution={board.execution_state}:"
            + f"state={board.strategy_state}:"
            + f"verification={board.verification_state}:"
            + f"loop_action={board.loop_action}:"
            + f"reason={board.reason}"
        )
    return "\n".join(lines) + "\n"


def write_strategy_feedback_loop_report(
    *,
    path: str | Path,
    report: StrategyFeedbackLoopReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_feedback_loop_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(asdict(report), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}
