"""Experiment planning helpers for sports tuning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.sports.phase1.learning_report import (
    SportsLearningReport,
    build_sports_learning_report,
)


@dataclass(slots=True, frozen=True)
class SportsTuningVariant:
    name: str
    focus: str
    overrides: dict[str, float | int | bool]
    rationale: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class SportsTuningPlan:
    learning_report: SportsLearningReport
    experiment_family: str
    loss_ranking: tuple[str, ...]
    variants: tuple[SportsTuningVariant, ...]


def build_sports_tuning_plan(
    *,
    scorecard_paths: list[str | Path],
) -> SportsTuningPlan:
    learning_report = build_sports_learning_report(scorecard_paths=scorecard_paths)
    experiment_family = learning_report.recommended_next_experiment
    return SportsTuningPlan(
        learning_report=learning_report,
        experiment_family=experiment_family,
        loss_ranking=learning_report.recurring_loss_ranking,
        variants=_build_variants_for_focus(
            experiment_family,
            loss_ranking=learning_report.recurring_loss_ranking,
            learning_report=learning_report,
        ),
    )


def format_sports_tuning_plan(plan: SportsTuningPlan) -> str:
    lines = [
        "# Sports Tuning Plan",
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


def build_sports_candidate_preset_registry(
    *,
    plan: SportsTuningPlan,
    base_match: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    match = dict(base_match or {})
    if "league" not in match:
        match["league"] = "nba"
    if "market_family" not in match:
        match["market_family"] = "moneyline"

    registry: dict[str, dict[str, object]] = {}
    for variant in plan.variants:
        registry[variant.name] = {
            "match": dict(match),
            "overrides": dict(variant.overrides),
            "rationale": list(variant.rationale),
            "focus": variant.focus,
        }
    return registry


def write_sports_tuning_plan(
    *,
    plan: SportsTuningPlan,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_sports_tuning_plan(plan), encoding="utf-8")
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(plan)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def write_sports_candidate_preset_registry(
    *,
    plan: SportsTuningPlan,
    output_path: str | Path,
    base_match: dict[str, str] | None = None,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(
            build_sports_candidate_preset_registry(plan=plan, base_match=base_match),
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_variants_for_focus(
    focus: str,
    *,
    loss_ranking: tuple[str, ...],
    learning_report: SportsLearningReport,
) -> tuple[SportsTuningVariant, ...]:
    if focus == "pricing":
        variants = [
            SportsTuningVariant(
                name="pricing_higher_edge_gate",
                focus=focus,
                overrides={"min_edge_bps": 90.0},
                rationale=("trade only cleaner CLV setups", "reduce marginal fair-value dislocations"),
            ),
            SportsTuningVariant(
                name="pricing_faster_stale_cancel",
                focus=focus,
                overrides={"stale_state_seconds": 90},
                rationale=("refresh stale anchors earlier", "reduce adverse line drift before start"),
            ),
        ]
        if loss_ranking[:2] == ("pricing", "selection"):
            variants.append(
                SportsTuningVariant(
                    name="pricing_selection_tighter_gate",
                    focus="pricing+selection",
                    overrides={"min_edge_bps": 95.0, "max_time_to_start_minutes": 150},
                    rationale=("pricing and selection losses both remain elevated", "prefer tighter pregame windows with stronger edge"),
                )
            )
        elif loss_ranking[:2] == ("pricing", "execution"):
            variants.append(
                SportsTuningVariant(
                    name="pricing_execution_combo",
                    focus="pricing+execution",
                    overrides={"min_edge_bps": 95.0, "stale_state_seconds": 75},
                    rationale=("pricing is weakest and execution is next", "tighten edge quality and refresh anchors earlier"),
                )
            )
        if learning_report.average_clv_bps < 0:
            variants.append(
                SportsTuningVariant(
                    name="pricing_clv_recovery_gate",
                    focus="pricing",
                    overrides={"min_edge_bps": 95.0, "stale_state_seconds": 75},
                    rationale=("long-run CLV remains negative", "tighten entry quality before widening sports flow"),
                )
            )
        return tuple(variants)
    if focus == "execution":
        variants = [
            SportsTuningVariant(
                name="execution_shorter_cancel_window",
                focus=focus,
                overrides={"cancel_before_start_minutes": 8},
                rationale=("avoid pre-start liquidity decay", "reduce late stale orders"),
            ),
            SportsTuningVariant(
                name="execution_more_maker_quotes",
                focus=focus,
                overrides={"allow_maker_quotes": True},
                rationale=("test higher maker participation on clean pregame books",),
            ),
        ]
        if loss_ranking[:2] == ("execution", "selection"):
            variants.append(
                SportsTuningVariant(
                    name="execution_selection_shorter_window",
                    focus="execution+selection",
                    overrides={"cancel_before_start_minutes": 8, "max_time_to_start_minutes": 150},
                    rationale=("execution and selection losses both remain elevated", "trim thin late windows before execution quality degrades"),
                )
            )
        elif loss_ranking[:2] == ("execution", "pricing"):
            variants.append(
                SportsTuningVariant(
                    name="execution_pricing_shorter_window",
                    focus="execution+pricing",
                    overrides={"cancel_before_start_minutes": 8, "min_edge_bps": 90.0},
                    rationale=("execution is weakest and pricing is next", "finish orders earlier while demanding cleaner CLV setups"),
                )
            )
        if learning_report.average_actionable_market_ratio < 0.5:
            variants.append(
                SportsTuningVariant(
                    name="execution_actionable_subset_guard",
                    focus="execution+selection",
                    overrides={"cancel_before_start_minutes": 10, "max_time_to_start_minutes": 120},
                    rationale=("actionable market ratio remains weak across repeated runs", "trade a smaller but cleaner pregame subset"),
                )
            )
        return tuple(variants)
    if focus == "evidence":
        return (
            SportsTuningVariant(
                name="collect_more_runs",
                focus=focus,
                overrides={},
                rationale=("insufficient repeat sports evidence", "collect another scorecard window"),
            ),
        )
    variants = [
        SportsTuningVariant(
            name="selection_higher_edge_gate",
            focus="selection",
            overrides={"min_edge_bps": 85.0},
            rationale=("tighten NBA pregame subset to higher edge events",),
        ),
        SportsTuningVariant(
            name="selection_tighter_time_window",
            focus="selection",
            overrides={"max_time_to_start_minutes": 180},
            rationale=("avoid thin long-dated pregame windows", "focus on more stable liquidity windows"),
        ),
    ]
    if loss_ranking[:2] == ("selection", "pricing"):
        variants.append(
            SportsTuningVariant(
                name="selection_pricing_combo",
                focus="selection+pricing",
                overrides={"min_edge_bps": 90.0, "max_time_to_start_minutes": 150},
                rationale=("selection is weakest and pricing is next", "tighten both edge and pregame timing together"),
            )
        )
    elif loss_ranking[:2] == ("selection", "execution"):
        variants.append(
            SportsTuningVariant(
                name="selection_execution_cleaner_window",
                focus="selection+execution",
                overrides={"min_edge_bps": 90.0, "cancel_before_start_minutes": 8},
                rationale=("selection is weakest and execution is next", "tighten entry quality and avoid late-order drag together"),
            )
        )
    if learning_report.average_actionable_market_ratio < 0.5:
        variants.append(
            SportsTuningVariant(
                name="selection_actionable_subset_guard",
                focus="selection",
                overrides={"min_edge_bps": 90.0, "max_time_to_start_minutes": 120},
                rationale=("too few markets remain actionable across repeated runs", "concentrate on a tighter pregame window"),
            )
        )
    return tuple(variants)


def _format_overrides(overrides: dict[str, float | int | bool]) -> str:
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
