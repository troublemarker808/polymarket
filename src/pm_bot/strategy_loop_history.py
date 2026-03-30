"""Longer-horizon history reports for strategy feedback loops."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class StrategyLoopHistoryEntry:
    path: str
    overall_loop_action: str
    next_step: str
    board_actions: dict[str, str]


@dataclass(slots=True, frozen=True)
class StrategyLoopHistoryReport:
    window_count: int
    latest_action: str
    recurring_stabilize_boards: tuple[str, ...]
    recurring_learn_boards: tuple[str, ...]
    recommended_mode: str
    next_step: str
    entries: tuple[StrategyLoopHistoryEntry, ...]


def build_strategy_loop_history_report(
    *,
    feedback_loop_paths: list[str | Path],
) -> StrategyLoopHistoryReport:
    entries = tuple(_load_entry(path) for path in feedback_loop_paths)
    stabilize_counts: dict[str, int] = {}
    learn_counts: dict[str, int] = {}
    for entry in entries:
        for board, action in entry.board_actions.items():
            if action == "stabilize":
                stabilize_counts[board] = stabilize_counts.get(board, 0) + 1
            if action == "learn":
                learn_counts[board] = learn_counts.get(board, 0) + 1

    recurring_stabilize_boards = tuple(sorted(board for board, count in stabilize_counts.items() if count >= 2))
    recurring_learn_boards = tuple(sorted(board for board, count in learn_counts.items() if count >= 2))
    latest_action = entries[-1].overall_loop_action if entries else "none"

    if recurring_stabilize_boards:
        recommended_mode = "stabilize"
        next_step = "freeze new strategy promotions on repeatedly unstable boards and re-baseline them"
    elif latest_action == "verify":
        recommended_mode = "verify"
        next_step = "finish missing verification windows before opening another execution cycle"
    elif recurring_learn_boards:
        recommended_mode = "learn"
        next_step = "focus the next experiment cycle on repeatedly weak boards before opening new promotions"
    else:
        recommended_mode = "advance"
        next_step = "continue the controlled promotion cycle and keep accumulating evidence"

    return StrategyLoopHistoryReport(
        window_count=len(entries),
        latest_action=latest_action,
        recurring_stabilize_boards=recurring_stabilize_boards,
        recurring_learn_boards=recurring_learn_boards,
        recommended_mode=recommended_mode,
        next_step=next_step,
        entries=entries,
    )


def format_strategy_loop_history_report(report: StrategyLoopHistoryReport) -> str:
    lines = [
        "# Strategy Loop History Report",
        "",
        f"- window_count: {report.window_count}",
        f"- latest_action: {report.latest_action}",
        f"- recurring_stabilize_boards: {', '.join(report.recurring_stabilize_boards) if report.recurring_stabilize_boards else 'none'}",
        f"- recurring_learn_boards: {', '.join(report.recurring_learn_boards) if report.recurring_learn_boards else 'none'}",
        f"- recommended_mode: {report.recommended_mode}",
        f"- next_step: {report.next_step}",
        "",
        "## Windows",
        "",
    ]
    for entry in report.entries:
        boards = ",".join(f"{board}={action}" for board, action in sorted(entry.board_actions.items()))
        lines.append(f"- {Path(entry.path).name}:action={entry.overall_loop_action}:boards={boards}:next={entry.next_step}")
    return "\n".join(lines) + "\n"


def write_strategy_loop_history_report(
    *,
    path: str | Path,
    report: StrategyLoopHistoryReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_loop_history_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def _load_entry(path: str | Path) -> StrategyLoopHistoryEntry:
    source_path = Path(path)
    json_path = source_path.with_suffix(".json")
    payload = json.loads(json_path.read_text(encoding="utf-8") if json_path.exists() else source_path.read_text(encoding="utf-8"))
    boards_payload = payload.get("boards", [])
    board_actions = {
        str(item.get("board", "")): str(item.get("loop_action", "observe"))
        for item in boards_payload
        if isinstance(item, dict)
    }
    return StrategyLoopHistoryEntry(
        path=str(Path(path)),
        overall_loop_action=str(payload.get("overall_loop_action", "observe")),
        next_step=str(payload.get("next_step", "")),
        board_actions=board_actions,
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
