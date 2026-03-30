"""Batch-oriented long-running operator automation helpers."""

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


@dataclass(slots=True, frozen=True)
class OpsChecklistItem:
    status: str
    item: str


@dataclass(slots=True, frozen=True)
class DailyOpsBundle:
    report: MultiBoardOpsReport
    generated_reports: tuple[str, ...]
    checklist: tuple[OpsChecklistItem, ...]


def build_daily_ops_bundle(
    *,
    crypto_operator_summary_path: str | Path,
    sports_scorecard_path: str | Path,
    weather_scorecard_path: str | Path,
    crypto_evidence_path: str | Path | None = None,
) -> DailyOpsBundle:
    report = build_multi_board_ops_report(
        crypto_operator_summary_path=crypto_operator_summary_path,
        sports_scorecard_path=sports_scorecard_path,
        weather_scorecard_path=weather_scorecard_path,
        crypto_evidence_path=crypto_evidence_path,
    )
    checklist = _build_checklist(report)
    generated_reports: tuple[str, ...] = (
        str(Path(crypto_operator_summary_path)),
        str(Path(sports_scorecard_path)),
        str(Path(weather_scorecard_path)),
    )
    if crypto_evidence_path is not None:
        generated_reports = generated_reports + (str(Path(crypto_evidence_path)),)
    return DailyOpsBundle(
        report=report,
        generated_reports=generated_reports,
        checklist=checklist,
    )


def build_daily_ops_bundle_from_specs(
    specs: tuple[MultiBoardInputSpec, ...],
) -> DailyOpsBundle:
    report = build_multi_board_ops_report_from_specs(specs)
    generated_reports = tuple(spec.source_path for spec in specs)
    evidence_reports = tuple(spec.evidence_path for spec in specs if spec.evidence_path is not None)
    generated_reports = generated_reports + evidence_reports
    checklist = _build_checklist(report)
    return DailyOpsBundle(
        report=report,
        generated_reports=generated_reports,
        checklist=checklist,
    )




def format_daily_ops_bundle(bundle: DailyOpsBundle) -> str:
    lines = [
        "# Daily Ops Bundle",
        "",
        f"- overall_action: {bundle.report.overall_action}",
        f"- overall_decision: {bundle.report.overall_decision}",
        f"- next_step: {bundle.report.next_step}",
        f"- rollback_target: {bundle.report.rollback_target or ''}",
        "",
        "## Source Reports",
        "",
    ]
    lines.extend(f"- {path}" for path in bundle.generated_reports)
    lines.extend(["", "## Checklist", ""])
    lines.extend(f"- [{item.status}] {item.item}" for item in bundle.checklist)
    if bundle.report.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {item}" for item in bundle.report.blockers)
    if bundle.report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in bundle.report.warnings)
    if bundle.report.escalation_actions:
        lines.extend(["", "## Escalation Actions", ""])
        lines.extend(f"- {item}" for item in bundle.report.escalation_actions)
    return "\n".join(lines) + "\n"


def write_daily_ops_bundle(
    *,
    path: str | Path,
    bundle: DailyOpsBundle,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_daily_ops_bundle(bundle), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize_bundle(bundle), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def _build_checklist(report: MultiBoardOpsReport) -> tuple[OpsChecklistItem, ...]:
    items: list[OpsChecklistItem] = []
    for board in report.boards:
        status = "done" if board.action == "proceed" else "todo"
        items.append(
            OpsChecklistItem(
                status=status,
                item=f"{board.board} board status -> {board.decision}",
            )
        )
    if report.overall_action == "pause":
        items.append(OpsChecklistItem(status="todo", item="stabilize blocked board before any new session"))
    elif report.overall_action == "review":
        items.append(OpsChecklistItem(status="todo", item="review cross-board artifacts and refresh scorecards"))
    else:
        items.append(OpsChecklistItem(status="done", item="prepare unified ops window and operator handoff"))
    return tuple(items)


def _normalize_bundle(bundle: DailyOpsBundle) -> dict[str, object]:
    return {
        "report": {
            "overall_action": bundle.report.overall_action,
            "overall_decision": bundle.report.overall_decision,
            "next_step": bundle.report.next_step,
            "rollback_target": bundle.report.rollback_target,
            "escalation_actions": list(bundle.report.escalation_actions),
            "blockers": list(bundle.report.blockers),
            "warnings": list(bundle.report.warnings),
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
                for board in bundle.report.boards
            ],
        },
        "generated_reports": list(bundle.generated_reports),
        "checklist": [
            {"status": item.status, "item": item.item}
            for item in bundle.checklist
        ],
    }
