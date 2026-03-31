"""Calibration helpers for Crypto Phase 1 fair-value models."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import MarketSnapshot
from pm_bot.strategies.common import parse_float
from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.baseline import (
    get_locked_crypto_calibration_baseline_preset,
    resolve_crypto_calibration_model_configs,
)
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.models import (
    CryptoBarrierModelConfig,
    CryptoFusionModelConfig,
    CryptoMarketDefinition,
    CryptoResidualModelConfig,
    CryptoUnderlyingState,
)
from pm_bot.strategies.crypto.phase1.pricing import observed_mid_probability
from pm_bot.strategies.crypto.phase1.replay import compute_crypto_phase1_fair_values_from_snapshots


@dataclass(slots=True, frozen=True)
class CryptoCalibrationMarketRow:
    dataset: str
    market_id: str
    instrument_key: str
    underlying: str
    event_family: str
    direction: str
    timestamp: datetime
    observed_probability: float
    fair_probability: float
    barrier_probability: float
    surface_probability: float | None
    gross_edge_bps: float
    net_edge_bps: float
    final_observed_probability: float
    repricing_bps: float
    barrier_miss_bps: float
    surface_miss_bps: float
    fusion_miss_bps: float
    late_repricing_miss_bps: float
    repricing_observed: bool
    sign_aligned: bool
    selection_miss: bool
    confidence: float
    residual_diagnostic_tag: str


@dataclass(slots=True, frozen=True)
class CryptoCalibrationDatasetReport:
    dataset: str
    snapshot_path: str
    processed_snapshots: int
    market_count: int
    positive_gross_edge_count: int
    positive_net_edge_count: int
    repricing_observed_count: int
    repricing_aligned_count: int
    sign_alignment_rate: float
    mean_signed_gap_bps: float
    mean_abs_gap_bps: float
    mean_net_edge_bps: float
    median_net_edge_bps: float
    mean_barrier_miss_bps: float
    mean_surface_miss_bps: float
    mean_fusion_miss_bps: float
    mean_late_repricing_miss_bps: float
    selection_miss_count: int
    calibration_score: float


@dataclass(slots=True, frozen=True)
class CryptoCalibrationReport:
    generated_at: datetime
    baseline_classification: str
    rewritten_objective: str
    locked_parameters: tuple[str, ...]
    tunable_parameters: tuple[str, ...]
    score_formula: str
    dataset_split: dict[str, str]
    dominant_failure_mechanisms: tuple[str, ...]
    datasets: tuple[CryptoCalibrationDatasetReport, ...]
    market_rows: tuple[CryptoCalibrationMarketRow, ...]


@dataclass(slots=True, frozen=True)
class CryptoCalibrationExperimentCandidate:
    name: str
    barrier_model_config: CryptoBarrierModelConfig
    fusion_model_config: CryptoFusionModelConfig


@dataclass(slots=True, frozen=True)
class CryptoCalibrationExperimentResult:
    candidate_name: str
    train_score: float
    validation_score: float
    holdout_score: float
    aggregate_score: float
    accepted: bool


@dataclass(slots=True, frozen=True)
class CryptoCalibrationPromotionDecision:
    decision: str
    locked_baseline_candidate: str
    evaluated_locked_baseline: bool
    recommended_candidate: str
    reason: str


@dataclass(slots=True, frozen=True)
class CryptoCalibrationExperimentReport:
    generated_at: datetime
    baseline_candidate: str
    dataset_split: dict[str, str]
    results: tuple[CryptoCalibrationExperimentResult, ...]
    promotion_decision: CryptoCalibrationPromotionDecision


def generate_crypto_calibration_report(
    *,
    train_snapshot_path: str | Path,
    validation_snapshot_path: str | Path,
    holdout_snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    output_dir: str | Path | None = None,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
    residual_model_config: CryptoResidualModelConfig | None = None,
) -> CryptoCalibrationReport:
    baseline_preset, resolved_barrier_model_config, resolved_fusion_model_config, resolved_residual_model_config = resolve_crypto_calibration_model_configs(
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
        residual_model_config=residual_model_config,
    )
    dataset_specs = {
        "train": Path(train_snapshot_path),
        "validation": Path(validation_snapshot_path),
        "holdout": Path(holdout_snapshot_path),
    }

    all_rows: list[CryptoCalibrationMarketRow] = []
    dataset_reports: list[CryptoCalibrationDatasetReport] = []
    for dataset, snapshot_path in dataset_specs.items():
        rows = build_crypto_calibration_rows(
            dataset=dataset,
            snapshot_path=snapshot_path,
            underlying_states=underlying_states,
            barrier_model_config=resolved_barrier_model_config,
            fusion_model_config=resolved_fusion_model_config,
            residual_model_config=resolved_residual_model_config,
        )
        all_rows.extend(rows)
        dataset_reports.append(_build_dataset_report(dataset=dataset, snapshot_path=snapshot_path, rows=rows))

    report = CryptoCalibrationReport(
        generated_at=datetime.now(tz=timezone.utc),
        baseline_classification=_classify_baseline(tuple(dataset_reports)),
        rewritten_objective=(
            "Maximize repricing-aligned net-edge coverage on fixed crypto ladder windows "
            "while penalizing negative net-edge saturation and false-positive trade candidates."
        ),
        locked_parameters=(
            "starting_equity",
            "max_daily_drawdown_pct",
            "max_consecutive_losses",
            "max_open_orders",
            "daily_order_soft_limit",
            "daily_order_hard_limit",
            "paper_place_latency_ms",
            "paper_cancel_latency_ms",
            "paper_taker_slippage_bps",
        ),
        tunable_parameters=(
            "barrier_distance_coefficient",
            "barrier_probability_floor",
            "barrier_probability_ceiling",
            "fusion_barrier_weight",
            "fusion_surface_weight",
            "residual_min_confidence",
            "residual_max_abs_correction_bps",
            "min_net_edge_bps",
            "maker_min_edge_bps",
        ),
        score_formula=(
            "score = (40 * sign_alignment_rate) + (8 * positive_net_edge_count) "
            "- (0.02 * mean_abs_gap_bps) - (0.03 * max(-mean_net_edge_bps, 0))"
        ),
        dataset_split={
            "baseline_preset": baseline_preset.preset_id,
            "baseline_candidate": baseline_preset.candidate_name,
            "train": str(dataset_specs["train"]),
            "validation": str(dataset_specs["validation"]),
            "holdout": str(dataset_specs["holdout"]),
        },
        dominant_failure_mechanisms=_describe_failure_mechanisms(tuple(dataset_reports)),
        datasets=tuple(dataset_reports),
        market_rows=tuple(all_rows),
    )
    if output_dir is not None:
        write_crypto_calibration_report(report=report, output_dir=output_dir)
    return report


def build_crypto_calibration_rows(
    *,
    dataset: str,
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
    residual_model_config: CryptoResidualModelConfig | None = None,
) -> tuple[CryptoCalibrationMarketRow, ...]:
    snapshots = load_market_snapshots(snapshot_path)
    normalized_by_market_id: dict[str, CryptoMarketDefinition] = {}
    latest_probability_by_market_id: dict[str, float] = {}
    for snapshot in snapshots:
        normalized = normalize_crypto_market(snapshot)
        if normalized is None:
            continue
        probability = observed_mid_probability(
            snapshot.best_bid_yes,
            snapshot.best_ask_yes,
            snapshot.last_traded_price,
        )
        if probability is None:
            continue
        normalized_by_market_id[snapshot.market_id] = normalized
        latest_probability_by_market_id[snapshot.market_id] = probability

    first_snapshot_by_market_id: dict[str, MarketSnapshot] = {}
    cache_by_market_id: dict[str, MarketSnapshot] = {}
    fair_value_by_market_id: dict[str, FairValueEstimate] = {}
    grouped_market_ids = defaultdict(set)
    for market_id, normalized in normalized_by_market_id.items():
        grouped_market_ids[normalized.series_key].add(market_id)

    for snapshot in snapshots:
        normalized = normalize_crypto_market(snapshot)
        if normalized is None:
            continue
        probability = observed_mid_probability(
            snapshot.best_bid_yes,
            snapshot.best_ask_yes,
            snapshot.last_traded_price,
        )
        if probability is None:
            continue
        cache_by_market_id[snapshot.market_id] = snapshot
        if snapshot.market_id not in first_snapshot_by_market_id:
            first_snapshot_by_market_id[snapshot.market_id] = snapshot

        series_market_ids = grouped_market_ids.get(normalized.series_key)
        if not series_market_ids:
            continue
        if all(market_id in cache_by_market_id for market_id in series_market_ids):
            missing = [market_id for market_id in series_market_ids if market_id not in fair_value_by_market_id]
            if missing:
                fair_values = compute_crypto_phase1_fair_values_from_snapshots(
                    snapshots=tuple(cache_by_market_id[market_id] for market_id in sorted(series_market_ids)),
                    underlying_states=underlying_states,
                    barrier_model_config=barrier_model_config,
                    fusion_model_config=fusion_model_config,
                    residual_model_config=residual_model_config,
                )
                fair_value_by_market_id.update({item.market_id: item for item in fair_values})

    rows: list[CryptoCalibrationMarketRow] = []
    for market_id, fair_value in sorted(fair_value_by_market_id.items()):
        normalized = normalized_by_market_id.get(market_id)
        first_snapshot = first_snapshot_by_market_id.get(market_id)
        final_observed_probability = latest_probability_by_market_id.get(market_id)
        if normalized is None or first_snapshot is None or final_observed_probability is None:
            continue
        first_observed_probability = observed_mid_probability(
            first_snapshot.best_bid_yes,
            first_snapshot.best_ask_yes,
            first_snapshot.last_traded_price,
        )
        if first_observed_probability is None:
            continue
        gross_edge_bps = parse_float(fair_value.supporting_values, "gross_edge_bps") or 0.0
        net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
        barrier_probability = parse_float(fair_value.supporting_values, "barrier_probability") or fair_value.fair_probability
        surface_probability = parse_float(fair_value.supporting_values, "surface_probability")
        repricing_bps = (final_observed_probability - first_observed_probability) * 10000
        repricing_observed = abs(repricing_bps) >= 1.0
        sign_aligned = False
        if repricing_observed and abs(gross_edge_bps) >= 1.0:
            sign_aligned = (gross_edge_bps > 0 and repricing_bps > 0) or (gross_edge_bps < 0 and repricing_bps < 0)
        barrier_miss_bps = abs(barrier_probability - final_observed_probability) * 10000
        surface_reference = surface_probability if surface_probability is not None else barrier_probability
        surface_miss_bps = abs(surface_reference - final_observed_probability) * 10000
        fusion_miss_bps = abs(fair_value.fair_probability - final_observed_probability) * 10000
        late_repricing_miss_bps = abs(repricing_bps - gross_edge_bps)
        selection_miss = gross_edge_bps > 0 and repricing_observed and not sign_aligned
        rows.append(
            CryptoCalibrationMarketRow(
                dataset=dataset,
                market_id=market_id,
                instrument_key=normalized.normalized.instrument_key,
                underlying=normalized.underlying,
                event_family=normalized.event_family,
                direction=normalized.direction,
                timestamp=first_snapshot.timestamp,
                observed_probability=first_observed_probability,
                fair_probability=fair_value.fair_probability,
                barrier_probability=barrier_probability,
                surface_probability=surface_probability,
                gross_edge_bps=gross_edge_bps,
                net_edge_bps=net_edge_bps,
                final_observed_probability=final_observed_probability,
                repricing_bps=repricing_bps,
                barrier_miss_bps=barrier_miss_bps,
                surface_miss_bps=surface_miss_bps,
                fusion_miss_bps=fusion_miss_bps,
                late_repricing_miss_bps=late_repricing_miss_bps,
                repricing_observed=repricing_observed,
                sign_aligned=sign_aligned,
                selection_miss=selection_miss,
                confidence=fair_value.confidence,
                residual_diagnostic_tag=str(fair_value.supporting_values.get("residual_diagnostic_tag", "")),
            )
        )
    return tuple(rows)


def write_crypto_calibration_report(*, report: CryptoCalibrationReport, output_dir: str | Path) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "report.json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "markets.jsonl").write_text(
        "".join(json.dumps(_normalize(asdict(row)), ensure_ascii=True) + "\n" for row in report.market_rows),
        encoding="utf-8",
    )
    (target_dir / "summary.md").write_text(format_crypto_calibration_report(report), encoding="utf-8")


def run_crypto_calibration_experiments(
    *,
    train_snapshot_path: str | Path,
    validation_snapshot_path: str | Path,
    holdout_snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    output_dir: str | Path | None = None,
    candidate_set: str = "default",
) -> CryptoCalibrationExperimentReport:
    candidates = build_crypto_calibration_candidates(candidate_set)
    results: list[CryptoCalibrationExperimentResult] = []
    baseline_preset = get_locked_crypto_calibration_baseline_preset()
    dataset_split = {
        "baseline_preset": baseline_preset.preset_id,
        "baseline_candidate": baseline_preset.candidate_name,
        "train": str(Path(train_snapshot_path)),
        "validation": str(Path(validation_snapshot_path)),
        "holdout": str(Path(holdout_snapshot_path)),
    }
    for candidate in candidates:
        train = generate_crypto_calibration_report(
            train_snapshot_path=train_snapshot_path,
            validation_snapshot_path=validation_snapshot_path,
            holdout_snapshot_path=holdout_snapshot_path,
            underlying_states=underlying_states,
            barrier_model_config=candidate.barrier_model_config,
            fusion_model_config=candidate.fusion_model_config,
        )
        scores = {item.dataset: item.calibration_score for item in train.datasets}
        result = CryptoCalibrationExperimentResult(
            candidate_name=candidate.name,
            train_score=scores.get("train", 0.0),
            validation_score=scores.get("validation", 0.0),
            holdout_score=scores.get("holdout", 0.0),
            aggregate_score=(
                (scores.get("train", 0.0) * 0.5)
                + (scores.get("validation", 0.0) * 0.3)
                + (scores.get("holdout", 0.0) * 0.2)
            ),
            accepted=(scores.get("validation", 0.0) >= scores.get("train", 0.0) - 40.0 and scores.get("holdout", 0.0) > -90.0),
        )
        results.append(result)
    report = CryptoCalibrationExperimentReport(
        generated_at=datetime.now(tz=timezone.utc),
        baseline_candidate=baseline_preset.candidate_name,
        dataset_split=dataset_split,
        results=tuple(sorted(results, key=lambda item: item.aggregate_score, reverse=True)),
        promotion_decision=_build_crypto_calibration_promotion_decision(
            locked_baseline_candidate=baseline_preset.candidate_name,
            results=tuple(sorted(results, key=lambda item: item.aggregate_score, reverse=True)),
        ),
    )
    if output_dir is not None:
        write_crypto_calibration_experiment_report(report=report, output_dir=output_dir)
    return report


def build_default_crypto_calibration_candidates() -> tuple[CryptoCalibrationExperimentCandidate, ...]:
    return (
        CryptoCalibrationExperimentCandidate(
            name="baseline",
            barrier_model_config=CryptoBarrierModelConfig(),
            fusion_model_config=CryptoFusionModelConfig(),
        ),
        CryptoCalibrationExperimentCandidate(
            name="shallower-barrier",
            barrier_model_config=CryptoBarrierModelConfig(steepness=2.0),
            fusion_model_config=CryptoFusionModelConfig(),
        ),
        CryptoCalibrationExperimentCandidate(
            name="surface-heavier",
            barrier_model_config=CryptoBarrierModelConfig(),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.55, surface_weight=0.45),
        ),
        CryptoCalibrationExperimentCandidate(
            name="shallower-plus-surface",
            barrier_model_config=CryptoBarrierModelConfig(steepness=2.0),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.55, surface_weight=0.45),
        ),
        CryptoCalibrationExperimentCandidate(
            name="much-shallower-plus-surface",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.8),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.5, surface_weight=0.5),
        ),
    )


def build_refined_crypto_calibration_candidates() -> tuple[CryptoCalibrationExperimentCandidate, ...]:
    return (
        CryptoCalibrationExperimentCandidate(
            name="baseline",
            barrier_model_config=CryptoBarrierModelConfig(),
            fusion_model_config=CryptoFusionModelConfig(),
        ),
        CryptoCalibrationExperimentCandidate(
            name="r2-s185-b50-s50",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.85),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.5, surface_weight=0.5),
        ),
        CryptoCalibrationExperimentCandidate(
            name="r2-s180-b50-s50",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.8),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.5, surface_weight=0.5),
        ),
        CryptoCalibrationExperimentCandidate(
            name="r2-s175-b50-s50",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.75),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.5, surface_weight=0.5),
        ),
        CryptoCalibrationExperimentCandidate(
            name="r2-s180-b55-s45",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.8),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.55, surface_weight=0.45),
        ),
        CryptoCalibrationExperimentCandidate(
            name="r2-s180-b45-s55",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.8),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.45, surface_weight=0.55),
        ),
        CryptoCalibrationExperimentCandidate(
            name="r2-s175-b45-s55",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.75),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.45, surface_weight=0.55),
        ),
    )


def build_btc_refined_crypto_calibration_candidates() -> tuple[CryptoCalibrationExperimentCandidate, ...]:
    return (
        CryptoCalibrationExperimentCandidate(
            name="baseline",
            barrier_model_config=CryptoBarrierModelConfig(),
            fusion_model_config=CryptoFusionModelConfig(),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s175-b45-s55",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.75),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.45, surface_weight=0.55),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s170-b45-s55",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.7),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.45, surface_weight=0.55),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s165-b45-s55",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.45, surface_weight=0.55),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s170-b40-s60",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.7),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.4, surface_weight=0.6),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s165-b40-s60",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.4, surface_weight=0.6),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s160-b40-s60",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.6),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.4, surface_weight=0.6),
        ),
        CryptoCalibrationExperimentCandidate(
            name="btc-r1-s165-b35-s65",
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
        ),
    )


def build_crypto_calibration_candidates(candidate_set: str) -> tuple[CryptoCalibrationExperimentCandidate, ...]:
    if candidate_set == "default":
        return build_default_crypto_calibration_candidates()
    if candidate_set == "refined":
        return build_refined_crypto_calibration_candidates()
    if candidate_set == "btc_refined":
        return build_btc_refined_crypto_calibration_candidates()
    raise ValueError(f"Unsupported crypto calibration candidate set: {candidate_set}")


def write_crypto_calibration_experiment_report(
    *,
    report: CryptoCalibrationExperimentReport,
    output_dir: str | Path,
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "experiments.json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "experiments.md").write_text(
        format_crypto_calibration_experiment_report(report),
        encoding="utf-8",
    )


def format_crypto_calibration_experiment_report(report: CryptoCalibrationExperimentReport) -> str:
    lines = [
        "# Crypto Calibration Experiments",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- baseline_candidate: {report.baseline_candidate}",
        "",
        "## Dataset Split",
        "",
    ]
    lines.extend(f"- {name}: {path}" for name, path in sorted(report.dataset_split.items()))
    lines.extend(
        [
            "",
            "## Promotion Decision",
            "",
            f"- decision: {report.promotion_decision.decision}",
            f"- locked_baseline_candidate: {report.promotion_decision.locked_baseline_candidate}",
            f"- evaluated_locked_baseline: {str(report.promotion_decision.evaluated_locked_baseline).lower()}",
            f"- recommended_candidate: {report.promotion_decision.recommended_candidate}",
            f"- reason: {report.promotion_decision.reason}",
            "",
            "## Results",
            "",
        ]
    )
    for item in report.results:
        lines.extend(
            [
                f"### {item.candidate_name}",
                "",
                f"- train_score: {item.train_score:.2f}",
                f"- validation_score: {item.validation_score:.2f}",
                f"- holdout_score: {item.holdout_score:.2f}",
                f"- aggregate_score: {item.aggregate_score:.2f}",
                f"- accepted: {str(item.accepted).lower()}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def format_crypto_calibration_report(report: CryptoCalibrationReport) -> str:
    lines = [
        "# Crypto Calibration Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- baseline_classification: {report.baseline_classification}",
        f"- rewritten_objective: {report.rewritten_objective}",
        "",
        "## Locked Parameters",
        "",
    ]
    lines.extend(f"- {item}" for item in report.locked_parameters)
    lines.extend(["", "## Tunable Parameters", ""])
    lines.extend(f"- {item}" for item in report.tunable_parameters)
    lines.extend(["", "## Score Formula", "", f"- {report.score_formula}", "", "## Dataset Split", ""])
    lines.extend(f"- {name}: {path}" for name, path in sorted(report.dataset_split.items()))
    lines.extend(["", "## Failure Mechanisms", ""])
    lines.extend(f"- {item}" for item in report.dominant_failure_mechanisms)
    lines.extend(["", "## Dataset Reports", ""])
    for dataset in report.datasets:
        lines.extend(
            [
                f"### {dataset.dataset}",
                "",
                f"- snapshot_path: {dataset.snapshot_path}",
                f"- processed_snapshots: {dataset.processed_snapshots}",
                f"- market_count: {dataset.market_count}",
                f"- positive_gross_edge_count: {dataset.positive_gross_edge_count}",
                f"- positive_net_edge_count: {dataset.positive_net_edge_count}",
                f"- repricing_observed_count: {dataset.repricing_observed_count}",
                f"- repricing_aligned_count: {dataset.repricing_aligned_count}",
                f"- sign_alignment_rate: {dataset.sign_alignment_rate:.4f}",
                f"- mean_signed_gap_bps: {dataset.mean_signed_gap_bps:.2f}",
                f"- mean_abs_gap_bps: {dataset.mean_abs_gap_bps:.2f}",
                f"- mean_net_edge_bps: {dataset.mean_net_edge_bps:.2f}",
                f"- median_net_edge_bps: {dataset.median_net_edge_bps:.2f}",
                f"- mean_barrier_miss_bps: {dataset.mean_barrier_miss_bps:.2f}",
                f"- mean_surface_miss_bps: {dataset.mean_surface_miss_bps:.2f}",
                f"- mean_fusion_miss_bps: {dataset.mean_fusion_miss_bps:.2f}",
                f"- mean_late_repricing_miss_bps: {dataset.mean_late_repricing_miss_bps:.2f}",
                f"- selection_miss_count: {dataset.selection_miss_count}",
                f"- calibration_score: {dataset.calibration_score:.2f}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_dataset_report(
    *,
    dataset: str,
    snapshot_path: Path,
    rows: tuple[CryptoCalibrationMarketRow, ...],
) -> CryptoCalibrationDatasetReport:
    if not rows:
        return CryptoCalibrationDatasetReport(
            dataset=dataset,
            snapshot_path=str(snapshot_path),
            processed_snapshots=len(load_market_snapshots(snapshot_path)),
            market_count=0,
            positive_gross_edge_count=0,
            positive_net_edge_count=0,
            repricing_observed_count=0,
            repricing_aligned_count=0,
            sign_alignment_rate=0.0,
            mean_signed_gap_bps=0.0,
            mean_abs_gap_bps=0.0,
            mean_net_edge_bps=0.0,
            median_net_edge_bps=0.0,
            mean_barrier_miss_bps=0.0,
            mean_surface_miss_bps=0.0,
            mean_fusion_miss_bps=0.0,
            mean_late_repricing_miss_bps=0.0,
            selection_miss_count=0,
            calibration_score=0.0,
        )

    signed_gaps = [(row.fair_probability - row.observed_probability) * 10000 for row in rows]
    repricing_rows = [row for row in rows if row.repricing_observed]
    repricing_aligned_count = sum(1 for row in repricing_rows if row.sign_aligned)
    sign_alignment_rate = (
        repricing_aligned_count / len(repricing_rows)
        if repricing_rows
        else 0.0
    )
    mean_abs_gap_bps = mean(abs(value) for value in signed_gaps)
    mean_net_edge_bps = mean(row.net_edge_bps for row in rows)
    calibration_score = (
        (40.0 * sign_alignment_rate)
        + (8.0 * sum(1 for row in rows if row.net_edge_bps > 0))
        - (0.02 * mean_abs_gap_bps)
        - (0.03 * max(-mean_net_edge_bps, 0.0))
    )
    return CryptoCalibrationDatasetReport(
        dataset=dataset,
        snapshot_path=str(snapshot_path),
        processed_snapshots=len(load_market_snapshots(snapshot_path)),
        market_count=len(rows),
        positive_gross_edge_count=sum(1 for row in rows if row.gross_edge_bps > 0),
        positive_net_edge_count=sum(1 for row in rows if row.net_edge_bps > 0),
        repricing_observed_count=len(repricing_rows),
        repricing_aligned_count=repricing_aligned_count,
        sign_alignment_rate=sign_alignment_rate,
        mean_signed_gap_bps=mean(signed_gaps),
        mean_abs_gap_bps=mean_abs_gap_bps,
        mean_net_edge_bps=mean_net_edge_bps,
        median_net_edge_bps=median(row.net_edge_bps for row in rows),
        mean_barrier_miss_bps=mean(row.barrier_miss_bps for row in rows),
        mean_surface_miss_bps=mean(row.surface_miss_bps for row in rows),
        mean_fusion_miss_bps=mean(row.fusion_miss_bps for row in rows),
        mean_late_repricing_miss_bps=mean(row.late_repricing_miss_bps for row in rows),
        selection_miss_count=sum(1 for row in rows if row.selection_miss),
        calibration_score=calibration_score,
    )


def _classify_baseline(datasets: tuple[CryptoCalibrationDatasetReport, ...]) -> str:
    positive_net_edges = sum(item.positive_net_edge_count for item in datasets)
    market_count = sum(item.market_count for item in datasets)
    mean_signed_gap_bps = mean(item.mean_signed_gap_bps for item in datasets) if datasets else 0.0
    real_runtime_datasets = [item for item in datasets if "runtime" in item.snapshot_path.lower()]
    synthetic_positive_only = (
        positive_net_edges > 0
        and all(item.positive_net_edge_count == 0 for item in real_runtime_datasets)
        and all(
            item.positive_net_edge_count == 0 or "compare_snapshots" in item.snapshot_path.lower()
            for item in datasets
        )
    )
    if real_runtime_datasets and synthetic_positive_only and mean_signed_gap_bps < -250:
        return "alpha-bound"
    if market_count > 0 and positive_net_edges == 0 and mean_signed_gap_bps < -250:
        return "alpha-bound"
    if market_count > 0 and positive_net_edges == 0:
        return "execution-bound"
    return "mixed"


def _build_crypto_calibration_promotion_decision(
    *,
    locked_baseline_candidate: str,
    results: tuple[CryptoCalibrationExperimentResult, ...],
) -> CryptoCalibrationPromotionDecision:
    locked_baseline_result = next((item for item in results if item.candidate_name == locked_baseline_candidate), None)
    best_result = results[0] if results else None
    if best_result is None:
        return CryptoCalibrationPromotionDecision(
            decision="keep_locked_baseline",
            locked_baseline_candidate=locked_baseline_candidate,
            evaluated_locked_baseline=locked_baseline_result is not None,
            recommended_candidate=locked_baseline_candidate,
            reason="No experiment results were produced.",
        )
    if locked_baseline_result is None:
        return CryptoCalibrationPromotionDecision(
            decision="keep_locked_baseline",
            locked_baseline_candidate=locked_baseline_candidate,
            evaluated_locked_baseline=False,
            recommended_candidate=locked_baseline_candidate,
            reason="Locked baseline was not included in the candidate set, so this run is exploratory only.",
        )
    if best_result.candidate_name == locked_baseline_candidate:
        return CryptoCalibrationPromotionDecision(
            decision="keep_locked_baseline",
            locked_baseline_candidate=locked_baseline_candidate,
            evaluated_locked_baseline=True,
            recommended_candidate=locked_baseline_candidate,
            reason="Locked baseline remains the strongest evaluated candidate on aggregate score.",
        )
    if (
        best_result.accepted
        and best_result.validation_score >= locked_baseline_result.validation_score
        and best_result.holdout_score >= locked_baseline_result.holdout_score
        and best_result.aggregate_score > locked_baseline_result.aggregate_score
    ):
        return CryptoCalibrationPromotionDecision(
            decision="promote_candidate",
            locked_baseline_candidate=locked_baseline_candidate,
            evaluated_locked_baseline=True,
            recommended_candidate=best_result.candidate_name,
            reason=(
                f"{best_result.candidate_name} beat the locked baseline on validation, holdout, "
                "and aggregate score while remaining accepted."
            ),
        )
    return CryptoCalibrationPromotionDecision(
        decision="keep_locked_baseline",
        locked_baseline_candidate=locked_baseline_candidate,
        evaluated_locked_baseline=True,
        recommended_candidate=locked_baseline_candidate,
        reason=(
            f"{best_result.candidate_name} ranked first, but it did not clear the full promotion gate "
            "against the locked baseline."
        ),
    )
    return "mixed"


def _describe_failure_mechanisms(
    datasets: tuple[CryptoCalibrationDatasetReport, ...],
) -> tuple[str, ...]:
    real_windows = [item for item in datasets if "runtime" in item.snapshot_path.lower()]
    failures: list[str] = []
    if real_windows and all(item.positive_net_edge_count == 0 for item in real_windows):
        failures.append(
            "Real runtime ladder windows currently produce zero positive-net-edge candidates, which points to a conservative fair-value stack rather than an execution plumbing failure."
        )
    if any(item.repricing_aligned_count > 0 for item in datasets):
        failures.append(
            "Synthetic compare windows can still produce repricing-aligned candidates, so the execution path is functional and the bottleneck has shifted toward model calibration and market selection."
        )
    if not failures:
        failures.append("Calibration evidence is currently mixed and needs more runtime windows.")
    return tuple(failures)


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    return value
