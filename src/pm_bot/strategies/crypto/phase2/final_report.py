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
class CryptoPhase2FinalScorecard:
    generated_at: datetime
    recommended_action: str
    readiness_score: float
    execution_quality: str
    evidence_status: str
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

    if evidence_status == "blocked":
        recommended_action = "pause"
    elif filtered.submitted_orders > 0 and filtered.status != "halted":
        recommended_action = "proceed"
    else:
        recommended_action = "review"

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

    return CryptoPhase2FinalScorecard(
        generated_at=suite_result.generated_at,
        recommended_action=recommended_action,
        readiness_score=readiness_score,
        execution_quality=execution_quality,
        evidence_status=evidence_status,
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
    )


def format_crypto_phase2_final_scorecard(scorecard: CryptoPhase2FinalScorecard) -> str:
    lines = [
        "# Crypto Phase 2 Final Scorecard",
        "",
        f"- recommended_action: {scorecard.recommended_action}",
        f"- readiness_score: {scorecard.readiness_score:.4f}",
        f"- execution_quality: {scorecard.execution_quality}",
        f"- evidence_status: {scorecard.evidence_status}",
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
