"""Experiment planning helpers for weather tuning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.weather.phase1.learning_report import (
    WeatherLearningReport,
    build_weather_learning_report,
)


@dataclass(slots=True, frozen=True)
class WeatherTuningVariant:
    name: str
    focus: str
    overrides: dict[str, float | int | tuple[str, ...]]
    rationale: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class WeatherTuningPlan:
    learning_report: WeatherLearningReport
    experiment_family: str
    loss_ranking: tuple[str, ...]
    variants: tuple[WeatherTuningVariant, ...]


def build_weather_tuning_plan(
    *,
    scorecard_paths: list[str | Path],
) -> WeatherTuningPlan:
    learning_report = build_weather_learning_report(scorecard_paths=scorecard_paths)
    experiment_family = learning_report.recommended_next_experiment
    return WeatherTuningPlan(
        learning_report=learning_report,
        experiment_family=experiment_family,
        loss_ranking=learning_report.recurring_loss_ranking,
        variants=_build_variants_for_focus(
            experiment_family,
            loss_ranking=learning_report.recurring_loss_ranking,
            learning_report=learning_report,
        ),
    )


def format_weather_tuning_plan(plan: WeatherTuningPlan) -> str:
    lines = [
        "# Weather Tuning Plan",
        "",
        f"- run_count: {plan.learning_report.run_count}",
        f"- experiment_family: {plan.experiment_family}",
        f"- recurring_focuses: {', '.join(plan.learning_report.recurring_focuses) if plan.learning_report.recurring_focuses else 'none'}",
        f"- recurring_loss_ranking: {', '.join(plan.loss_ranking) if plan.loss_ranking else 'none'}",
        "",
        "## Variants",
        "",
    ]
    for variant in plan.variants:
        lines.extend(
            [
                f"### {variant.name}",
                "",
                f"- focus: {variant.focus}",
                f"- overrides: {_format_overrides(variant.overrides)}",
                f"- rationale: {', '.join(variant.rationale)}",
                "",
            ]
        )
    lines.append("## Learning Actions")
    lines.append("")
    lines.extend(f"- {action}" for action in plan.learning_report.recommended_actions)
    return "\n".join(lines).strip() + "\n"


def build_weather_candidate_preset_registry(
    *,
    plan: WeatherTuningPlan,
    base_match: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    match = dict(base_match or {})
    if "event_family" not in match:
        match["event_family"] = "daily_high_temperature_threshold"
    if "settlement_source" not in match:
        match["settlement_source"] = "official"

    registry: dict[str, dict[str, object]] = {}
    for variant in plan.variants:
        registry[variant.name] = {
            "match": dict(match),
            "overrides": _normalize(variant.overrides),
            "rationale": list(variant.rationale),
            "focus": variant.focus,
        }
    return registry


def write_weather_tuning_plan(
    *,
    plan: WeatherTuningPlan,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_weather_tuning_plan(plan), encoding="utf-8")
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(plan)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def write_weather_candidate_preset_registry(
    *,
    plan: WeatherTuningPlan,
    output_path: str | Path,
    base_match: dict[str, str] | None = None,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(
            build_weather_candidate_preset_registry(plan=plan, base_match=base_match),
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_variants_for_focus(
    focus: str,
    *,
    loss_ranking: tuple[str, ...],
    learning_report: WeatherLearningReport,
) -> tuple[WeatherTuningVariant, ...]:
    if focus == "settlement":
        variants = [
            WeatherTuningVariant(
                name="settlement_higher_strip_gate",
                focus=focus,
                overrides={"min_strip_inconsistency_bps": 45.0},
                rationale=("tighten strip consistency threshold", "avoid fragile settlement structures"),
            ),
            WeatherTuningVariant(
                name="settlement_official_sooner",
                focus=focus,
                overrides={"use_official_forecast_inside_hours": 18},
                rationale=("switch to official forecasts earlier", "reduce late-run settlement drift"),
            ),
        ]
        if loss_ranking[:2] == ("settlement", "selection"):
            variants.append(
                WeatherTuningVariant(
                    name="settlement_selection_combo",
                    focus="settlement+selection",
                    overrides={"min_strip_inconsistency_bps": 45.0, "min_edge_bps": 90.0},
                    rationale=("settlement is weakest and selection is next", "require cleaner strips and stronger entry edges together"),
                )
            )
        elif loss_ranking[:2] == ("settlement", "execution"):
            variants.append(
                WeatherTuningVariant(
                    name="settlement_execution_combo",
                    focus="settlement+execution",
                    overrides={"min_strip_inconsistency_bps": 45.0, "min_edge_bps": 85.0},
                    rationale=("settlement is weakest and execution is next", "require cleaner strips and stronger edge before entering"),
                )
            )
        if learning_report.average_monotonicity_gap_bps > 150:
            variants.append(
                WeatherTuningVariant(
                    name="settlement_gap_recovery_gate",
                    focus="settlement",
                    overrides={"min_strip_inconsistency_bps": 50.0, "use_official_forecast_inside_hours": 24},
                    rationale=("monotonicity gap remains too wide across repeated runs", "tighten strip gate and switch to official forecasts earlier"),
                )
            )
        return tuple(variants)
    if focus == "execution":
        variants = [
            WeatherTuningVariant(
                name="execution_higher_edge_gate",
                focus=focus,
                overrides={"min_edge_bps": 80.0},
                rationale=("trade only stronger weather dislocations",),
            ),
            WeatherTuningVariant(
                name="execution_restrict_model_runs",
                focus=focus,
                overrides={"model_runs_utc": ("00", "12")},
                rationale=("reduce noisy overnight run combinations",),
            ),
        ]
        if loss_ranking[:2] == ("execution", "selection"):
            variants.append(
                WeatherTuningVariant(
                    name="execution_selection_cleaner_runs",
                    focus="execution+selection",
                    overrides={"min_edge_bps": 85.0, "model_runs_utc": ("00", "12")},
                    rationale=("execution and selection losses are both elevated", "restrict to cleaner runs with stronger edge"),
                )
            )
        elif loss_ranking[:2] == ("execution", "settlement"):
            variants.append(
                WeatherTuningVariant(
                    name="execution_settlement_cleaner_runs",
                    focus="execution+settlement",
                    overrides={"min_edge_bps": 85.0, "min_strip_inconsistency_bps": 45.0},
                    rationale=("execution is weakest and settlement is next", "trade fewer runs and require cleaner strip structure"),
                )
            )
        if learning_report.average_actionable_market_ratio < 0.5:
            variants.append(
                WeatherTuningVariant(
                    name="execution_actionable_subset_guard",
                    focus="execution+selection",
                    overrides={"min_edge_bps": 90.0, "model_runs_utc": ("00", "12")},
                    rationale=("too few markets remain actionable across repeated runs", "restrict to a smaller but cleaner weather subset"),
                )
            )
        return tuple(variants)
    if focus == "evidence":
        return (
            WeatherTuningVariant(
                name="collect_more_runs",
                focus=focus,
                overrides={},
                rationale=("insufficient repeat weather evidence", "collect another scorecard window"),
            ),
        )
    variants = [
        WeatherTuningVariant(
            name="selection_higher_edge_gate",
            focus="selection",
            overrides={"min_edge_bps": 85.0},
            rationale=("tighten weather entry set to cleaner threshold markets",),
        ),
        WeatherTuningVariant(
            name="selection_higher_strip_gate",
            focus="selection",
            overrides={"min_strip_inconsistency_bps": 35.0},
            rationale=("require stronger strip inconsistency before entry",),
        ),
    ]
    if loss_ranking[:2] == ("selection", "settlement"):
        variants.append(
            WeatherTuningVariant(
                name="selection_settlement_combo",
                focus="selection+settlement",
                overrides={"min_edge_bps": 90.0, "min_strip_inconsistency_bps": 45.0},
                rationale=("selection is weakest and settlement is next", "only trade cleaner threshold series with stronger strip signal"),
            )
        )
    elif loss_ranking[:2] == ("selection", "execution"):
        variants.append(
            WeatherTuningVariant(
                name="selection_execution_combo",
                focus="selection+execution",
                overrides={"min_edge_bps": 90.0, "model_runs_utc": ("00", "12")},
                rationale=("selection is weakest and execution is next", "tighten edge and restrict to cleaner forecast runs together"),
            )
        )
    if learning_report.average_actionable_market_ratio < 0.5:
        variants.append(
            WeatherTuningVariant(
                name="selection_actionable_subset_guard",
                focus="selection",
                overrides={"min_edge_bps": 90.0, "min_strip_inconsistency_bps": 40.0},
                rationale=("actionable market ratio remains weak", "tighten both edge and strip gates before expanding weather flow"),
            )
        )
    return tuple(variants)


def _format_overrides(overrides: dict[str, float | int | tuple[str, ...]]) -> str:
    if not overrides:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(overrides.items()))


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
