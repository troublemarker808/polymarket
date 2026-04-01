"""Unified research pipeline for the current Crypto Phase 2 module."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.crypto.phase1.baseline import get_locked_crypto_calibration_baseline_preset
from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.selection import (
    generate_crypto_market_selection_report,
    recommended_runtime_blocked_series_keys,
)
from pm_bot.strategies.crypto.phase2.final_report import (
    CryptoPhase2FinalScorecard,
    build_crypto_phase2_final_scorecard,
    write_crypto_phase2_final_scorecard,
)
from pm_bot.strategies.crypto.phase2.replay import run_crypto_phase2_replay


_LOCKED_BASELINE = get_locked_crypto_calibration_baseline_preset()
WORKING_BARRIER_MODEL_CONFIG = _LOCKED_BASELINE.barrier_model_config
WORKING_FUSION_MODEL_CONFIG = _LOCKED_BASELINE.fusion_model_config


@dataclass(slots=True, frozen=True)
class CryptoPhase2ReplayDigest:
    label: str
    output_dir: str
    signals_generated: int
    submitted_orders: int
    submitted_notional: float
    events_recorded: int
    today_pnl: float
    total_equity: float
    status: str
    maker_fill_rate: float
    taker_fill_rate: float
    expiration_rate: float
    stop_out_rate: float
    average_trade_pnl: float
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
    closed_trade_net_pnl: float
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
    execution_feedback_bias: str
    top_loss_trades: tuple[dict[str, Any], ...]
    top_loss_market_breakdown: tuple[dict[str, Any], ...]
    top_loss_signature_breakdown: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class CryptoPhase2SuiteResult:
    generated_at: datetime
    snapshot_path: str
    selection_output_dir: str
    selection_blocked_series_keys: tuple[str, ...]
    unfiltered_replay: CryptoPhase2ReplayDigest
    filtered_replay: CryptoPhase2ReplayDigest
    final_scorecard: CryptoPhase2FinalScorecard


async def run_crypto_phase2_suite(
    *,
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    config_dir: str | Path = "configs/profiles/research-crypto-phase2-v1",
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    strategy_overrides: dict[str, object] | None = None,
) -> CryptoPhase2SuiteResult:
    resolved_output_dir = Path(output_dir) if output_dir is not None else Path("data/research") / "crypto-phase2-suite"
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    selection_output_dir = resolved_output_dir / "selection"
    selection_report = generate_crypto_market_selection_report(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        output_dir=selection_output_dir,
        barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
        fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
    )
    blocked_series_keys = recommended_runtime_blocked_series_keys(selection_report)

    unfiltered_output_dir = resolved_output_dir / "replay-unfiltered"
    filtered_output_dir = resolved_output_dir / "replay-filtered"
    suite_run_id = run_id or "crypto-phase2-suite"

    await run_crypto_phase2_replay(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        config_dir=config_dir,
        limit=limit,
        output_dir=unfiltered_output_dir,
        run_id=f"{suite_run_id}-unfiltered",
        barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
        fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
        apply_series_filter=False,
        strategy_overrides=strategy_overrides,
    )
    await run_crypto_phase2_replay(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        config_dir=config_dir,
        limit=limit,
        output_dir=filtered_output_dir,
        run_id=f"{suite_run_id}-filtered",
        barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
        fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
        apply_series_filter=True,
        strategy_overrides=strategy_overrides,
    )

    partial_result = CryptoPhase2SuiteResult(
        generated_at=datetime.now(tz=timezone.utc),
        snapshot_path=str(Path(snapshot_path)),
        selection_output_dir=str(selection_output_dir),
        selection_blocked_series_keys=blocked_series_keys,
        unfiltered_replay=_load_replay_digest("unfiltered", unfiltered_output_dir),
        filtered_replay=_load_replay_digest("filtered", filtered_output_dir),
        final_scorecard=CryptoPhase2FinalScorecard(
            generated_at=datetime.now(tz=timezone.utc),
            recommended_action="review",
            readiness_score=0.0,
            execution_quality="unknown",
            evidence_status="pending",
            route_stage_acceptance_decision="review",
            route_stage_failed_stages=("scan_quality",),
            route_stage_statuses={"scan_quality": "review"},
            route_stage_blockers={"scan_quality": ("pending final scorecard",)},
            dominant_route_stage_blocker="pending final scorecard",
            next_constrained_action="complete final scorecard synthesis before tuning decisions.",
            reasons=("pending final scorecard",),
            blocked_series_keys=(),
            filtered_orders=0,
            filtered_signals=0,
            filtered_pnl=0.0,
            filtered_status="",
            filter_order_delta=0,
            selection_quality_score=0.0,
            pricing_quality_score=0.0,
            execution_quality_score=0.0,
            exit_quality_score=0.0,
            sizing_quality_score=0.0,
            average_signal_edge_bps=0.0,
            average_adverse_fill_bps=0.0,
            expected_edge_capture_bps=0.0,
            edge_capture_ratio=0.0,
            average_trade_expected_edge_bps=0.0,
            average_trade_execution_drag_bps=0.0,
            average_trade_realized_pnl_bps=0.0,
            average_barrier_observed_gap_bps=0.0,
            average_surface_observed_gap_bps=0.0,
            average_fusion_observed_gap_bps=0.0,
            average_barrier_surface_disagreement_bps=0.0,
            closed_trade_count=0,
            winning_trade_rate=0.0,
            average_win_trade_pnl=0.0,
            average_loss_trade_pnl=0.0,
            average_submitted_notional=0.0,
            large_notional_share=0.0,
            dominant_exit_reason="none",
            stop_loss_exit_share=0.0,
            passive_cleanup_exit_share=0.0,
            exit_family_balance_score=0.0,
            small_bucket_pnl_per_notional=0.0,
            medium_bucket_pnl_per_notional=0.0,
            large_bucket_pnl_per_notional=0.0,
            submitted_notional=0.0,
            pnl_per_notional=0.0,
            profit_focus="selection",
            secondary_profit_focus="pricing",
            loss_ranking=("selection", "pricing", "execution", "exit", "sizing"),
            selection_loss=1.0,
            pricing_loss=1.0,
            execution_loss=1.0,
            exit_loss=1.0,
            sizing_loss=1.0,
            total_profit_loss=5.0,
            tuning_priority="selection",
            tuning_actions=("pending final scorecard",),
            component_reasons={},
            promotion_decision="review",
            promotion_stage_label="paper available",
            promotion_blocking_reasons=("pending final scorecard",),
            promotion_min_closed_trades=3,
            promotion_min_edge_capture_ratio=0.35,
            promotion_max_execution_loss_ratio=0.65,
            promotion_min_pnl_per_notional=0.0,
            observed_execution_loss_ratio=0.0,
            promotion_max_single_loss_pnl=-0.2,
            promotion_max_top3_loss_concentration_ratio=0.75,
            observed_max_single_loss_pnl=0.0,
            observed_top3_loss_concentration_ratio=0.0,
            top_loss_trades=(),
            top_loss_market_breakdown=(),
            top_loss_signature_breakdown=(),
        ),
    )
    result = CryptoPhase2SuiteResult(
        generated_at=partial_result.generated_at,
        snapshot_path=partial_result.snapshot_path,
        selection_output_dir=partial_result.selection_output_dir,
        selection_blocked_series_keys=partial_result.selection_blocked_series_keys,
        unfiltered_replay=partial_result.unfiltered_replay,
        filtered_replay=partial_result.filtered_replay,
        final_scorecard=build_crypto_phase2_final_scorecard(partial_result),
    )
    write_crypto_phase2_suite_result(result=result, output_dir=resolved_output_dir)
    return result


def write_crypto_phase2_suite_result(*, result: CryptoPhase2SuiteResult, output_dir: str | Path) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "suite.json").write_text(
        json.dumps(_normalize(asdict(result)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "suite.md").write_text(format_crypto_phase2_suite_result(result), encoding="utf-8")
    write_crypto_phase2_final_scorecard(scorecard=result.final_scorecard, output_dir=target_dir)


def format_crypto_phase2_suite_result(result: CryptoPhase2SuiteResult) -> str:
    lines = [
        "# Crypto Phase 2 Suite",
        "",
        f"- generated_at: {result.generated_at.isoformat()}",
        f"- snapshot_path: {result.snapshot_path}",
        f"- selection_output_dir: {result.selection_output_dir}",
        f"- blocked_series_keys: {', '.join(result.selection_blocked_series_keys) if result.selection_blocked_series_keys else 'none'}",
        "",
        "## Replays",
        "",
    ]
    for replay in (result.unfiltered_replay, result.filtered_replay):
        lines.extend(
            [
                f"### {replay.label}",
                "",
                f"- output_dir: {replay.output_dir}",
                f"- signals_generated: {replay.signals_generated}",
                f"- submitted_orders: {replay.submitted_orders}",
                f"- submitted_notional: {replay.submitted_notional:.6f}",
                f"- events_recorded: {replay.events_recorded}",
                f"- today_pnl: {replay.today_pnl:.6f}",
                f"- total_equity: {replay.total_equity:.6f}",
                f"- status: {replay.status}",
                f"- maker_fill_rate: {replay.maker_fill_rate:.4f}",
                f"- taker_fill_rate: {replay.taker_fill_rate:.4f}",
                f"- expiration_rate: {replay.expiration_rate:.4f}",
                f"- stop_out_rate: {replay.stop_out_rate:.4f}",
                f"- average_trade_pnl: {replay.average_trade_pnl:.6f}",
                f"- average_signal_edge_bps: {replay.average_signal_edge_bps:.4f}",
                f"- average_adverse_fill_bps: {replay.average_adverse_fill_bps:.4f}",
                f"- expected_edge_capture_bps: {replay.expected_edge_capture_bps:.4f}",
                f"- edge_capture_ratio: {replay.edge_capture_ratio:.4f}",
                f"- average_trade_expected_edge_bps: {replay.average_trade_expected_edge_bps:.4f}",
                f"- average_trade_execution_drag_bps: {replay.average_trade_execution_drag_bps:.4f}",
                f"- average_trade_realized_pnl_bps: {replay.average_trade_realized_pnl_bps:.4f}",
                f"- average_barrier_observed_gap_bps: {replay.average_barrier_observed_gap_bps:.4f}",
                f"- average_surface_observed_gap_bps: {replay.average_surface_observed_gap_bps:.4f}",
                f"- average_fusion_observed_gap_bps: {replay.average_fusion_observed_gap_bps:.4f}",
                f"- average_barrier_surface_disagreement_bps: {replay.average_barrier_surface_disagreement_bps:.4f}",
                f"- closed_trade_net_pnl: {replay.closed_trade_net_pnl:.6f}",
                f"- closed_trade_count: {replay.closed_trade_count}",
                f"- winning_trade_rate: {replay.winning_trade_rate:.4f}",
                f"- average_win_trade_pnl: {replay.average_win_trade_pnl:.6f}",
                f"- average_loss_trade_pnl: {replay.average_loss_trade_pnl:.6f}",
                f"- average_submitted_notional: {replay.average_submitted_notional:.6f}",
                f"- large_notional_share: {replay.large_notional_share:.4f}",
                f"- dominant_exit_reason: {replay.dominant_exit_reason}",
                f"- stop_loss_exit_share: {replay.stop_loss_exit_share:.4f}",
                f"- passive_cleanup_exit_share: {replay.passive_cleanup_exit_share:.4f}",
                f"- exit_family_balance_score: {replay.exit_family_balance_score:.4f}",
                f"- small_bucket_pnl_per_notional: {replay.small_bucket_pnl_per_notional:.6f}",
                f"- medium_bucket_pnl_per_notional: {replay.medium_bucket_pnl_per_notional:.6f}",
                f"- large_bucket_pnl_per_notional: {replay.large_bucket_pnl_per_notional:.6f}",
                f"- execution_feedback_bias: {replay.execution_feedback_bias}",
                f"- top_loss_trades: {json.dumps(list(replay.top_loss_trades), ensure_ascii=True)}",
                f"- top_loss_market_breakdown: {json.dumps(list(replay.top_loss_market_breakdown), ensure_ascii=True)}",
                f"- top_loss_signature_breakdown: {json.dumps(list(replay.top_loss_signature_breakdown), ensure_ascii=True)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Delta",
            "",
            f"- signals_delta: {result.filtered_replay.signals_generated - result.unfiltered_replay.signals_generated}",
            f"- orders_delta: {result.filtered_replay.submitted_orders - result.unfiltered_replay.submitted_orders}",
            f"- pnl_delta: {result.filtered_replay.today_pnl - result.unfiltered_replay.today_pnl:.6f}",
            "",
            "## Final Scorecard",
            "",
            f"- recommended_action: {result.final_scorecard.recommended_action}",
            f"- readiness_score: {result.final_scorecard.readiness_score:.4f}",
            f"- execution_quality: {result.final_scorecard.execution_quality}",
            f"- evidence_status: {result.final_scorecard.evidence_status}",
            f"- route_stage_acceptance_decision: {result.final_scorecard.route_stage_acceptance_decision}",
            f"- route_stage_failed_stages: {', '.join(result.final_scorecard.route_stage_failed_stages) if result.final_scorecard.route_stage_failed_stages else 'none'}",
            f"- dominant_route_stage_blocker: {result.final_scorecard.dominant_route_stage_blocker or 'none'}",
            f"- next_constrained_action: {result.final_scorecard.next_constrained_action}",
            f"- promotion_decision: {result.final_scorecard.promotion_decision}",
            f"- promotion_stage_label: {result.final_scorecard.promotion_stage_label}",
            f"- promotion_blocking_reasons: {', '.join(result.final_scorecard.promotion_blocking_reasons) if result.final_scorecard.promotion_blocking_reasons else 'none'}",
            f"- profit_focus: {result.final_scorecard.profit_focus}",
            f"- selection_quality_score: {result.final_scorecard.selection_quality_score:.4f}",
            f"- pricing_quality_score: {result.final_scorecard.pricing_quality_score:.4f}",
            f"- execution_quality_score: {result.final_scorecard.execution_quality_score:.4f}",
            f"- exit_quality_score: {result.final_scorecard.exit_quality_score:.4f}",
            f"- sizing_quality_score: {result.final_scorecard.sizing_quality_score:.4f}",
            f"- selection_loss: {result.final_scorecard.selection_loss:.4f}",
            f"- pricing_loss: {result.final_scorecard.pricing_loss:.4f}",
            f"- execution_loss: {result.final_scorecard.execution_loss:.4f}",
            f"- exit_loss: {result.final_scorecard.exit_loss:.4f}",
            f"- sizing_loss: {result.final_scorecard.sizing_loss:.4f}",
            f"- total_profit_loss: {result.final_scorecard.total_profit_loss:.4f}",
            f"- tuning_priority: {result.final_scorecard.tuning_priority}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _load_replay_digest(label: str, output_dir: Path) -> CryptoPhase2ReplayDigest:
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    execution_feedback = _load_execution_feedback(output_dir / "events.jsonl")
    pricing_decomposition = _load_pricing_decomposition(output_dir / "fair_values.jsonl")
    return CryptoPhase2ReplayDigest(
        label=label,
        output_dir=str(output_dir),
        signals_generated=int(metrics.get("signals_generated", 0)),
        submitted_orders=int(metrics.get("submitted_orders", 0)),
        submitted_notional=float(execution_feedback["submitted_notional"]),
        events_recorded=int(metrics.get("events_recorded", 0)),
        today_pnl=float(metrics.get("today_pnl", 0.0)),
        total_equity=float(metrics.get("total_equity", 0.0)),
        status=str(metrics.get("status", "")),
        maker_fill_rate=float(execution_feedback["maker_fill_rate"]),
        taker_fill_rate=float(execution_feedback["taker_fill_rate"]),
        expiration_rate=float(execution_feedback["expiration_rate"]),
        stop_out_rate=float(execution_feedback["stop_out_rate"]),
        average_trade_pnl=float(execution_feedback["average_trade_pnl"]),
        average_signal_edge_bps=float(execution_feedback["average_signal_edge_bps"]),
        average_adverse_fill_bps=float(execution_feedback["average_adverse_fill_bps"]),
        expected_edge_capture_bps=float(execution_feedback["expected_edge_capture_bps"]),
        edge_capture_ratio=float(execution_feedback["edge_capture_ratio"]),
        average_trade_expected_edge_bps=float(execution_feedback["average_trade_expected_edge_bps"]),
        average_trade_execution_drag_bps=float(execution_feedback["average_trade_execution_drag_bps"]),
        average_trade_realized_pnl_bps=float(execution_feedback["average_trade_realized_pnl_bps"]),
        average_barrier_observed_gap_bps=float(pricing_decomposition["average_barrier_observed_gap_bps"]),
        average_surface_observed_gap_bps=float(pricing_decomposition["average_surface_observed_gap_bps"]),
        average_fusion_observed_gap_bps=float(pricing_decomposition["average_fusion_observed_gap_bps"]),
        average_barrier_surface_disagreement_bps=float(pricing_decomposition["average_barrier_surface_disagreement_bps"]),
        closed_trade_net_pnl=float(execution_feedback["closed_trade_net_pnl"]),
        closed_trade_count=int(execution_feedback["closed_trade_count"]),
        winning_trade_rate=float(execution_feedback["winning_trade_rate"]),
        average_win_trade_pnl=float(execution_feedback["average_win_trade_pnl"]),
        average_loss_trade_pnl=float(execution_feedback["average_loss_trade_pnl"]),
        average_submitted_notional=float(execution_feedback["average_submitted_notional"]),
        large_notional_share=float(execution_feedback["large_notional_share"]),
        dominant_exit_reason=str(execution_feedback["dominant_exit_reason"]),
        stop_loss_exit_share=float(execution_feedback["stop_loss_exit_share"]),
        passive_cleanup_exit_share=float(execution_feedback["passive_cleanup_exit_share"]),
        exit_family_balance_score=float(execution_feedback["exit_family_balance_score"]),
        small_bucket_pnl_per_notional=float(execution_feedback["small_bucket_pnl_per_notional"]),
        medium_bucket_pnl_per_notional=float(execution_feedback["medium_bucket_pnl_per_notional"]),
        large_bucket_pnl_per_notional=float(execution_feedback["large_bucket_pnl_per_notional"]),
        execution_feedback_bias=str(execution_feedback["execution_feedback_bias"]),
        top_loss_trades=tuple(execution_feedback["top_loss_trades"]),
        top_loss_market_breakdown=tuple(execution_feedback["top_loss_market_breakdown"]),
        top_loss_signature_breakdown=tuple(execution_feedback["top_loss_signature_breakdown"]),
    )


def _load_execution_feedback(events_path: Path) -> dict[str, Any]:
    if not events_path.exists():
        return {
            "maker_fill_rate": 0.0,
            "taker_fill_rate": 0.0,
            "expiration_rate": 0.0,
            "stop_out_rate": 0.0,
            "average_trade_pnl": 0.0,
            "average_signal_edge_bps": 0.0,
            "average_adverse_fill_bps": 0.0,
            "expected_edge_capture_bps": 0.0,
            "edge_capture_ratio": 0.0,
            "average_trade_expected_edge_bps": 0.0,
            "average_trade_execution_drag_bps": 0.0,
            "average_trade_realized_pnl_bps": 0.0,
            "submitted_notional": 0.0,
            "closed_trade_net_pnl": 0.0,
            "closed_trade_count": 0,
            "winning_trade_rate": 0.0,
            "average_win_trade_pnl": 0.0,
            "average_loss_trade_pnl": 0.0,
            "average_submitted_notional": 0.0,
            "large_notional_share": 0.0,
            "dominant_exit_reason": "none",
            "stop_loss_exit_share": 0.0,
            "passive_cleanup_exit_share": 0.0,
            "exit_family_balance_score": 0.0,
            "small_bucket_pnl_per_notional": 0.0,
            "medium_bucket_pnl_per_notional": 0.0,
            "large_bucket_pnl_per_notional": 0.0,
            "execution_feedback_bias": "stable",
            "top_loss_trades": [],
            "top_loss_market_breakdown": [],
            "top_loss_signature_breakdown": [],
        }

    maker_submitted = 0
    taker_submitted = 0
    maker_filled = 0
    taker_filled = 0
    expired_orders = 0
    closed_trades = 0
    negative_closed_trades = 0
    positive_closed_trades = 0
    total_trade_pnl = 0.0
    weighted_signal_edge_bps = 0.0
    weighted_adverse_fill_bps = 0.0
    fill_weight = 0.0
    submitted_notional = 0.0
    submitted_order_count = 0
    large_notional_orders = 0
    total_positive_trade_pnl = 0.0
    total_negative_trade_pnl = 0.0
    exit_reason_by_intent: dict[str, str] = {}
    exit_reason_counts: dict[str, int] = {}
    intent_signal_edge_weighted: dict[str, float] = {}
    intent_fill_shares: dict[str, float] = {}
    intent_adverse_fill_weighted: dict[str, float] = {}
    intent_matched_notional: dict[str, float] = {}
    intent_closed_pnl: dict[str, float] = {}
    intent_bucket: dict[str, str] = {}
    intent_metadata: dict[str, dict[str, str]] = {}
    bucket_submitted_notional = {"small": 0.0, "medium": 0.0, "large": 0.0}
    bucket_closed_pnl = {"small": 0.0, "medium": 0.0, "large": 0.0}
    top_loss_candidates: list[dict[str, Any]] = []
    market_loss_totals: dict[str, float] = {}
    market_loss_counts: dict[str, int] = {}
    signature_loss_totals: dict[str, float] = {}
    signature_loss_counts: dict[str, int] = {}

    for raw_line in events_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        decoded = json.loads(raw_line)
        if not isinstance(decoded, dict):
            continue
        event_type = str(decoded.get("event_type", ""))
        payload = decoded.get("payload", {})
        if not isinstance(payload, dict):
            continue
        if event_type == "order.submitted":
            order_notional = float(payload.get("notional", 0.0) or 0.0)
            submitted_notional += order_notional
            submitted_order_count += 1
            bucket = _size_bucket(order_notional)
            bucket_submitted_notional[bucket] += order_notional
            if order_notional >= 6.0:
                large_notional_orders += 1
            intent_id = str(payload.get("intent_id", "")).strip()
            if intent_id:
                intent_bucket[intent_id] = bucket
            diagnostics = payload.get("diagnostics", {})
            rationale_tags = payload.get("rationale_tags", [])
            if not isinstance(diagnostics, dict):
                diagnostics = {}
            if not isinstance(rationale_tags, list):
                rationale_tags = []
            signal_type = str(diagnostics.get("signal_type", "")).strip().lower()
            if intent_id and signal_type == "exit":
                exit_reason_by_intent[intent_id] = next(
                    (
                        str(tag)
                        for tag in rationale_tags
                        if isinstance(tag, str)
                        and tag in {"stop_loss", "aging_exit", "stale_position_cleanup", "time_stop", "adverse_fill_reversal"}
                    ),
                    "exit",
                )
            if str(payload.get("time_in_force", "")).upper() == "IOC":
                taker_submitted += 1
            else:
                maker_submitted += 1
            if intent_id:
                signal_type = str(diagnostics.get("signal_type", "unknown") or "unknown").strip() or "unknown"
                execution_route = str(diagnostics.get("execution_route", "unknown") or "unknown").strip() or "unknown"
                phase2_preset = str(diagnostics.get("phase2_preset", "unknown") or "unknown").strip() or "unknown"
                intent_metadata[intent_id] = {
                    "signal_type": signal_type,
                    "execution_route": execution_route,
                    "phase2_preset": phase2_preset,
                    "side": str(payload.get("side", "unknown") or "unknown").strip() or "unknown",
                    "market_id": str(payload.get("market_id", "unknown") or "unknown").strip() or "unknown",
                    "underlying_group_id": str(payload.get("underlying_group_id", "unknown") or "unknown").strip() or "unknown",
                    "thesis_group_id": str(payload.get("thesis_group_id", "unknown") or "unknown").strip() or "unknown",
                }
        elif event_type in {"order.filled", "order.partially_filled"}:
            fill_source = str(payload.get("fill_source", "")).lower()
            if fill_source == "taker":
                taker_filled += 1
            else:
                maker_filled += 1
            fill_shares_delta = float(payload.get("fill_shares_delta", 0.0) or 0.0)
            if fill_shares_delta > 0:
                intent_id = str(payload.get("intent_id", "")).strip()
                signal_edge_bps = float(payload.get("signal_edge_bps", 0.0) or 0.0)
                weighted_signal_edge_bps += signal_edge_bps * fill_shares_delta
                fill_weight += fill_shares_delta
                if intent_id:
                    intent_signal_edge_weighted[intent_id] = intent_signal_edge_weighted.get(intent_id, 0.0) + (
                        signal_edge_bps * fill_shares_delta
                    )
                    intent_fill_shares[intent_id] = intent_fill_shares.get(intent_id, 0.0) + fill_shares_delta
                    intent_matched_notional[intent_id] = intent_matched_notional.get(intent_id, 0.0) + float(
                        payload.get("fill_notional_delta", 0.0) or 0.0
                    )
                trade_side = str(payload.get("trade_side", "")).upper()
                mid_price = payload.get("mid_price")
                average_fill_price = payload.get("average_fill_price")
                if mid_price not in {None, ""} and average_fill_price not in {None, ""}:
                    mid = float(mid_price or 0.0)
                    fill = float(average_fill_price or 0.0)
                    if mid > 0:
                        if trade_side == "SELL":
                            adverse_fill_bps = max(0.0, ((mid - fill) / mid) * 10000)
                        else:
                            adverse_fill_bps = max(0.0, ((fill - mid) / mid) * 10000)
                        weighted_adverse_fill_bps += adverse_fill_bps * fill_shares_delta
                        if intent_id:
                            intent_adverse_fill_weighted[intent_id] = intent_adverse_fill_weighted.get(intent_id, 0.0) + (
                                adverse_fill_bps * fill_shares_delta
                            )
        elif event_type == "order.expired":
            expired_orders += 1
        elif event_type == "trade.closed":
            closed_trades += 1
            net_pnl = float(payload.get("net_pnl", 0.0) or 0.0)
            total_trade_pnl += net_pnl
            intent_id = str(payload.get("intent_id", "")).strip()
            exit_reason = exit_reason_by_intent.get(intent_id, "unknown")
            exit_reason_counts[exit_reason] = exit_reason_counts.get(exit_reason, 0) + 1
            closed_bucket: str | None = intent_bucket.get(intent_id)
            if closed_bucket:
                bucket_closed_pnl[closed_bucket] += net_pnl
            if intent_id:
                intent_closed_pnl[intent_id] = intent_closed_pnl.get(intent_id, 0.0) + net_pnl
            metadata = intent_metadata.get(intent_id, {})
            market_id = str(payload.get("market_id", metadata.get("market_id", "unknown")) or "unknown")
            signal_type = metadata.get("signal_type", "unknown")
            execution_route = metadata.get("execution_route", "unknown")
            phase2_preset = metadata.get("phase2_preset", "unknown")
            side = metadata.get("side", "unknown")
            underlying_group_id = str(payload.get("underlying_group_id", metadata.get("underlying_group_id", "unknown")) or "unknown")
            thesis_group_id = str(payload.get("thesis_group_id", metadata.get("thesis_group_id", "unknown")) or "unknown")
            signature = "|".join((signal_type, execution_route, phase2_preset, side))
            if net_pnl < 0:
                negative_closed_trades += 1
                total_negative_trade_pnl += net_pnl
                market_loss_totals[market_id] = market_loss_totals.get(market_id, 0.0) + abs(net_pnl)
                market_loss_counts[market_id] = market_loss_counts.get(market_id, 0) + 1
                signature_loss_totals[signature] = signature_loss_totals.get(signature, 0.0) + abs(net_pnl)
                signature_loss_counts[signature] = signature_loss_counts.get(signature, 0) + 1
                top_loss_candidates.append(
                    {
                        "intent_id": intent_id or "unknown",
                        "market_id": market_id,
                        "net_pnl": round(net_pnl, 6),
                        "abs_loss": round(abs(net_pnl), 6),
                        "signal_type": signal_type,
                        "execution_route": execution_route,
                        "phase2_preset": phase2_preset,
                        "side": side,
                        "underlying_group_id": underlying_group_id,
                        "thesis_group_id": thesis_group_id,
                        "signature": signature,
                        "closed_at": str(payload.get("closed_at", "") or ""),
                    }
                )
            elif net_pnl > 0:
                positive_closed_trades += 1
                total_positive_trade_pnl += net_pnl

    maker_fill_rate = (maker_filled / maker_submitted) if maker_submitted > 0 else 0.0
    taker_fill_rate = (taker_filled / taker_submitted) if taker_submitted > 0 else 0.0
    expiration_rate = (expired_orders / maker_submitted) if maker_submitted > 0 else 0.0
    stop_out_rate = (negative_closed_trades / closed_trades) if closed_trades > 0 else 0.0
    average_trade_pnl = (total_trade_pnl / closed_trades) if closed_trades > 0 else 0.0
    average_signal_edge_bps = (weighted_signal_edge_bps / fill_weight) if fill_weight > 0 else 0.0
    average_adverse_fill_bps = (weighted_adverse_fill_bps / fill_weight) if fill_weight > 0 else 0.0
    expected_edge_capture_bps = max(0.0, average_signal_edge_bps - average_adverse_fill_bps)
    edge_capture_ratio = (
        max(0.0, min(1.5, expected_edge_capture_bps / average_signal_edge_bps))
        if average_signal_edge_bps > 0
        else 0.0
    )
    winning_trade_rate = (positive_closed_trades / closed_trades) if closed_trades > 0 else 0.0
    average_win_trade_pnl = (total_positive_trade_pnl / positive_closed_trades) if positive_closed_trades > 0 else 0.0
    average_loss_trade_pnl = (total_negative_trade_pnl / negative_closed_trades) if negative_closed_trades > 0 else 0.0
    average_submitted_notional = (submitted_notional / submitted_order_count) if submitted_order_count > 0 else 0.0
    large_notional_share = (large_notional_orders / submitted_order_count) if submitted_order_count > 0 else 0.0
    dominant_exit_reason = max(exit_reason_counts.items(), key=lambda item: item[1])[0] if exit_reason_counts else "none"
    stop_loss_exit_share = (exit_reason_counts.get("stop_loss", 0) / closed_trades) if closed_trades > 0 else 0.0
    passive_cleanup_exit_share = (
        (
            exit_reason_counts.get("aging_exit", 0)
            + exit_reason_counts.get("stale_position_cleanup", 0)
            + exit_reason_counts.get("time_stop", 0)
        ) / closed_trades
        if closed_trades > 0
        else 0.0
    )
    trade_expected_edge_total = 0.0
    trade_execution_drag_total = 0.0
    trade_realized_pnl_bps_total = 0.0
    trade_level_count = 0
    for intent_id, matched_notional in intent_matched_notional.items():
        if matched_notional <= 0:
            continue
        fill_shares = intent_fill_shares.get(intent_id, 0.0)
        expected_edge = (
            intent_signal_edge_weighted.get(intent_id, 0.0) / fill_shares
            if fill_shares > 0
            else 0.0
        )
        execution_drag = (
            intent_adverse_fill_weighted.get(intent_id, 0.0) / fill_shares
            if fill_shares > 0
            else 0.0
        )
        trade_expected_edge_total += expected_edge
        trade_execution_drag_total += execution_drag
        if intent_id in intent_closed_pnl:
            trade_realized_pnl_bps_total += (intent_closed_pnl[intent_id] / matched_notional) * 10000
        trade_level_count += 1
    exit_family_balance_score = max(
        0.0,
        min(
            1.0,
            1.0 - (stop_loss_exit_share * 0.6) - (passive_cleanup_exit_share * 0.4),
        ),
    ) if closed_trades > 0 else 0.0
    small_bucket_pnl_per_notional = (
        bucket_closed_pnl["small"] / bucket_submitted_notional["small"]
        if bucket_submitted_notional["small"] > 0
        else 0.0
    )
    medium_bucket_pnl_per_notional = (
        bucket_closed_pnl["medium"] / bucket_submitted_notional["medium"]
        if bucket_submitted_notional["medium"] > 0
        else 0.0
    )
    large_bucket_pnl_per_notional = (
        bucket_closed_pnl["large"] / bucket_submitted_notional["large"]
        if bucket_submitted_notional["large"] > 0
        else 0.0
    )
    if stop_out_rate >= 0.5:
        execution_feedback_bias = "more_passive"
    elif expiration_rate >= 0.6 and maker_fill_rate < 0.2:
        execution_feedback_bias = "more_aggressive"
    else:
        execution_feedback_bias = "stable"
    top_loss_trades = sorted(
        top_loss_candidates,
        key=lambda item: (float(item["net_pnl"]), str(item["market_id"]), str(item["intent_id"])),
    )[:3]
    top_loss_market_breakdown = [
        {"market_id": market_id, "total_abs_loss": round(total_abs_loss, 6), "loss_count": market_loss_counts[market_id]}
        for market_id, total_abs_loss in sorted(
            market_loss_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
    ]
    top_loss_signature_breakdown = [
        {"signature": signature, "total_abs_loss": round(total_abs_loss, 6), "loss_count": signature_loss_counts[signature]}
        for signature, total_abs_loss in sorted(
            signature_loss_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
    ]
    return {
        "maker_fill_rate": round(maker_fill_rate, 4),
        "taker_fill_rate": round(taker_fill_rate, 4),
        "expiration_rate": round(expiration_rate, 4),
        "stop_out_rate": round(stop_out_rate, 4),
        "average_trade_pnl": round(average_trade_pnl, 6),
        "average_signal_edge_bps": round(average_signal_edge_bps, 4),
        "average_adverse_fill_bps": round(average_adverse_fill_bps, 4),
        "expected_edge_capture_bps": round(expected_edge_capture_bps, 4),
        "edge_capture_ratio": round(edge_capture_ratio, 4),
        "average_trade_expected_edge_bps": round((trade_expected_edge_total / trade_level_count), 4) if trade_level_count > 0 else 0.0,
        "average_trade_execution_drag_bps": round((trade_execution_drag_total / trade_level_count), 4) if trade_level_count > 0 else 0.0,
        "average_trade_realized_pnl_bps": round((trade_realized_pnl_bps_total / trade_level_count), 4) if trade_level_count > 0 else 0.0,
        "submitted_notional": round(submitted_notional, 6),
        "closed_trade_net_pnl": round(total_trade_pnl, 6),
        "closed_trade_count": closed_trades,
        "winning_trade_rate": round(winning_trade_rate, 4),
        "average_win_trade_pnl": round(average_win_trade_pnl, 6),
        "average_loss_trade_pnl": round(average_loss_trade_pnl, 6),
        "average_submitted_notional": round(average_submitted_notional, 6),
        "large_notional_share": round(large_notional_share, 4),
        "dominant_exit_reason": dominant_exit_reason,
        "stop_loss_exit_share": round(stop_loss_exit_share, 4),
        "passive_cleanup_exit_share": round(passive_cleanup_exit_share, 4),
        "exit_family_balance_score": round(exit_family_balance_score, 4),
        "small_bucket_pnl_per_notional": round(small_bucket_pnl_per_notional, 6),
        "medium_bucket_pnl_per_notional": round(medium_bucket_pnl_per_notional, 6),
        "large_bucket_pnl_per_notional": round(large_bucket_pnl_per_notional, 6),
        "execution_feedback_bias": execution_feedback_bias,
        "top_loss_trades": top_loss_trades,
        "top_loss_market_breakdown": top_loss_market_breakdown,
        "top_loss_signature_breakdown": top_loss_signature_breakdown,
    }


def _size_bucket(notional: float) -> str:
    if notional < 4.5:
        return "small"
    if notional < 6.0:
        return "medium"
    return "large"


def _load_pricing_decomposition(fair_values_path: Path) -> dict[str, float]:
    if not fair_values_path.exists():
        return {
            "average_barrier_observed_gap_bps": 0.0,
            "average_surface_observed_gap_bps": 0.0,
            "average_fusion_observed_gap_bps": 0.0,
            "average_barrier_surface_disagreement_bps": 0.0,
        }
    barrier_gap_total = 0.0
    surface_gap_total = 0.0
    fusion_gap_total = 0.0
    barrier_surface_gap_total = 0.0
    count = 0
    surface_count = 0
    for raw_line in fair_values_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        decoded = json.loads(raw_line)
        if not isinstance(decoded, dict):
            continue
        observed_probability = decoded.get("observed_probability")
        fair_probability = decoded.get("fair_probability")
        supporting_values = decoded.get("supporting_values", {})
        if not isinstance(supporting_values, dict):
            supporting_values = {}
        barrier_probability = supporting_values.get("barrier_probability")
        surface_probability = supporting_values.get("surface_probability")
        if not isinstance(observed_probability, (int, float)) or not isinstance(fair_probability, (int, float)):
            continue
        if isinstance(barrier_probability, (int, float)):
            barrier_gap_total += abs(float(barrier_probability) - float(observed_probability)) * 10000
        else:
            barrier_gap_total += abs(float(fair_probability) - float(observed_probability)) * 10000
        fusion_gap_total += abs(float(fair_probability) - float(observed_probability)) * 10000
        count += 1
        if isinstance(surface_probability, (int, float)):
            surface_gap_total += abs(float(surface_probability) - float(observed_probability)) * 10000
            if isinstance(barrier_probability, (int, float)):
                barrier_surface_gap_total += abs(float(barrier_probability) - float(surface_probability)) * 10000
            surface_count += 1
    return {
        "average_barrier_observed_gap_bps": round((barrier_gap_total / count), 4) if count > 0 else 0.0,
        "average_surface_observed_gap_bps": round((surface_gap_total / surface_count), 4) if surface_count > 0 else 0.0,
        "average_fusion_observed_gap_bps": round((fusion_gap_total / count), 4) if count > 0 else 0.0,
        "average_barrier_surface_disagreement_bps": round((barrier_surface_gap_total / surface_count), 4) if surface_count > 0 else 0.0,
    }


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
