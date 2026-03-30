"""Application planning helpers for weather preset change packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.weather.phase1.preset_change_package import WeatherPresetChangePackage


@dataclass(slots=True, frozen=True)
class WeatherPresetApplyPlan:
    next_working_preset: str
    ready_to_apply: bool
    apply_mode: str
    steps: tuple[str, ...]
    blockers: tuple[str, ...]


def build_weather_preset_apply_plan(
    *,
    package: WeatherPresetChangePackage,
) -> WeatherPresetApplyPlan:
    blockers: list[str] = []
    if not package.ready_to_apply:
        blockers.append("weather preset change package is not ready_to_apply")
    if not package.patch:
        blockers.append("weather working preset patch is empty")
    if getattr(package, "strategy_state", "degraded") == "quarantined":
        blockers.append("weather preset is quarantined and cannot be applied")

    if blockers:
        apply_mode = "hold"
        steps = (
            "keep the current weather working preset unchanged",
            "collect another weather preset promotion evidence window",
            "re-run weather auto experiments before attempting application",
        )
    else:
        apply_mode = "review_then_apply"
        steps = (
            f"review weather candidate {package.next_working_preset} against the current working preset",
            "apply the working preset patch into the weather preset registry",
            "run a fresh weather verification replay after patch application",
        )

    return WeatherPresetApplyPlan(
        next_working_preset=package.next_working_preset,
        ready_to_apply=package.ready_to_apply,
        apply_mode=apply_mode,
        steps=steps,
        blockers=tuple(blockers),
    )


def format_weather_preset_apply_plan(plan: WeatherPresetApplyPlan) -> str:
    lines = [
        "# Weather Preset Apply Plan",
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


def write_weather_preset_apply_plan(
    *,
    plan: WeatherPresetApplyPlan,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_weather_preset_apply_plan(plan),
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
