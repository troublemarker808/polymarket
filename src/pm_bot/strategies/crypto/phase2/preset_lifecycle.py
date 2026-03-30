"""Lifecycle management for crypto phase2 working and candidate presets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.crypto.phase2.tuning_plan import build_crypto_phase2_candidate_preset_registry


@dataclass(slots=True, frozen=True)
class CryptoPhase2PresetLifecycle:
    working_preset: str
    candidate_presets: tuple[str, ...]
    retired_presets: tuple[str, ...]
    promotion_decision: str
    promotion_reason: str
    next_working_preset: str
    apply_ready: bool
    strategy_state: str
    strategy_state_reason: str


def build_crypto_phase2_preset_lifecycle(
    *,
    report: Any,
    evidence: Any | None = None,
    current_working_preset: str = "baseline",
    strategy_state: str | None = None,
    strategy_state_reason: str | None = None,
) -> CryptoPhase2PresetLifecycle:
    candidate_registry = build_crypto_phase2_candidate_preset_registry(plan=report.tuning_plan)
    candidate_presets = tuple(candidate_registry.keys())
    retired_presets: tuple[str, ...]
    resolved_strategy_state = strategy_state or "candidate"
    resolved_strategy_state_reason = strategy_state_reason or "strategy state pending version comparison"
    evidence_ready = bool(getattr(evidence, "ready_to_apply", report.promotion_decision == "promote_candidate"))
    apply_ready = evidence_ready and resolved_strategy_state not in {"degraded", "quarantined"}
    if report.promotion_decision == "promote_candidate" and apply_ready:
        next_working_preset = report.promotion_target
        retired_presets = (current_working_preset,)
    else:
        next_working_preset = current_working_preset
        retired_presets = ()
    if report.promotion_decision == "keep_baseline":
        candidate_presets = tuple(name for name in candidate_presets if name != current_working_preset)
    return CryptoPhase2PresetLifecycle(
        working_preset=current_working_preset,
        candidate_presets=candidate_presets,
        retired_presets=retired_presets,
        promotion_decision=report.promotion_decision,
        promotion_reason=report.promotion_reason,
        next_working_preset=next_working_preset,
        apply_ready=apply_ready,
        strategy_state=resolved_strategy_state,
        strategy_state_reason=resolved_strategy_state_reason,
    )


def format_crypto_phase2_preset_lifecycle(lifecycle: CryptoPhase2PresetLifecycle) -> str:
    lines = [
        "# Crypto Phase 2 Preset Lifecycle",
        "",
        f"- working_preset: {lifecycle.working_preset}",
        f"- next_working_preset: {lifecycle.next_working_preset}",
        f"- promotion_decision: {lifecycle.promotion_decision}",
        f"- promotion_reason: {lifecycle.promotion_reason}",
        f"- apply_ready: {str(lifecycle.apply_ready).lower()}",
        f"- strategy_state: {lifecycle.strategy_state}",
        f"- strategy_state_reason: {lifecycle.strategy_state_reason}",
        f"- candidate_presets: {', '.join(lifecycle.candidate_presets) if lifecycle.candidate_presets else 'none'}",
        f"- retired_presets: {', '.join(lifecycle.retired_presets) if lifecycle.retired_presets else 'none'}",
        "",
    ]
    return "\n".join(lines)


def build_crypto_phase2_working_preset_patch(
    *,
    lifecycle: CryptoPhase2PresetLifecycle,
    report: Any,
    base_match: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    apply_ready = bool(getattr(lifecycle, "apply_ready", True))
    if lifecycle.promotion_decision != "promote_candidate" or not apply_ready:
        return {}
    candidate_registry = build_crypto_phase2_candidate_preset_registry(
        plan=report.tuning_plan,
        base_match=base_match,
    )
    promoted = candidate_registry.get(lifecycle.next_working_preset)
    if not isinstance(promoted, dict):
        return {}
    return {lifecycle.next_working_preset: promoted}


def write_crypto_phase2_preset_lifecycle(
    *,
    lifecycle: CryptoPhase2PresetLifecycle,
    output_dir: str | Path,
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "preset_lifecycle.md").write_text(
        format_crypto_phase2_preset_lifecycle(lifecycle) + "\n",
        encoding="utf-8",
    )
    (target_dir / "preset_lifecycle.json").write_text(
        json.dumps(_normalize(asdict(lifecycle)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def write_crypto_phase2_working_preset_patch(
    *,
    lifecycle: CryptoPhase2PresetLifecycle,
    report: Any,
    output_dir: str | Path,
    base_match: dict[str, str] | None = None,
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    patch = build_crypto_phase2_working_preset_patch(
        lifecycle=lifecycle,
        report=report,
        base_match=base_match,
    )
    (target_dir / "working_preset_patch.json").write_text(
        json.dumps(patch, ensure_ascii=True, indent=2),
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
