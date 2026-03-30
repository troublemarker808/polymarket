"""Cross-run learning summaries for crypto phase2 suite outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class CryptoPhase2LearningReport:
    run_count: int
    recurring_profit_focuses: tuple[str, ...]
    recurring_tuning_priorities: tuple[str, ...]
    recommended_next_experiment: str
    recommended_actions: tuple[str, ...]
    focus_counts: dict[str, int]
    tuning_counts: dict[str, int]
    average_component_losses: dict[str, float]
    recurring_loss_ranking: tuple[str, ...]
    average_edge_capture_ratio: float
    average_signal_edge_bps: float
    average_adverse_fill_bps: float
    average_pnl_per_notional: float
    average_trade_expected_edge_bps: float
    average_trade_execution_drag_bps: float
    average_trade_realized_pnl_bps: float
    average_fusion_observed_gap_bps: float
    average_barrier_surface_disagreement_bps: float
    average_win_trade_pnl: float
    average_loss_trade_pnl: float
    average_submitted_notional: float
    average_large_notional_share: float
    dominant_exit_reason: str
    average_stop_loss_exit_share: float
    average_passive_cleanup_exit_share: float
    average_exit_family_balance_score: float
    average_small_bucket_pnl_per_notional: float
    average_medium_bucket_pnl_per_notional: float
    average_large_bucket_pnl_per_notional: float


def build_crypto_phase2_learning_report(
    *,
    suite_paths: list[str | Path],
) -> CryptoPhase2LearningReport:
    focus_counter: Counter[str] = Counter()
    tuning_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()
    component_loss_totals: dict[str, float] = {
        "selection": 0.0,
        "pricing": 0.0,
        "execution": 0.0,
        "exit": 0.0,
        "sizing": 0.0,
    }
    component_loss_counts: dict[str, int] = {key: 0 for key in component_loss_totals}
    edge_capture_ratio_total = 0.0
    signal_edge_total = 0.0
    adverse_fill_total = 0.0
    pnl_per_notional_total = 0.0
    trade_expected_edge_total = 0.0
    trade_execution_drag_total = 0.0
    trade_realized_pnl_bps_total = 0.0
    fusion_gap_total = 0.0
    barrier_surface_disagreement_total = 0.0
    average_win_trade_pnl_total = 0.0
    average_loss_trade_pnl_total = 0.0
    average_submitted_notional_total = 0.0
    average_large_notional_share_total = 0.0
    exit_reason_counter: Counter[str] = Counter()
    average_stop_loss_exit_share_total = 0.0
    average_passive_cleanup_exit_share_total = 0.0
    average_exit_family_balance_score_total = 0.0
    average_small_bucket_pnl_per_notional_total = 0.0
    average_medium_bucket_pnl_per_notional_total = 0.0
    average_large_bucket_pnl_per_notional_total = 0.0
    edge_capture_count = 0
    signal_edge_count = 0
    adverse_fill_count = 0
    pnl_per_notional_count = 0
    trade_expected_edge_count = 0
    trade_execution_drag_count = 0
    trade_realized_pnl_bps_count = 0
    fusion_gap_count = 0
    barrier_surface_disagreement_count = 0
    average_win_trade_pnl_count = 0
    average_loss_trade_pnl_count = 0
    average_submitted_notional_count = 0
    average_large_notional_share_count = 0
    average_stop_loss_exit_share_count = 0
    average_passive_cleanup_exit_share_count = 0
    average_exit_family_balance_score_count = 0
    average_small_bucket_pnl_per_notional_count = 0
    average_medium_bucket_pnl_per_notional_count = 0
    average_large_bucket_pnl_per_notional_count = 0

    for suite_path in suite_paths:
        payload = _load_suite_payload(suite_path)
        final_scorecard = payload.get("final_scorecard", {})
        if not isinstance(final_scorecard, dict):
            continue
        profit_focus = str(final_scorecard.get("profit_focus", "")).strip()
        tuning_priority = str(final_scorecard.get("tuning_priority", "")).strip()
        if profit_focus:
            focus_counter[profit_focus] += 1
        if tuning_priority:
            tuning_counter[tuning_priority] += 1
        tuning_actions = final_scorecard.get("tuning_actions", [])
        if isinstance(tuning_actions, list):
            for action in tuning_actions:
                if isinstance(action, str) and action:
                    action_counter[action] += 1
        for component in component_loss_totals:
            loss_value = final_scorecard.get(f"{component}_loss")
            if isinstance(loss_value, (int, float)):
                component_loss_totals[component] += float(loss_value)
                component_loss_counts[component] += 1
        edge_capture_ratio = final_scorecard.get("edge_capture_ratio")
        if isinstance(edge_capture_ratio, (int, float)):
            edge_capture_ratio_total += float(edge_capture_ratio)
            edge_capture_count += 1
        average_signal_edge_bps = final_scorecard.get("average_signal_edge_bps")
        if isinstance(average_signal_edge_bps, (int, float)):
            signal_edge_total += float(average_signal_edge_bps)
            signal_edge_count += 1
        average_adverse_fill_bps = final_scorecard.get("average_adverse_fill_bps")
        if isinstance(average_adverse_fill_bps, (int, float)):
            adverse_fill_total += float(average_adverse_fill_bps)
            adverse_fill_count += 1
        pnl_per_notional = final_scorecard.get("pnl_per_notional")
        if isinstance(pnl_per_notional, (int, float)):
            pnl_per_notional_total += float(pnl_per_notional)
            pnl_per_notional_count += 1
        trade_expected_edge = final_scorecard.get("average_trade_expected_edge_bps")
        if isinstance(trade_expected_edge, (int, float)):
            trade_expected_edge_total += float(trade_expected_edge)
            trade_expected_edge_count += 1
        trade_execution_drag = final_scorecard.get("average_trade_execution_drag_bps")
        if isinstance(trade_execution_drag, (int, float)):
            trade_execution_drag_total += float(trade_execution_drag)
            trade_execution_drag_count += 1
        trade_realized_pnl_bps = final_scorecard.get("average_trade_realized_pnl_bps")
        if isinstance(trade_realized_pnl_bps, (int, float)):
            trade_realized_pnl_bps_total += float(trade_realized_pnl_bps)
            trade_realized_pnl_bps_count += 1
        fusion_gap = final_scorecard.get("average_fusion_observed_gap_bps")
        if isinstance(fusion_gap, (int, float)):
            fusion_gap_total += float(fusion_gap)
            fusion_gap_count += 1
        barrier_surface_gap = final_scorecard.get("average_barrier_surface_disagreement_bps")
        if isinstance(barrier_surface_gap, (int, float)):
            barrier_surface_disagreement_total += float(barrier_surface_gap)
            barrier_surface_disagreement_count += 1
        average_win_trade_pnl = final_scorecard.get("average_win_trade_pnl")
        if isinstance(average_win_trade_pnl, (int, float)):
            average_win_trade_pnl_total += float(average_win_trade_pnl)
            average_win_trade_pnl_count += 1
        average_loss_trade_pnl = final_scorecard.get("average_loss_trade_pnl")
        if isinstance(average_loss_trade_pnl, (int, float)):
            average_loss_trade_pnl_total += float(average_loss_trade_pnl)
            average_loss_trade_pnl_count += 1
        average_submitted_notional = final_scorecard.get("average_submitted_notional")
        if isinstance(average_submitted_notional, (int, float)):
            average_submitted_notional_total += float(average_submitted_notional)
            average_submitted_notional_count += 1
        average_large_notional_share = final_scorecard.get("large_notional_share")
        if isinstance(average_large_notional_share, (int, float)):
            average_large_notional_share_total += float(average_large_notional_share)
            average_large_notional_share_count += 1
        dominant_exit_reason = str(final_scorecard.get("dominant_exit_reason", "")).strip()
        if dominant_exit_reason:
            exit_reason_counter[dominant_exit_reason] += 1
        stop_loss_exit_share = final_scorecard.get("stop_loss_exit_share")
        if isinstance(stop_loss_exit_share, (int, float)):
            average_stop_loss_exit_share_total += float(stop_loss_exit_share)
            average_stop_loss_exit_share_count += 1
        passive_cleanup_exit_share = final_scorecard.get("passive_cleanup_exit_share")
        if isinstance(passive_cleanup_exit_share, (int, float)):
            average_passive_cleanup_exit_share_total += float(passive_cleanup_exit_share)
            average_passive_cleanup_exit_share_count += 1
        exit_family_balance_score = final_scorecard.get("exit_family_balance_score")
        if isinstance(exit_family_balance_score, (int, float)):
            average_exit_family_balance_score_total += float(exit_family_balance_score)
            average_exit_family_balance_score_count += 1
        small_bucket_pnl_per_notional = final_scorecard.get("small_bucket_pnl_per_notional")
        if isinstance(small_bucket_pnl_per_notional, (int, float)):
            average_small_bucket_pnl_per_notional_total += float(small_bucket_pnl_per_notional)
            average_small_bucket_pnl_per_notional_count += 1
        medium_bucket_pnl_per_notional = final_scorecard.get("medium_bucket_pnl_per_notional")
        if isinstance(medium_bucket_pnl_per_notional, (int, float)):
            average_medium_bucket_pnl_per_notional_total += float(medium_bucket_pnl_per_notional)
            average_medium_bucket_pnl_per_notional_count += 1
        large_bucket_pnl_per_notional = final_scorecard.get("large_bucket_pnl_per_notional")
        if isinstance(large_bucket_pnl_per_notional, (int, float)):
            average_large_bucket_pnl_per_notional_total += float(large_bucket_pnl_per_notional)
            average_large_bucket_pnl_per_notional_count += 1

    recurring_focuses = tuple(
        component for component, count in focus_counter.items() if count >= 2
    )
    recurring_tuning_priorities = tuple(
        component for component, count in tuning_counter.items() if count >= 2
    )
    average_component_losses = {
        component: round(component_loss_totals[component] / component_loss_counts[component], 4)
        for component in component_loss_totals
        if component_loss_counts[component] > 0
    }
    recurring_loss_ranking = tuple(
        component
        for component, _loss in sorted(
            average_component_losses.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    if recurring_loss_ranking:
        recommended_next_experiment = recurring_loss_ranking[0]
    elif tuning_counter:
        recommended_next_experiment = tuning_counter.most_common(1)[0][0]
    elif focus_counter:
        recommended_next_experiment = focus_counter.most_common(1)[0][0]
    else:
        recommended_next_experiment = "collect_more_runs"

    recommended_actions = tuple(
        action for action, _count in action_counter.most_common(3)
    ) or ("collect more suite runs before changing presets",)
    average_edge_capture_ratio = round(edge_capture_ratio_total / edge_capture_count, 4) if edge_capture_count > 0 else 0.0
    average_signal_edge_bps = round(signal_edge_total / signal_edge_count, 4) if signal_edge_count > 0 else 0.0
    average_adverse_fill_bps = round(adverse_fill_total / adverse_fill_count, 4) if adverse_fill_count > 0 else 0.0
    average_pnl_per_notional = round(pnl_per_notional_total / pnl_per_notional_count, 6) if pnl_per_notional_count > 0 else 0.0
    average_trade_expected_edge_bps = round(trade_expected_edge_total / trade_expected_edge_count, 4) if trade_expected_edge_count > 0 else 0.0
    average_trade_execution_drag_bps = round(trade_execution_drag_total / trade_execution_drag_count, 4) if trade_execution_drag_count > 0 else 0.0
    average_trade_realized_pnl_bps = round(trade_realized_pnl_bps_total / trade_realized_pnl_bps_count, 4) if trade_realized_pnl_bps_count > 0 else 0.0
    average_fusion_observed_gap_bps = round(fusion_gap_total / fusion_gap_count, 4) if fusion_gap_count > 0 else 0.0
    average_barrier_surface_disagreement_bps = round(
        barrier_surface_disagreement_total / barrier_surface_disagreement_count,
        4,
    ) if barrier_surface_disagreement_count > 0 else 0.0
    average_win_trade_pnl = round(average_win_trade_pnl_total / average_win_trade_pnl_count, 6) if average_win_trade_pnl_count > 0 else 0.0
    average_loss_trade_pnl = round(average_loss_trade_pnl_total / average_loss_trade_pnl_count, 6) if average_loss_trade_pnl_count > 0 else 0.0
    average_submitted_notional = round(average_submitted_notional_total / average_submitted_notional_count, 6) if average_submitted_notional_count > 0 else 0.0
    average_large_notional_share = round(
        average_large_notional_share_total / average_large_notional_share_count,
        4,
    ) if average_large_notional_share_count > 0 else 0.0
    dominant_exit_reason = exit_reason_counter.most_common(1)[0][0] if exit_reason_counter else "none"
    average_stop_loss_exit_share = round(
        average_stop_loss_exit_share_total / average_stop_loss_exit_share_count,
        4,
    ) if average_stop_loss_exit_share_count > 0 else 0.0
    average_passive_cleanup_exit_share = round(
        average_passive_cleanup_exit_share_total / average_passive_cleanup_exit_share_count,
        4,
    ) if average_passive_cleanup_exit_share_count > 0 else 0.0
    average_exit_family_balance_score = round(
        average_exit_family_balance_score_total / average_exit_family_balance_score_count,
        4,
    ) if average_exit_family_balance_score_count > 0 else 0.0
    average_small_bucket_pnl_per_notional = round(
        average_small_bucket_pnl_per_notional_total / average_small_bucket_pnl_per_notional_count,
        6,
    ) if average_small_bucket_pnl_per_notional_count > 0 else 0.0
    average_medium_bucket_pnl_per_notional = round(
        average_medium_bucket_pnl_per_notional_total / average_medium_bucket_pnl_per_notional_count,
        6,
    ) if average_medium_bucket_pnl_per_notional_count > 0 else 0.0
    average_large_bucket_pnl_per_notional = round(
        average_large_bucket_pnl_per_notional_total / average_large_bucket_pnl_per_notional_count,
        6,
    ) if average_large_bucket_pnl_per_notional_count > 0 else 0.0
    if average_edge_capture_ratio < 0.5:
        recommended_actions = (
            "prioritize variants that improve edge capture before widening trade flow",
            *recommended_actions,
        )
    if average_pnl_per_notional <= 0.0:
        recommended_actions = (
            *recommended_actions,
            "keep notional conservative until pnl per notional turns positive across repeated runs",
        )
    if average_fusion_observed_gap_bps >= 125:
        recommended_actions = (
            "prioritize repricing and calibration variants before widening execution flow",
            *recommended_actions,
        )
    if average_loss_trade_pnl < 0 and abs(average_loss_trade_pnl) > max(average_win_trade_pnl, 0.01):
        recommended_actions = (
            "tighten exits before widening flow because losing closes remain larger than winning closes",
            *recommended_actions,
        )
    if average_large_notional_share >= 0.3 and average_pnl_per_notional <= 0.0:
        recommended_actions = (
            "reduce clip size concentration until larger notional buckets earn positive pnl efficiency",
            *recommended_actions,
        )
    if average_stop_loss_exit_share >= 0.25:
        recommended_actions = (
            "prioritize exit variants that reduce repeated stop-loss closures before widening trade flow",
            *recommended_actions,
        )
    if average_passive_cleanup_exit_share >= 0.35:
        recommended_actions = (
            "tighten aging and stale cleanup exits because too many positions linger into passive cleanup",
            *recommended_actions,
        )
    if average_trade_execution_drag_bps >= 20.0:
        recommended_actions = (
            "prioritize execution variants that cut trade-level drag before widening flow",
            *recommended_actions,
        )
    if average_trade_realized_pnl_bps <= 0.0:
        recommended_actions = (
            "hold current scaling until trade-level realized pnl turns positive across repeated runs",
            *recommended_actions,
        )
    if average_exit_family_balance_score < 0.5:
        recommended_actions = (
            "rebalance exit families because defensive exits dominate the current close mix",
            *recommended_actions,
        )
    if average_large_bucket_pnl_per_notional < average_small_bucket_pnl_per_notional - 0.01:
        recommended_actions = (
            "de-emphasize large sizing buckets until large-clip pnl efficiency catches up to small clips",
            *recommended_actions,
        )

    return CryptoPhase2LearningReport(
        run_count=len(suite_paths),
        recurring_profit_focuses=recurring_focuses,
        recurring_tuning_priorities=recurring_tuning_priorities,
        recommended_next_experiment=recommended_next_experiment,
        recommended_actions=recommended_actions,
        focus_counts=dict(sorted(focus_counter.items())),
        tuning_counts=dict(sorted(tuning_counter.items())),
        average_component_losses=average_component_losses,
        recurring_loss_ranking=recurring_loss_ranking,
        average_edge_capture_ratio=average_edge_capture_ratio,
        average_signal_edge_bps=average_signal_edge_bps,
        average_adverse_fill_bps=average_adverse_fill_bps,
        average_pnl_per_notional=average_pnl_per_notional,
        average_trade_expected_edge_bps=average_trade_expected_edge_bps,
        average_trade_execution_drag_bps=average_trade_execution_drag_bps,
        average_trade_realized_pnl_bps=average_trade_realized_pnl_bps,
        average_fusion_observed_gap_bps=average_fusion_observed_gap_bps,
        average_barrier_surface_disagreement_bps=average_barrier_surface_disagreement_bps,
        average_win_trade_pnl=average_win_trade_pnl,
        average_loss_trade_pnl=average_loss_trade_pnl,
        average_submitted_notional=average_submitted_notional,
        average_large_notional_share=average_large_notional_share,
        dominant_exit_reason=dominant_exit_reason,
        average_stop_loss_exit_share=average_stop_loss_exit_share,
        average_passive_cleanup_exit_share=average_passive_cleanup_exit_share,
        average_exit_family_balance_score=average_exit_family_balance_score,
        average_small_bucket_pnl_per_notional=average_small_bucket_pnl_per_notional,
        average_medium_bucket_pnl_per_notional=average_medium_bucket_pnl_per_notional,
        average_large_bucket_pnl_per_notional=average_large_bucket_pnl_per_notional,
    )


def format_crypto_phase2_learning_report(report: CryptoPhase2LearningReport) -> str:
    lines = [
        "# Crypto Phase 2 Learning Report",
        "",
        f"- run_count: {report.run_count}",
        f"- recommended_next_experiment: {report.recommended_next_experiment}",
        f"- recurring_profit_focuses: {', '.join(report.recurring_profit_focuses) if report.recurring_profit_focuses else 'none'}",
        f"- recurring_tuning_priorities: {', '.join(report.recurring_tuning_priorities) if report.recurring_tuning_priorities else 'none'}",
        f"- recurring_loss_ranking: {', '.join(report.recurring_loss_ranking) if report.recurring_loss_ranking else 'none'}",
        f"- average_edge_capture_ratio: {report.average_edge_capture_ratio:.4f}",
        f"- average_signal_edge_bps: {report.average_signal_edge_bps:.4f}",
        f"- average_adverse_fill_bps: {report.average_adverse_fill_bps:.4f}",
        f"- average_pnl_per_notional: {report.average_pnl_per_notional:.6f}",
        f"- average_trade_expected_edge_bps: {report.average_trade_expected_edge_bps:.4f}",
        f"- average_trade_execution_drag_bps: {report.average_trade_execution_drag_bps:.4f}",
        f"- average_trade_realized_pnl_bps: {report.average_trade_realized_pnl_bps:.4f}",
        f"- average_fusion_observed_gap_bps: {report.average_fusion_observed_gap_bps:.4f}",
        f"- average_barrier_surface_disagreement_bps: {report.average_barrier_surface_disagreement_bps:.4f}",
        f"- average_win_trade_pnl: {report.average_win_trade_pnl:.6f}",
        f"- average_loss_trade_pnl: {report.average_loss_trade_pnl:.6f}",
        f"- average_submitted_notional: {report.average_submitted_notional:.6f}",
        f"- average_large_notional_share: {report.average_large_notional_share:.4f}",
        f"- dominant_exit_reason: {report.dominant_exit_reason}",
        f"- average_stop_loss_exit_share: {report.average_stop_loss_exit_share:.4f}",
        f"- average_passive_cleanup_exit_share: {report.average_passive_cleanup_exit_share:.4f}",
        f"- average_exit_family_balance_score: {report.average_exit_family_balance_score:.4f}",
        f"- average_small_bucket_pnl_per_notional: {report.average_small_bucket_pnl_per_notional:.6f}",
        f"- average_medium_bucket_pnl_per_notional: {report.average_medium_bucket_pnl_per_notional:.6f}",
        f"- average_large_bucket_pnl_per_notional: {report.average_large_bucket_pnl_per_notional:.6f}",
        "",
        "## Recommended Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in report.recommended_actions)
    lines.extend(["", "## Focus Counts", ""])
    for component, count in report.focus_counts.items():
        lines.append(f"- {component}: {count}")
    lines.extend(["", "## Tuning Counts", ""])
    for component, count in report.tuning_counts.items():
        lines.append(f"- {component}: {count}")
    lines.extend(["", "## Average Component Losses", ""])
    for component, loss in report.average_component_losses.items():
        lines.append(f"- {component}: {loss:.4f}")
    return "\n".join(lines) + "\n"


def write_crypto_phase2_learning_report(
    *,
    report: CryptoPhase2LearningReport,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_crypto_phase2_learning_report(report), encoding="utf-8")
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_suite_payload(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
