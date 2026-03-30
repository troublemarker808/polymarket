"""Multi-session promotion evidence reports for crypto operator bundles."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal


EvidenceStage = Literal["sync_shadow_stability", "small_live_stability"]


@dataclass(slots=True, frozen=True)
class PromotionEvidenceThresholds:
    min_sessions: int
    min_total_orders_submitted: int
    max_pause_sessions: int
    max_review_sessions: int
    max_high_alert_sessions: int


@dataclass(slots=True, frozen=True)
class PromotionEvidenceEntry:
    bundle_path: str
    session_label: str | None
    overall_action: str
    overall_decision: str
    next_step: str
    alert_count: int
    alert_codes: tuple[str, ...]
    orders_submitted: int
    orders_filled: int
    recommended_route_bias: str | None


@dataclass(slots=True, frozen=True)
class PromotionEvidenceReport:
    stage: EvidenceStage
    ready: bool
    session_count: int
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, str]
    entries: tuple[PromotionEvidenceEntry, ...]


def build_promotion_evidence_report(
    *,
    stage: EvidenceStage,
    bundle_paths: list[str | Path],
) -> PromotionEvidenceReport:
    thresholds = _thresholds(stage)
    entries = tuple(_load_entry(path) for path in bundle_paths)
    blockers: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}

    pause_sessions = sum(1 for entry in entries if entry.overall_action == "pause")
    review_sessions = sum(1 for entry in entries if entry.overall_action == "review")
    high_alert_sessions = sum(
        1
        for entry in entries
        if any(
            code == "promotion_blocked"
            or code.startswith("runtime_halted:")
            or code == "data_failures_active"
            for code in entry.alert_codes
        )
    )
    total_orders_submitted = sum(entry.orders_submitted for entry in entries)
    more_aggressive_sessions = sum(1 for entry in entries if entry.recommended_route_bias == "more_aggressive")

    _require(
        condition=len(entries) >= thresholds.min_sessions,
        checks=checks,
        key="session_count",
        ok_value=str(len(entries)),
        fail_value=str(len(entries)),
        blockers=blockers,
        blocker_message=(
            "Not enough operator bundles for stability evidence "
            f"({thresholds.min_sessions} required)."
        ),
    )
    _require(
        condition=total_orders_submitted >= thresholds.min_total_orders_submitted,
        checks=checks,
        key="total_orders_submitted",
        ok_value=str(total_orders_submitted),
        fail_value=str(total_orders_submitted),
        blockers=blockers,
        blocker_message=(
            "Submitted-order evidence is too thin for this promotion stage "
            f"({thresholds.min_total_orders_submitted} required)."
        ),
    )
    _require(
        condition=pause_sessions <= thresholds.max_pause_sessions,
        checks=checks,
        key="pause_sessions",
        ok_value=str(pause_sessions),
        fail_value=str(pause_sessions),
        blockers=blockers,
        blocker_message="At least one evidence window ended in pause; stability is not sufficient.",
    )
    _warn(
        condition=review_sessions <= thresholds.max_review_sessions,
        checks=checks,
        key="review_sessions",
        ok_value=str(review_sessions),
        warn_value=str(review_sessions),
        warnings=warnings,
        warning_message="Too many evidence windows ended in review.",
    )
    _warn(
        condition=high_alert_sessions <= thresholds.max_high_alert_sessions,
        checks=checks,
        key="high_alert_sessions",
        ok_value=str(high_alert_sessions),
        warn_value=str(high_alert_sessions),
        warnings=warnings,
        warning_message="Too many evidence windows contained critical or promotion-blocking alerts.",
    )
    _warn(
        condition=more_aggressive_sessions == 0,
        checks=checks,
        key="execution_route_bias",
        ok_value="stable_or_passive",
        warn_value=f"more_aggressive_sessions={more_aggressive_sessions}",
        warnings=warnings,
        warning_message="Execution feedback requested a more aggressive route in at least one evidence window.",
    )

    return PromotionEvidenceReport(
        stage=stage,
        ready=not blockers,
        session_count=len(entries),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        checks=checks,
        entries=entries,
    )


def format_promotion_evidence_report(report: PromotionEvidenceReport) -> str:
    lines = [
        "# Promotion Evidence Report",
        "",
        f"- stage: {report.stage}",
        f"- ready: {str(report.ready).lower()}",
        f"- session_count: {report.session_count}",
        f"- blockers: {len(report.blockers)}",
        f"- warnings: {len(report.warnings)}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(report.checks.items()))
    lines.extend(["", "## Sessions", ""])
    for entry in report.entries:
        lines.append(
            "- "
            + f"{entry.session_label or Path(entry.bundle_path).name}:"
            + f"action={entry.overall_action}:"
            + f"orders={entry.orders_submitted}/{entry.orders_filled}:"
            + f"alerts={entry.alert_count}:"
            + f"route_bias={entry.recommended_route_bias or 'none'}"
        )
    if report.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {item}" for item in report.blockers)
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report.warnings)
    return "\n".join(lines) + "\n"


def write_promotion_evidence_report(
    *,
    path: str | Path,
    report: PromotionEvidenceReport,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_promotion_evidence_report(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize_report(report), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_promotion_evidence_report(path: str | Path) -> PromotionEvidenceReport | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return PromotionEvidenceReport(
        stage=str(payload.get("stage", "sync_shadow_stability")),  # type: ignore[arg-type]
        ready=bool(payload.get("ready", False)),
        session_count=int(payload.get("session_count", 0)),
        blockers=tuple(str(item) for item in payload.get("blockers", [])),
        warnings=tuple(str(item) for item in payload.get("warnings", [])),
        checks={str(key): str(value) for key, value in dict(payload.get("checks", {})).items()},
        entries=tuple(
            PromotionEvidenceEntry(
                bundle_path=str(item.get("bundle_path", "")),
                session_label=_optional_str(item.get("session_label")),
                overall_action=str(item.get("overall_action", "")),
                overall_decision=str(item.get("overall_decision", "")),
                next_step=str(item.get("next_step", "")),
                alert_count=int(item.get("alert_count", 0)),
                alert_codes=tuple(str(code) for code in item.get("alert_codes", [])),
                orders_submitted=int(item.get("orders_submitted", 0)),
                orders_filled=int(item.get("orders_filled", 0)),
                recommended_route_bias=_optional_str(item.get("recommended_route_bias")),
            )
            for item in payload.get("entries", [])
        ),
    )


def _load_entry(path: str | Path) -> PromotionEvidenceEntry:
    payload = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    combined = payload.get("combined", {})
    artifacts = payload.get("artifacts", {})
    execution_feedback = payload.get("execution_feedback")
    return PromotionEvidenceEntry(
        bundle_path=str(Path(path)),
        session_label=_optional_str(artifacts.get("session_label")),
        overall_action=str(combined.get("overall_action", "")),
        overall_decision=str(combined.get("overall_decision", "")),
        next_step=str(combined.get("next_step", "")),
        alert_count=int(combined.get("alert_count", 0)),
        alert_codes=tuple(str(item) for item in combined.get("alert_codes", [])),
        orders_submitted=int(artifacts.get("orders_submitted", 0) or 0),
        orders_filled=int(artifacts.get("orders_filled", 0) or 0),
        recommended_route_bias=(
            _optional_str(execution_feedback.get("recommended_route_bias"))
            if isinstance(execution_feedback, dict)
            else None
        ),
    )


def _thresholds(stage: EvidenceStage) -> PromotionEvidenceThresholds:
    if stage == "small_live_stability":
        return PromotionEvidenceThresholds(
            min_sessions=3,
            min_total_orders_submitted=3,
            max_pause_sessions=0,
            max_review_sessions=1,
            max_high_alert_sessions=1,
        )
    return PromotionEvidenceThresholds(
        min_sessions=2,
        min_total_orders_submitted=2,
        max_pause_sessions=0,
        max_review_sessions=1,
        max_high_alert_sessions=1,
    )


def _require(
    *,
    condition: bool,
    checks: dict[str, str],
    key: str,
    ok_value: str,
    fail_value: str,
    blockers: list[str],
    blocker_message: str,
) -> None:
    checks[key] = ok_value if condition else f"blocked:{fail_value}"
    if not condition:
        blockers.append(blocker_message)


def _warn(
    *,
    condition: bool,
    checks: dict[str, str],
    key: str,
    ok_value: str,
    warn_value: str,
    warnings: list[str],
    warning_message: str,
) -> None:
    checks[key] = ok_value if condition else f"warn:{warn_value}"
    if not condition:
        warnings.append(warning_message)


def _optional_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _normalize_report(report: PromotionEvidenceReport) -> dict[str, object]:
    return {
        "stage": report.stage,
        "ready": report.ready,
        "session_count": report.session_count,
        "blockers": list(report.blockers),
        "warnings": list(report.warnings),
        "checks": dict(report.checks),
        "entries": [
            {
                "bundle_path": entry.bundle_path,
                "session_label": entry.session_label,
                "overall_action": entry.overall_action,
                "overall_decision": entry.overall_decision,
                "next_step": entry.next_step,
                "alert_count": entry.alert_count,
                "alert_codes": list(entry.alert_codes),
                "orders_submitted": entry.orders_submitted,
                "orders_filled": entry.orders_filled,
                "recommended_route_bias": entry.recommended_route_bias,
            }
            for entry in report.entries
        ],
    }
