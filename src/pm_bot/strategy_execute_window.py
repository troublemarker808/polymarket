"""Controlled execution of multi-board strategy change windows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import json
from pathlib import Path
from typing import Any, cast

from pm_bot.strategies.crypto.phase2.preset_apply import apply_crypto_phase2_preset_change_package
from pm_bot.strategies.crypto.phase2.preset_rollback import rollback_crypto_phase2_preset_application
from pm_bot.strategies.sports.phase1.preset_apply import apply_sports_preset_change_package
from pm_bot.strategies.sports.phase1.preset_rollback import rollback_sports_preset_application
from pm_bot.strategies.weather.phase1.preset_apply import apply_weather_preset_change_package
from pm_bot.strategies.weather.phase1.preset_rollback import rollback_weather_preset_application
from pm_bot.strategy_change_window import StrategyChangeWindow
from pm_bot.strategy_governance import StrategyGovernanceReport


@dataclass(slots=True, frozen=True)
class StrategyBoardExecutionResult:
    board: str
    planned_action: str
    executed_action: str
    success: bool
    output_config_path: str | None
    blockers: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class StrategyExecutionWindowReport:
    window_action: str
    first_step: str
    executed: bool
    halted: bool
    next_step: str
    board_results: tuple[StrategyBoardExecutionResult, ...]


def execute_strategy_change_window(
    *,
    governance_report: StrategyGovernanceReport,
    change_window: StrategyChangeWindow,
    crypto_change_package_path: str | Path | None = None,
    sports_change_package_path: str | Path | None = None,
    weather_change_package_path: str | Path | None = None,
    crypto_target_config_path: str | Path | None = None,
    sports_target_config_path: str | Path | None = None,
    weather_target_config_path: str | Path | None = None,
    crypto_apply_result_path: str | Path | None = None,
    sports_apply_result_path: str | Path | None = None,
    weather_apply_result_path: str | Path | None = None,
) -> StrategyExecutionWindowReport:
    del governance_report
    board_results: list[StrategyBoardExecutionResult] = []

    if change_window.rollback_order:
        for board in change_window.rollback_order:
            board_results.append(
                _execute_rollback(
                    board=board,
                    apply_result_path={
                        "crypto": crypto_apply_result_path,
                        "sports": sports_apply_result_path,
                        "weather": weather_apply_result_path,
                    }[board],
                )
            )
        for board in change_window.observe_order:
            board_results.append(_observe_board(board))
        halted = any(not result.success for result in board_results if result.planned_action == "rollback")
        next_step = (
            "fix rollback blockers before any further preset application"
            if halted
            else "re-run verification on rolled back boards before re-opening the change window"
        )
        return StrategyExecutionWindowReport(
            window_action=change_window.window_action,
            first_step=change_window.first_step,
            executed=True,
            halted=halted,
            next_step=next_step,
            board_results=tuple(board_results),
        )

    if change_window.apply_order:
        for board in change_window.apply_order:
            board_results.append(
                _execute_apply(
                    board=board,
                    change_package_path={
                        "crypto": crypto_change_package_path,
                        "sports": sports_change_package_path,
                        "weather": weather_change_package_path,
                    }[board],
                    target_config_path={
                        "crypto": crypto_target_config_path,
                        "sports": sports_target_config_path,
                        "weather": weather_target_config_path,
                    }[board],
                )
            )
        for board in change_window.observe_order:
            board_results.append(_observe_board(board))
        halted = any(not result.success for result in board_results if result.planned_action == "apply")
        next_step = (
            "fix apply blockers and keep current working presets unchanged on failed boards"
            if halted
            else "run board-level verification reports for all newly applied presets"
        )
        return StrategyExecutionWindowReport(
            window_action=change_window.window_action,
            first_step=change_window.first_step,
            executed=True,
            halted=halted,
            next_step=next_step,
            board_results=tuple(board_results),
        )

    for board in change_window.observe_order:
        board_results.append(_observe_board(board))
    if not board_results:
        board_results.append(
            StrategyBoardExecutionResult(
                board="none",
                planned_action="hold",
                executed_action="hold",
                success=True,
                output_config_path=None,
                blockers=(),
                notes=("collect another evidence window before making preset changes",),
            )
        )
    return StrategyExecutionWindowReport(
        window_action=change_window.window_action,
        first_step=change_window.first_step,
        executed=False,
        halted=False,
        next_step="continue observation and evidence collection",
        board_results=tuple(board_results),
    )


def format_strategy_execution_window_report(report: StrategyExecutionWindowReport) -> str:
    lines = [
        "# Strategy Execution Window Report",
        "",
        f"- window_action: {report.window_action}",
        f"- first_step: {report.first_step}",
        f"- executed: {str(report.executed).lower()}",
        f"- halted: {str(report.halted).lower()}",
        f"- next_step: {report.next_step}",
        "",
        "## Board Results",
        "",
    ]
    for result in report.board_results:
        lines.append(
            "- "
            + f"{result.board}:planned={result.planned_action}:executed={result.executed_action}:"
            + f"success={str(result.success).lower()}:"
            + f"output={result.output_config_path or 'none'}"
        )
        for note in result.notes:
            lines.append(f"  note: {note}")
        for blocker in result.blockers:
            lines.append(f"  blocker: {blocker}")
    return "\n".join(lines) + "\n"


def write_strategy_execution_window_report(
    *,
    path: str | Path,
    report: StrategyExecutionWindowReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_execution_window_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def _execute_apply(
    *,
    board: str,
    change_package_path: str | Path | None,
    target_config_path: str | Path | None,
) -> StrategyBoardExecutionResult:
    if change_package_path is None or target_config_path is None:
        return StrategyBoardExecutionResult(
            board=board,
            planned_action="apply",
            executed_action="blocked",
            success=False,
            output_config_path=None,
            blockers=("missing change_package_path or target_config_path for apply",),
            notes=(),
        )
    result: Any
    if board == "crypto":
        result = apply_crypto_phase2_preset_change_package(
            change_package_path=change_package_path,
            target_config_path=target_config_path,
        )
    elif board == "sports":
        result = apply_sports_preset_change_package(
            change_package_path=change_package_path,
            target_config_path=target_config_path,
        )
    else:
        result = apply_weather_preset_change_package(
            change_package_path=change_package_path,
            target_config_path=target_config_path,
        )
    payload = _result_payload(result)
    blockers = tuple(str(item) for item in payload.get("blockers", []))
    notes = tuple(str(item) for item in payload.get("verification_steps", []))
    return StrategyBoardExecutionResult(
        board=board,
        planned_action="apply",
        executed_action="apply",
        success=bool(payload.get("applied", False)),
        output_config_path=_optional_str(payload.get("output_config_path")),
        blockers=blockers,
        notes=notes,
    )


def _execute_rollback(
    *,
    board: str,
    apply_result_path: str | Path | None,
) -> StrategyBoardExecutionResult:
    if apply_result_path is None:
        return StrategyBoardExecutionResult(
            board=board,
            planned_action="rollback",
            executed_action="blocked",
            success=False,
            output_config_path=None,
            blockers=("missing apply_result_path for rollback",),
            notes=(),
        )
    apply_payload = _load_json(apply_result_path)
    backup_config_path = _optional_str(apply_payload.get("backup_config_path"))
    target_config_path = _optional_str(apply_payload.get("target_config_path"))
    output_config_path = _optional_str(apply_payload.get("rollback_output_config_path"))
    if backup_config_path is None or target_config_path is None:
        return StrategyBoardExecutionResult(
            board=board,
            planned_action="rollback",
            executed_action="blocked",
            success=False,
            output_config_path=output_config_path,
            blockers=("apply result does not include backup_config_path and target_config_path",),
            notes=(),
        )
    result: Any
    if board == "crypto":
        result = rollback_crypto_phase2_preset_application(
            backup_config_path=backup_config_path,
            target_config_path=target_config_path,
            output_config_path=output_config_path,
        )
    elif board == "sports":
        result = rollback_sports_preset_application(
            backup_config_path=backup_config_path,
            target_config_path=target_config_path,
            output_config_path=output_config_path,
        )
    else:
        result = rollback_weather_preset_application(
            backup_config_path=backup_config_path,
            target_config_path=target_config_path,
            output_config_path=output_config_path,
        )
    payload = _result_payload(result)
    blockers = tuple(str(item) for item in payload.get("blockers", []))
    notes = (
        "re-run the previous working preset verification window before re-opening promotion",
    ) if bool(payload.get("rolled_back", False)) else ()
    return StrategyBoardExecutionResult(
        board=board,
        planned_action="rollback",
        executed_action="rollback",
        success=bool(payload.get("rolled_back", False)),
        output_config_path=_optional_str(payload.get("output_config_path")),
        blockers=blockers,
        notes=notes,
    )


def _observe_board(board: str) -> StrategyBoardExecutionResult:
    return StrategyBoardExecutionResult(
        board=board,
        planned_action="observe",
        executed_action="observe",
        success=True,
        output_config_path=None,
        blockers=(),
        notes=("continue verification observation without modifying the current config",),
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _result_payload(result: Any) -> dict[str, Any]:
    if is_dataclass(result):
        payload = asdict(cast(Any, result))
        if isinstance(payload, dict):
            return payload
    if isinstance(result, dict):
        return result
    data = getattr(result, "__dict__", None)
    if isinstance(data, dict):
        return dict(data)
    return {}


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
