"""Application planning helpers for crypto phase2 preset change packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.crypto.phase2.preset_change_package import CryptoPhase2PresetChangePackage


@dataclass(slots=True, frozen=True)
class CryptoPhase2PresetApplyPlan:
    next_working_preset: str
    ready_to_apply: bool
    apply_mode: str
    steps: tuple[str, ...]
    blockers: tuple[str, ...]


def build_crypto_phase2_preset_apply_plan(
    *,
    package: CryptoPhase2PresetChangePackage,
) -> CryptoPhase2PresetApplyPlan:
    blockers: list[str] = []
    if not package.ready_to_apply:
        blockers.append("preset change package is not ready_to_apply")
    if not package.patch:
        blockers.append("working preset patch is empty")
    if package.recurring_targeted_improvement < 0.03:
        blockers.append("recurring targeted improvement remains below the application threshold")

    if blockers:
        apply_mode = "hold"
        steps_list = [
            "keep the current working preset unchanged",
            "collect another preset promotion evidence window",
            "re-run auto experiments before attempting application",
        ]
    else:
        apply_mode = "review_then_apply"
        steps_list = [
            f"review candidate {package.next_working_preset} against the current working preset",
            f"confirm recurring targeted improvement of {package.recurring_targeted_improvement:.4f} is still valid for the current weakest components",
            "apply the working preset patch into the phase2 preset registry",
            "run a fresh verification suite after patch application",
        ]

    return CryptoPhase2PresetApplyPlan(
        next_working_preset=package.next_working_preset,
        ready_to_apply=package.ready_to_apply,
        apply_mode=apply_mode,
        steps=tuple(steps_list),
        blockers=tuple(blockers),
    )


def format_crypto_phase2_preset_apply_plan(
    plan: CryptoPhase2PresetApplyPlan,
) -> str:
    lines = [
        "# Crypto Phase 2 Preset Apply Plan",
        "",
        f"- next_working_preset: {plan.next_working_preset}",
        f"- ready_to_apply: {str(plan.ready_to_apply).lower()}",
        f"- apply_mode: {plan.apply_mode}",
        "",
        "## Steps",
        "",
    ]
    lines.extend(f"- {step}" for step in plan.steps)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in plan.blockers or ("none",))
    return "\n".join(lines) + "\n"


def write_crypto_phase2_preset_apply_plan(
    *,
    plan: CryptoPhase2PresetApplyPlan,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_crypto_phase2_preset_apply_plan(plan),
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(plan)), ensure_ascii=True, indent=2),
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
