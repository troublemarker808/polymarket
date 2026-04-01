"""Final crypto phase2 scorecard and recommendation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pm_bot.strategies.crypto.phase2.suite import CryptoPhase2ReplayDigest, CryptoPhase2SuiteResult


@dataclass(slots=True, frozen=True)
class _CryptoPromotionGateEvaluation:
    decision: str
    stage_label: str
    blocking_reasons: tuple[str, ...]
    min_closed_trades: int
    min_edge_capture_ratio: float
    max_execution_loss_ratio: float
    min_pnl_per_notional: float
    observed_execution_loss_ratio: float
    max_single_loss_pnl: float
    max_top3_loss_concentration_ratio: float
    observed_max_single_loss_pnl: float
    observed_top3_loss_concentration_ratio: float


@dataclass(slots=True, frozen=True)
class _CryptoRouteStageGateEvaluation:
    acceptance_decision: str
    statuses: dict[str, str]
    blockers: dict[str, tuple[str, ...]]
    failed_stages: tuple[str, ...]


_PROMOTION_MIN_CLOSED_TRADES = 3
_PROMOTION_MIN_EDGE_CAPTURE_RATIO = 0.35
_PROMOTION_MAX_EXECUTION_LOSS_RATIO = 0.65
_PROMOTION_MIN_PNL_PER_NOTIONAL = 0.0
_PROMOTION_MAX_SINGLE_LOSS_PNL = -0.20
_PROMOTION_MAX_TOP3_LOSS_CONCENTRATION_RATIO = 0.75


@dataclass(slots=True, frozen=True)
class CryptoPhase2FinalScorecard:
    generated_at: datetime
    recommended_action: str
    readiness_score: float
    execution_quality: str
    evidence_status: str
    route_stage_acceptance_decision: str
    route_stage_failed_stages: tuple[str, ...]
    route_stage_statuses: dict[str, str]
    route_stage_blockers: dict[str, tuple[str, ...]]
    dominant_route_stage_blocker: str | None
    next_constrained_action: str
    reasons: tuple[str, ...]
    blocked_series_keys: tuple[str, ...]
    filtered_orders: int
    filtered_signals: int
    filtered_pnl: float
    filtered_status: str
    filter_order_delta: int
    selection_quality_score: float
    pricing_quality_score: float
    execution_quality_score: float
    exit_quality_score: float
    sizing_quality_score: float
    average_signal_edge_bps: float
    average_adverse_fill_bps: float
    expected_edge_capture_bps: float
    edge_capture_ratio: float
    average_trade_expected_edge_bps: float
    average_trade_execution_drag_bps: float
    average_trade_realized_pnl_bps: float
    average_barrier_observed_gap_bps: float
    average_surface_observed_gap_bps: float
    average_fusion_observed_gap_bps: float
    average_barrier_surface_disagreement_bps: float
    closed_trade_count: int
    winning_trade_rate: float
    average_win_trade_pnl: float
    average_loss_trade_pnl: float
    average_submitted_notional: float
    large_notional_share: float
    dominant_exit_reason: str
    stop_loss_exit_share: float
    passive_cleanup_exit_share: float
    exit_family_balance_score: float
    small_bucket_pnl_per_notional: float
    medium_bucket_pnl_per_notional: float
    large_bucket_pnl_per_notional: float
    submitted_notional: float
    pnl_per_notional: float
    profit_focus: str
    secondary_profit_focus: str
    loss_ranking: tuple[str, ...]
    selection_loss: float
    pricing_loss: float
    execution_loss: float
    exit_loss: float
    sizing_loss: float
    total_profit_loss: float
    tuning_priority: str
    tuning_actions: tuple[str, ...]
    component_reasons: dict[str, tuple[str, ...]]
    promotion_decision: str
    promotion_stage_label: str
    promotion_blocking_reasons: tuple[str, ...]
    promotion_min_closed_trades: int
    promotion_min_edge_capture_ratio: float
    promotion_max_execution_loss_ratio: float
    promotion_min_pnl_per_notional: float
    observed_execution_loss_ratio: float
    promotion_max_single_loss_pnl: float
    promotion_max_top3_loss_concentration_ratio: float
    observed_max_single_loss_pnl: float
    observed_top3_loss_concentration_ratio: float
    top_loss_trades: tuple[dict[str, Any], ...]
    top_loss_market_breakdown: tuple[dict[str, Any], ...]
    top_loss_signature_breakdown: tuple[dict[str, Any], ...]


def build_crypto_phase2_final_scorecard(
    suite_result: CryptoPhase2SuiteResult,
) -> CryptoPhase2FinalScorecard:
    reasons: list[str] = []
    execution_quality = "stable"
    evidence_status = "ready"
    filtered = suite_result.filtered_replay
    unfiltered = suite_result.unfiltered_replay
    filter_order_delta = filtered.submitted_orders - unfiltered.submitted_orders

    if filtered.status == "halted":
        reasons.append("filtered replay halted")
        execution_quality = "unstable"
        evidence_status = "blocked"
    if filtered.submitted_orders <= 0:
        reasons.append("filtered replay produced no submitted orders")
        evidence_status = "thin"
    if filtered.signals_generated <= 0:
        reasons.append("filtered replay produced no signals")
    if filtered.today_pnl < 0 and filtered.closed_trade_count > 0:
        reasons.append("filtered replay pnl is negative")
        execution_quality = "fragile"
    if filter_order_delta < 0:
        reasons.append("selection filter removed more orders than it stabilized")
        execution_quality = "fragile"
    if suite_result.selection_blocked_series_keys:
        reasons.append("selection filter still blocks runtime ladder families")
    promotion_gate = _evaluate_btc_promotion_gate(filtered=filtered)
    route_stage_gate = _evaluate_route_stage_gates(
        filtered=filtered,
        unfiltered=unfiltered,
        blocked_series_keys=suite_result.selection_blocked_series_keys,
        promotion_gate=promotion_gate,
        filter_order_delta=filter_order_delta,
    )
    recommended_action = _merge_decisions(route_stage_gate.acceptance_decision, promotion_gate.decision)
    if route_stage_gate.failed_stages:
        reasons.extend(
            f"route stage blocked: {stage} ({', '.join(route_stage_gate.blockers.get(stage, ())) or 'unknown'})"
            for stage in route_stage_gate.failed_stages
        )
    if promotion_gate.blocking_reasons:
        reasons.extend(f"promotion gate blocked: {reason}" for reason in promotion_gate.blocking_reasons)

    score = 1.0
    if filtered.status == "halted":
        score -= 0.45
    if filtered.submitted_orders <= 0:
        score -= 0.25
    if filtered.signals_generated <= 0:
        score -= 0.15
    if filtered.today_pnl < 0 and filtered.closed_trade_count > 0:
        score -= 0.1
    if filter_order_delta < 0:
        score -= 0.05
    if route_stage_gate.acceptance_decision == "pause":
        score -= 0.2
    elif route_stage_gate.acceptance_decision == "review":
        score -= 0.1
    if promotion_gate.decision == "pause":
        score -= 0.2
    elif promotion_gate.decision == "review":
        score -= 0.1
    readiness_score = max(0.0, round(score, 4))
    component_scores, component_losses, profit_focus = _profit_component_scores(
        filtered=filtered,
        unfiltered=unfiltered,
        blocked_series_keys=suite_result.selection_blocked_series_keys,
    )
    loss_ranking = tuple(
        component
        for component, _loss in sorted(
            component_losses.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    secondary_profit_focus = loss_ranking[1] if len(loss_ranking) > 1 else profit_focus
    tuning_priority, tuning_actions = _tuning_recommendations(
        weakest_component=profit_focus,
        secondary_component=secondary_profit_focus,
        filtered=filtered,
        component_losses=component_losses,
    )
    dominant_route_stage_blocker = _dominant_route_stage_blocker(route_stage_gate)
    next_constrained_action = _next_constrained_action(route_stage_gate)

    return CryptoPhase2FinalScorecard(
        generated_at=suite_result.generated_at,
        recommended_action=recommended_action,
        readiness_score=readiness_score,
        execution_quality=execution_quality,
        evidence_status=evidence_status,
        route_stage_acceptance_decision=route_stage_gate.acceptance_decision,
        route_stage_failed_stages=route_stage_gate.failed_stages,
        route_stage_statuses=route_stage_gate.statuses,
        route_stage_blockers=route_stage_gate.blockers,
        dominant_route_stage_blocker=dominant_route_stage_blocker,
        next_constrained_action=next_constrained_action,
        reasons=tuple(reasons) if reasons else ("filtered replay stable enough for continued promotion",),
        blocked_series_keys=suite_result.selection_blocked_series_keys,
        filtered_orders=filtered.submitted_orders,
        filtered_signals=filtered.signals_generated,
        filtered_pnl=filtered.today_pnl,
        filtered_status=filtered.status,
        filter_order_delta=filter_order_delta,
        selection_quality_score=component_scores["selection"][0],
        pricing_quality_score=component_scores["pricing"][0],
        execution_quality_score=component_scores["execution"][0],
        exit_quality_score=component_scores["exit"][0],
        sizing_quality_score=component_scores["sizing"][0],
        average_signal_edge_bps=filtered.average_signal_edge_bps,
        average_adverse_fill_bps=filtered.average_adverse_fill_bps,
        expected_edge_capture_bps=filtered.expected_edge_capture_bps,
        edge_capture_ratio=filtered.edge_capture_ratio,
        average_trade_expected_edge_bps=filtered.average_trade_expected_edge_bps,
        average_trade_execution_drag_bps=filtered.average_trade_execution_drag_bps,
        average_trade_realized_pnl_bps=filtered.average_trade_realized_pnl_bps,
        average_barrier_observed_gap_bps=filtered.average_barrier_observed_gap_bps,
        average_surface_observed_gap_bps=filtered.average_surface_observed_gap_bps,
        average_fusion_observed_gap_bps=filtered.average_fusion_observed_gap_bps,
        average_barrier_surface_disagreement_bps=filtered.average_barrier_surface_disagreement_bps,
        closed_trade_count=filtered.closed_trade_count,
        winning_trade_rate=filtered.winning_trade_rate,
        average_win_trade_pnl=filtered.average_win_trade_pnl,
        average_loss_trade_pnl=filtered.average_loss_trade_pnl,
        average_submitted_notional=filtered.average_submitted_notional,
        large_notional_share=filtered.large_notional_share,
        dominant_exit_reason=filtered.dominant_exit_reason,
        stop_loss_exit_share=filtered.stop_loss_exit_share,
        passive_cleanup_exit_share=filtered.passive_cleanup_exit_share,
        exit_family_balance_score=filtered.exit_family_balance_score,
        small_bucket_pnl_per_notional=filtered.small_bucket_pnl_per_notional,
        medium_bucket_pnl_per_notional=filtered.medium_bucket_pnl_per_notional,
        large_bucket_pnl_per_notional=filtered.large_bucket_pnl_per_notional,
        submitted_notional=filtered.submitted_notional,
        pnl_per_notional=((filtered.closed_trade_net_pnl / filtered.submitted_notional) if filtered.submitted_notional > 0 else 0.0),
        profit_focus=profit_focus,
        secondary_profit_focus=secondary_profit_focus,
        loss_ranking=loss_ranking,
        selection_loss=component_losses["selection"],
        pricing_loss=component_losses["pricing"],
        execution_loss=component_losses["execution"],
        exit_loss=component_losses["exit"],
        sizing_loss=component_losses["sizing"],
        total_profit_loss=round(sum(component_losses.values()), 4),
        tuning_priority=tuning_priority,
        tuning_actions=tuning_actions,
        component_reasons={key: value[1] for key, value in component_scores.items()},
        promotion_decision=promotion_gate.decision,
        promotion_stage_label=promotion_gate.stage_label,
        promotion_blocking_reasons=promotion_gate.blocking_reasons,
        promotion_min_closed_trades=promotion_gate.min_closed_trades,
        promotion_min_edge_capture_ratio=promotion_gate.min_edge_capture_ratio,
        promotion_max_execution_loss_ratio=promotion_gate.max_execution_loss_ratio,
        promotion_min_pnl_per_notional=promotion_gate.min_pnl_per_notional,
        observed_execution_loss_ratio=promotion_gate.observed_execution_loss_ratio,
        promotion_max_single_loss_pnl=promotion_gate.max_single_loss_pnl,
        promotion_max_top3_loss_concentration_ratio=promotion_gate.max_top3_loss_concentration_ratio,
        observed_max_single_loss_pnl=promotion_gate.observed_max_single_loss_pnl,
        observed_top3_loss_concentration_ratio=promotion_gate.observed_top3_loss_concentration_ratio,
        top_loss_trades=filtered.top_loss_trades,
        top_loss_market_breakdown=filtered.top_loss_market_breakdown,
        top_loss_signature_breakdown=filtered.top_loss_signature_breakdown,
    )


def format_crypto_phase2_final_scorecard(scorecard: CryptoPhase2FinalScorecard) -> str:
    lines = [
        "# Crypto Phase 2 Final Scorecard",
        "",
        f"- recommended_action: {scorecard.recommended_action}",
        f"- readiness_score: {scorecard.readiness_score:.4f}",
        f"- execution_quality: {scorecard.execution_quality}",
        f"- evidence_status: {scorecard.evidence_status}",
        f"- route_stage_acceptance_decision: {scorecard.route_stage_acceptance_decision}",
        f"- route_stage_failed_stages: {', '.join(scorecard.route_stage_failed_stages) if scorecard.route_stage_failed_stages else 'none'}",
        f"- dominant_route_stage_blocker: {scorecard.dominant_route_stage_blocker or 'none'}",
        f"- next_constrained_action: {scorecard.next_constrained_action}",
        f"- filtered_orders: {scorecard.filtered_orders}",
        f"- filtered_signals: {scorecard.filtered_signals}",
        f"- filtered_pnl: {scorecard.filtered_pnl:.6f}",
        f"- filtered_status: {scorecard.filtered_status}",
        f"- filter_order_delta: {scorecard.filter_order_delta}",
        f"- profit_focus: {scorecard.profit_focus}",
        f"- secondary_profit_focus: {scorecard.secondary_profit_focus}",
        f"- loss_ranking: {', '.join(scorecard.loss_ranking)}",
        f"- blocked_series_keys: {', '.join(scorecard.blocked_series_keys) if scorecard.blocked_series_keys else 'none'}",
        "",
        "## BTC Promotion Gate",
        "",
        f"- promotion_decision: {scorecard.promotion_decision}",
        f"- promotion_stage_label: {scorecard.promotion_stage_label}",
        f"- promotion_min_closed_trades: {scorecard.promotion_min_closed_trades}",
        f"- promotion_min_edge_capture_ratio: {scorecard.promotion_min_edge_capture_ratio:.4f}",
        f"- promotion_max_execution_loss_ratio: {scorecard.promotion_max_execution_loss_ratio:.4f}",
        f"- promotion_min_pnl_per_notional: {scorecard.promotion_min_pnl_per_notional:.6f}",
        f"- observed_execution_loss_ratio: {scorecard.observed_execution_loss_ratio:.4f}",
        f"- promotion_max_single_loss_pnl: {scorecard.promotion_max_single_loss_pnl:.6f}",
        f"- promotion_max_top3_loss_concentration_ratio: {scorecard.promotion_max_top3_loss_concentration_ratio:.4f}",
        f"- observed_max_single_loss_pnl: {scorecard.observed_max_single_loss_pnl:.6f}",
        f"- observed_top3_loss_concentration_ratio: {scorecard.observed_top3_loss_concentration_ratio:.4f}",
        f"- promotion_blocking_reasons: {', '.join(scorecard.promotion_blocking_reasons) if scorecard.promotion_blocking_reasons else 'none'}",
        "",
        "## Route Stage Gates",
        "",
        f"- scan_quality: {scorecard.route_stage_statuses.get('scan_quality', 'unknown')}",
        f"- scan_quality_blockers: {', '.join(scorecard.route_stage_blockers.get('scan_quality', ())) if scorecard.route_stage_blockers.get('scan_quality', ()) else 'none'}",
        f"- selection_pass_through: {scorecard.route_stage_statuses.get('selection_pass_through', 'unknown')}",
        f"- selection_pass_through_blockers: {', '.join(scorecard.route_stage_blockers.get('selection_pass_through', ())) if scorecard.route_stage_blockers.get('selection_pass_through', ()) else 'none'}",
        f"- route_conversion_quality: {scorecard.route_stage_statuses.get('route_conversion_quality', 'unknown')}",
        f"- route_conversion_quality_blockers: {', '.join(scorecard.route_stage_blockers.get('route_conversion_quality', ())) if scorecard.route_stage_blockers.get('route_conversion_quality', ()) else 'none'}",
        f"- close_out_quality: {scorecard.route_stage_statuses.get('close_out_quality', 'unknown')}",
        f"- close_out_quality_blockers: {', '.join(scorecard.route_stage_blockers.get('close_out_quality', ())) if scorecard.route_stage_blockers.get('close_out_quality', ()) else 'none'}",
        f"- profitability_tail_risk: {scorecard.route_stage_statuses.get('profitability_tail_risk', 'unknown')}",
        f"- profitability_tail_risk_blockers: {', '.join(scorecard.route_stage_blockers.get('profitability_tail_risk', ())) if scorecard.route_stage_blockers.get('profitability_tail_risk', ()) else 'none'}",
        "",
        "## Profit Components",
        "",
        f"- selection_quality_score: {scorecard.selection_quality_score:.4f}",
        f"- pricing_quality_score: {scorecard.pricing_quality_score:.4f}",
        f"- execution_quality_score: {scorecard.execution_quality_score:.4f}",
        f"- exit_quality_score: {scorecard.exit_quality_score:.4f}",
        f"- sizing_quality_score: {scorecard.sizing_quality_score:.4f}",
        f"- average_signal_edge_bps: {scorecard.average_signal_edge_bps:.4f}",
        f"- average_adverse_fill_bps: {scorecard.average_adverse_fill_bps:.4f}",
        f"- expected_edge_capture_bps: {scorecard.expected_edge_capture_bps:.4f}",
        f"- edge_capture_ratio: {scorecard.edge_capture_ratio:.4f}",
        f"- average_trade_expected_edge_bps: {scorecard.average_trade_expected_edge_bps:.4f}",
        f"- average_trade_execution_drag_bps: {scorecard.average_trade_execution_drag_bps:.4f}",
        f"- average_trade_realized_pnl_bps: {scorecard.average_trade_realized_pnl_bps:.4f}",
        f"- average_barrier_observed_gap_bps: {scorecard.average_barrier_observed_gap_bps:.4f}",
        f"- average_surface_observed_gap_bps: {scorecard.average_surface_observed_gap_bps:.4f}",
        f"- average_fusion_observed_gap_bps: {scorecard.average_fusion_observed_gap_bps:.4f}",
        f"- average_barrier_surface_disagreement_bps: {scorecard.average_barrier_surface_disagreement_bps:.4f}",
        f"- closed_trade_count: {scorecard.closed_trade_count}",
        f"- winning_trade_rate: {scorecard.winning_trade_rate:.4f}",
        f"- average_win_trade_pnl: {scorecard.average_win_trade_pnl:.6f}",
        f"- average_loss_trade_pnl: {scorecard.average_loss_trade_pnl:.6f}",
        f"- average_submitted_notional: {scorecard.average_submitted_notional:.6f}",
        f"- large_notional_share: {scorecard.large_notional_share:.4f}",
        f"- dominant_exit_reason: {scorecard.dominant_exit_reason}",
        f"- stop_loss_exit_share: {scorecard.stop_loss_exit_share:.4f}",
        f"- passive_cleanup_exit_share: {scorecard.passive_cleanup_exit_share:.4f}",
        f"- exit_family_balance_score: {scorecard.exit_family_balance_score:.4f}",
        f"- small_bucket_pnl_per_notional: {scorecard.small_bucket_pnl_per_notional:.6f}",
        f"- medium_bucket_pnl_per_notional: {scorecard.medium_bucket_pnl_per_notional:.6f}",
        f"- large_bucket_pnl_per_notional: {scorecard.large_bucket_pnl_per_notional:.6f}",
        f"- submitted_notional: {scorecard.submitted_notional:.6f}",
        f"- pnl_per_notional: {scorecard.pnl_per_notional:.6f}",
        "",
        "## Profit Loss Decomposition",
        "",
        f"- selection_loss: {scorecard.selection_loss:.4f}",
        f"- pricing_loss: {scorecard.pricing_loss:.4f}",
        f"- execution_loss: {scorecard.execution_loss:.4f}",
        f"- exit_loss: {scorecard.exit_loss:.4f}",
        f"- sizing_loss: {scorecard.sizing_loss:.4f}",
        f"- total_profit_loss: {scorecard.total_profit_loss:.4f}",
        "",
        f"- tuning_priority: {scorecard.tuning_priority}",
        "",
        "## Tuning Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in scorecard.tuning_actions)
    lines.extend(
        [
        "",
        "## Top Loss Attribution",
        "",
        f"- top_loss_trades: {json.dumps(list(scorecard.top_loss_trades), ensure_ascii=True)}",
        f"- top_loss_market_breakdown: {json.dumps(list(scorecard.top_loss_market_breakdown), ensure_ascii=True)}",
        f"- top_loss_signature_breakdown: {json.dumps(list(scorecard.top_loss_signature_breakdown), ensure_ascii=True)}",
        "",
        "## Reasons",
        "",
        ]
    )
    lines.extend(f"- {reason}" for reason in scorecard.reasons)
    lines.extend(["", "## Component Reasons", ""])
    for component, reasons in scorecard.component_reasons.items():
        joined = ", ".join(reasons) if reasons else "stable"
        lines.append(f"- {component}: {joined}")
    return "\n".join(lines) + "\n"


def write_crypto_phase2_final_scorecard(
    *,
    scorecard: CryptoPhase2FinalScorecard,
    output_dir: str | Path,
) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "final_scorecard.md").write_text(
        format_crypto_phase2_final_scorecard(scorecard),
        encoding="utf-8",
    )
    (target_dir / "final_scorecard.json").write_text(
        json.dumps(_normalize(asdict(scorecard)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value


def _evaluate_btc_promotion_gate(
    *,
    filtered: "CryptoPhase2ReplayDigest",
) -> _CryptoPromotionGateEvaluation:
    blocking_reasons: list[str] = []
    if filtered.status == "halted":
        blocking_reasons.append("risk_status_halted")
    if filtered.closed_trade_count < _PROMOTION_MIN_CLOSED_TRADES:
        blocking_reasons.append("insufficient_closed_trade_count")
    if filtered.edge_capture_ratio < _PROMOTION_MIN_EDGE_CAPTURE_RATIO:
        blocking_reasons.append("edge_capture_ratio_below_floor")
    observed_execution_loss_ratio = _execution_loss_ratio(filtered=filtered)
    if observed_execution_loss_ratio > _PROMOTION_MAX_EXECUTION_LOSS_RATIO:
        blocking_reasons.append("execution_loss_ratio_above_ceiling")
    observed_max_single_loss_pnl = _max_single_loss_pnl(filtered=filtered)
    if observed_max_single_loss_pnl < _PROMOTION_MAX_SINGLE_LOSS_PNL:
        blocking_reasons.append("single_loss_breach")
    observed_top3_loss_concentration_ratio = _top3_loss_concentration_ratio(filtered=filtered)
    if observed_top3_loss_concentration_ratio > _PROMOTION_MAX_TOP3_LOSS_CONCENTRATION_RATIO:
        blocking_reasons.append("top3_loss_concentration_above_ceiling")
    pnl_per_notional = (
        filtered.closed_trade_net_pnl / filtered.submitted_notional
        if filtered.submitted_notional > 0
        else 0.0
    )
    if pnl_per_notional <= _PROMOTION_MIN_PNL_PER_NOTIONAL:
        blocking_reasons.append("pnl_per_notional_not_positive")
    if "risk_status_halted" in blocking_reasons:
        decision = "pause"
    elif blocking_reasons:
        decision = "review"
    else:
        decision = "proceed"
    return _CryptoPromotionGateEvaluation(
        decision=decision,
        stage_label=_promotion_stage_label(decision=decision),
        blocking_reasons=tuple(blocking_reasons),
        min_closed_trades=_PROMOTION_MIN_CLOSED_TRADES,
        min_edge_capture_ratio=_PROMOTION_MIN_EDGE_CAPTURE_RATIO,
        max_execution_loss_ratio=_PROMOTION_MAX_EXECUTION_LOSS_RATIO,
        min_pnl_per_notional=_PROMOTION_MIN_PNL_PER_NOTIONAL,
        observed_execution_loss_ratio=observed_execution_loss_ratio,
        max_single_loss_pnl=_PROMOTION_MAX_SINGLE_LOSS_PNL,
        max_top3_loss_concentration_ratio=_PROMOTION_MAX_TOP3_LOSS_CONCENTRATION_RATIO,
        observed_max_single_loss_pnl=observed_max_single_loss_pnl,
        observed_top3_loss_concentration_ratio=observed_top3_loss_concentration_ratio,
    )


def _evaluate_route_stage_gates(
    *,
    filtered: "CryptoPhase2ReplayDigest",
    unfiltered: "CryptoPhase2ReplayDigest",
    blocked_series_keys: tuple[str, ...],
    promotion_gate: _CryptoPromotionGateEvaluation,
    filter_order_delta: int,
) -> _CryptoRouteStageGateEvaluation:
    statuses: dict[str, str] = {}
    blockers: dict[str, tuple[str, ...]] = {}

    scan_blockers: list[str] = []
    if filtered.signals_generated <= 0:
        scan_blockers.append("scan_no_signals")
    if blocked_series_keys:
        scan_blockers.append("scan_runtime_blocked_series")
    statuses["scan_quality"] = _gate_status(scan_blockers)
    blockers["scan_quality"] = tuple(scan_blockers)

    selection_blockers: list[str] = []
    if filtered.submitted_orders <= 0:
        selection_blockers.append("selection_no_submitted_orders")
    if filtered.signals_generated > 0 and (filtered.submitted_orders / filtered.signals_generated) < 0.2:
        selection_blockers.append("selection_low_pass_through")
    if filter_order_delta < 0:
        selection_blockers.append("selection_negative_order_delta")
    statuses["selection_pass_through"] = _gate_status(selection_blockers)
    blockers["selection_pass_through"] = tuple(selection_blockers)

    route_blockers: list[str] = []
    if filtered.status == "halted":
        route_blockers.append("route_halted")
    if filtered.maker_fill_rate < 0.2 and filtered.expiration_rate >= 0.5:
        route_blockers.append("route_maker_expire_dominance")
    if filtered.average_adverse_fill_bps >= 35:
        route_blockers.append("route_adverse_fill_too_high")
    statuses["route_conversion_quality"] = _gate_status(route_blockers)
    blockers["route_conversion_quality"] = tuple(route_blockers)

    close_out_blockers: list[str] = []
    if filtered.closed_trade_count <= 0:
        close_out_blockers.append("close_out_no_closed_trades")
    if filtered.stop_out_rate >= 0.5:
        close_out_blockers.append("close_out_stop_out_pressure")
    if filtered.average_trade_realized_pnl_bps < 0:
        close_out_blockers.append("close_out_negative_realized_pnl_bps")
    statuses["close_out_quality"] = _gate_status(close_out_blockers)
    blockers["close_out_quality"] = tuple(close_out_blockers)

    profitability_blockers: list[str] = []
    pnl_per_notional = (
        filtered.closed_trade_net_pnl / filtered.submitted_notional
        if filtered.submitted_notional > 0
        else 0.0
    )
    if pnl_per_notional <= 0:
        profitability_blockers.append("profitability_non_positive_pnl_per_notional")
    if "single_loss_breach" in promotion_gate.blocking_reasons:
        profitability_blockers.append("tail_loss_single_loss_breach")
    if "top3_loss_concentration_above_ceiling" in promotion_gate.blocking_reasons:
        profitability_blockers.append("tail_loss_top3_concentration_breach")
    if (
        filtered.submitted_notional > 0
        and filtered.large_notional_share >= 0.3
        and pnl_per_notional <= 0.0
    ):
        profitability_blockers.append("sizing_large_notional_without_efficiency")
    if (
        filtered.large_bucket_pnl_per_notional
        < filtered.small_bucket_pnl_per_notional - 0.01
    ):
        profitability_blockers.append("sizing_large_bucket_underperformance")
    statuses["profitability_tail_risk"] = _gate_status(profitability_blockers)
    blockers["profitability_tail_risk"] = tuple(profitability_blockers)

    failed_stages = tuple(stage for stage, status in statuses.items() if status != "pass")
    if any(status == "blocked" for status in statuses.values()):
        acceptance_decision = "pause" if filtered.status == "halted" else "review"
    elif failed_stages:
        acceptance_decision = "review"
    else:
        acceptance_decision = "proceed"
    if unfiltered.signals_generated <= 0 and filtered.signals_generated <= 0:
        acceptance_decision = "review"
    return _CryptoRouteStageGateEvaluation(
        acceptance_decision=acceptance_decision,
        statuses=statuses,
        blockers=blockers,
        failed_stages=failed_stages,
    )


def _gate_status(blockers: list[str]) -> str:
    if not blockers:
        return "pass"
    if any(
        blocker in {"scan_no_signals", "selection_no_submitted_orders", "route_halted", "close_out_no_closed_trades"}
        for blocker in blockers
    ):
        return "blocked"
    return "review"


def _merge_decisions(first: str, second: str) -> str:
    ranks = {"proceed": 0, "review": 1, "pause": 2}
    return first if ranks.get(first, 1) >= ranks.get(second, 1) else second


def _dominant_route_stage_blocker(
    route_stage_gate: _CryptoRouteStageGateEvaluation,
) -> str | None:
    for stage in route_stage_gate.failed_stages:
        blockers = route_stage_gate.blockers.get(stage, ())
        if blockers:
            return blockers[0]
    return None


def _next_constrained_action(
    route_stage_gate: _CryptoRouteStageGateEvaluation,
) -> str:
    if not route_stage_gate.failed_stages:
        return "collect another comparable evidence window and confirm stability before promotion."
    primary_stage = route_stage_gate.failed_stages[0]
    if primary_stage == "scan_quality":
        return "repair scan/selection input quality before adjusting execution thresholds."
    if primary_stage == "selection_pass_through":
        return "improve selection pass-through on tradable families before route tuning."
    if primary_stage == "route_conversion_quality":
        return "reduce maker-expiry loops and stabilize route conversion before increasing activity."
    if primary_stage == "close_out_quality":
        return "tighten exit containment and improve close quality before adding new flow."
    if primary_stage == "profitability_tail_risk":
        return "reduce sizing and tail-loss concentration before seeking promotion."
    return "resolve the dominant route-stage blocker before next tuning iteration."


def _execution_loss_ratio(*, filtered: "CryptoPhase2ReplayDigest") -> float:
    expected_edge = filtered.average_trade_expected_edge_bps
    execution_drag = filtered.average_trade_execution_drag_bps
    if expected_edge <= 0:
        return 1.0 if execution_drag > 0 else 0.0
    return max(0.0, min(2.0, execution_drag / expected_edge))


def _max_single_loss_pnl(*, filtered: "CryptoPhase2ReplayDigest") -> float:
    losses: list[float] = []
    for trade in filtered.top_loss_trades:
        if not isinstance(trade, dict):
            continue
        raw_pnl = trade.get("net_pnl", trade.get("realized_pnl"))
        try:
            pnl = float(raw_pnl)
        except (TypeError, ValueError):
            continue
        if pnl < 0:
            losses.append(pnl)
    return min(losses) if losses else 0.0


def _top3_loss_concentration_ratio(*, filtered: "CryptoPhase2ReplayDigest") -> float:
    losses: list[float] = []
    for trade in filtered.top_loss_trades:
        if not isinstance(trade, dict):
            continue
        raw_pnl = trade.get("net_pnl", trade.get("realized_pnl"))
        try:
            pnl = float(raw_pnl)
        except (TypeError, ValueError):
            continue
        if pnl < 0:
            losses.append(abs(pnl))
    if not losses:
        return 0.0
    negative_trade_count = int(round(max(0.0, (1.0 - filtered.winning_trade_rate) * filtered.closed_trade_count)))
    gross_negative_pnl = abs(filtered.average_loss_trade_pnl) * float(max(1, negative_trade_count))
    if gross_negative_pnl <= 0:
        return 0.0
    top3_abs_loss = sum(sorted(losses, reverse=True)[:3])
    return max(0.0, min(1.0, top3_abs_loss / gross_negative_pnl))


def _promotion_stage_label(*, decision: str) -> str:
    if decision == "proceed":
        return "shadow validation"
    return "paper available"


def _profit_component_scores(
    *,
    filtered: "CryptoPhase2ReplayDigest",
    unfiltered: "CryptoPhase2ReplayDigest",
    blocked_series_keys: tuple[str, ...],
) -> tuple[dict[str, tuple[float, tuple[str, ...]]], dict[str, float], str]:
    order_capture_ratio = (
        filtered.submitted_orders / filtered.signals_generated
        if filtered.signals_generated > 0
        else 0.0
    )
    pnl_per_order = (
        filtered.today_pnl / filtered.submitted_orders
        if filtered.submitted_orders > 0
        else 0.0
    )

    selection_reasons: list[str] = []
    selection_score = 1.0
    if blocked_series_keys:
        selection_score -= 0.2
        selection_reasons.append("runtime still blocks ladder families")
    if filtered.signals_generated <= 0:
        selection_score -= 0.35
        selection_reasons.append("no filtered signals")
    if filtered.submitted_orders <= 0:
        selection_score -= 0.2
        selection_reasons.append("selection yields no submitted trades")
    if filtered.submitted_orders < unfiltered.submitted_orders:
        selection_score -= 0.1
        selection_reasons.append("filter removes more orders than it preserves")

    pricing_reasons: list[str] = []
    pricing_score = 1.0
    if filtered.today_pnl < 0 and filtered.closed_trade_count > 0:
        pricing_score -= 0.3
        pricing_reasons.append("negative filtered pnl")
    elif filtered.today_pnl == 0.0:
        pricing_score -= 0.1
        pricing_reasons.append("flat filtered pnl")
    if unfiltered.today_pnl > filtered.today_pnl:
        pricing_score -= 0.15
        pricing_reasons.append("selection currently loses pnl versus unfiltered replay")
    if filtered.average_signal_edge_bps <= 0:
        pricing_score -= 0.15
        pricing_reasons.append("filled trades do not preserve positive modeled edge")
    if filtered.edge_capture_ratio < 0.35:
        pricing_score -= 0.2
        pricing_reasons.append("captured edge is too small versus modeled edge")
    elif filtered.edge_capture_ratio < 0.65:
        pricing_score -= 0.1
        pricing_reasons.append("modeled edge decays before it becomes realized pnl")
    if filtered.average_fusion_observed_gap_bps >= 250 and filtered.edge_capture_ratio < 0.5:
        pricing_score -= 0.12
        pricing_reasons.append("fused fair values remain far from observed pricing without enough realized capture")
    elif filtered.average_fusion_observed_gap_bps >= 125 and filtered.edge_capture_ratio < 0.35:
        pricing_score -= 0.06
        pricing_reasons.append("repricing gap stays elevated and realized capture remains weak")
    if filtered.average_barrier_surface_disagreement_bps >= 175:
        pricing_score -= 0.12
        pricing_reasons.append("barrier and surface models disagree too much")
    elif filtered.average_barrier_surface_disagreement_bps >= 75:
        pricing_score -= 0.06
        pricing_reasons.append("barrier and surface models still diverge meaningfully")

    execution_reasons: list[str] = []
    execution_score = 1.0
    if filtered.status == "halted":
        execution_score -= 0.45
        execution_reasons.append("filtered replay halted")
    if filtered.maker_fill_rate < 0.2 and filtered.expiration_rate >= 0.5:
        execution_score -= 0.2
        execution_reasons.append("maker quotes expire before filling")
    elif filtered.maker_fill_rate < 0.4 and filtered.expiration_rate >= 0.3:
        execution_score -= 0.1
        execution_reasons.append("maker fill rate is weak versus expiration")
    if order_capture_ratio < 0.2:
        execution_score -= 0.2
        execution_reasons.append("low signal-to-order capture ratio")
    elif order_capture_ratio < 0.5:
        execution_score -= 0.1
        execution_reasons.append("moderate signal-to-order capture ratio")
    if filtered.execution_feedback_bias == "more_passive":
        execution_score -= 0.1
        execution_reasons.append("recent execution feedback prefers more passive routing")
    if filtered.average_adverse_fill_bps >= 35:
        execution_score -= 0.15
        execution_reasons.append("fills give up too much edge versus mid-price")
    elif filtered.average_adverse_fill_bps >= 15:
        execution_score -= 0.08
        execution_reasons.append("fill slippage is elevated")
    if filtered.average_trade_execution_drag_bps >= 45:
        execution_score -= 0.12
        execution_reasons.append("trade-level execution drag remains too high")
    elif filtered.average_trade_execution_drag_bps >= 20:
        execution_score -= 0.06
        execution_reasons.append("trade-level execution drag remains elevated")

    exit_reasons: list[str] = []
    exit_score = 1.0
    if filtered.closed_trade_count > 0 and filtered.submitted_orders > 0 and pnl_per_order < 0:
        exit_score -= 0.25
        exit_reasons.append("negative pnl per submitted order")
    elif filtered.closed_trade_count > 0 and filtered.submitted_orders > 0 and pnl_per_order == 0:
        exit_score -= 0.1
        exit_reasons.append("flat pnl per submitted order")
    if filtered.closed_trade_count > 0 and filtered.stop_out_rate >= 0.5:
        exit_score -= 0.25
        exit_reasons.append("closed trades are repeatedly stopping out")
    elif filtered.closed_trade_count > 0 and filtered.stop_out_rate >= 0.25:
        exit_score -= 0.1
        exit_reasons.append("closed trades show elevated stop-out pressure")
    if filtered.closed_trade_count > 0 and filtered.winning_trade_rate < 0.35 and filtered.closed_trade_net_pnl < 0:
        exit_score -= 0.15
        exit_reasons.append("exits fail to convert enough positions into positive closes")
    if filtered.closed_trade_count > 0 and filtered.average_loss_trade_pnl < 0 and abs(filtered.average_loss_trade_pnl) > max(filtered.average_win_trade_pnl, 0.01):
        exit_score -= 0.1
        exit_reasons.append("losing exits are materially larger than winning exits")
    if filtered.closed_trade_count > 0 and filtered.average_win_trade_pnl <= 0 and filtered.closed_trade_net_pnl <= 0:
        exit_score -= 0.08
        exit_reasons.append("exit path is not preserving positive close quality")
    if filtered.closed_trade_count > 0 and filtered.stop_loss_exit_share >= 0.4:
        exit_score -= 0.1
        exit_reasons.append("stop-loss exits dominate realized closes")
    elif filtered.closed_trade_count > 0 and filtered.stop_loss_exit_share >= 0.2:
        exit_score -= 0.05
        exit_reasons.append("stop-loss exits remain elevated")
    if filtered.closed_trade_count > 0 and filtered.passive_cleanup_exit_share >= 0.5:
        exit_score -= 0.08
        exit_reasons.append("too many closes rely on aging or stale cleanup exits")
    if filtered.closed_trade_count > 0 and filtered.exit_family_balance_score < 0.45:
        exit_score -= 0.1
        exit_reasons.append("exit family mix is too skewed toward defensive cleanup paths")
    if filtered.closed_trade_count > 0 and filtered.average_trade_realized_pnl_bps < 0:
        exit_score -= 0.08
        exit_reasons.append("trade-level realized pnl stays negative after execution and exit effects")

    sizing_reasons: list[str] = []
    sizing_score = 1.0
    if filtered.submitted_orders > 0 and abs(filtered.today_pnl) < 0.01:
        sizing_score -= 0.15
        sizing_reasons.append("captured pnl per order is too small")
    if filtered.submitted_orders > unfiltered.submitted_orders and filtered.today_pnl < unfiltered.today_pnl:
        sizing_score -= 0.2
        sizing_reasons.append("added order volume does not improve pnl capture")
    if filtered.average_trade_pnl < 0:
        sizing_score -= 0.15
        sizing_reasons.append("average closed-trade pnl is negative")
    pnl_per_notional = (filtered.closed_trade_net_pnl / filtered.submitted_notional) if filtered.submitted_notional > 0 else 0.0
    if filtered.submitted_notional > 0 and pnl_per_notional < -0.01:
        sizing_score -= 0.15
        sizing_reasons.append("sizing loses too much pnl per unit of deployed notional")
    elif filtered.submitted_notional > 0 and pnl_per_notional <= 0.0:
        sizing_score -= 0.08
        sizing_reasons.append("deployed notional is not producing positive net capture")
    if filtered.large_notional_share >= 0.5 and pnl_per_notional <= 0.0:
        sizing_score -= 0.1
        sizing_reasons.append("too much flow sits in larger clips before pnl efficiency is proven")
    elif filtered.large_notional_share >= 0.3 and pnl_per_notional <= 0.0:
        sizing_score -= 0.05
        sizing_reasons.append("larger clips remain too common for current pnl efficiency")
    if filtered.large_bucket_pnl_per_notional < filtered.small_bucket_pnl_per_notional - 0.01:
        sizing_score -= 0.1
        sizing_reasons.append("large notional bucket underperforms small clips materially")
    elif filtered.medium_bucket_pnl_per_notional < filtered.small_bucket_pnl_per_notional - 0.008:
        sizing_score -= 0.05
        sizing_reasons.append("medium notional bucket underperforms small clips")

    scores = {
        "selection": (max(0.0, round(selection_score, 4)), tuple(selection_reasons) or ("selection stable",)),
        "pricing": (max(0.0, round(pricing_score, 4)), tuple(pricing_reasons) or ("pricing stable",)),
        "execution": (max(0.0, round(execution_score, 4)), tuple(execution_reasons) or ("execution stable",)),
        "exit": (max(0.0, round(exit_score, 4)), tuple(exit_reasons) or ("exit stable",)),
        "sizing": (max(0.0, round(sizing_score, 4)), tuple(sizing_reasons) or ("sizing stable",)),
    }
    losses = {component: round(1.0 - score_details[0], 4) for component, score_details in scores.items()}
    weakest_component = min(scores.items(), key=lambda item: item[1][0])[0]
    return scores, losses, weakest_component


def _tuning_recommendations(
    *,
    weakest_component: str,
    secondary_component: str,
    filtered: "CryptoPhase2ReplayDigest",
    component_losses: dict[str, float],
) -> tuple[str, tuple[str, ...]]:
    actions: list[str] = []

    if weakest_component == "selection":
        actions.extend(
            [
                "raise min_net_edge_bps for the weakest family preset before adding more order flow",
                "tighten runtime tradability gates for markets that remain watch_only or blocked",
            ]
        )
    elif weakest_component == "pricing":
        actions.extend(
            [
                "re-run phase1 calibration against the locked baseline before widening execution thresholds",
                "compare filtered versus unfiltered pnl by family to isolate mispriced ladders",
            ]
        )
    elif weakest_component == "execution":
        if filtered.expiration_rate >= 0.5:
            actions.append("reduce maker_quote_ttl_seconds or increase maker_aggressiveness for the active preset")
        if filtered.execution_feedback_bias == "more_passive":
            actions.append("raise taker_urgency_threshold and reduce default_notional until stop-out pressure normalizes")
        else:
            actions.append("lower taker_urgency_threshold for families that miss too many fills")
    elif weakest_component == "exit":
        actions.extend(
            [
                "tighten aging/stale exit thresholds so weak positions recycle earlier",
                "lower max_holding_multiplier for presets with repeated negative closed trades",
            ]
        )
    elif weakest_component == "sizing":
        actions.extend(
            [
                "reduce default_notional for families with negative average trade pnl",
                "only scale size back up after pnl per order turns positive across repeated runs",
            ]
        )

    if not actions:
        actions.append("keep the current preset stable and collect another evidence window before retuning")
    if secondary_component != weakest_component and component_losses.get(secondary_component, 0.0) >= 0.2:
        actions.append(
            f"design the next variant to also address secondary loss in {secondary_component} instead of retuning {weakest_component} in isolation"
        )
    if component_losses.get("execution", 0.0) >= 0.3 and weakest_component != "execution":
        actions.append("keep execution-loss on watch even if another component is currently weaker")
    return weakest_component, tuple(actions)
