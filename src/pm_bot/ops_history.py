"""Historical summaries for scheduled multi-board ops runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.multi_board_ops import load_multi_board_ops_report


@dataclass(slots=True, frozen=True)
class OpsHistoryRun:
    run_date: str
    run_id: str
    overall_action: str
    overall_decision: str
    rollback_target: str | None
    blocker_count: int
    warning_count: int
    board_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class OpsHistoryReport:
    total_runs: int
    latest_action: str
    recent_actions: tuple[str, ...]
    review_streak: int
    pause_streak: int
    proceed_streak: int
    recommended_attention: str
    board_review_counts: tuple[str, ...]
    recurring_issues: tuple[str, ...]
    recent_runs: tuple[OpsHistoryRun, ...]


def build_ops_history_report(
    *,
    output_root: str | Path,
    limit: int = 5,
) -> OpsHistoryReport:
    recent_runs = _load_recent_runs(output_root=output_root, limit=limit)
    review_streak = _leading_streak(recent_runs, "review")
    pause_streak = _leading_streak(recent_runs, "pause")
    proceed_streak = _leading_streak(recent_runs, "proceed")
    latest_action = recent_runs[0].overall_action if recent_runs else "unknown"
    board_review_counts = _board_review_counts(recent_runs)
    if pause_streak >= 1:
        recommended_attention = "pause_and_stabilize"
    elif review_streak >= 2:
        recommended_attention = "escalate_review_streak"
    elif latest_action == "proceed":
        recommended_attention = "continue_scheduled_ops"
    else:
        recommended_attention = "collect_more_runs"
    return OpsHistoryReport(
        total_runs=len(recent_runs),
        latest_action=latest_action,
        recent_actions=tuple(run.overall_action for run in recent_runs),
        review_streak=review_streak,
        pause_streak=pause_streak,
        proceed_streak=proceed_streak,
        recommended_attention=recommended_attention,
        board_review_counts=board_review_counts,
        recurring_issues=_recurring_issues(recent_runs),
        recent_runs=recent_runs,
    )


def format_ops_history_report(report: OpsHistoryReport) -> str:
    lines = [
        "# Ops History Report",
        "",
        f"- total_runs: {report.total_runs}",
        f"- latest_action: {report.latest_action}",
        f"- recent_actions: {','.join(report.recent_actions) if report.recent_actions else 'none'}",
        f"- review_streak: {report.review_streak}",
        f"- pause_streak: {report.pause_streak}",
        f"- proceed_streak: {report.proceed_streak}",
        f"- recommended_attention: {report.recommended_attention}",
        "",
        "## Board Review Counts",
        "",
    ]
    lines.extend(f"- {item}" for item in report.board_review_counts)
    if report.recurring_issues:
        lines.extend(["", "## Recurring Issues", ""])
        lines.extend(f"- {item}" for item in report.recurring_issues)
    lines.extend(["", "## Recent Runs", ""])
    for run in report.recent_runs:
        lines.append(
            "- "
            + f"{run.run_date}/{run.run_id}:action={run.overall_action}:"
            + f"blockers={run.blocker_count}:warnings={run.warning_count}:"
            + f"rollback_target={run.rollback_target or ''}:"
            + f"boards={','.join(run.board_actions)}"
        )
    return "\n".join(lines) + "\n"


def write_ops_history_report(
    *,
    path: str | Path,
    report: OpsHistoryReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_ops_history_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(report), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_ops_history_report(path: str | Path) -> OpsHistoryReport | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    recent_runs = tuple(
        OpsHistoryRun(
            run_date=str(item.get("run_date", "")),
            run_id=str(item.get("run_id", "")),
            overall_action=str(item.get("overall_action", "")),
            overall_decision=str(item.get("overall_decision", "")),
            rollback_target=(
                str(item["rollback_target"])
                if item.get("rollback_target") not in (None, "")
                else None
            ),
            blocker_count=int(item.get("blocker_count", 0)),
            warning_count=int(item.get("warning_count", 0)),
            board_actions=tuple(str(entry) for entry in item.get("board_actions", [])),
            blockers=tuple(str(entry) for entry in item.get("blockers", [])),
            warnings=tuple(str(entry) for entry in item.get("warnings", [])),
        )
        for item in payload.get("recent_runs", [])
    )
    return OpsHistoryReport(
        total_runs=int(payload.get("total_runs", 0)),
        latest_action=str(payload.get("latest_action", "")),
        recent_actions=tuple(str(item) for item in payload.get("recent_actions", [])),
        review_streak=int(payload.get("review_streak", 0)),
        pause_streak=int(payload.get("pause_streak", 0)),
        proceed_streak=int(payload.get("proceed_streak", 0)),
        recommended_attention=str(payload.get("recommended_attention", "")),
        board_review_counts=tuple(str(item) for item in payload.get("board_review_counts", [])),
        recurring_issues=tuple(str(item) for item in payload.get("recurring_issues", [])),
        recent_runs=recent_runs,
    )


def _load_recent_runs(
    *,
    output_root: str | Path,
    limit: int,
) -> tuple[OpsHistoryRun, ...]:
    root = Path(output_root)
    candidates = sorted(root.glob("*/*/multi-board-ops.md"), reverse=True)
    runs: list[OpsHistoryRun] = []
    for path in candidates:
        report = load_multi_board_ops_report(path)
        if report is None:
            continue
        run_dir = path.parent
        runs.append(
            OpsHistoryRun(
                run_date=run_dir.parent.name,
                run_id=run_dir.name,
                overall_action=report.overall_action,
                overall_decision=report.overall_decision,
                rollback_target=report.rollback_target,
                blocker_count=len(report.blockers),
                warning_count=len(report.warnings),
                board_actions=tuple(f"{board.board}={board.action}" for board in report.boards),
                blockers=report.blockers,
                warnings=report.warnings,
            )
        )
        if len(runs) >= limit:
            break
    return tuple(runs)


def _leading_streak(runs: tuple[OpsHistoryRun, ...], action: str) -> int:
    streak = 0
    for run in runs:
        if run.overall_action != action:
            break
        streak += 1
    return streak


def _board_review_counts(runs: tuple[OpsHistoryRun, ...]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for run in runs:
        for entry in run.board_actions:
            board, _, action = entry.partition("=")
            if action == "review":
                counts[board] = counts.get(board, 0) + 1
    return tuple(f"{board}={counts[board]}" for board in sorted(counts))


def _recurring_issues(runs: tuple[OpsHistoryRun, ...]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for run in runs:
        seen = set(run.blockers) | set(run.warnings)
        for item in seen:
            counts[item] = counts.get(item, 0) + 1
    recurring = [
        f"{item}={count}"
        for item, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
        if count >= 2
    ]
    return tuple(recurring[:5])


def _normalize(report: OpsHistoryReport) -> dict[str, object]:
    payload = asdict(report)
    payload["recent_actions"] = list(report.recent_actions)
    payload["board_review_counts"] = list(report.board_review_counts)
    payload["recurring_issues"] = list(report.recurring_issues)
    payload["recent_runs"] = [
        {
            **asdict(run),
            "board_actions": list(run.board_actions),
            "blockers": list(run.blockers),
            "warnings": list(run.warnings),
        }
        for run in report.recent_runs
    ]
    return payload
