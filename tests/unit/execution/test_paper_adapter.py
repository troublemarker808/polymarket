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
