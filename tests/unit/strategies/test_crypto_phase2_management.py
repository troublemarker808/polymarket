from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, SignalSide
from pm_bot.runtime.state import ClosedTrade, PendingOrderState, PositionState
from pm_bot.strategies.crypto.phase2 import (
    build_position_intent,
    classify_crypto_signal,
    evaluate_exit,
    is_reentry_blocked,
    summarize_execution_feedback,
    summarize_execution_feedback_from_events,
    update_reentry_state,
)


FIXTURE_CASES = Path("tests/fixtures/crypto_phase2/execution_cases.json")


def test_build_position_intent_captures_entry_thesis() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)

    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
    )

    assert intent.market_id == "eth-dip-1000"
    assert intent.signal_type == "repricing_edge"
    assert intent.expected_exit_mode == "fair_value_reversion"
    assert intent.expected_holding_seconds == 3600
    assert intent.effective_horizon_days == 0.0


def test_evaluate_exit_triggers_fair_value_exit_for_buy_yes_position() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.18,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.185,
        best_bid_no=0.815,
        as_of=created_at + timedelta(minutes=20),
    )

    assert exit_decision.should_exit
    assert exit_decision.exit_side == SignalSide.SELL_YES
    assert exit_decision.reason == "fair_value_reached"


def test_evaluate_exit_uses_aging_exit_threshold_after_half_life() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.18,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.177,
        best_bid_no=0.823,
        as_of=created_at + timedelta(minutes=31),
        exit_edge_bps=75.0,
        aging_exit_edge_bps=150.0,
        aging_start_fraction=0.5,
        stale_start_fraction=1.0,
    )

    assert exit_decision.should_exit
    assert exit_decision.reason == "aging_exit"


def test_evaluate_exit_uses_stale_cleanup_after_expected_holding_window() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.165,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.162,
        best_bid_no=0.838,
        as_of=created_at + timedelta(hours=1, minutes=1),
        exit_edge_bps=75.0,
        aging_exit_edge_bps=150.0,
        stale_exit_edge_bps=300.0,
        aging_start_fraction=0.5,
        stale_start_fraction=1.0,
    )

    assert exit_decision.should_exit
    assert exit_decision.reason == "stale_position_cleanup"


def test_evaluate_exit_caps_expected_holding_seconds_for_execution_time_scale() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.162,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.162,
        best_bid_no=0.838,
        as_of=created_at + timedelta(minutes=6),
        execution_max_holding_seconds=300.0,
        exit_edge_bps=75.0,
        aging_exit_edge_bps=150.0,
        stale_exit_edge_bps=300.0,
        aging_start_fraction=0.5,
        stale_start_fraction=1.0,
    )

    assert exit_decision.should_exit
    assert exit_decision.reason == "stale_position_cleanup"


def test_build_position_intent_raises_holding_window_for_long_horizon_market() -> None:
    fair_value = FairValueEstimate(
        market_id="btc-dip-50000",
        category=Category.CRYPTO,
        fair_probability=0.34,
        confidence=0.75,
        half_life_seconds=3600,
        observed_probability=0.31,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={
            "net_edge_bps": 300.0,
            "gross_edge_bps": 420.0,
            "effective_horizon_days": 120.0,
        },
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)

    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="btc-dip-50000-no",
        created_at=created_at,
    )

    assert intent.expected_exit_mode == "fair_value_reversion"
    assert intent.effective_horizon_days == 120.0
    assert intent.expected_holding_seconds == 6 * 3600


def test_evaluate_exit_does_not_apply_minute_cap_to_long_horizon_market() -> None:
    fair_value = FairValueEstimate(
        market_id="btc-dip-50000",
        category=Category.CRYPTO,
        fair_probability=0.34,
        confidence=0.75,
        half_life_seconds=3600,
        observed_probability=0.31,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={
            "net_edge_bps": 300.0,
            "gross_edge_bps": 420.0,
            "effective_horizon_days": 120.0,
        },
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="btc-dip-50000-yes",
        created_at=created_at,
    )
    position = PositionState(
        market_id="btc-dip-50000",
        token_id="btc-dip-50000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=14.4,
        average_entry_price=0.31,
        mark_price=0.331,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.331,
        best_bid_no=0.669,
        as_of=created_at + timedelta(minutes=2),
        execution_max_holding_seconds=60.0,
        max_holding_multiplier=1.0,
        aging_start_fraction=0.5,
        stale_start_fraction=1.0,
    )

    assert not exit_decision.should_exit
    assert exit_decision.reason == "hold"


def test_evaluate_exit_does_not_stop_out_on_single_tick_drop_for_coarse_market() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.10,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.10,
        best_bid_no=0.90,
        as_of=created_at + timedelta(minutes=2),
        stop_loss_bps=250.0,
        stop_loss_min_ticks=2,
        tick_size=0.01,
    )

    assert not exit_decision.should_exit
    assert exit_decision.reason == "hold"


def test_evaluate_exit_triggers_adverse_fill_reversal_for_taker_entry() -> None:
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.11,
        confidence=0.7,
        half_life_seconds=60,
        observed_probability=0.105,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model",),
        supporting_values={"net_edge_bps": 100.0, "gross_edge_bps": 120.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
        entry_fill_price=0.110055,
        entry_mid_price=0.105,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.110055,
        mark_price=0.10,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.10,
        best_bid_no=0.90,
        as_of=created_at + timedelta(seconds=5),
        stop_loss_max_remaining_edge_bps=150.0,
        adverse_fill_exit_bps=75.0,
        adverse_fill_max_remaining_edge_bps=150.0,
    )

    assert exit_decision.should_exit
    assert exit_decision.reason == "adverse_fill_reversal"


def test_evaluate_exit_ignores_adverse_fill_reversal_when_remaining_edge_is_large() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
        entry_fill_price=0.110055,
        entry_mid_price=0.105,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.110055,
        mark_price=0.10,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.10,
        best_bid_no=0.90,
        as_of=created_at + timedelta(seconds=5),
        stop_loss_max_remaining_edge_bps=150.0,
        adverse_fill_exit_bps=75.0,
        adverse_fill_max_remaining_edge_bps=150.0,
    )

    assert not exit_decision.should_exit
    assert exit_decision.reason == "hold"


def test_evaluate_exit_ignores_time_stop_when_remaining_edge_is_still_large() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.12,
        best_bid_no=0.88,
        as_of=created_at + timedelta(minutes=2),
        execution_max_holding_seconds=60.0,
        max_holding_multiplier=1.0,
        time_stop_max_remaining_edge_bps=300.0,
    )

    assert not exit_decision.should_exit
    assert exit_decision.reason == "hold"


def test_evaluate_exit_holds_for_fresh_fill_even_when_adverse_reversal_would_trigger() -> None:
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    created_at = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=created_at,
        entry_fill_price=0.110055,
        entry_mid_price=0.105,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        notional=5.0,
        opened_at=created_at,
        shares=45.0,
        average_entry_price=0.110055,
        mark_price=0.10,
    )

    exit_decision = evaluate_exit(
        fair_value=fair_value,
        position=position,
        intent=intent,
        best_bid_yes=0.10,
        best_bid_no=0.90,
        as_of=created_at,
        adverse_fill_exit_bps=75.0,
        min_holding_seconds_before_exit=1.0,
    )

    assert not exit_decision.should_exit
    assert exit_decision.reason == "fresh_fill_hold"


def test_update_reentry_state_blocks_after_stop_loss() -> None:
    market_id = "eth-dip-1000"
    now = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    state = update_reentry_state(
        market_id=market_id,
        previous=None,
        exit_decision=_stop_loss_exit(market_id),
        as_of=now,
        cooldown_seconds=300,
        quarantine_after_stopouts=3,
    )

    assert state.stop_out_count == 1
    assert not state.quarantine_active
    assert is_reentry_blocked(state=state, as_of=now + timedelta(seconds=120))
    assert not is_reentry_blocked(state=state, as_of=now + timedelta(seconds=301))


def test_summarize_execution_feedback_recommends_more_passive_after_loss_cluster() -> None:
    pending_orders = (
        _pending_order("o1", ttl=300, matched_shares=0.0, status="expired"),
        _pending_order("o2", ttl=300, matched_shares=1.0, status="filled"),
        _pending_order("o3", ttl=30, matched_shares=2.0, status="filled", signal_edge_bps=400.0),
    )
    closed_trades = (
        _closed_trade(-0.5),
        _closed_trade(-0.3),
        _closed_trade(0.2),
    )

    feedback = summarize_execution_feedback(
        pending_orders=pending_orders,
        closed_trades=closed_trades,
    )

    assert feedback.maker_fill_rate == 0.5
    assert feedback.repeated_expiration_rate == 0.5
    assert feedback.repeated_stop_out_rate == 0.6667
    assert feedback.recommended_route_bias == "more_passive"


def test_summarize_execution_feedback_from_events_recommends_more_aggressive_after_expiry_cluster() -> None:
    recent_events = (
        {
            "event_type": "order.submitted",
            "payload": {
                "order_id": "o1",
                "market_id": "eth-dip-1000",
                "token_id": "eth-dip-1000-yes",
                "strategy_id": "crypto.phase2",
                "side": "buy_yes",
                "price": 0.11,
                "size": 10.0,
                "notional": 1.1,
                "quote_ttl_seconds": 60,
                "created_at": "2026-03-28T00:00:00+00:00",
                "updated_at": "2026-03-28T00:00:00+00:00",
            },
        },
        {
            "event_type": "order.expired",
            "payload": {
                "order_id": "o1",
                "market_id": "eth-dip-1000",
                "token_id": "eth-dip-1000-yes",
                "strategy_id": "crypto.phase2",
                "side": "buy_yes",
                "limit_price": 0.11,
                "requested_shares": 10.0,
                "requested_notional": 1.1,
                "quote_ttl_seconds": 60,
                "updated_at": "2026-03-28T00:01:00+00:00",
                "created_at": "2026-03-28T00:00:00+00:00",
                "status": "expired",
            },
        },
    )

    feedback = summarize_execution_feedback_from_events(
        recent_events=recent_events,
        pending_orders=(
            _pending_order("o1", ttl=60, matched_shares=0.0, status="expired"),
            _pending_order("o2", ttl=60, matched_shares=0.0, status="expired"),
            _pending_order("o3", ttl=60, matched_shares=0.0, status="expired"),
        ),
    )

    assert feedback.maker_fill_rate == 0.0
    assert feedback.repeated_expiration_rate == 1.0
    assert feedback.recommended_route_bias == "more_aggressive"


def test_summarize_execution_feedback_from_events_ignores_recovered_live_closed_trades() -> None:
    recent_events = (
        {
            "event_type": "trade.closed",
            "payload": {
                "market_id": "eth-dip-1000",
                "token_id": "eth-dip-1000-yes",
                "strategy_id": "recovered.live",
                "realized_pnl": -0.5,
                "fees_paid": 0.05,
                "closed_at": "2026-03-28T00:01:00+00:00",
            },
        },
    )

    feedback = summarize_execution_feedback_from_events(
        recent_events=recent_events,
        pending_orders=(),
    )

    assert feedback.repeated_stop_out_rate == 0.0
    assert feedback.recommended_route_bias == "stable"


def _fair_value(case_key: str) -> FairValueEstimate:
    payload = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))[case_key]
    return FairValueEstimate(
        market_id=str(payload["market_id"]),
        category=Category.CRYPTO,
        fair_probability=float(payload["fair_probability"]),
        confidence=float(payload["confidence"]),
        half_life_seconds=int(payload["half_life_seconds"]),
        observed_probability=float(payload["observed_probability"]),
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={
            "net_edge_bps": float(payload["net_edge_bps"]),
            "gross_edge_bps": float(payload["gross_edge_bps"]),
        },
    )


def _stop_loss_exit(market_id: str):
    from pm_bot.strategies.crypto.phase2.models import CryptoExitDecision

    return CryptoExitDecision(
        market_id=market_id,
        should_exit=True,
        exit_side=SignalSide.SELL_YES,
        reason="stop_loss",
        target_price=0.09,
        remaining_edge_bps=-200.0,
        rationale_tags=("stop_loss",),
    )


def _pending_order(
    order_id: str,
    *,
    ttl: int,
    matched_shares: float,
    status: str,
    signal_edge_bps: float | None = None,
) -> PendingOrderState:
    now = datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
    return PendingOrderState(
        order_id=order_id,
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        side="buy_yes",
        limit_price=0.11,
        requested_shares=10.0,
        requested_notional=1.1,
        matched_shares=matched_shares,
        matched_notional=matched_shares * 0.11,
        fees_paid=0.0,
        status=status,
        created_at=now,
        updated_at=now,
        intent_id=None,
        quote_ttl_seconds=ttl,
        signal_edge_bps=signal_edge_bps,
    )


def _closed_trade(realized_pnl: float) -> ClosedTrade:
    return ClosedTrade(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2.execution",
        realized_pnl=realized_pnl,
        fees_paid=0.0,
        closed_at=datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc),
        intent_id=None,
    )
