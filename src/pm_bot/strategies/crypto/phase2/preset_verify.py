"""Verification helpers for applied crypto phase2 preset changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class CryptoPhase2PresetVerificationReport:
    baseline_suite_path: str
    candidate_suite_path: str
    verification_decision: str
    rollback_recommended: bool
    readiness_delta: float
    total_profit_loss_delta: float
    filtered_pnl_delta: float
    targeted_loss_delta: float
    baseline_action: str
    candidate_action: str
    reasons: tuple[str, ...]
    next_step: str


def build_crypto_phase2_preset_verification_report(
    *,
    baseline_suite_path: str | Path,
    candidate_suite_path: str | Path,
) -> CryptoPhase2PresetVerificationReport:
    baseline_payload = _load_payload(baseline_suite_path)
    candidate_payload = _load_payload(candidate_suite_path)
    baseline_scorecard = _load_final_scorecard(baseline_payload)
    candidate_scorecard = _load_final_scorecard(candidate_payload)

    baseline_readiness = _as_float(baseline_scorecard.get("readiness_score"))
    candidate_readiness = _as_float(candidate_scorecard.get("readiness_score"))
    baseline_loss = _as_float(baseline_scorecard.get("total_profit_loss"))
    candidate_loss = _as_float(candidate_scorecard.get("total_profit_loss"))
    baseline_pnl = _as_float(baseline_scorecard.get("filtered_pnl"), default=0.0)
    candidate_pnl = _as_float(candidate_scorecard.get("filtered_pnl"), default=0.0)
    baseline_action = str(baseline_scorecard.get("recommended_action", "review"))
    candidate_action = str(candidate_scorecard.get("recommended_action", "review"))
    targeted_loss_delta = round(
        _targeted_loss_total(candidate_scorecard) - _targeted_loss_total(baseline_scorecard),
        4,
    )

    readiness_delta = round(candidate_readiness - baseline_readiness, 4)
    total_profit_loss_delta = round(candidate_loss - baseline_loss, 4)
    filtered_pnl_delta = round(candidate_pnl - baseline_pnl, 6)

    reasons: list[str] = []
    if candidate_action != "proceed":
        reasons.append("candidate verification suite does not remain proceed-grade")
    if readiness_delta < -0.03:
        reasons.append("candidate readiness_score regressed materially versus baseline")
    if total_profit_loss_delta > 0.2:
        reasons.append("candidate total_profit_loss increased materially versus baseline")
    if filtered_pnl_delta < -0.01:
        reasons.append("candidate filtered_pnl regressed versus baseline")
    if targeted_loss_delta > 0.03:
        reasons.append("candidate targeted-loss improvement regressed versus baseline")

    if reasons:
        if candidate_action == "pause" or len(reasons) >= 2:
            verification_decision = "rollback"
            next_step = "rollback to the previous working preset and collect another experiment window"
        else:
            verification_decision = "hold"
            next_step = "keep the candidate in review and collect another verification suite"
    else:
        verification_decision = "pass"
        next_step = "keep the candidate preset as the next working preset and continue observation"

    return CryptoPhase2PresetVerificationReport(
        baseline_suite_path=str(Path(baseline_suite_path)),
        candidate_suite_path=str(Path(candidate_suite_path)),
        verification_decision=verification_decision,
        rollback_recommended=(verification_decision == "rollback"),
        readiness_delta=readiness_delta,
        total_profit_loss_delta=total_profit_loss_delta,
        filtered_pnl_delta=filtered_pnl_delta,
        targeted_loss_delta=targeted_loss_delta,
        baseline_action=baseline_action,
        candidate_action=candidate_action,
        reasons=tuple(reasons) if reasons else ("candidate verification remains stronger than or equal to baseline",),
        next_step=next_step,
    )


def format_crypto_phase2_preset_verification_report(
    report: CryptoPhase2PresetVerificationReport,
) -> str:
    lines = [
        "# Crypto Phase 2 Preset Verification Report",
        "",
        f"- baseline_suite_path: {report.baseline_suite_path}",
        f"- candidate_suite_path: {report.candidate_suite_path}",
        f"- verification_decision: {report.verification_decision}",
        f"- rollback_recommended: {str(report.rollback_recommended).lower()}",
        f"- baseline_action: {report.baseline_action}",
        f"- candidate_action: {report.candidate_action}",
        f"- readiness_delta: {report.readiness_delta:.4f}",
        f"- total_profit_loss_delta: {report.total_profit_loss_delta:.4f}",
        f"- filtered_pnl_delta: {report.filtered_pnl_delta:.6f}",
        f"- targeted_loss_delta: {report.targeted_loss_delta:.4f}",
        f"- next_step: {report.next_step}",
        "",
        "## Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in report.reasons)
    return "\n".join(lines) + "\n"


def write_crypto_phase2_preset_verification_report(
    *,
    report: CryptoPhase2PresetVerificationReport,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_crypto_phase2_preset_verification_report(report),
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_payload(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _load_final_scorecard(payload: dict[str, Any]) -> dict[str, Any]:
    final_scorecard = payload.get("final_scorecard", {})
    if isinstance(final_scorecard, dict):
        return final_scorecard
    return {}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _targeted_loss_total(scorecard: dict[str, Any]) -> float:
    primary = str(scorecard.get("profit_focus", "")).strip()
    secondary = str(scorecard.get("secondary_profit_focus", "")).strip()
    total = 0.0
    counted = False
    for component in (primary, secondary):
        if not component:
            continue
        total += _as_float(scorecard.get(f"{component}_loss"))
        counted = True
    return total if counted else _as_float(scorecard.get("total_profit_loss"))


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
