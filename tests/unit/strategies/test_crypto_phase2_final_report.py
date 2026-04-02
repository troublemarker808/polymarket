from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast

from pm_bot.strategies.crypto.phase2.final_report import build_crypto_phase2_final_scorecard
from pm_bot.strategies.crypto.phase2.suite import CryptoPhase2ReplayDigest, CryptoPhase2SuiteResult


def test_final_scorecard_promotion_gate_proceeds_when_profitability_and_stability_are_healthy() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=6,
        closed_trade_net_pnl=0.6,
        submitted_notional=10.0,
        edge_capture_ratio=0.6,
        average_trade_expected_edge_bps=100.0,
        average_trade_execution_drag_bps=20.0,
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert scorecard.recommended_action == "proceed"
    assert scorecard.operator_verdict == "go_next_maturity_step"
    assert scorecard.promotion_decision == "proceed"
    assert scorecard.promotion_stage_label == "shadow validation"
    assert scorecard.promotion_blocking_reasons == ()
    assert scorecard.route_stage_acceptance_decision == "proceed"
    assert scorecard.route_stage_failed_stages == ()
    assert scorecard.route_stage_statuses["scan_quality"] == "pass"
    assert scorecard.dominant_route_stage_blocker is None


def test_final_scorecard_promotion_gate_reviews_when_evidence_is_thin() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=1,
        closed_trade_net_pnl=0.2,
        submitted_notional=5.0,
        edge_capture_ratio=0.55,
        average_trade_expected_edge_bps=90.0,
        average_trade_execution_drag_bps=20.0,
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert scorecard.recommended_action == "review"
    assert scorecard.promotion_decision == "review"
    assert "insufficient_closed_trade_count" in scorecard.promotion_blocking_reasons
    assert "close_out_insufficient_closed_trade_density" in scorecard.route_stage_blockers["close_out_quality"]
    assert scorecard.route_stage_acceptance_decision in {"proceed", "review"}


def test_final_scorecard_promotion_gate_pauses_on_halted_status_even_if_profitability_is_positive() -> None:
    filtered = _digest(
        label="filtered",
        status="halted",
        closed_trade_count=8,
        closed_trade_net_pnl=1.2,
        submitted_notional=10.0,
        edge_capture_ratio=0.75,
        average_trade_expected_edge_bps=120.0,
        average_trade_execution_drag_bps=30.0,
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert scorecard.recommended_action == "pause"
    assert scorecard.operator_verdict == "review_required"
    assert scorecard.promotion_decision == "pause"
    assert "risk_status_halted" in scorecard.promotion_blocking_reasons
    assert scorecard.route_stage_statuses["route_conversion_quality"] == "blocked"
    assert "route_halted" in scorecard.route_stage_blockers["route_conversion_quality"]


def test_final_scorecard_promotion_gate_reviews_when_single_loss_breaches_bound() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=6,
        closed_trade_net_pnl=0.4,
        submitted_notional=10.0,
        edge_capture_ratio=0.6,
        average_trade_expected_edge_bps=100.0,
        average_trade_execution_drag_bps=20.0,
        top_loss_trades=(
            {"market_id": "btc-1", "net_pnl": -0.25},
            {"market_id": "btc-2", "net_pnl": -0.06},
        ),
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert scorecard.promotion_decision == "review"
    assert "single_loss_breach" in scorecard.promotion_blocking_reasons
    assert scorecard.observed_max_single_loss_pnl == -0.25
    assert "tail_loss_single_loss_breach" in scorecard.route_stage_blockers["profitability_tail_risk"]


def test_final_scorecard_promotion_gate_reviews_when_top3_loss_concentration_is_too_high() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=10,
        closed_trade_net_pnl=0.5,
        submitted_notional=10.0,
        edge_capture_ratio=0.6,
        average_trade_expected_edge_bps=100.0,
        average_trade_execution_drag_bps=20.0,
        winning_trade_rate=0.4,
        average_loss_trade_pnl=-0.05,
        top_loss_trades=(
            {"market_id": "btc-1", "net_pnl": -0.15},
            {"market_id": "btc-2", "net_pnl": -0.10},
            {"market_id": "btc-3", "net_pnl": -0.06},
        ),
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert scorecard.promotion_decision == "review"
    assert "top3_loss_concentration_above_ceiling" in scorecard.promotion_blocking_reasons
    assert scorecard.observed_top3_loss_concentration_ratio > scorecard.promotion_max_top3_loss_concentration_ratio
    assert "tail_loss_top3_concentration_breach" in scorecard.route_stage_blockers["profitability_tail_risk"]
    assert scorecard.dominant_route_stage_blocker == "tail_loss_top3_concentration_breach"


def test_final_scorecard_route_stage_flags_sizing_large_bucket_underperformance() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=8,
        closed_trade_net_pnl=0.3,
        submitted_notional=12.0,
        edge_capture_ratio=0.7,
        average_trade_expected_edge_bps=100.0,
        average_trade_execution_drag_bps=20.0,
    )
    filtered = replace(
        filtered,
        small_bucket_pnl_per_notional=0.02,
        large_bucket_pnl_per_notional=-0.01,
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert "sizing_large_bucket_underperformance" in scorecard.route_stage_blockers["profitability_tail_risk"]
    assert scorecard.route_stage_acceptance_decision == "review"


def test_final_scorecard_route_stage_flags_signature_concentration_and_maps_action() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=10,
        closed_trade_net_pnl=0.4,
        submitted_notional=10.0,
        edge_capture_ratio=0.7,
        average_trade_expected_edge_bps=100.0,
        average_trade_execution_drag_bps=20.0,
        winning_trade_rate=0.8,
        average_loss_trade_pnl=-0.1,
        top_loss_signature_breakdown=(
            {"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.19, "loss_count": 2},
        ),
    )
    filtered = replace(
        filtered,
        average_adverse_fill_bps=10.0,
        stop_out_rate=0.2,
        average_trade_realized_pnl_bps=10.0,
        passive_cleanup_exit_share=0.2,
    )
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=_digest(label="unfiltered")))

    assert "tail_loss_signature_concentration_breach" in scorecard.route_stage_blockers["profitability_tail_risk"]
    assert scorecard.next_constrained_action == (
        "tighten signature-level loss caps and reduce repeat exposure on the dominant losing signature."
    )
    assert scorecard.operator_summary.startswith("Primary blocker is signature-level loss concentration")


def test_final_scorecard_does_not_fail_scan_quality_for_expected_policy_blocked_series() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=0,
        closed_trade_net_pnl=0.0,
        submitted_notional=5.0,
        edge_capture_ratio=0.0,
        average_trade_expected_edge_bps=0.0,
        average_trade_execution_drag_bps=0.0,
    )
    filtered = replace(
        filtered,
        signals_generated=1,
        submitted_orders=1,
        closed_trade_count=0,
        closed_trade_net_pnl=0.0,
    )
    unfiltered = replace(filtered, label="unfiltered")
    scorecard = build_crypto_phase2_final_scorecard(
        CryptoPhase2SuiteResult(
            generated_at=datetime(2026, 4, 1, tzinfo=UTC),
            snapshot_path="snapshot.jsonl",
            selection_output_dir="selection",
            selection_blocked_series_keys=("when-will-bitcoin-hit-150k",),
            unfiltered_replay=unfiltered,
            filtered_replay=filtered,
            final_scorecard=cast(Any, None),
        )
    )

    assert scorecard.route_stage_statuses["scan_quality"] == "pass"
    assert scorecard.route_stage_blockers["scan_quality"] == ()
    assert scorecard.next_constrained_action != "repair scan/selection input quality before adjusting execution thresholds."


def test_final_scorecard_does_not_fail_selection_for_expected_filtered_order_delta() -> None:
    filtered = _digest(
        label="filtered",
        status="running",
        closed_trade_count=0,
        closed_trade_net_pnl=0.0,
        submitted_notional=5.0,
        edge_capture_ratio=0.0,
        average_trade_expected_edge_bps=0.0,
        average_trade_execution_drag_bps=0.0,
    )
    filtered = replace(filtered, signals_generated=5, submitted_orders=5, submitted_notional=25.0)
    unfiltered = replace(filtered, label="unfiltered", signals_generated=7, submitted_orders=6, submitted_notional=30.0)
    scorecard = build_crypto_phase2_final_scorecard(_suite(filtered=filtered, unfiltered=unfiltered))

    assert scorecard.route_stage_statuses["selection_pass_through"] == "pass"
    assert scorecard.route_stage_blockers["selection_pass_through"] == ()


def _suite(*, filtered: CryptoPhase2ReplayDigest, unfiltered: CryptoPhase2ReplayDigest) -> CryptoPhase2SuiteResult:
    return CryptoPhase2SuiteResult(
        generated_at=datetime(2026, 4, 1, tzinfo=UTC),
        snapshot_path="snapshot.jsonl",
        selection_output_dir="selection",
        selection_blocked_series_keys=(),
        unfiltered_replay=unfiltered,
        filtered_replay=filtered,
        final_scorecard=cast(Any, None),
    )


def _digest(
    *,
    label: str,
    status: str = "running",
    closed_trade_count: int = 4,
    closed_trade_net_pnl: float = 0.2,
    submitted_notional: float = 8.0,
    edge_capture_ratio: float = 0.45,
    average_trade_expected_edge_bps: float = 80.0,
    average_trade_execution_drag_bps: float = 25.0,
    winning_trade_rate: float = 0.6,
    average_loss_trade_pnl: float = -0.05,
    top_loss_trades: tuple[dict[str, Any], ...] = (),
    top_loss_signature_breakdown: tuple[dict[str, Any], ...] = (),
) -> CryptoPhase2ReplayDigest:
    return CryptoPhase2ReplayDigest(
        label=label,
        output_dir=f"/tmp/{label}",
        signals_generated=10,
        submitted_orders=6,
        submitted_notional=submitted_notional,
        events_recorded=20,
        today_pnl=0.1,
        total_equity=100.1,
        status=status,
        maker_fill_rate=0.5,
        taker_fill_rate=0.4,
        expiration_rate=0.2,
        stop_out_rate=0.2,
        average_trade_pnl=0.02,
        average_signal_edge_bps=120.0,
        average_adverse_fill_bps=15.0,
        expected_edge_capture_bps=60.0,
        edge_capture_ratio=edge_capture_ratio,
        average_trade_expected_edge_bps=average_trade_expected_edge_bps,
        average_trade_execution_drag_bps=average_trade_execution_drag_bps,
        average_trade_realized_pnl_bps=20.0,
        average_barrier_observed_gap_bps=80.0,
        average_surface_observed_gap_bps=70.0,
        average_fusion_observed_gap_bps=75.0,
        average_barrier_surface_disagreement_bps=25.0,
        closed_trade_net_pnl=closed_trade_net_pnl,
        closed_trade_count=closed_trade_count,
        winning_trade_rate=winning_trade_rate,
        average_win_trade_pnl=0.08,
        average_loss_trade_pnl=average_loss_trade_pnl,
        average_submitted_notional=4.5,
        large_notional_share=0.25,
        dominant_exit_reason="fair_value_reached",
        stop_loss_exit_share=0.1,
        passive_cleanup_exit_share=0.1,
        exit_family_balance_score=0.8,
        small_bucket_pnl_per_notional=0.02,
        medium_bucket_pnl_per_notional=0.015,
        large_bucket_pnl_per_notional=0.01,
        execution_feedback_bias="stable",
        top_loss_trades=top_loss_trades,
        top_loss_market_breakdown=(),
        top_loss_signature_breakdown=top_loss_signature_breakdown,
    )
