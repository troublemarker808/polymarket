import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PendingOrderState, PositionState, RuntimeStatus
from pm_bot.strategies.crypto.phase2 import (
    CryptoExecutionFeedback,
    CryptoPhase2Strategy,
    build_position_intent,
    classify_crypto_signal,
)
from pm_bot.strategies.crypto.phase2.models import CryptoReentryState


FIXTURE_CASES = Path("tests/fixtures/crypto_phase2/execution_cases.json")


def test_crypto_phase2_strategy_generates_entry_signal_from_phase1_fair_value() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "market_selection_actions": {"eth-dip-1000": "tradable_market"},
                "market_selection_reasons": {"eth-dip-1000": ("tight_runtime_spread",)},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.BUY_YES
    assert signal.target_price == 0.11
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds == 30
    assert signal.rationale_tags == ("repricing_edge", "taker")
    assert signal.diagnostics["signal_type"] == "repricing_edge"
    assert signal.diagnostics["execution_route"] == "taker"
    assert signal.diagnostics["selection_action"] == "tradable_market"
    assert signal.diagnostics["selection_reasons"] == ["tight_runtime_spread"]


def test_crypto_phase2_strategy_generates_exit_signal_for_existing_position() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.185,
        best_ask_yes=0.19,
        best_bid_no=0.81,
        best_ask_no=0.82,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.185,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.target_price == 0.185
    assert signal.time_in_force == "IOC"
    assert signal.rationale_tags == ("fair_value_reached",)


def test_crypto_phase2_strategy_uses_passive_exit_for_stale_position_cleanup() -> None:
    strategy = CryptoPhase2Strategy({"execution_max_holding_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.162,
        best_ask_yes=0.17,
        best_bid_no=0.83,
        best_ask_no=0.84,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.162,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.target_price == 0.172
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 15
    assert signal.rationale_tags == ("stale_position_cleanup",)


def test_crypto_phase2_strategy_does_not_reprice_identical_pending_exit() -> None:
    strategy = CryptoPhase2Strategy({"execution_max_holding_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.162,
        best_ask_yes=0.17,
        best_bid_no=0.83,
        best_ask_no=0.84,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.162,
    )
    pending_order = PendingOrderState(
        order_id="paper-1",
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side="sell_yes",
        limit_price=0.172,
        requested_shares=45.0,
        requested_notional=7.65,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=2),
        updated_at=now - timedelta(seconds=2),
        quote_ttl_seconds=15,
        time_in_force="GTC",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position, pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_submit_second_passive_exit_while_first_pending() -> None:
    strategy = CryptoPhase2Strategy({"execution_max_holding_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )
    pending_order = PendingOrderState(
        order_id="paper-exit-1",
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side="sell_yes",
        limit_price=0.13,
        requested_shares=45.0,
        requested_notional=5.85,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=5),
        updated_at=now - timedelta(seconds=5),
        quote_ttl_seconds=5,
        time_in_force="GTC",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position, pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_respects_exit_repost_cooldown_after_expiry() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "exit_repost_cooldown_seconds": 30.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": "sell_yes",
                            "limit_price": 0.12,
                            "updated_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_submit_second_passive_exit_from_recent_event_lock() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "exit_repost_cooldown_seconds": 30.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": SignalSide.SELL_YES.value,
                            "price": 0.13,
                            "created_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_forces_ioc_after_repeated_time_stop_expiries() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "exit_repost_cooldown_seconds": 0.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "trade_side": "SELL",
                            "limit_price": 0.13,
                            "updated_at": (now - timedelta(seconds=20)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "trade_side": "SELL",
                            "limit_price": 0.13,
                            "updated_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.12
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds is None
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_counts_stale_exit_cancels_toward_ioc_escalation() -> None:
    strategy = CryptoPhase2Strategy({"time_stop_force_ioc_after_expiries": 2})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.185,
        best_ask_yes=0.19,
        best_bid_no=0.81,
        best_ask_no=0.82,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.185,
    )
    context = {
        "dashboard_state": _dashboard(position=position),
        "fair_values_by_market_id": {"eth-dip-1000": fair_value},
        "position_intents_by_market_id": {"eth-dip-1000": intent},
        "recent_events": [
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "order_id": "order-1",
                    "side": SignalSide.SELL_YES.value,
                    "reason": "stale_ttl_cancel",
                    "created_at": (now - timedelta(seconds=90)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "order_id": "order-1",
                    "side": SignalSide.SELL_YES.value,
                    "reason": "exchange_canceled",
                    "created_at": (now - timedelta(seconds=89)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "order_id": "order-2",
                    "side": SignalSide.SELL_YES.value,
                    "reason": "stale_ttl_cancel",
                    "created_at": (now - timedelta(seconds=40)).isoformat(),
                },
            },
        ],
    }

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context=context))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds is None


def test_crypto_phase2_strategy_respects_reentry_block() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    reentry_state = CryptoReentryState(
        market_id="eth-dip-1000",
        blocked_until=now + timedelta(minutes=5),
        stop_out_count=1,
        quarantine_active=False,
        reason="cooldown",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "reentry_state_by_market_id": {"eth-dip-1000": reentry_state},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_respects_entry_repost_cooldown_after_expiry() -> None:
    strategy = CryptoPhase2Strategy({"entry_repost_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": "buy_yes",
                            "limit_price": 0.1,
                            "updated_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_respects_entry_failure_cooldown_after_rejection() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_repost_cooldown_seconds": 120.0,
            "entry_failure_cooldown_seconds": 180.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.rejected",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "side": "buy_yes",
                            "reason": "execution submit failed: RuntimeError: FOK couldn't be fully filled",
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_blocks_repeat_entry_after_recent_submission_same_market() -> None:
    strategy = CryptoPhase2Strategy({"entry_failure_cooldown_seconds": 180.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "side": "buy_yes",
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_blocks_sibling_market_when_same_thesis_position_exists() -> None:
    strategy = CryptoPhase2Strategy({"single_active_market_per_thesis": True})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-dip-45000",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")
    existing_position = PositionState(
        market_id="btc-dip-40000",
        token_id="btc-dip-40000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=2),
        shares=10.0,
        average_entry_price=0.5,
        thesis_group_id="crypto:eth:dip",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=existing_position),
                "fair_values_by_market_id": {"btc-dip-45000": fair_value},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_quarantines_market_after_repeated_no_fill_attempts() -> None:
    strategy = CryptoPhase2Strategy({"max_no_fill_entry_attempts_per_market": 2})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-dip-50000",
        best_bid_yes=0.36,
        best_ask_yes=0.37,
        best_bid_no=0.63,
        best_ask_no=0.64,
    )
    fair_value = _fair_value("repricing_yes")
    context = {
        "dashboard_state": _dashboard(),
        "fair_values_by_market_id": {"btc-dip-50000": fair_value},
        "market_selection_actions": {"btc-dip-50000": "selective_market"},
        "market_selection_reasons": {"btc-dip-50000": ("wide_spread",)},
        "recent_events": [
            {
                "event_type": "order.submitted",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-1",
                    "created_at": (now - timedelta(seconds=60)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-1",
                    "reason": "stale_ttl_cancel",
                    "updated_at": (now - timedelta(seconds=30)).isoformat(),
                },
            },
            {
                "event_type": "order.submitted",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-2",
                    "created_at": (now - timedelta(seconds=20)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-2",
                    "reason": "stale_ttl_cancel",
                    "updated_at": (now - timedelta(seconds=10)).isoformat(),
                },
            },
        ],
    }

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context=context))

    assert signals == []


def test_crypto_phase2_strategy_allows_retry_after_failure_cooldown_expires() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_repost_cooldown_seconds": 120.0,
            "entry_failure_cooldown_seconds": 60.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.rejected",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "side": "buy_yes",
                            "reason": "execution submit failed: RuntimeError: exchange rejected order",
                            "created_at": (now - timedelta(seconds=90)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1


def test_crypto_phase2_strategy_respects_exit_failure_cooldown_after_rejection() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "min_confidence": 0.6,
            "min_net_edge_bps": 50.0,
            "exit_failure_cooldown_seconds": 180.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 20, tzinfo=UTC),
        market_id="701502",
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.43,
        best_ask_no=0.44,
    )
    position = PositionState(
        market_id="701502",
        token_id="701502-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        shares=11.111111,
        average_entry_price=0.4509,
        opened_at=snapshot.timestamp - timedelta(minutes=10),
    )
    fair_value = FairValueEstimate(
        market_id="701502",
        category=Category.CRYPTO,
        fair_probability=0.4294996,
        confidence=0.75,
        half_life_seconds=60,
        observed_probability=0.565,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model",),
        supporting_values={"gross_edge_bps": -1355.0, "net_edge_bps": 1240.0},
    )
    rejected_at = snapshot.timestamp.isoformat()
    context = {
        "dashboard_state": _dashboard(position=position),
        "fair_values_by_market_id": {"701502": fair_value},
        "position_intents_by_market_id": {
            "701502": build_position_intent(
                fair_value=fair_value,
                classification=classify_crypto_signal(fair_value=fair_value),
                token_id="701502-no",
                created_at=snapshot.timestamp - timedelta(minutes=10),
                entry_fill_price=0.4509,
            )
        },
        "recent_events": [
            {
                "event_type": "order.rejected",
                "payload": {
                    "market_id": "701502",
                    "side": SignalSide.SELL_NO.value,
                    "created_at": rejected_at,
                },
            }
        ],
    }
    signals = list(asyncio.run(strategy.evaluate(snapshot, context)))
    assert signals == []


def test_crypto_phase2_strategy_skips_entry_when_series_is_blocked() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "blocked_series_keys": {"eth-dip-ladder"},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_skips_entry_when_market_is_blocked() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "blocked_market_ids": {"eth-dip-1000"},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_scales_down_notional_when_feedback_is_more_passive() -> None:
    strategy = CryptoPhase2Strategy({"default_notional": 5.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.5,
                    taker_shortfall_bps=20.0,
                    repeated_expiration_rate=0.4,
                    repeated_stop_out_rate=0.7,
                    recommended_route_bias="more_passive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size == 3.75
    assert signal.diagnostics["execution_feedback_bias"] == "more_passive"
    assert signal.diagnostics["execution_feedback_notional"] == 3.75


def test_crypto_phase2_strategy_becomes_more_aggressive_when_feedback_says_so() -> None:
    strategy = CryptoPhase2Strategy({"default_notional": 5.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.0,
                    taker_shortfall_bps=0.0,
                    repeated_expiration_rate=1.0,
                    repeated_stop_out_rate=0.0,
                    recommended_route_bias="more_aggressive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.quote_ttl_seconds == 30
    assert signal.target_size == 5.75
    assert signal.diagnostics["execution_feedback_bias"] == "more_aggressive"


def test_crypto_phase2_strategy_applies_family_preset_registry() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "default_notional": 5.0,
            "taker_urgency_threshold": 0.72,
            "preset_registry": {
                "btc_reach_fast": {
                    "match": {"underlying": "BTC", "event_family": "reach"},
                    "overrides": {
                        "default_notional": 8.0,
                        "taker_urgency_threshold": 0.9,
                    },
                }
            },
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-100k",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-100k": fair_value},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size == 8.0
    assert signal.diagnostics["phase2_preset"] == "btc_reach_fast"
    assert signal.time_in_force == "GTC"


def test_crypto_phase2_strategy_locks_same_bullish_thesis_across_dip_and_reach_markets() -> None:
    strategy = CryptoPhase2Strategy({"thesis_entry_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    reach_snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=0.09,
        best_ask_yes=0.10,
        best_bid_no=0.90,
        best_ask_no=0.91,
        tick_size=0.01,
        liquidity_score=0.8,
        metadata={
            "question": "Will Bitcoin hit $150K by December 31, 2026?",
            "event_slug": "btc-reach-2026",
            "no_token_id": "reach-no",
        },
    )
    fair_value = FairValueEstimate(
        market_id="reach-150k",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.8,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 140.0, "gross_edge_bps": 400.0},
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=reach_snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"reach-150k": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "dip-50k",
                            "side": SignalSide.BUY_NO.value,
                            "thesis_group_id": "crypto:btc:bullish",
                            "updated_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


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


def _snapshot(
    *,
    timestamp: datetime,
    market_id: str,
    best_bid_yes: float,
    best_ask_yes: float,
    best_bid_no: float,
    best_ask_no: float,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=market_id,
        category=Category.CRYPTO,
        timestamp=timestamp,
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=best_bid_no,
        best_ask_no=best_ask_no,
        tick_size=0.01,
        liquidity_score=0.5,
        metadata={"event_slug": "eth-dip-ladder", "no_token_id": f"{market_id}-no"},
    )


def _dashboard(
    position: PositionState | None = None,
    pending_orders: tuple[PendingOrderState, ...] = (),
) -> DashboardState:
    return DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=() if position is None else (position,),
        pending_orders=pending_orders,
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )
