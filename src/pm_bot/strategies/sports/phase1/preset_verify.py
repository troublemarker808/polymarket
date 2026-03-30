"""Verification helpers for applied sports preset changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class SportsPresetVerificationReport:
    baseline_scorecard_path: str
    candidate_scorecard_path: str
    verification_decision: str
    rollback_recommended: bool
    readiness_delta: float
    total_profit_loss_delta: float
    baseline_action: str
    candidate_action: str
    reasons: tuple[str, ...]
    next_step: str


def build_sports_preset_verification_report(
    *,
    baseline_scorecard_path: str | Path,
    candidate_scorecard_path: str | Path,
) -> SportsPresetVerificationReport:
    baseline_scorecard = _load_scorecard(baseline_scorecard_path)
    candidate_scorecard = _load_scorecard(candidate_scorecard_path)

    baseline_readiness = _as_float(baseline_scorecard.get("readiness_score"))
    candidate_readiness = _as_float(candidate_scorecard.get("readiness_score"))
    baseline_loss = _as_float(baseline_scorecard.get("total_profit_loss"))
    candidate_loss = _as_float(candidate_scorecard.get("total_profit_loss"))
    baseline_action = str(baseline_scorecard.get("recommended_action", "review"))
    candidate_action = str(candidate_scorecard.get("recommended_action", "review"))

    readiness_delta = round(candidate_readiness - baseline_readiness, 4)
    total_profit_loss_delta = round(candidate_loss - baseline_loss, 4)

    reasons: list[str] = []
    if candidate_action != "proceed":
        reasons.append("candidate sports scorecard no longer remains proceed-grade")
    if readiness_delta < -0.03:
        reasons.append("candidate sports readiness_score regressed materially versus baseline")
    if total_profit_loss_delta > 0.2:
        reasons.append("candidate sports total_profit_loss increased materially versus baseline")

    if reasons:
        if candidate_action == "pause" or len(reasons) >= 2:
            verification_decision = "rollback"
            next_step = "rollback to the previous sports working preset and collect another replay window"
        else:
            verification_decision = "hold"
            next_step = "keep the sports candidate preset under review and collect another verification scorecard"
    else:
        verification_decision = "pass"
        next_step = "keep the sports candidate preset as the next working preset and continue observation"

    return SportsPresetVerificationReport(
        baseline_scorecard_path=str(Path(baseline_scorecard_path)),
        candidate_scorecard_path=str(Path(candidate_scorecard_path)),
        verification_decision=verification_decision,
        rollback_recommended=(verification_decision == "rollback"),
        readiness_delta=readiness_delta,
        total_profit_loss_delta=total_profit_loss_delta,
        baseline_action=baseline_action,
        candidate_action=candidate_action,
        reasons=tuple(reasons) if reasons else ("candidate sports verification remains stronger than or equal to baseline",),
        next_step=next_step,
    )


def format_sports_preset_verification_report(report: SportsPresetVerificationReport) -> str:
    lines = [
        "# Sports Preset Verification Report",
        "",
        f"- baseline_scorecard_path: {report.baseline_scorecard_path}",
        f"- candidate_scorecard_path: {report.candidate_scorecard_path}",
        f"- verification_decision: {report.verification_decision}",
        f"- rollback_recommended: {str(report.rollback_recommended).lower()}",
        f"- baseline_action: {report.baseline_action}",
        f"- candidate_action: {report.candidate_action}",
        f"- readiness_delta: {report.readiness_delta:.4f}",
        f"- total_profit_loss_delta: {report.total_profit_loss_delta:.4f}",
        f"- next_step: {report.next_step}",
        "",
        "## Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in report.reasons)
    return "\n".join(lines) + "\n"


def write_sports_preset_verification_report(
    *,
    report: SportsPresetVerificationReport,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_sports_preset_verification_report(report),
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_scorecard(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
