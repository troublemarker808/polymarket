"""Experiment planning helpers for crypto phase2 tuning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.crypto.phase2.learning_report import (
    CryptoPhase2LearningReport,
    build_crypto_phase2_learning_report,
)


@dataclass(slots=True, frozen=True)
class CryptoPhase2TuningVariant:
    name: str
    focus: str
    overrides: dict[str, float | int]
    rationale: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoPhase2TuningPlan:
    learning_report: CryptoPhase2LearningReport
    latest_profit_focus: str
    secondary_profit_focus: str
    latest_tuning_priority: str
    experiment_family: str
    loss_ranking: tuple[str, ...]
    variants: tuple[CryptoPhase2TuningVariant, ...]


def build_crypto_phase2_tuning_plan(
    *,
    suite_paths: list[str | Path],
) -> CryptoPhase2TuningPlan:
    learning_report = build_crypto_phase2_learning_report(suite_paths=suite_paths)
    latest_suite = _load_suite_payload(suite_paths[-1]) if suite_paths else {}
    final_scorecard = latest_suite.get("final_scorecard", {})
    latest_profit_focus = (
        str(final_scorecard.get("profit_focus", "")).strip()
        if isinstance(final_scorecard, dict)
        else ""
    ) or learning_report.recommended_next_experiment
    secondary_profit_focus = (
        str(final_scorecard.get("secondary_profit_focus", "")).strip()
        if isinstance(final_scorecard, dict)
        else ""
    ) or latest_profit_focus
    latest_tuning_priority = (
        str(final_scorecard.get("tuning_priority", "")).strip()
        if isinstance(final_scorecard, dict)
        else ""
    ) or learning_report.recommended_next_experiment
    experiment_family = learning_report.recommended_next_experiment or latest_tuning_priority
    loss_ranking_raw = final_scorecard.get("loss_ranking", []) if isinstance(final_scorecard, dict) else []
    loss_ranking = tuple(str(item) for item in loss_ranking_raw if isinstance(item, str)) or (
        learning_report.recurring_loss_ranking
        if learning_report.recurring_loss_ranking
        else (latest_profit_focus, secondary_profit_focus)
    )

    variants = _build_variants_for_focus(
        focus=experiment_family,
        secondary_focus=secondary_profit_focus,
        loss_ranking=loss_ranking,
        learning_report=learning_report,
        final_scorecard=final_scorecard if isinstance(final_scorecard, dict) else {},
    )
    return CryptoPhase2TuningPlan(
        learning_report=learning_report,
        latest_profit_focus=latest_profit_focus,
        secondary_profit_focus=secondary_profit_focus,
        latest_tuning_priority=latest_tuning_priority,
        experiment_family=experiment_family,
        loss_ranking=loss_ranking,
        variants=variants,
    )


def format_crypto_phase2_tuning_plan(plan: CryptoPhase2TuningPlan) -> str:
    lines = [
        "# Crypto Phase 2 Tuning Plan",
        "",
        f"- run_count: {plan.learning_report.run_count}",
        f"- latest_profit_focus: {plan.latest_profit_focus}",
        f"- secondary_profit_focus: {plan.secondary_profit_focus}",
        f"- latest_tuning_priority: {plan.latest_tuning_priority}",
        f"- experiment_family: {plan.experiment_family}",
        f"- loss_ranking: {', '.join(plan.loss_ranking)}",
        f"- recommended_next_experiment: {plan.learning_report.recommended_next_experiment}",
        "",
        "## Variants",
        "",
    ]
    for variant in plan.variants:
        lines.append(f"### {variant.name}")
        lines.append("")
        lines.append(f"- focus: {variant.focus}")
        lines.append(f"- overrides: {_format_overrides(variant.overrides)}")
        lines.append(f"- rationale: {', '.join(variant.rationale)}")
        lines.append("")
    lines.append("## Learning Actions")
    lines.append("")
    lines.extend(f"- {action}" for action in plan.learning_report.recommended_actions)
    return "\n".join(lines).strip() + "\n"


def build_crypto_phase2_candidate_preset_registry(
    *,
    plan: CryptoPhase2TuningPlan,
    base_match: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    match = dict(base_match or {})
    if "underlying" not in match:
        match["underlying"] = "BTC"
    if "event_family" not in match and plan.experiment_family in {"selection", "pricing", "execution", "exit", "sizing"}:
        match["event_family"] = "reach"

    registry: dict[str, dict[str, object]] = {}
    for variant in plan.variants:
        registry[variant.name] = {
            "match": dict(match),
            "overrides": dict(variant.overrides),
            "rationale": list(variant.rationale),
            "focus": variant.focus,
        }
    return registry


def write_crypto_phase2_tuning_plan(
    *,
    plan: CryptoPhase2TuningPlan,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_crypto_phase2_tuning_plan(plan), encoding="utf-8")
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(plan)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def write_crypto_phase2_candidate_preset_registry(
    *,
    plan: CryptoPhase2TuningPlan,
    output_path: str | Path,
    base_match: dict[str, str] | None = None,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    registry = build_crypto_phase2_candidate_preset_registry(plan=plan, base_match=base_match)
    target_path.write_text(
        json.dumps(registry, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _build_variants_for_focus(
    *,
    focus: str,
    secondary_focus: str,
    loss_ranking: tuple[str, ...],
    learning_report: CryptoPhase2LearningReport,
    final_scorecard: dict[str, Any],
) -> tuple[CryptoPhase2TuningVariant, ...]:
    variants: list[CryptoPhase2TuningVariant] = []
    if focus == "execution":
        variants.extend(
            [
                CryptoPhase2TuningVariant(
                    name="execution_faster_quotes",
                    focus=focus,
                    overrides={"maker_quote_ttl_seconds": 45, "maker_aggressiveness": 1.15},
                    rationale=("reduce expiration pressure", "improve maker fill rate"),
                ),
                CryptoPhase2TuningVariant(
                    name="execution_faster_taker",
                    focus=focus,
                    overrides={"taker_urgency_threshold": 0.64},
                    rationale=("reduce missed fills", "test more aggressive taker routing"),
                ),
            ]
        )
        if secondary_focus == "exit":
            variants.append(
                CryptoPhase2TuningVariant(
                    name="execution_exit_guard",
                    focus="execution+exit",
                    overrides={
                        "maker_quote_ttl_seconds": 45,
                        "maker_aggressiveness": 1.1,
                        "aging_exit_edge_bps": 125.0,
                        "max_holding_multiplier": 1.5,
                    },
                    rationale=("execution is weakest and exit is the next drag", "improve fills without leaving weak positions stale"),
                )
            )
        if learning_report.average_edge_capture_ratio < 0.5:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="execution_capture_repricing",
                    focus="execution+pricing",
                    overrides={
                        "maker_quote_ttl_seconds": 40,
                        "maker_aggressiveness": 1.1,
                        "min_net_edge_bps": 100.0,
                    },
                    rationale=("execution edge capture remains weak across repeated runs", "pair faster quoting with cleaner edge requirements"),
                )
            )
        if learning_report.average_trade_execution_drag_bps >= 20.0:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="execution_trade_drag_guard",
                    focus="execution",
                    overrides={"maker_quote_ttl_seconds": 35, "maker_aggressiveness": 1.15, "taker_urgency_threshold": 0.62},
                    rationale=("trade-level execution drag remains elevated", "reduce quote decay and missed capture before widening flow"),
                )
            )
    elif focus == "exit":
        variants.extend(
            [
                CryptoPhase2TuningVariant(
                    name="exit_faster_recycle",
                    focus=focus,
                    overrides={"aging_exit_edge_bps": 125.0, "max_holding_multiplier": 1.5},
                    rationale=("recycle weak positions faster", "reduce prolonged stop-out drift"),
                ),
                CryptoPhase2TuningVariant(
                    name="exit_tighter_stale_cleanup",
                    focus=focus,
                    overrides={"stale_exit_edge_bps": 220.0, "stale_start_fraction": 0.85},
                    rationale=("exit stale positions earlier", "cut repeated negative closes"),
                ),
            ]
        )
        if secondary_focus == "execution":
            variants.append(
                CryptoPhase2TuningVariant(
                    name="exit_execution_recycle",
                    focus="exit+execution",
                    overrides={
                        "aging_exit_edge_bps": 125.0,
                        "max_holding_multiplier": 1.5,
                        "taker_urgency_threshold": 0.64,
                    },
                    rationale=("exit is weakest and execution is the next drag", "recycle weak positions faster while reducing missed fills"),
                )
            )
        if learning_report.average_loss_trade_pnl < 0 and abs(learning_report.average_loss_trade_pnl) > max(learning_report.average_win_trade_pnl, 0.01):
            variants.append(
                CryptoPhase2TuningVariant(
                    name="exit_loss_asymmetry_guard",
                    focus="exit",
                    overrides={"aging_exit_edge_bps": 115.0, "max_holding_multiplier": 1.35, "stop_loss_bps": 225.0},
                    rationale=("losing closes remain larger than winning closes across repeated runs", "tighten exit asymmetry before expanding flow"),
                )
            )
        if learning_report.average_stop_loss_exit_share >= 0.25:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="exit_stop_loss_cluster_guard",
                    focus="exit",
                    overrides={"stop_loss_bps": 225.0, "stop_loss_max_remaining_edge_bps": 125.0},
                    rationale=("stop-loss exits dominate repeated closes", "tighten repeated stop-loss clusters before increasing flow"),
                )
            )
        if learning_report.average_passive_cleanup_exit_share >= 0.35:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="exit_passive_cleanup_guard",
                    focus="exit",
                    overrides={"aging_exit_edge_bps": 110.0, "stale_start_fraction": 0.9, "stale_exit_edge_bps": 240.0},
                    rationale=("too many exits rely on aging or stale cleanup", "recycle weak positions earlier instead of waiting for passive cleanup"),
                )
            )
        if learning_report.average_exit_family_balance_score < 0.5:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="exit_family_rebalance_guard",
                    focus="exit",
                    overrides={"aging_exit_edge_bps": 105.0, "stale_start_fraction": 0.88, "max_holding_multiplier": 1.3},
                    rationale=("exit families remain skewed toward defensive cleanup", "rebalance toward earlier thesis-aware recycling"),
                )
            )
    elif focus == "sizing":
        variants.extend(
            [
                CryptoPhase2TuningVariant(
                    name="sizing_smaller_clip",
                    focus=focus,
                    overrides={"default_notional": 4.0},
                    rationale=("reduce loss per trade", "stabilize negative average trade pnl"),
                ),
                CryptoPhase2TuningVariant(
                    name="sizing_higher_edge_gate",
                    focus=focus,
                    overrides={"min_net_edge_bps": 95.0, "default_notional": 4.5},
                    rationale=("only size into cleaner edges", "avoid low-value flow"),
                ),
            ]
        )
        if secondary_focus == "execution":
            variants.append(
                CryptoPhase2TuningVariant(
                    name="sizing_execution_smaller_faster",
                    focus="sizing+execution",
                    overrides={"default_notional": 4.0, "taker_urgency_threshold": 0.64},
                    rationale=("reduce loss per trade", "pair smaller clips with faster completion on weak execution runs"),
                )
            )
        if learning_report.average_pnl_per_notional <= 0.0:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="sizing_pnl_efficiency_guard",
                    focus="sizing",
                    overrides={"default_notional": 3.75, "min_net_edge_bps": 100.0},
                    rationale=("pnl per notional remains non-positive across repeated runs", "reduce deployed capital until efficiency improves"),
                )
            )
        if learning_report.average_large_notional_share >= 0.3 and learning_report.average_pnl_per_notional <= 0.0:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="sizing_large_clip_concentration_guard",
                    focus="sizing",
                    overrides={"default_notional": 3.5, "min_net_edge_bps": 102.0},
                    rationale=("too much flow remains concentrated in larger clips", "force smaller sizing until larger buckets prove efficient"),
                )
            )
        if learning_report.average_large_bucket_pnl_per_notional < learning_report.average_small_bucket_pnl_per_notional - 0.01:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="sizing_bucket_efficiency_guard",
                    focus="sizing",
                    overrides={"default_notional": 3.5, "min_net_edge_bps": 105.0},
                    rationale=("large sizing buckets underperform small clips", "force sizing back toward proven efficient buckets"),
                )
            )
    elif focus == "pricing":
        variants.extend(
            [
                CryptoPhase2TuningVariant(
                    name="pricing_higher_edge_filter",
                    focus=focus,
                    overrides={"min_net_edge_bps": 100.0},
                    rationale=("reduce mispriced entries", "force cleaner calibration residuals"),
                ),
                CryptoPhase2TuningVariant(
                    name="pricing_wider_confidence_gate",
                    focus=focus,
                    overrides={"min_confidence": 0.68},
                    rationale=("only trade higher-confidence fair values", "test calibration discipline"),
                ),
            ]
        )
        if secondary_focus == "selection":
            variants.append(
                CryptoPhase2TuningVariant(
                    name="pricing_selection_high_confidence",
                    focus="pricing+selection",
                    overrides={"min_net_edge_bps": 105.0, "min_confidence": 0.68},
                    rationale=("pricing is weakest and selection is next", "only keep higher-confidence, higher-edge ladders"),
                )
            )
        if learning_report.average_edge_capture_ratio < 0.5:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="pricing_capture_high_confidence",
                    focus="pricing+execution",
                    overrides={"min_net_edge_bps": 105.0, "min_confidence": 0.7, "maker_quote_ttl_seconds": 40},
                    rationale=("pricing is weak and realized edge capture remains soft", "raise confidence while reducing quote decay"),
                )
            )
        if learning_report.average_fusion_observed_gap_bps >= 125:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="pricing_repricing_capture_guard",
                    focus="pricing+execution",
                    overrides={"min_net_edge_bps": 110.0, "maker_quote_ttl_seconds": 35},
                    rationale=("fused fair values still sit too far from observed pricing", "tighten repricing edge requirements while reducing quote decay"),
                )
            )
        if learning_report.average_trade_expected_edge_bps > 0 and learning_report.average_trade_realized_pnl_bps <= 0:
            variants.append(
                CryptoPhase2TuningVariant(
                    name="pricing_realization_gap_guard",
                    focus="pricing+execution",
                    overrides={"min_net_edge_bps": 110.0, "min_confidence": 0.72, "maker_quote_ttl_seconds": 35},
                    rationale=("trade-level realized pnl remains negative despite positive expected edge", "tighten pricing and reduce quote decay together"),
                )
            )
    else:
        variants.extend(
            [
                CryptoPhase2TuningVariant(
                    name="selection_higher_edge_gate",
                    focus="selection",
                    overrides={"min_net_edge_bps": 100.0},
                    rationale=("filter weaker candidates earlier", "improve order conversion quality"),
                ),
                CryptoPhase2TuningVariant(
                    name="selection_tighter_spread_gate",
                    focus="selection",
                    overrides={"max_spread_bps": 175.0},
                    rationale=("exclude noisy wide-spread markets", "improve realized execution quality"),
                ),
            ]
        )
        if secondary_focus == "pricing":
            variants.append(
                CryptoPhase2TuningVariant(
                    name="selection_pricing_high_confidence",
                    focus="selection+pricing",
                    overrides={"min_net_edge_bps": 105.0, "min_confidence": 0.68},
                    rationale=("selection is weakest and pricing is next", "tighten edge and confidence gates together"),
                )
            )

    if (
        isinstance(final_scorecard.get("execution_loss"), (int, float))
        and float(final_scorecard.get("execution_loss", 0.0)) >= 0.3
        and all("default_notional" not in variant.overrides for variant in variants)
    ):
        variants.append(
            CryptoPhase2TuningVariant(
                name=f"{focus}_smaller_clip_guard",
                focus=focus,
                overrides={"default_notional": 4.25},
                rationale=("execution loss remains elevated", "guard against oversizing while retuning"),
            )
        )

    if len(variants) >= 2 and loss_ranking[:2] == ("execution", "sizing") and all(
        variant.name != "execution_sizing_balanced"
        for variant in variants
    ):
        variants.append(
            CryptoPhase2TuningVariant(
                name="execution_sizing_balanced",
                focus="execution+sizing",
                overrides={"default_notional": 4.25, "maker_quote_ttl_seconds": 45, "maker_aggressiveness": 1.1},
                rationale=("execution and sizing are both elevated losses", "balance clip reduction with faster fill handling"),
            )
        )

    if learning_report.run_count < 2:
        variants = [
            CryptoPhase2TuningVariant(
                name="collect_more_runs",
                focus="evidence",
                overrides={},
                rationale=("insufficient repeat evidence", "collect another suite before changing presets"),
            )
        ]
    return tuple(variants)


def _load_suite_payload(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _format_overrides(overrides: dict[str, float | int]) -> str:
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
