import asyncio
from datetime import UTC, datetime, timedelta

from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.paper_adapter import PaperExecutionAdapter


def _build_snapshot(
    *,
    timestamp: datetime,
    best_bid_yes: float,
    best_ask_yes: float,
    best_bid_no: float,
    best_ask_no: float,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=timestamp,
        resolution_time=None,
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=best_bid_no,
        best_ask_no=best_ask_no,
        metadata={"no_token_id": "no-token"},
    )


def test_paper_adapter_fills_marketable_buy_order() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    submitted_at = datetime(2026, 3, 24, 2, 36, 30, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.41,
        size=10.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=4.1,
    )

    asyncio.run(adapter.submit(intent))
    update = adapter.reconcile_snapshot(
        _build_snapshot(
            timestamp=submitted_at,
            best_bid_yes=0.39,
            best_ask_yes=0.40,
            best_bid_no=0.60,
            best_ask_no=0.61,
        ),
    )

    assert len(update.filled_orders) == 1
    assert len(adapter.pending_order_states()) == 0
    positions = adapter.position_states()
    assert len(positions) == 1
    assert positions[0].shares == 10.0
    assert positions[0].average_entry_price == 0.40
    assert positions[0].mark_price == 0.39
    assert round(positions[0].unrealized_pnl, 6) == -0.1


def test_paper_adapter_expires_stale_orders() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    now = datetime(2026, 3, 24, 2, 37, 0, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.30,
        size=10.0,
        time_in_force="GTC",
        created_at=now - timedelta(seconds=30),
        notional=3.0,
    )

    asyncio.run(adapter.submit(intent))
    update = adapter.reconcile_snapshot(
        _build_snapshot(
            timestamp=now,
            best_bid_yes=0.45,
            best_ask_yes=0.46,
            best_bid_no=0.54,
            best_ask_no=0.55,
        ),
    )

    assert len(update.expired_orders) == 1
    assert len(adapter.pending_order_states()) == 0


def test_paper_adapter_cancels_unfilled_ioc_order_on_first_eligible_snapshot() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    created_at = datetime(2026, 3, 24, 2, 37, 0, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.phase2",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.39,
        size=10.0,
        time_in_force="IOC",
        created_at=created_at,
        notional=3.9,
        quote_ttl_seconds=30,
    )

    asyncio.run(adapter.submit(intent))
    update = adapter.reconcile_snapshot(
        _build_snapshot(
            timestamp=created_at + timedelta(seconds=1),
            best_bid_yes=0.38,
            best_ask_yes=0.40,
            best_bid_no=0.60,
            best_ask_no=0.62,
        ),
    )

    assert len(update.canceled_orders) == 1
    assert len(update.filled_orders) == 0
    assert len(adapter.pending_order_states()) == 0


def test_paper_adapter_cancel_stale_orders_uses_expiry_path() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    created_at = datetime(2026, 3, 24, 2, 36, 0, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.30,
        size=10.0,
        time_in_force="GTC",
        created_at=created_at,
        notional=3.0,
    )

    asyncio.run(adapter.submit(intent))
    expired = asyncio.run(adapter.cancel_stale_orders(now=created_at + timedelta(seconds=16)))

    assert len(expired) == 1
    assert expired[0].status.value == "canceled"
    assert len(adapter.pending_order_states()) == 0


def test_paper_adapter_does_not_repeat_stale_cancel_for_same_order() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    created_at = datetime(2026, 3, 24, 2, 36, 0, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.30,
        size=10.0,
        time_in_force="GTC",
        created_at=created_at,
        notional=3.0,
    )

    asyncio.run(adapter.submit(intent))
    first = asyncio.run(adapter.cancel_stale_orders(now=created_at + timedelta(seconds=16)))
    second = asyncio.run(adapter.cancel_stale_orders(now=created_at + timedelta(seconds=17)))

    assert len(first) == 1
    assert second == ()


def test_paper_adapter_cancel_order_removes_pending_order_immediately() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    created_at = datetime(2026, 3, 24, 2, 36, 0, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.30,
        size=10.0,
        time_in_force="GTC",
        created_at=created_at,
        notional=3.0,
        signal_edge_bps=100.0,
    )

    order_id = asyncio.run(adapter.submit(intent))
    canceled = asyncio.run(adapter.cancel_order(order_id, now=created_at + timedelta(seconds=1)))

    assert canceled is not None
    assert canceled.order_id == order_id
    assert canceled.status.value == "canceled"
    assert adapter.pending_order_states() == ()


def test_paper_adapter_cancel_order_keeps_updated_at_monotonic() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    created_at = datetime(2026, 3, 24, 2, 36, 0, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.30,
        size=10.0,
        time_in_force="GTC",
        created_at=created_at,
        notional=3.0,
        signal_edge_bps=100.0,
    )

    order_id = asyncio.run(adapter.submit(intent))
    canceled = asyncio.run(adapter.cancel_order(order_id, now=created_at - timedelta(seconds=5)))

    assert canceled is not None
    assert canceled.updated_at == created_at


def test_paper_adapter_closes_position_on_marketable_sell() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=15)
    entry_time = datetime(2026, 3, 24, 2, 36, 30, tzinfo=UTC)
    entry_intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.41,
        size=10.0,
        time_in_force="GTC",
        created_at=entry_time,
        notional=4.1,
    )
    asyncio.run(adapter.submit(entry_intent))
    adapter.reconcile_snapshot(
        _build_snapshot(
            timestamp=entry_time,
            best_bid_yes=0.39,
            best_ask_yes=0.40,
            best_bid_no=0.60,
            best_ask_no=0.61,
        ),
    )

    exit_time = entry_time + timedelta(minutes=1)
    exit_intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.SELL_YES,
        price=0.60,
        size=10.0,
        time_in_force="GTC",
        created_at=exit_time,
        notional=6.0,
    )
    asyncio.run(adapter.submit(exit_intent))
    adapter.reconcile_snapshot(
        _build_snapshot(
            timestamp=exit_time,
            best_bid_yes=0.60,
            best_ask_yes=0.61,
            best_bid_no=0.39,
            best_ask_no=0.40,
        ),
    )

    closed_trades = adapter.drain_closed_trades()
    assert len(adapter.position_states()) == 0
    assert len(closed_trades) == 1
    assert round(closed_trades[0].net_pnl, 6) == 2.0
