"""Bundled change package for crypto phase2 working preset updates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.crypto.phase2.preset_lifecycle import (
    CryptoPhase2PresetLifecycle,
    build_crypto_phase2_working_preset_patch,
)
from pm_bot.strategies.crypto.phase2.preset_promotion_evidence import (
    CryptoPhase2PresetPromotionEvidence,
)
from pm_bot.strategies.crypto.phase2.version_compare import build_crypto_phase2_version_comparison


@dataclass(slots=True, frozen=True)
class CryptoPhase2PresetChangePackage:
    next_working_preset: str
    ready_to_apply: bool
    promotion_decision: str
    promotion_reason: str
    recurring_targeted_improvement: float
    strategy_state: str
    strategy_state_reason: str
    lifecycle: CryptoPhase2PresetLifecycle
    evidence: CryptoPhase2PresetPromotionEvidence
    patch: dict[str, dict[str, object]]


def build_crypto_phase2_preset_change_package(
    *,
    lifecycle: CryptoPhase2PresetLifecycle,
    evidence: CryptoPhase2PresetPromotionEvidence,
    report: Any,
    base_match: dict[str, str] | None = None,
) -> CryptoPhase2PresetChangePackage:
    if hasattr(report, "baseline") and hasattr(report, "winner"):
        version_comparison = build_crypto_phase2_version_comparison(report=report, evidence=evidence)
        strategy_state = version_comparison.strategy_state
        strategy_state_reason = version_comparison.reasons[0] if version_comparison.reasons else "none"
    else:
        strategy_state = "candidate" if evidence.ready_to_apply else "degraded"
        strategy_state_reason = (
            "crypto promotion evidence is ready for a candidate preset"
            if evidence.ready_to_apply
            else "crypto preset still needs more evidence"
        )
    patch = build_crypto_phase2_working_preset_patch(
        lifecycle=lifecycle,
        report=report,
        base_match=base_match,
    )
    return CryptoPhase2PresetChangePackage(
        next_working_preset=lifecycle.next_working_preset,
        ready_to_apply=(
            evidence.ready_to_apply
            and lifecycle.promotion_decision == "promote_candidate"
            and lifecycle.strategy_state not in {"degraded", "quarantined"}
            and bool(patch)
        ),
        promotion_decision=lifecycle.promotion_decision,
        promotion_reason=lifecycle.promotion_reason,
        recurring_targeted_improvement=evidence.recurring_targeted_improvement,
        strategy_state=strategy_state,
        strategy_state_reason=strategy_state_reason,
        lifecycle=lifecycle,
        evidence=evidence,
        patch=patch,
    )


def format_crypto_phase2_preset_change_package(
    package: CryptoPhase2PresetChangePackage,
) -> str:
    lines = [
        "# Crypto Phase 2 Preset Change Package",
        "",
        f"- next_working_preset: {package.next_working_preset}",
        f"- ready_to_apply: {str(package.ready_to_apply).lower()}",
        f"- promotion_decision: {package.promotion_decision}",
        f"- promotion_reason: {package.promotion_reason}",
        f"- recurring_targeted_improvement: {package.recurring_targeted_improvement:.4f}",
        f"- strategy_state: {package.strategy_state}",
        f"- strategy_state_reason: {package.strategy_state_reason}",
        "",
        "## Lifecycle",
        "",
        f"- working_preset: {package.lifecycle.working_preset}",
        f"- candidate_presets: {', '.join(package.lifecycle.candidate_presets) if package.lifecycle.candidate_presets else 'none'}",
        f"- retired_presets: {', '.join(package.lifecycle.retired_presets) if package.lifecycle.retired_presets else 'none'}",
        "",
        "## Evidence",
        "",
        f"- report_count: {package.evidence.report_count}",
        f"- recurring_promotion_target: {package.evidence.recurring_promotion_target}",
        f"- recurring_promotion_count: {package.evidence.recurring_promotion_count}",
        f"- recurring_targeted_improvement: {package.evidence.recurring_targeted_improvement:.4f}",
        "",
        "## Patch",
        "",
        json.dumps(package.patch, ensure_ascii=True, indent=2),
        "",
    ]
    return "\n".join(lines)


def write_crypto_phase2_preset_change_package(
    *,
    package: CryptoPhase2PresetChangePackage,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_crypto_phase2_preset_change_package(package) + "\n",
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(package)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
