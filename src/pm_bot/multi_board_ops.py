"""Unified multi-board operator summaries and evidence reports."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable


@dataclass(slots=True, frozen=True)
class MultiBoardBoardStatus:
    board: str
    action: str
    decision: str
    source_path: str
    evidence_ready: bool | None
    reviewed_items: int
    actionable_items: int
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class MultiBoardOpsReport:
    overall_action: str
    overall_decision: str
    next_step: str
    rollback_target: str | None
    escalation_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    boards: tuple[MultiBoardBoardStatus, ...]


@dataclass(slots=True, frozen=True)
class MultiBoardInputSpec:
    board: str
    source_path: str
    evidence_path: str | None
    loader: Callable[[str, str | None], MultiBoardBoardStatus]


def default_multi_board_input_specs(
    *,
    crypto_operator_summary_path: str | Path,
    sports_scorecard_path: str | Path,
    weather_scorecard_path: str | Path,
    crypto_evidence_path: str | Path | None = None,
) -> tuple[MultiBoardInputSpec, ...]:
    return (
        MultiBoardInputSpec(
            board="crypto",
            source_path=str(Path(crypto_operator_summary_path)),
            evidence_path=(str(Path(crypto_evidence_path)) if crypto_evidence_path is not None else None),
            loader=_load_crypto_status,
        ),
        MultiBoardInputSpec(
            board="sports",
            source_path=str(Path(sports_scorecard_path)),
            evidence_path=None,
            loader=_load_sports_status,
        ),
        MultiBoardInputSpec(
            board="weather",
            source_path=str(Path(weather_scorecard_path)),
            evidence_path=None,
            loader=_load_weather_status,
        ),
    )


def build_multi_board_ops_report(
    *,
    crypto_operator_summary_path: str | Path,
    sports_scorecard_path: str | Path,
    weather_scorecard_path: str | Path,
    crypto_evidence_path: str | Path | None = None,
) -> MultiBoardOpsReport:
    return build_multi_board_ops_report_from_specs(
        default_multi_board_input_specs(
            crypto_operator_summary_path=crypto_operator_summary_path,
            sports_scorecard_path=sports_scorecard_path,
            weather_scorecard_path=weather_scorecard_path,
            crypto_evidence_path=crypto_evidence_path,
        )
    )


def build_multi_board_ops_report_from_specs(
    specs: tuple[MultiBoardInputSpec, ...],
) -> MultiBoardOpsReport:
    boards = tuple(
        spec.loader(spec.source_path, spec.evidence_path)
        for spec in specs
    )

    blockers: list[str] = []
    warnings: list[str] = []
    actions = [board.action for board in boards]
    for board in boards:
        if board.action == "pause":
            blockers.append(f"{board.board} requires pause: {board.decision}")
        warnings.extend(f"{board.board}: {warning}" for warning in board.warnings)
    overall_action = _merge_actions(actions)
    rollback_target: str | None = None
    escalation_actions: list[str] = []
    if overall_action == "pause":
        next_step = "stabilize_blocked_board"
        paused_boards = [board.board for board in boards if board.action == "pause"]
        rollback_target = paused_boards[0] if paused_boards else None
        escalation_actions.extend(
            f"pause {board} board and inspect latest operator artifacts"
            for board in paused_boards
        )
    elif overall_action == "review":
        next_step = "review_cross_board_artifacts"
        review_boards = [board.board for board in boards if board.action == "review"]
        rollback_target = review_boards[0] if review_boards else None
        escalation_actions.extend(
            f"review {board} board scorecard and refresh supporting evidence"
            for board in review_boards
        )
    else:
        next_step = "prepare_unified_ops_window"
        escalation_actions.append("proceed with unified ops window and operator handoff")
    overall_decision = (
        f"{overall_action}:"
        + ",".join(f"{board.board}={board.action}" for board in boards)
    )
    return MultiBoardOpsReport(
        overall_action=overall_action,
        overall_decision=overall_decision,
        next_step=next_step,
        rollback_target=rollback_target,
        escalation_actions=tuple(escalation_actions),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        boards=boards,
    )


def format_multi_board_ops_report(report: MultiBoardOpsReport) -> str:
    lines = [
        "# Multi-Board Ops Report",
        "",
        f"- overall_action: {report.overall_action}",
        f"- overall_decision: {report.overall_decision}",
        f"- next_step: {report.next_step}",
        f"- rollback_target: {report.rollback_target or ''}",
        f"- blockers: {len(report.blockers)}",
        f"- warnings: {len(report.warnings)}",
        "",
        "## Boards",
        "",
    ]
    for board in report.boards:
        lines.append(
            "- "
            + f"{board.board}:action={board.action}:"
            + f"reviewed={board.reviewed_items}:"
            + f"actionable={board.actionable_items}:"
            + f"evidence_ready={_optional_bool(board.evidence_ready)}:"
            + f"decision={board.decision}"
        )
    if report.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {item}" for item in report.blockers)
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report.warnings)
    if report.escalation_actions:
        lines.extend(["", "## Escalation Actions", ""])
        lines.extend(f"- {item}" for item in report.escalation_actions)
    return "\n".join(lines) + "\n"


def write_multi_board_ops_report(
    *,
    path: str | Path,
    report: MultiBoardOpsReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_multi_board_ops_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize_report(report), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_multi_board_ops_report(path: str | Path) -> MultiBoardOpsReport | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    boards = tuple(
        MultiBoardBoardStatus(
            board=str(item.get("board", "")),
            action=str(item.get("action", "")),
            decision=str(item.get("decision", "")),
            source_path=str(item.get("source_path", "")),
            evidence_ready=(
                bool(item["evidence_ready"])
                if item.get("evidence_ready") is not None
                else None
            ),
            reviewed_items=int(item.get("reviewed_items", 0)),
            actionable_items=int(item.get("actionable_items", 0)),
            warnings=tuple(str(warning) for warning in item.get("warnings", [])),
        )
        for item in payload.get("boards", [])
    )
    return MultiBoardOpsReport(
        overall_action=str(payload.get("overall_action", "")),
        overall_decision=str(payload.get("overall_decision", "")),
        next_step=str(payload.get("next_step", "")),
        rollback_target=(
            str(payload["rollback_target"])
            if payload.get("rollback_target") not in (None, "")
            else None
        ),
        escalation_actions=tuple(str(item) for item in payload.get("escalation_actions", [])),
        blockers=tuple(str(item) for item in payload.get("blockers", [])),
        warnings=tuple(str(item) for item in payload.get("warnings", [])),
        boards=boards,
    )


def _load_crypto_status(
    bundle_path: str,
    evidence_path: str | None,
) -> MultiBoardBoardStatus:
    payload = json.loads(Path(bundle_path).with_suffix(".json").read_text(encoding="utf-8"))
    combined = payload.get("combined", {})
    action = str(combined.get("overall_action", "review"))
    decision = str(combined.get("overall_decision", "review"))
    warnings: list[str] = []
    evidence_ready: bool | None = None
    if evidence_path is not None:
        evidence_payload = json.loads(Path(evidence_path).with_suffix(".json").read_text(encoding="utf-8"))
        evidence_ready = bool(evidence_payload.get("ready", False))
        if not evidence_ready:
            warnings.extend(str(item) for item in evidence_payload.get("blockers", []))
        warnings.extend(str(item) for item in evidence_payload.get("warnings", []))
        if action == "proceed" and evidence_ready is False:
            action = "review"
            decision = f"review:crypto_evidence_ready=false:{decision}"
    return MultiBoardBoardStatus(
        board="crypto",
        action=action,
        decision=decision,
        source_path=str(Path(bundle_path)),
        evidence_ready=evidence_ready,
        reviewed_items=1,
        actionable_items=1 if action == "proceed" else 0,
        warnings=tuple(warnings),
    )


def _load_sports_status(path: str, evidence_path: str | None = None) -> MultiBoardBoardStatus:
    del evidence_path
    payload = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    actionable_events = int(payload.get("actionable_events", 0))
    reviewed_events = int(payload.get("reviewed_events", len(rows)))
    review_events = int(payload.get("review_events", 0))
    action = "proceed" if actionable_events >= 1 and review_events == 0 else "review"
    warnings = []
    if review_events > 0:
        warnings.append(f"review_events={review_events}")
    return MultiBoardBoardStatus(
        board="sports",
        action=action,
        decision=f"{action}:events={reviewed_events}:actionable={actionable_events}:review={review_events}",
        source_path=str(Path(path)),
        evidence_ready=None,
        reviewed_items=reviewed_events,
        actionable_items=actionable_events,
        warnings=tuple(warnings),
    )


def _load_weather_status(path: str, evidence_path: str | None = None) -> MultiBoardBoardStatus:
    del evidence_path
    payload = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    actionable_series = int(payload.get("actionable_series", 0))
    reviewed_series = int(payload.get("reviewed_series", len(rows)))
    review_series = int(payload.get("review_series", 0))
    action = "proceed" if actionable_series >= 1 and review_series == 0 else "review"
    warnings = []
    if review_series > 0:
        warnings.append(f"review_series={review_series}")
    return MultiBoardBoardStatus(
        board="weather",
        action=action,
        decision=f"{action}:series={reviewed_series}:actionable={actionable_series}:review={review_series}",
        source_path=str(Path(path)),
        evidence_ready=None,
        reviewed_items=reviewed_series,
        actionable_items=actionable_series,
        warnings=tuple(warnings),
    )


def _merge_actions(actions: list[str]) -> str:
    if "pause" in actions:
        return "pause"
    if "review" in actions:
        return "review"
    return "proceed"


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return "none"
    return str(value).lower()


def _normalize_report(report: MultiBoardOpsReport) -> dict[str, object]:
    return {
        "overall_action": report.overall_action,
        "overall_decision": report.overall_decision,
        "next_step": report.next_step,
        "rollback_target": report.rollback_target,
        "escalation_actions": list(report.escalation_actions),
        "blockers": list(report.blockers),
        "warnings": list(report.warnings),
        "boards": [
            {
                "board": board.board,
                "action": board.action,
                "decision": board.decision,
                "source_path": board.source_path,
                "evidence_ready": board.evidence_ready,
                "reviewed_items": board.reviewed_items,
                "actionable_items": board.actionable_items,
                "warnings": list(board.warnings),
            }
            for board in report.boards
        ],
    }
