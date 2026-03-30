"""Automatic experiment execution for weather tuning variants."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tomllib
from typing import Any

from pm_bot.strategies.weather.phase1.final_report import WeatherFinalScorecard
from pm_bot.strategies.weather.phase1.preset_lifecycle import (
    build_weather_preset_lifecycle,
    write_weather_preset_lifecycle,
    write_weather_working_preset_patch,
)
from pm_bot.strategies.weather.phase1.replay import run_weather_phase1_replay
from pm_bot.strategies.weather.phase1.tuning_plan import WeatherTuningPlan, build_weather_tuning_plan


@dataclass(slots=True, frozen=True)
class WeatherExperimentResult:
    variant_name: str
    focus: str
    readiness_score: float
    total_profit_loss: float
    recommended_action: str
    tuning_priority: str
    profit_focus: str
    loss_ranking: tuple[str, ...]
    selection_loss: float
    settlement_loss: float
    execution_loss: float
    target_alignment_score: int
    targeted_loss_improvement: float
    output_dir: str


@dataclass(slots=True, frozen=True)
class WeatherAutoExperimentsReport:
    tuning_plan: WeatherTuningPlan
    baseline: WeatherExperimentResult
    candidates: tuple[WeatherExperimentResult, ...]
    winner: WeatherExperimentResult
    winner_reason: str
    promotion_decision: str
    promotion_target: str
    promotion_reason: str


async def run_weather_auto_experiments(
    *,
    scorecard_paths: list[str | Path],
    snapshot_path: str | Path,
    forecast_payloads: Sequence[dict[str, object]],
    skill_payloads: Sequence[dict[str, object]],
    config_dir: str | Path = "configs/profiles/research-weather-phase1-v1",
    limit: int | None = None,
    output_dir: str | Path | None = None,
) -> WeatherAutoExperimentsReport:
    tuning_plan = build_weather_tuning_plan(scorecard_paths=scorecard_paths)
    resolved_output_dir = Path(output_dir) if output_dir is not None else Path("data/research") / "weather-auto-experiments"
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    await run_weather_phase1_replay(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
        config_dir=config_dir,
        limit=limit,
        output_dir=resolved_output_dir / "baseline",
        run_id="weather-auto-baseline",
    )
    baseline = _experiment_result("baseline", "baseline", _load_scorecard(resolved_output_dir / "baseline"))

    candidate_results: list[WeatherExperimentResult] = []
    for variant in tuning_plan.variants:
        profile_dir = resolved_output_dir / "_profiles" / variant.name
        _write_weather_variant_profile(
            source_config_dir=Path(config_dir),
            target_config_dir=profile_dir,
            overrides=variant.overrides,
        )
        candidate_output_dir = resolved_output_dir / variant.name
        await run_weather_phase1_replay(
            snapshot_path=snapshot_path,
            forecast_payloads=forecast_payloads,
            skill_payloads=skill_payloads,
            config_dir=profile_dir,
            limit=limit,
            output_dir=candidate_output_dir,
            run_id=f"weather-auto-{variant.name}",
        )
        candidate_results.append(
            _experiment_result(variant.name, variant.focus, _load_scorecard(candidate_output_dir))
        )

    enriched_candidates = tuple(
        _enrich_candidate(
            candidate,
            baseline=baseline,
            learning_ranking=tuning_plan.learning_report.recurring_loss_ranking,
        )
        for candidate in candidate_results
    )
    baseline = _enrich_candidate(
        baseline,
        baseline=baseline,
        learning_ranking=tuning_plan.learning_report.recurring_loss_ranking,
    )
    winner = _select_winner(baseline=baseline, candidates=enriched_candidates)
    report = WeatherAutoExperimentsReport(
        tuning_plan=tuning_plan,
        baseline=baseline,
        candidates=enriched_candidates,
        winner=winner,
        winner_reason=_winner_reason(winner=winner, baseline=baseline),
        promotion_decision=_promotion_decision(winner=winner, baseline=baseline, candidates=enriched_candidates),
        promotion_target=(winner.variant_name if winner.variant_name != "baseline" else "baseline"),
        promotion_reason=_promotion_reason(winner=winner, baseline=baseline, candidates=enriched_candidates),
    )
    write_weather_auto_experiments_report(report=report, output_dir=resolved_output_dir)
    return report


def format_weather_auto_experiments_report(report: WeatherAutoExperimentsReport) -> str:
    lines = [
        "# Weather Auto Experiments",
        "",
        f"- experiment_family: {report.tuning_plan.experiment_family}",
        f"- winner: {report.winner.variant_name}",
        f"- winner_reason: {report.winner_reason}",
        f"- promotion_decision: {report.promotion_decision}",
        f"- promotion_target: {report.promotion_target}",
        f"- promotion_reason: {report.promotion_reason}",
        "",
        "## Baseline",
        "",
        f"- readiness_score: {report.baseline.readiness_score:.4f}",
        f"- total_profit_loss: {report.baseline.total_profit_loss:.4f}",
        f"- recommended_action: {report.baseline.recommended_action}",
        f"- target_alignment_score: {report.baseline.target_alignment_score}",
        f"- targeted_loss_improvement: {report.baseline.targeted_loss_improvement:.4f}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in report.candidates:
        lines.extend(
            [
                f"### {candidate.variant_name}",
                "",
                f"- focus: {candidate.focus}",
                f"- readiness_score: {candidate.readiness_score:.4f}",
                f"- total_profit_loss: {candidate.total_profit_loss:.4f}",
                f"- recommended_action: {candidate.recommended_action}",
                f"- tuning_priority: {candidate.tuning_priority}",
                f"- target_alignment_score: {candidate.target_alignment_score}",
                f"- targeted_loss_improvement: {candidate.targeted_loss_improvement:.4f}",
                f"- output_dir: {candidate.output_dir}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def write_weather_auto_experiments_report(
    *,
    report: WeatherAutoExperimentsReport,
    output_dir: str | Path,
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "auto_experiments.md").write_text(
        format_weather_auto_experiments_report(report),
        encoding="utf-8",
    )
    (target_dir / "auto_experiments.json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    lifecycle = build_weather_preset_lifecycle(report=report)
    write_weather_preset_lifecycle(lifecycle=lifecycle, output_dir=target_dir)
    write_weather_working_preset_patch(
        lifecycle=lifecycle,
        report=report,
        output_dir=target_dir,
    )


def _experiment_result(
    variant_name: str,
    focus: str,
    scorecard: WeatherFinalScorecard,
) -> WeatherExperimentResult:
    return WeatherExperimentResult(
        variant_name=variant_name,
        focus=focus,
        readiness_score=scorecard.readiness_score,
        total_profit_loss=scorecard.total_profit_loss,
        recommended_action=scorecard.recommended_action,
        tuning_priority=scorecard.tuning_priority,
        profit_focus=scorecard.profit_focus,
        loss_ranking=tuple(
            component
            for component, _loss in sorted(
                (
                    ("selection", scorecard.selection_loss),
                    ("settlement", scorecard.settlement_loss),
                    ("execution", scorecard.execution_loss),
                ),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        selection_loss=scorecard.selection_loss,
        settlement_loss=scorecard.settlement_loss,
        execution_loss=scorecard.execution_loss,
        target_alignment_score=0,
        targeted_loss_improvement=0.0,
        output_dir=str(Path(scorecard.report_path).parent),
    )


def _load_scorecard(output_dir: Path) -> WeatherFinalScorecard:
    decoded = json.loads((output_dir / "weather_final_scorecard.json").read_text(encoding="utf-8"))
    return WeatherFinalScorecard(**decoded)


def _select_winner(
    *,
    baseline: WeatherExperimentResult,
    candidates: tuple[WeatherExperimentResult, ...],
) -> WeatherExperimentResult:
    if not candidates:
        return baseline
    ranked = sorted(
        (baseline, *candidates),
        key=lambda item: (
            item.recommended_action != "proceed",
            -item.target_alignment_score,
            -_targeted_loss_improvement(experiment=item, baseline=baseline),
            -item.readiness_score,
            item.total_profit_loss,
        ),
    )
    return ranked[0]


def _winner_reason(
    *,
    winner: WeatherExperimentResult,
    baseline: WeatherExperimentResult,
) -> str:
    if winner.variant_name == baseline.variant_name:
        return "baseline remains the strongest current weather preset"
    targeted_improvement = _targeted_loss_improvement(experiment=winner, baseline=baseline)
    if targeted_improvement >= 0.03:
        return f"candidate improved targeted weather loss components by {targeted_improvement:.4f}"
    if winner.readiness_score > baseline.readiness_score:
        return "candidate improved readiness_score over baseline"
    if winner.total_profit_loss < baseline.total_profit_loss:
        return "candidate reduced total_profit_loss versus baseline"
    return "candidate outranked baseline on combined weather experiment ordering"


def _promotion_decision(
    *,
    winner: WeatherExperimentResult,
    baseline: WeatherExperimentResult,
    candidates: tuple[WeatherExperimentResult, ...],
) -> str:
    if not candidates:
        return "keep_baseline"
    if winner.variant_name == baseline.variant_name:
        return "keep_baseline"
    if winner.recommended_action != "proceed":
        return "collect_more_evidence"
    if winner.readiness_score < baseline.readiness_score:
        return "collect_more_evidence"
    targeted_improvement = _targeted_loss_improvement(experiment=winner, baseline=baseline)
    if winner.target_alignment_score <= 0:
        return "collect_more_evidence"
    if targeted_improvement < 0.03 and winner.total_profit_loss >= baseline.total_profit_loss:
        return "collect_more_evidence"
    if winner.total_profit_loss > baseline.total_profit_loss:
        return "collect_more_evidence"
    return "promote_candidate"


def _promotion_reason(
    *,
    winner: WeatherExperimentResult,
    baseline: WeatherExperimentResult,
    candidates: tuple[WeatherExperimentResult, ...],
) -> str:
    decision = _promotion_decision(winner=winner, baseline=baseline, candidates=candidates)
    if decision == "keep_baseline":
        return "baseline remains the strongest current working weather preset"
    if decision == "collect_more_evidence":
        return "winner is promising but does not yet clear targeted weather loss-improvement conditions"
    return "winner clears current weather promotion conditions over baseline"


def _loss_for_component(experiment: WeatherExperimentResult, component: str) -> float:
    mapping = {
        "selection": experiment.selection_loss,
        "settlement": experiment.settlement_loss,
        "execution": experiment.execution_loss,
    }
    return mapping.get(component, experiment.total_profit_loss)


def _targeted_loss_improvement(
    *,
    experiment: WeatherExperimentResult,
    baseline: WeatherExperimentResult,
) -> float:
    if experiment.variant_name == baseline.variant_name:
        return 0.0
    targets = [component for component in experiment.focus.split("+") if component]
    if not targets:
        targets = [experiment.profit_focus]
    baseline_loss = sum(_loss_for_component(baseline, component) for component in targets)
    candidate_loss = sum(_loss_for_component(experiment, component) for component in targets)
    return round(baseline_loss - candidate_loss, 4)


def _enrich_candidate(
    experiment: WeatherExperimentResult,
    *,
    baseline: WeatherExperimentResult,
    learning_ranking: tuple[str, ...],
) -> WeatherExperimentResult:
    targets = tuple(component for component in experiment.focus.split("+") if component) or (experiment.profit_focus,)
    alignment = sum(1 for component in targets if component in learning_ranking[:2] or component in experiment.loss_ranking[:2])
    return WeatherExperimentResult(
        variant_name=experiment.variant_name,
        focus=experiment.focus,
        readiness_score=experiment.readiness_score,
        total_profit_loss=experiment.total_profit_loss,
        recommended_action=experiment.recommended_action,
        tuning_priority=experiment.tuning_priority,
        profit_focus=experiment.profit_focus,
        loss_ranking=experiment.loss_ranking,
        selection_loss=experiment.selection_loss,
        settlement_loss=experiment.settlement_loss,
        execution_loss=experiment.execution_loss,
        target_alignment_score=alignment,
        targeted_loss_improvement=_targeted_loss_improvement(experiment=experiment, baseline=baseline),
        output_dir=experiment.output_dir,
    )


def _write_weather_variant_profile(
    *,
    source_config_dir: Path,
    target_config_dir: Path,
    overrides: dict[str, float | int | tuple[str, ...]],
) -> None:
    target_config_dir.mkdir(parents=True, exist_ok=True)
    base_path = _resolve_config_path(source_config_dir, "base.local.toml", "base.example.toml")
    weather_path = _resolve_config_path(source_config_dir, "weather.v1.toml", "weather.v1.example.toml")
    base_doc = _load_toml(base_path)
    weather_doc = _load_toml(weather_path)
    strategy = weather_doc.setdefault("strategy", {})
    if not isinstance(strategy, dict):
        strategy = {}
        weather_doc["strategy"] = strategy
    threshold = strategy.setdefault("threshold", {})
    if not isinstance(threshold, dict):
        threshold = {}
        strategy["threshold"] = threshold
    ensemble = strategy.setdefault("ensemble", {})
    if not isinstance(ensemble, dict):
        ensemble = {}
        strategy["ensemble"] = ensemble

    for key, value in overrides.items():
        if key in {"min_strip_inconsistency_bps", "use_official_forecast_inside_hours"}:
            threshold[str(key)] = value
        else:
            ensemble[str(key)] = list(value) if isinstance(value, tuple) else value

    (target_config_dir / "base.local.toml").write_text(_render_toml(base_doc), encoding="utf-8")
    (target_config_dir / "weather.v1.toml").write_text(_render_toml(weather_doc), encoding="utf-8")


def _resolve_config_path(root: Path, preferred: str, fallback: str) -> Path:
    preferred_path = root / preferred
    if preferred_path.exists():
        return preferred_path
    return root / fallback


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        decoded = tomllib.load(handle)
    if isinstance(decoded, dict):
        return decoded
    raise ValueError(f"config must decode to a mapping: {path}")


def _render_toml(document: dict[str, Any]) -> str:
    scalar_lines: list[str] = []
    table_lines: list[str] = []
    _render_section(document, (), scalar_lines, table_lines)
    rendered = scalar_lines[:]
    if scalar_lines and table_lines:
        rendered.append("")
    rendered.extend(table_lines)
    return "\n".join(rendered).rstrip() + "\n"


def _render_section(
    value: dict[str, Any],
    prefix: tuple[str, ...],
    scalar_lines: list[str],
    table_lines: list[str],
) -> None:
    scalar_items: list[tuple[str, Any]] = []
    nested_items: list[tuple[str, dict[str, Any]]] = []
    for key, item in value.items():
        if isinstance(item, dict):
            nested_items.append((str(key), item))
        else:
            scalar_items.append((str(key), item))
    if prefix:
        table_lines.append(f"[{'.'.join(prefix)}]")
    target_lines = table_lines if prefix else scalar_lines
    for key, item in scalar_items:
        target_lines.append(f"{key} = {_render_value(item)}")
    if prefix and (scalar_items or nested_items):
        table_lines.append("")
    for index, (key, nested) in enumerate(nested_items):
        _render_section(nested, prefix + (key,), scalar_lines, table_lines)
        if index != len(nested_items) - 1:
            table_lines.append("")


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    if isinstance(value, tuple):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    if value is None:
        return '""'
    return _render_value(str(value))


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
