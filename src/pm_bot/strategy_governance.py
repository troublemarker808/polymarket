"""Unified strategy governance summaries across boards."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class StrategyGovernanceBoardStatus:
    board: str
    next_working_preset: str
    promotion_decision: str
    ready_to_apply: bool
    apply_mode: str | None
    applied: bool | None
    verification_decision: str | None
    rollback_recommended: bool | None
    action: str
    reason: str
    warnings: tuple[str, ...]
    strategy_state: str = "degraded"


@dataclass(slots=True, frozen=True)
class StrategyGovernanceReport:
    overall_action: str
    overall_reason: str
    next_step: str
    apply_ready_boards: tuple[str, ...]
    rollback_boards: tuple[str, ...]
    boards: tuple[StrategyGovernanceBoardStatus, ...]
    warnings: tuple[str, ...]


def build_strategy_governance_report(
    *,
    crypto_change_package_path: str | Path,
    sports_change_package_path: str | Path,
    weather_change_package_path: str | Path,
    crypto_version_compare_path: str | Path | None = None,
    sports_version_compare_path: str | Path | None = None,
    weather_version_compare_path: str | Path | None = None,
    crypto_apply_plan_path: str | Path | None = None,
    sports_apply_plan_path: str | Path | None = None,
    weather_apply_plan_path: str | Path | None = None,
    crypto_apply_result_path: str | Path | None = None,
    sports_apply_result_path: str | Path | None = None,
    weather_apply_result_path: str | Path | None = None,
    crypto_verify_path: str | Path | None = None,
    sports_verify_path: str | Path | None = None,
    weather_verify_path: str | Path | None = None,
) -> StrategyGovernanceReport:
    boards = (
        _build_board_status(
            "crypto",
            change_package_path=crypto_change_package_path,
            version_compare_path=crypto_version_compare_path,
            apply_plan_path=crypto_apply_plan_path,
            apply_result_path=crypto_apply_result_path,
            verify_path=crypto_verify_path,
        ),
        _build_board_status(
            "sports",
            change_package_path=sports_change_package_path,
            version_compare_path=sports_version_compare_path,
            apply_plan_path=sports_apply_plan_path,
            apply_result_path=sports_apply_result_path,
            verify_path=sports_verify_path,
        ),
        _build_board_status(
            "weather",
            change_package_path=weather_change_package_path,
            version_compare_path=weather_version_compare_path,
            apply_plan_path=weather_apply_plan_path,
            apply_result_path=weather_apply_result_path,
            verify_path=weather_verify_path,
        ),
    )

    warnings = tuple(
        f"{board.board}: {warning}"
        for board in boards
        for warning in board.warnings
    )
    rollback_boards = tuple(board.board for board in boards if board.action == "rollback")
    apply_ready_boards = tuple(
        board.board
        for board in boards
        if board.action == "apply"
    )

    if rollback_boards:
        overall_action = "rollback"
        overall_reason = "one or more boards failed verification after candidate application"
        next_step = "rollback flagged boards and collect another experiment window"
    elif any(board.action == "hold" for board in boards):
        overall_action = "hold"
        overall_reason = "one or more boards still require more evidence before application"
        next_step = "keep current working presets where required and collect more evidence"
    elif apply_ready_boards:
        overall_action = "apply"
        overall_reason = "all non-held boards are ready for controlled application"
        next_step = "apply ready boards in a controlled window and run verification immediately after"
    else:
        overall_action = "review"
        overall_reason = "board promotion state remains under review"
        next_step = "review change packages and refresh the next experiment cycle"

    return StrategyGovernanceReport(
        overall_action=overall_action,
        overall_reason=overall_reason,
        next_step=next_step,
        apply_ready_boards=apply_ready_boards,
        rollback_boards=rollback_boards,
        boards=boards,
        warnings=warnings,
    )


def format_strategy_governance_report(report: StrategyGovernanceReport) -> str:
    lines = [
        "# Strategy Governance Report",
        "",
        f"- overall_action: {report.overall_action}",
        f"- overall_reason: {report.overall_reason}",
        f"- next_step: {report.next_step}",
        f"- apply_ready_boards: {', '.join(report.apply_ready_boards) if report.apply_ready_boards else 'none'}",
        f"- rollback_boards: {', '.join(report.rollback_boards) if report.rollback_boards else 'none'}",
        "",
        "## Boards",
        "",
    ]
    for board in report.boards:
        lines.append(
            "- "
            + f"{board.board}:action={board.action}:"
            + f"promotion={board.promotion_decision}:"
            + f"state={board.strategy_state}:"
            + f"next={board.next_working_preset}:"
            + f"ready={str(board.ready_to_apply).lower()}:"
            + f"applied={_optional_bool(board.applied)}:"
            + f"verify={board.verification_decision or 'none'}:"
            + f"reason={board.reason}"
        )
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report.warnings)
    return "\n".join(lines) + "\n"


def write_strategy_governance_report(
    *,
    path: str | Path,
    report: StrategyGovernanceReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_governance_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_strategy_governance_report(path: str | Path) -> StrategyGovernanceReport | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    boards = tuple(
        StrategyGovernanceBoardStatus(
            board=str(item.get("board", "")),
            next_working_preset=str(item.get("next_working_preset", "unknown")),
            promotion_decision=str(item.get("promotion_decision", "review")),
            strategy_state=str(item.get("strategy_state", "degraded")),
            ready_to_apply=bool(item.get("ready_to_apply", False)),
            apply_mode=_optional_str(item.get("apply_mode")),
            applied=_optional_bool_value(item.get("applied")),
            verification_decision=_optional_str(item.get("verification_decision")),
            rollback_recommended=_optional_bool_value(item.get("rollback_recommended")),
            action=str(item.get("action", "hold")),
            reason=str(item.get("reason", "")),
            warnings=tuple(str(warning) for warning in item.get("warnings", [])),
        )
        for item in payload.get("boards", [])
    )
    return StrategyGovernanceReport(
        overall_action=str(payload.get("overall_action", "review")),
        overall_reason=str(payload.get("overall_reason", "")),
        next_step=str(payload.get("next_step", "")),
        apply_ready_boards=tuple(str(item) for item in payload.get("apply_ready_boards", [])),
        rollback_boards=tuple(str(item) for item in payload.get("rollback_boards", [])),
        boards=boards,
        warnings=tuple(str(item) for item in payload.get("warnings", [])),
    )


def _build_board_status(
    board: str,
    *,
    change_package_path: str | Path,
    version_compare_path: str | Path | None,
    apply_plan_path: str | Path | None,
    apply_result_path: str | Path | None,
    verify_path: str | Path | None,
) -> StrategyGovernanceBoardStatus:
    package = _load_json(change_package_path)
    version_compare = _load_json(version_compare_path) if version_compare_path is not None else {}
    plan = _load_json(apply_plan_path) if apply_plan_path is not None else {}
    apply_result = _load_json(apply_result_path) if apply_result_path is not None else {}
    verify_report = _load_json(verify_path) if verify_path is not None else {}

    next_working_preset = str(package.get("next_working_preset", "unknown"))
    promotion_decision = str(package.get("promotion_decision", "review"))
    strategy_state = str(
        package.get(
            "strategy_state",
            version_compare.get("strategy_state", "degraded"),
        )
    )
    version_recommendation = _optional_str(version_compare.get("recommendation"))
    ready_to_apply = bool(package.get("ready_to_apply", False))
    apply_mode = _optional_str(plan.get("apply_mode"))
    applied = _optional_bool_value(apply_result.get("applied"))
    verification_decision = _optional_str(verify_report.get("verification_decision"))
    rollback_recommended = _optional_bool_value(verify_report.get("rollback_recommended"))

    warnings: list[str] = []
    if promotion_decision != "promote_candidate":
        warnings.append(f"promotion_decision={promotion_decision}")
    if strategy_state in {"degraded", "quarantined"}:
        warnings.append(f"strategy_state={strategy_state}")
    if version_recommendation not in (None, "", "promote", "keep_current"):
        warnings.append(f"version_recommendation={version_recommendation}")
    if not ready_to_apply:
        warnings.append("package not ready_to_apply")
    if apply_mode == "hold":
        warnings.append("apply plan remains hold")

    if strategy_state == "quarantined":
        action = "hold"
        reason = "strategy remains quarantined and cannot advance"
    elif version_recommendation == "promote" and ready_to_apply and (applied in (None, False)):
        action = "apply"
        reason = "version comparison and evidence both support controlled application"
    elif strategy_state == "candidate" and promotion_decision != "promote_candidate":
        action = "hold"
        reason = "candidate state remains exploratory until promotion conditions clear"
    elif version_recommendation == "quarantine":
        action = "hold"
        reason = "version comparison still quarantines this board"
    elif verification_decision == "rollback":
        action = "rollback"
        reason = "verification requires rollback"
    elif verification_decision == "hold":
        action = "hold"
        reason = "verification still needs another evidence window"
    elif ready_to_apply and applied is True and verification_decision == "pass":
        action = "observe"
        reason = "candidate has been applied and verification currently passes"
    elif ready_to_apply and (applied in (None, False)):
        action = "apply"
        reason = "candidate is ready for controlled application"
    else:
        action = "hold"
        reason = "candidate still requires more evidence before application"

    return StrategyGovernanceBoardStatus(
        board=board,
        next_working_preset=next_working_preset,
        promotion_decision=promotion_decision,
        strategy_state=strategy_state,
        ready_to_apply=ready_to_apply,
        apply_mode=apply_mode,
        applied=applied,
        verification_decision=verification_decision,
        rollback_recommended=rollback_recommended,
        action=action,
        reason=reason,
        warnings=tuple(warnings),
    )


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return "none"
    return str(value).lower()


def _optional_bool_value(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
