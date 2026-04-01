from __future__ import annotations

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
    assert scorecard.promotion_decision == "proceed"
    assert scorecard.promotion_stage_label == "shadow validation"
    assert scorecard.promotion_blocking_reasons == ()


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
    assert scorecard.promotion_decision == "pause"
    assert "risk_status_halted" in scorecard.promotion_blocking_reasons


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
        winning_trade_rate=0.6,
        average_win_trade_pnl=0.08,
        average_loss_trade_pnl=-0.05,
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
    )
