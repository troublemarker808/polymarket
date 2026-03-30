"""Unified operator console rendering for multi-board operations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from pm_bot.multi_board_ops import (
    MultiBoardInputSpec,
    MultiBoardOpsReport,
    build_multi_board_ops_report,
    build_multi_board_ops_report_from_specs,
)
from pm_bot.ops_automation import (
    DailyOpsBundle,
    build_daily_ops_bundle,
    build_daily_ops_bundle_from_specs,
)


@dataclass(slots=True, frozen=True)
class OpsConsoleBoardView:
    board: str
    action: str
    decision: str
    reviewed_items: int
    actionable_items: int
    evidence_ready: bool | None
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class UnifiedOpsConsole:
    overall_action: str
    overall_decision: str
    next_step: str
    rollback_target: str | None
    checklist_completion_ratio: float
    blocker_count: int
    warning_count: int
    boards: tuple[OpsConsoleBoardView, ...]
    checklist: tuple[str, ...]
    escalation_actions: tuple[str, ...]
    generated_reports: tuple[str, ...]


def build_unified_ops_console(
    *,
    crypto_operator_summary_path: str | Path,
    sports_scorecard_path: str | Path,
    weather_scorecard_path: str | Path,
    crypto_evidence_path: str | Path | None = None,
) -> UnifiedOpsConsole:
    report = build_multi_board_ops_report(
        crypto_operator_summary_path=crypto_operator_summary_path,
        sports_scorecard_path=sports_scorecard_path,
        weather_scorecard_path=weather_scorecard_path,
        crypto_evidence_path=crypto_evidence_path,
    )
    bundle = build_daily_ops_bundle(
        crypto_operator_summary_path=crypto_operator_summary_path,
        sports_scorecard_path=sports_scorecard_path,
        weather_scorecard_path=weather_scorecard_path,
        crypto_evidence_path=crypto_evidence_path,
    )
    return _console_from_report_and_bundle(report=report, bundle=bundle)


def build_unified_ops_console_from_specs(
    specs: tuple[MultiBoardInputSpec, ...],
) -> UnifiedOpsConsole:
    report = build_multi_board_ops_report_from_specs(specs)
    bundle = build_daily_ops_bundle_from_specs(specs)
    return _console_from_report_and_bundle(report=report, bundle=bundle)




def format_unified_ops_console(console: UnifiedOpsConsole) -> str:
    lines = [
        "# Unified Ops Console",
        "",
        f"- overall_action: {console.overall_action}",
        f"- overall_decision: {console.overall_decision}",
        f"- next_step: {console.next_step}",
        f"- rollback_target: {console.rollback_target or ''}",
        f"- blockers: {console.blocker_count}",
        f"- warnings: {console.warning_count}",
        f"- checklist_completion: {console.checklist_completion_ratio:.2f}",
        "",
        "## Boards",
        "",
    ]
    for board in console.boards:
        lines.append(
            "- "
            + f"{board.board}:action={board.action}:"
            + f"reviewed={board.reviewed_items}:"
            + f"actionable={board.actionable_items}:"
            + f"evidence_ready={_optional_bool(board.evidence_ready)}:"
            + f"decision={board.decision}"
        )
    lines.extend(["", "## Checklist", ""])
    lines.extend(f"- {item}" for item in console.checklist)
    lines.extend(["", "## Escalation Actions", ""])
    lines.extend(f"- {item}" for item in console.escalation_actions)
    lines.extend(["", "## Reports", ""])
    lines.extend(f"- {path}" for path in console.generated_reports)
    return "\n".join(lines) + "\n"


def write_unified_ops_console(
    *,
    path: str | Path,
    console: UnifiedOpsConsole,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_unified_ops_console(console), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize_console(console), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_unified_ops_console(path: str | Path) -> UnifiedOpsConsole | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    boards = tuple(
        OpsConsoleBoardView(
            board=str(item.get("board", "")),
            action=str(item.get("action", "")),
            decision=str(item.get("decision", "")),
            reviewed_items=int(item.get("reviewed_items", 0)),
            actionable_items=int(item.get("actionable_items", 0)),
            evidence_ready=(
                bool(item["evidence_ready"])
                if item.get("evidence_ready") is not None
                else None
            ),
            warnings=tuple(str(entry) for entry in item.get("warnings", [])),
        )
        for item in payload.get("boards", [])
    )
    return UnifiedOpsConsole(
        overall_action=str(payload.get("overall_action", "")),
        overall_decision=str(payload.get("overall_decision", "")),
        next_step=str(payload.get("next_step", "")),
        rollback_target=(
            str(payload["rollback_target"])
            if payload.get("rollback_target") not in (None, "")
            else None
        ),
        checklist_completion_ratio=float(payload.get("checklist_completion_ratio", 0.0)),
        blocker_count=int(payload.get("blocker_count", 0)),
        warning_count=int(payload.get("warning_count", 0)),
        boards=boards,
        checklist=tuple(str(item) for item in payload.get("checklist", [])),
        escalation_actions=tuple(str(item) for item in payload.get("escalation_actions", [])),
        generated_reports=tuple(str(item) for item in payload.get("generated_reports", [])),
    )


def _console_from_report_and_bundle(
    *,
    report: MultiBoardOpsReport,
    bundle: DailyOpsBundle,
) -> UnifiedOpsConsole:
    completed_items = sum(1 for item in bundle.checklist if item.status == "done")
    ratio = completed_items / len(bundle.checklist) if bundle.checklist else 0.0
    boards = tuple(
        OpsConsoleBoardView(
            board=board.board,
            action=board.action,
            decision=board.decision,
            reviewed_items=board.reviewed_items,
            actionable_items=board.actionable_items,
            evidence_ready=board.evidence_ready,
            warnings=board.warnings,
        )
        for board in report.boards
    )
    return UnifiedOpsConsole(
        overall_action=report.overall_action,
        overall_decision=report.overall_decision,
        next_step=report.next_step,
        rollback_target=report.rollback_target,
        checklist_completion_ratio=ratio,
        blocker_count=len(report.blockers),
        warning_count=len(report.warnings),
        boards=boards,
        checklist=tuple(f"[{item.status}] {item.item}" for item in bundle.checklist),
        escalation_actions=report.escalation_actions,
        generated_reports=bundle.generated_reports,
    )


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return "none"
    return str(value).lower()


def _normalize_console(console: UnifiedOpsConsole) -> dict[str, object]:
    return {
        "overall_action": console.overall_action,
        "overall_decision": console.overall_decision,
        "next_step": console.next_step,
        "rollback_target": console.rollback_target,
        "checklist_completion_ratio": console.checklist_completion_ratio,
        "blocker_count": console.blocker_count,
        "warning_count": console.warning_count,
        "boards": [
            {
                "board": board.board,
                "action": board.action,
                "decision": board.decision,
                "reviewed_items": board.reviewed_items,
                "actionable_items": board.actionable_items,
                "evidence_ready": board.evidence_ready,
                "warnings": list(board.warnings),
            }
            for board in console.boards
        ],
        "checklist": list(console.checklist),
        "escalation_actions": list(console.escalation_actions),
        "generated_reports": list(console.generated_reports),
    }
