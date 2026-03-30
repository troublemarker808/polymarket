"""Compact long-horizon decision artifact for strategy loop history."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.strategy_loop_history import StrategyLoopHistoryReport


@dataclass(slots=True, frozen=True)
class StrategyLoopDecision:
    recommended_mode: str
    latest_action: str
    primary_board: str | None
    next_step: str


def build_strategy_loop_decision(report: StrategyLoopHistoryReport) -> StrategyLoopDecision:
    primary_board: str | None = None
    if report.recurring_stabilize_boards:
        primary_board = report.recurring_stabilize_boards[0]
    elif report.recurring_learn_boards:
        primary_board = report.recurring_learn_boards[0]
    return StrategyLoopDecision(
        recommended_mode=report.recommended_mode,
        latest_action=report.latest_action,
        primary_board=primary_board,
        next_step=report.next_step,
    )


def format_strategy_loop_decision(decision: StrategyLoopDecision) -> str:
    lines = [
        "# Strategy Loop Decision",
        "",
        f"- recommended_mode: {decision.recommended_mode}",
        f"- latest_action: {decision.latest_action}",
        f"- primary_board: {decision.primary_board or ''}",
        f"- next_step: {decision.next_step}",
    ]
    return "\n".join(lines) + "\n"


def write_strategy_loop_decision(
    *,
    path: str | Path,
    decision: StrategyLoopDecision,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_loop_decision(decision), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(asdict(decision), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_strategy_loop_decision(path: str | Path) -> StrategyLoopDecision | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return StrategyLoopDecision(
        recommended_mode=str(payload.get("recommended_mode", "")),
        latest_action=str(payload.get("latest_action", "")),
        primary_board=(str(payload["primary_board"]) if payload.get("primary_board") not in (None, "") else None),
        next_step=str(payload.get("next_step", "")),
    )
