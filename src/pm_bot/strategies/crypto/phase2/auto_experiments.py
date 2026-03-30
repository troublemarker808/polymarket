"""Automatic experiment execution for crypto phase2 tuning variants."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, cast

from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState
from pm_bot.strategies.crypto.phase2.suite import CryptoPhase2SuiteResult, run_crypto_phase2_suite
from pm_bot.strategies.crypto.phase2.preset_lifecycle import (
    build_crypto_phase2_preset_lifecycle,
    write_crypto_phase2_preset_lifecycle,
    write_crypto_phase2_working_preset_patch,
)
from pm_bot.strategies.crypto.phase2.tuning_plan import (
    CryptoPhase2TuningPlan,
    build_crypto_phase2_tuning_plan,
)


@dataclass(slots=True, frozen=True)
class CryptoPhase2ExperimentResult:
    variant_name: str
    focus: str
    secondary_focus: str
    loss_ranking: tuple[str, ...]
    readiness_score: float
    total_profit_loss: float
    filtered_pnl: float
    recommended_action: str
    tuning_priority: str
    selection_loss: float
    pricing_loss: float
    execution_loss: float
    exit_loss: float
    sizing_loss: float
    average_loss_trade_pnl: float
    large_notional_share: float
    average_trade_execution_drag_bps: float
    average_trade_realized_pnl_bps: float
    exit_family_balance_score: float
    large_bucket_pnl_per_notional: float
    target_alignment_score: int
    targeted_loss_improvement: float
    output_dir: str


@dataclass(slots=True, frozen=True)
class CryptoPhase2AutoExperimentsReport:
    tuning_plan: CryptoPhase2TuningPlan
    baseline: CryptoPhase2ExperimentResult
    candidates: tuple[CryptoPhase2ExperimentResult, ...]
    winner: CryptoPhase2ExperimentResult
    winner_reason: str
    promotion_decision: str
    promotion_target: str
    promotion_reason: str


async def run_crypto_phase2_auto_experiments(
    *,
    suite_paths: list[str | Path],
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    config_dir: str | Path = "configs/profiles/research-crypto-phase2-v1",
    limit: int | None = None,
    output_dir: str | Path | None = None,
) -> CryptoPhase2AutoExperimentsReport:
    tuning_plan = build_crypto_phase2_tuning_plan(suite_paths=suite_paths)
    resolved_output_dir = Path(output_dir) if output_dir is not None else Path("data/research") / "crypto-phase2-auto-experiments"
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    baseline_result = await run_crypto_phase2_suite(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        config_dir=config_dir,
        limit=limit,
        output_dir=resolved_output_dir / "baseline",
        run_id="crypto-phase2-auto-baseline",
    )
    baseline = _experiment_result("baseline", "baseline", baseline_result)

    candidate_results: list[CryptoPhase2ExperimentResult] = []
    for variant in tuning_plan.variants:
        variant_result = await run_crypto_phase2_suite(
            snapshot_path=snapshot_path,
            underlying_states=underlying_states,
            config_dir=config_dir,
            limit=limit,
            output_dir=resolved_output_dir / variant.name,
            run_id=f"crypto-phase2-auto-{variant.name}",
            strategy_overrides=cast(dict[str, object], dict(variant.overrides)),
        )
        candidate_results.append(_experiment_result(variant.name, variant.focus, variant_result))
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
    winner_reason = _winner_reason(winner=winner, baseline=baseline)
    report = CryptoPhase2AutoExperimentsReport(
        tuning_plan=tuning_plan,
        baseline=baseline,
        candidates=enriched_candidates,
        winner=winner,
        winner_reason=winner_reason,
        promotion_decision=_promotion_decision(winner=winner, baseline=baseline, candidates=enriched_candidates),
        promotion_target=(winner.variant_name if winner.variant_name != baseline.variant_name else "baseline"),
        promotion_reason=_promotion_reason(winner=winner, baseline=baseline, candidates=enriched_candidates),
    )
    write_crypto_phase2_auto_experiments_report(report=report, output_dir=resolved_output_dir)
    return report


def format_crypto_phase2_auto_experiments_report(report: CryptoPhase2AutoExperimentsReport) -> str:
    lines = [
        "# Crypto Phase 2 Auto Experiments",
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
        f"- filtered_pnl: {report.baseline.filtered_pnl:.6f}",
        f"- recommended_action: {report.baseline.recommended_action}",
        f"- average_loss_trade_pnl: {report.baseline.average_loss_trade_pnl:.6f}",
        f"- large_notional_share: {report.baseline.large_notional_share:.4f}",
        f"- average_trade_execution_drag_bps: {report.baseline.average_trade_execution_drag_bps:.4f}",
        f"- average_trade_realized_pnl_bps: {report.baseline.average_trade_realized_pnl_bps:.4f}",
        f"- exit_family_balance_score: {report.baseline.exit_family_balance_score:.4f}",
        f"- large_bucket_pnl_per_notional: {report.baseline.large_bucket_pnl_per_notional:.6f}",
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
                f"- secondary_focus: {candidate.secondary_focus}",
                f"- loss_ranking: {', '.join(candidate.loss_ranking)}",
                f"- readiness_score: {candidate.readiness_score:.4f}",
                f"- total_profit_loss: {candidate.total_profit_loss:.4f}",
                f"- filtered_pnl: {candidate.filtered_pnl:.6f}",
                f"- recommended_action: {candidate.recommended_action}",
                f"- tuning_priority: {candidate.tuning_priority}",
                f"- average_loss_trade_pnl: {candidate.average_loss_trade_pnl:.6f}",
                f"- large_notional_share: {candidate.large_notional_share:.4f}",
                f"- average_trade_execution_drag_bps: {candidate.average_trade_execution_drag_bps:.4f}",
                f"- average_trade_realized_pnl_bps: {candidate.average_trade_realized_pnl_bps:.4f}",
                f"- exit_family_balance_score: {candidate.exit_family_balance_score:.4f}",
                f"- large_bucket_pnl_per_notional: {candidate.large_bucket_pnl_per_notional:.6f}",
                f"- target_alignment_score: {candidate.target_alignment_score}",
                f"- targeted_loss_improvement: {candidate.targeted_loss_improvement:.4f}",
                f"- output_dir: {candidate.output_dir}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def write_crypto_phase2_auto_experiments_report(
    *,
    report: CryptoPhase2AutoExperimentsReport,
    output_dir: str | Path,
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "auto_experiments.md").write_text(
        format_crypto_phase2_auto_experiments_report(report),
        encoding="utf-8",
    )
    (target_dir / "auto_experiments.json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    lifecycle = build_crypto_phase2_preset_lifecycle(report=report)
    write_crypto_phase2_preset_lifecycle(lifecycle=lifecycle, output_dir=target_dir)
    write_crypto_phase2_working_preset_patch(
        lifecycle=lifecycle,
        report=report,
        output_dir=target_dir,
    )


def _experiment_result(
    variant_name: str,
    focus: str,
    suite_result: CryptoPhase2SuiteResult,
) -> CryptoPhase2ExperimentResult:
    return CryptoPhase2ExperimentResult(
        variant_name=variant_name,
        focus=focus,
        secondary_focus=suite_result.final_scorecard.secondary_profit_focus,
        loss_ranking=suite_result.final_scorecard.loss_ranking,
        readiness_score=suite_result.final_scorecard.readiness_score,
        total_profit_loss=suite_result.final_scorecard.total_profit_loss,
        filtered_pnl=suite_result.final_scorecard.filtered_pnl,
        recommended_action=suite_result.final_scorecard.recommended_action,
        tuning_priority=suite_result.final_scorecard.tuning_priority,
        selection_loss=suite_result.final_scorecard.selection_loss,
        pricing_loss=suite_result.final_scorecard.pricing_loss,
        execution_loss=suite_result.final_scorecard.execution_loss,
        exit_loss=suite_result.final_scorecard.exit_loss,
        sizing_loss=suite_result.final_scorecard.sizing_loss,
        average_loss_trade_pnl=suite_result.final_scorecard.average_loss_trade_pnl,
        large_notional_share=suite_result.final_scorecard.large_notional_share,
        average_trade_execution_drag_bps=suite_result.final_scorecard.average_trade_execution_drag_bps,
        average_trade_realized_pnl_bps=suite_result.final_scorecard.average_trade_realized_pnl_bps,
        exit_family_balance_score=suite_result.final_scorecard.exit_family_balance_score,
        large_bucket_pnl_per_notional=suite_result.final_scorecard.large_bucket_pnl_per_notional,
        target_alignment_score=0,
        targeted_loss_improvement=0.0,
        output_dir=str(Path(suite_result.filtered_replay.output_dir).parent),
    )


def _select_winner(
    *,
    baseline: CryptoPhase2ExperimentResult,
    candidates: tuple[CryptoPhase2ExperimentResult, ...],
) -> CryptoPhase2ExperimentResult:
    if not candidates:
        return baseline
    enriched = (baseline, *(_enrich_candidate(candidate, baseline=baseline, learning_ranking=()) for candidate in candidates))
    ranked = sorted(
        enriched,
        key=lambda item: (
            item.recommended_action != "proceed",
            -item.target_alignment_score,
            -_targeted_loss_improvement(experiment=item, baseline=baseline),
            -item.readiness_score,
            item.total_profit_loss,
            -item.filtered_pnl,
        ),
    )
    return ranked[0]


def _winner_reason(
    *,
    winner: CryptoPhase2ExperimentResult,
    baseline: CryptoPhase2ExperimentResult,
) -> str:
    if winner.variant_name == baseline.variant_name:
        return "baseline remains the strongest current preset"
    targeted_improvement = _targeted_loss_improvement(experiment=winner, baseline=baseline)
    if targeted_improvement >= 0.03:
        if winner.target_alignment_score > 0:
            return (
                f"candidate improved targeted loss components by {targeted_improvement:.4f} "
                + f"with alignment score {winner.target_alignment_score}"
            )
        return f"candidate improved targeted loss components by {targeted_improvement:.4f} versus baseline"
    if winner.readiness_score > baseline.readiness_score:
        return "candidate improved readiness_score over baseline"
    if winner.total_profit_loss < baseline.total_profit_loss:
        return "candidate reduced total_profit_loss versus baseline"
    if winner.filtered_pnl > baseline.filtered_pnl:
        return "candidate improved filtered pnl versus baseline"
    return "candidate outranked baseline on combined experiment ordering"


def _promotion_decision(
    *,
    winner: CryptoPhase2ExperimentResult,
    baseline: CryptoPhase2ExperimentResult,
    candidates: tuple[CryptoPhase2ExperimentResult, ...],
) -> str:
    if not candidates:
        return "keep_baseline"
    if winner.variant_name == baseline.variant_name:
        return "keep_baseline"
    if winner.recommended_action != "proceed":
        return "collect_more_evidence"
    targeted_improvement = _targeted_loss_improvement(experiment=winner, baseline=baseline)
    total_loss_improvement = baseline.total_profit_loss - winner.total_profit_loss
    pnl_delta = winner.filtered_pnl - baseline.filtered_pnl
    exit_asymmetry_improvement = abs(baseline.average_loss_trade_pnl) - abs(winner.average_loss_trade_pnl)
    size_concentration_improvement = baseline.large_notional_share - winner.large_notional_share
    execution_drag_improvement = float(getattr(baseline, "average_trade_execution_drag_bps", 0.0)) - float(
        getattr(winner, "average_trade_execution_drag_bps", 0.0)
    )
    exit_balance_improvement = float(getattr(winner, "exit_family_balance_score", 0.0)) - float(
        getattr(baseline, "exit_family_balance_score", 0.0)
    )
    large_bucket_efficiency_improvement = float(getattr(winner, "large_bucket_pnl_per_notional", 0.0)) - float(
        getattr(baseline, "large_bucket_pnl_per_notional", 0.0)
    )
    if winner.readiness_score < baseline.readiness_score:
        return "collect_more_evidence"
    if winner.target_alignment_score <= 0:
        return "collect_more_evidence"
    if (
        targeted_improvement < 0.03
        and total_loss_improvement < 0.05
        and exit_asymmetry_improvement <= 0
        and size_concentration_improvement <= 0
        and execution_drag_improvement <= 0
        and exit_balance_improvement <= 0
        and large_bucket_efficiency_improvement <= 0
    ):
        return "collect_more_evidence"
    if winner.total_profit_loss > baseline.total_profit_loss and winner.filtered_pnl <= baseline.filtered_pnl:
        return "collect_more_evidence"
    if pnl_delta < -0.02 and winner.readiness_score <= baseline.readiness_score:
        return "collect_more_evidence"
    if float(getattr(winner, "average_trade_realized_pnl_bps", 0.0)) < float(
        getattr(baseline, "average_trade_realized_pnl_bps", 0.0)
    ) and targeted_improvement < 0.05:
        return "collect_more_evidence"
    return "promote_candidate"


def _promotion_reason(
    *,
    winner: CryptoPhase2ExperimentResult,
    baseline: CryptoPhase2ExperimentResult,
    candidates: tuple[CryptoPhase2ExperimentResult, ...],
) -> str:
    decision = _promotion_decision(winner=winner, baseline=baseline, candidates=candidates)
    if decision == "keep_baseline":
        return "baseline remains the strongest current working preset"
    if decision == "collect_more_evidence":
        return "winner is promising but does not yet clear targeted loss-improvement conditions"
    return "winner clears current promotion conditions over baseline"


def _loss_for_component(experiment: CryptoPhase2ExperimentResult, component: str) -> float:
    mapping = {
        "selection": experiment.selection_loss,
        "pricing": experiment.pricing_loss,
        "execution": experiment.execution_loss,
        "exit": experiment.exit_loss,
        "sizing": experiment.sizing_loss,
    }
    return mapping.get(component, experiment.total_profit_loss)


def _targeted_loss_improvement(
    *,
    experiment: CryptoPhase2ExperimentResult,
    baseline: CryptoPhase2ExperimentResult,
) -> float:
    if experiment.variant_name == baseline.variant_name:
        return 0.0
    components: list[str] = []
    primary = experiment.tuning_priority or experiment.focus
    if primary:
        components.append(primary)
    if experiment.secondary_focus and experiment.secondary_focus not in components:
        components.append(experiment.secondary_focus)
    improvements = [
        _loss_for_component(baseline, component) - _loss_for_component(experiment, component)
        for component in components
    ]
    if not improvements:
        return baseline.total_profit_loss - experiment.total_profit_loss
    average_improvement = sum(improvements) / len(improvements)
    if primary == "exit":
        average_improvement += max(
            0.0,
            abs(baseline.average_loss_trade_pnl) - abs(experiment.average_loss_trade_pnl),
        )
    if primary == "sizing":
        average_improvement += max(
            0.0,
            baseline.large_notional_share - experiment.large_notional_share,
        )
    return round(average_improvement, 4)


def _target_alignment_score(
    *,
    experiment: CryptoPhase2ExperimentResult,
    learning_ranking: tuple[str, ...],
) -> int:
    if not learning_ranking:
        return 0
    target_components: list[str] = []
    primary = experiment.tuning_priority or experiment.focus
    if primary:
        target_components.append(primary)
    if experiment.secondary_focus and experiment.secondary_focus not in target_components:
        target_components.append(experiment.secondary_focus)
    top_learning = tuple(item for item in learning_ranking[:2] if item)
    return sum(1 for component in top_learning if component in target_components)


def _enrich_candidate(
    candidate: CryptoPhase2ExperimentResult,
    *,
    baseline: CryptoPhase2ExperimentResult,
    learning_ranking: tuple[str, ...],
) -> CryptoPhase2ExperimentResult:
    return CryptoPhase2ExperimentResult(
        variant_name=candidate.variant_name,
        focus=candidate.focus,
        secondary_focus=candidate.secondary_focus,
        loss_ranking=candidate.loss_ranking,
        readiness_score=candidate.readiness_score,
        total_profit_loss=candidate.total_profit_loss,
        filtered_pnl=candidate.filtered_pnl,
        recommended_action=candidate.recommended_action,
        tuning_priority=candidate.tuning_priority,
        selection_loss=candidate.selection_loss,
        pricing_loss=candidate.pricing_loss,
        execution_loss=candidate.execution_loss,
        exit_loss=candidate.exit_loss,
        sizing_loss=candidate.sizing_loss,
        average_loss_trade_pnl=candidate.average_loss_trade_pnl,
        large_notional_share=candidate.large_notional_share,
        average_trade_execution_drag_bps=float(getattr(candidate, "average_trade_execution_drag_bps", 0.0)),
        average_trade_realized_pnl_bps=float(getattr(candidate, "average_trade_realized_pnl_bps", 0.0)),
        exit_family_balance_score=float(getattr(candidate, "exit_family_balance_score", 0.0)),
        large_bucket_pnl_per_notional=float(getattr(candidate, "large_bucket_pnl_per_notional", 0.0)),
        target_alignment_score=_target_alignment_score(experiment=candidate, learning_ranking=learning_ranking),
        targeted_loss_improvement=_targeted_loss_improvement(experiment=candidate, baseline=baseline),
        output_dir=getattr(candidate, "output_dir", ""),
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
