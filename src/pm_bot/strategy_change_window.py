"""Controlled multi-board strategy change window planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.strategy_governance import StrategyGovernanceReport, load_strategy_governance_report


@dataclass(slots=True, frozen=True)
class StrategyChangeWindow:
    window_action: str
    first_step: str
    apply_order: tuple[str, ...]
    rollback_order: tuple[str, ...]
    observe_order: tuple[str, ...]
    steps: tuple[str, ...]


def build_strategy_change_window(report: StrategyGovernanceReport) -> StrategyChangeWindow:
    rollback_order = tuple(board.board for board in report.boards if board.action == "rollback")
    apply_order = tuple(board.board for board in report.boards if board.action == "apply")
    observe_order = tuple(board.board for board in report.boards if board.action == "observe")
    quarantined_boards = tuple(board.board for board in report.boards if board.strategy_state == "quarantined")
    degraded_hold_boards = tuple(
        board.board
        for board in report.boards
        if board.strategy_state == "degraded" and board.action == "hold"
    )

    steps: list[str] = []
    if rollback_order or quarantined_boards:
        window_action = "stabilize"
        if rollback_order:
            first_step = f"rollback {rollback_order[0]}"
        else:
            first_step = f"quarantine {quarantined_boards[0]}"
        steps.extend(f"rollback {board} candidate preset to the previous working preset" for board in rollback_order)
        steps.extend(f"keep {board} quarantined and block promotion until fresh evidence clears" for board in quarantined_boards)
        if apply_order:
            steps.append("hold remaining apply-ready boards until rollback verification clears")
        if observe_order:
            steps.append("continue observing already-applied boards that still verify cleanly")
        if degraded_hold_boards:
            steps.extend(f"keep {board} in degraded hold and refresh experiments before any apply attempt" for board in degraded_hold_boards)
    elif apply_order:
        window_action = "apply"
        first_step = f"apply {apply_order[0]}"
        steps.extend(f"apply {board} change package in a controlled window" for board in apply_order)
        if observe_order:
            steps.extend(f"continue observation window for {board}" for board in observe_order)
        if degraded_hold_boards:
            steps.extend(f"leave {board} on degraded hold while stronger candidates continue forward" for board in degraded_hold_boards)
    elif observe_order:
        window_action = "observe"
        first_step = f"observe {observe_order[0]}"
        steps.extend(f"continue post-apply verification observation for {board}" for board in observe_order)
        if degraded_hold_boards:
            steps.extend(f"refresh {board} experiments before reopening another apply window" for board in degraded_hold_boards)
    else:
        window_action = "hold"
        first_step = "collect more evidence"
        if degraded_hold_boards:
            steps.extend(f"collect another evidence window for {board} before attempting any preset application" for board in degraded_hold_boards)
        else:
            steps.append("collect another evidence window before attempting any preset application")

    return StrategyChangeWindow(
        window_action=window_action,
        first_step=first_step,
        apply_order=apply_order,
        rollback_order=rollback_order,
        observe_order=observe_order,
        steps=tuple(steps),
    )


def format_strategy_change_window(window: StrategyChangeWindow) -> str:
    lines = [
        "# Strategy Change Window",
        "",
        f"- window_action: {window.window_action}",
        f"- first_step: {window.first_step}",
        f"- rollback_order: {', '.join(window.rollback_order) if window.rollback_order else 'none'}",
        f"- apply_order: {', '.join(window.apply_order) if window.apply_order else 'none'}",
        f"- observe_order: {', '.join(window.observe_order) if window.observe_order else 'none'}",
        "",
        "## Steps",
        "",
    ]
    lines.extend(f"- {step}" for step in window.steps)
    return "\n".join(lines) + "\n"


def write_strategy_change_window(
    *,
    path: str | Path,
    window: StrategyChangeWindow,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_change_window(window), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(asdict(window), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_strategy_change_window(path: str | Path) -> StrategyChangeWindow | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return StrategyChangeWindow(
        window_action=str(payload.get("window_action", "")),
        first_step=str(payload.get("first_step", "")),
        apply_order=tuple(str(item) for item in payload.get("apply_order", [])),
        rollback_order=tuple(str(item) for item in payload.get("rollback_order", [])),
        observe_order=tuple(str(item) for item in payload.get("observe_order", [])),
        steps=tuple(str(item) for item in payload.get("steps", [])),
    )


def build_strategy_change_window_from_report_path(path: str | Path) -> StrategyChangeWindow:
    report = load_strategy_governance_report(path)
    if report is None:
        raise FileNotFoundError(f"strategy governance report sidecar not found for {path}")
    return build_strategy_change_window(report)
