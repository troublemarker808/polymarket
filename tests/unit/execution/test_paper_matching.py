import asyncio
from datetime import UTC, datetime, timedelta

from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderBookLevel, OrderIntent, SignalSide
from pm_bot.execution.paper_adapter import PaperExecutionAdapter


def _snapshot(
    *,
    timestamp: datetime,
    best_bid_yes: float = 0.48,
    best_ask_yes: float = 0.52,
    best_bid_no: float = 0.48,
    best_ask_no: float = 0.52,
    yes_bid_levels: tuple[OrderBookLevel, ...] = (),
    yes_ask_levels: tuple[OrderBookLevel, ...] = (),
    no_bid_levels: tuple[OrderBookLevel, ...] | None = None,
    no_ask_levels: tuple[OrderBookLevel, ...] | None = None,
    last_trade_price: float | None = None,
    last_trade_side: str | None = None,
    last_trade_size: float | None = None,
    last_trade_event_at: datetime | None = None,
) -> MarketSnapshot:
    metadata = {"no_token_id": "no-token"}
    if last_trade_event_at is not None:
        metadata["last_trade_event_at"] = last_trade_event_at.isoformat()
    resolved_no_bid_levels = (
        no_bid_levels
        if no_bid_levels is not None
        else tuple(OrderBookLevel(price=round(1 - level.price, 6), size=level.size) for level in yes_ask_levels)
    )
    resolved_no_ask_levels = (
        no_ask_levels
        if no_ask_levels is not None
        else tuple(OrderBookLevel(price=round(1 - level.price, 6), size=level.size) for level in yes_bid_levels)
    )
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
        best_bid_yes_size=yes_bid_levels[0].size if yes_bid_levels else None,
        best_ask_yes_size=yes_ask_levels[0].size if yes_ask_levels else None,
        yes_bid_levels=yes_bid_levels,
        yes_ask_levels=yes_ask_levels,
        best_bid_no_size=resolved_no_bid_levels[0].size if resolved_no_bid_levels else None,
        best_ask_no_size=resolved_no_ask_levels[0].size if resolved_no_ask_levels else None,
        no_bid_levels=resolved_no_bid_levels,
        no_ask_levels=resolved_no_ask_levels,
        last_traded_price=last_trade_price,
        last_trade_side=last_trade_side,
        last_trade_size=last_trade_size,
        metadata=metadata,
    )


def test_paper_matching_consumes_queue_before_partial_fill() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30)
    submitted_at = datetime(2026, 3, 25, 0, 0, tzinfo=UTC)
    initial = _snapshot(
        timestamp=submitted_at,
        best_bid_yes=0.49,
        best_ask_yes=0.52,
        yes_bid_levels=(
            OrderBookLevel(price=0.49, size=3.0),
            OrderBookLevel(price=0.48, size=5.0),
        ),
    )
    adapter.reconcile_snapshot(initial)

    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.48,
        size=8.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=3.84,
    )
    asyncio.run(adapter.submit(intent))

    first_trade = _snapshot(
        timestamp=submitted_at + timedelta(seconds=1),
        best_bid_yes=0.49,
        best_ask_yes=0.52,
        yes_bid_levels=initial.yes_bid_levels,
        last_trade_price=0.48,
        last_trade_side="SELL",
        last_trade_size=6.0,
        last_trade_event_at=submitted_at + timedelta(seconds=1),
    )
    first_update = adapter.reconcile_snapshot(first_trade)
    assert len(first_update.partial_fill_orders) == 0
    assert adapter.pending_order_states()[0].matched_shares == 0.0

    second_trade = _snapshot(
        timestamp=submitted_at + timedelta(seconds=2),
        best_bid_yes=0.49,
        best_ask_yes=0.52,
        yes_bid_levels=initial.yes_bid_levels,
        last_trade_price=0.48,
        last_trade_side="SELL",
        last_trade_size=6.0,
        last_trade_event_at=submitted_at + timedelta(seconds=2),
    )
    second_update = adapter.reconcile_snapshot(second_trade)
    assert len(second_update.partial_fill_orders) == 1
    assert round(adapter.pending_order_states()[0].matched_shares, 6) == 4.0

    third_trade = _snapshot(
        timestamp=submitted_at + timedelta(seconds=3),
        best_bid_yes=0.49,
        best_ask_yes=0.52,
        yes_bid_levels=initial.yes_bid_levels,
        last_trade_price=0.48,
        last_trade_side="SELL",
        last_trade_size=10.0,
        last_trade_event_at=submitted_at + timedelta(seconds=3),
    )
    third_update = adapter.reconcile_snapshot(third_trade)
    assert len(third_update.filled_orders) == 1
    assert len(adapter.pending_order_states()) == 0
    assert len(adapter.position_states()) == 1
    assert adapter.position_states()[0].shares == 8.0


def test_paper_matching_sweeps_multiple_ask_levels_for_marketable_buy() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30, taker_slippage_bps=0.0)
    submitted_at = datetime(2026, 3, 25, 0, 1, tzinfo=UTC)
    initial = _snapshot(
        timestamp=submitted_at,
        best_bid_yes=0.49,
        best_ask_yes=0.50,
        yes_ask_levels=(
            OrderBookLevel(price=0.50, size=5.0),
            OrderBookLevel(price=0.51, size=7.0),
        ),
    )
    adapter.reconcile_snapshot(initial)

    intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.51,
        size=12.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=6.12,
    )
    asyncio.run(adapter.submit(intent))

    update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(milliseconds=1),
            best_bid_yes=0.49,
            best_ask_yes=0.50,
            yes_ask_levels=initial.yes_ask_levels,
        )
    )

    assert len(update.filled_orders) == 1
    position = adapter.position_states()[0]
    assert position.shares == 12.0
    assert round(position.average_entry_price, 6) == round(((5 * 0.50) + (7 * 0.51)) / 12, 6)


def test_paper_matching_falls_back_to_top_of_book_when_depth_is_stale() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30, taker_slippage_bps=0.0)
    submitted_at = datetime(2026, 3, 25, 0, 2, tzinfo=UTC)
    initial = _snapshot(
        timestamp=submitted_at,
        best_bid_yes=0.46,
        best_ask_yes=0.48,
        yes_ask_levels=(OrderBookLevel(price=0.48, size=40.0),),
    )
    adapter.reconcile_snapshot(initial)

    intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.47,
        size=10.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=4.7,
    )
    asyncio.run(adapter.submit(intent))

    update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(seconds=1),
            best_bid_yes=0.46,
            best_ask_yes=0.47,
            yes_ask_levels=initial.yes_ask_levels,
        )
    )

    assert len(update.filled_orders) == 1
    position = adapter.position_states()[0]
    assert position.shares == 10.0
    assert round(position.average_entry_price, 6) == 0.47


def test_paper_matching_maps_yes_trade_into_no_space_for_passive_buy() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30)
    submitted_at = datetime(2026, 3, 25, 0, 3, tzinfo=UTC)
    adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at,
            best_bid_yes=0.64,
            best_ask_yes=0.65,
            best_bid_no=0.35,
            best_ask_no=0.36,
        )
    )

    intent = OrderIntent(
        strategy_id="crypto.execution_sample",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="no-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_NO,
        price=0.3609,
        size=10.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=3.609,
    )
    asyncio.run(adapter.submit(intent))

    update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(seconds=1),
            best_bid_yes=0.64,
            best_ask_yes=0.65,
            best_bid_no=0.35,
            best_ask_no=0.36,
            last_trade_price=0.64,
            last_trade_side="BUY",
            last_trade_size=10.0,
        )
    )

    assert len(update.filled_orders) == 1
    position = adapter.position_states()[0]
    assert position.token_id == "no-token"
    assert round(position.average_entry_price, 6) == 0.36


def test_paper_matching_does_not_fill_sell_no_from_yes_side_buy_trade() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30, taker_slippage_bps=0.0)
    submitted_at = datetime(2026, 3, 25, 0, 4, tzinfo=UTC)
    initial = _snapshot(
        timestamp=submitted_at,
        best_bid_yes=0.64,
        best_ask_yes=0.66,
        best_bid_no=0.34,
        best_ask_no=0.36,
        yes_bid_levels=(OrderBookLevel(price=0.64, size=20.0),),
    )
    adapter.reconcile_snapshot(initial)

    open_intent = OrderIntent(
        strategy_id="crypto.execution_sample",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="no-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_NO,
        price=0.3609,
        size=10.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=3.609,
    )
    asyncio.run(adapter.submit(open_intent))
    open_update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(milliseconds=1),
            best_bid_yes=0.64,
            best_ask_yes=0.66,
            best_bid_no=0.34,
            best_ask_no=0.36,
            yes_bid_levels=initial.yes_bid_levels,
        )
    )
    assert len(open_update.filled_orders) == 1

    close_intent = OrderIntent(
        strategy_id="crypto.execution_sample",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="no-token",
        action=OrderAction.PLACE,
        side=SignalSide.SELL_NO,
        price=0.349125,
        size=10.0,
        time_in_force="GTC",
        created_at=submitted_at + timedelta(seconds=1),
        notional=3.49125,
    )
    asyncio.run(adapter.submit(close_intent))

    close_update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(seconds=2),
            best_bid_yes=0.64,
            best_ask_yes=0.66,
            best_bid_no=0.34,
            best_ask_no=0.36,
            last_trade_price=0.64,
            last_trade_side="BUY",
            last_trade_size=10.0,
        )
    )

    assert len(close_update.filled_orders) == 0
    assert len(close_update.partial_fill_orders) == 0
    assert len(adapter.position_states()) == 1
    assert adapter.pending_order_states()[0].order_id == "paper-2"
    assert adapter.pending_order_states()[0].matched_shares == 0.0


def test_paper_matching_does_not_replay_stale_last_trade_on_new_snapshot_timestamp() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30)
    submitted_at = datetime(2026, 3, 25, 0, 5, tzinfo=UTC)
    adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at,
            best_bid_yes=0.48,
            best_ask_yes=0.52,
        )
    )

    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.48,
        size=4.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=1.92,
    )
    asyncio.run(adapter.submit(intent))

    first_update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(seconds=1),
            best_bid_yes=0.48,
            best_ask_yes=0.52,
            last_trade_price=0.48,
            last_trade_side="SELL",
            last_trade_size=2.0,
        )
    )
    assert len(first_update.partial_fill_orders) == 1
    assert round(adapter.pending_order_states()[0].matched_shares, 6) == 2.0

    second_update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(seconds=2),
            best_bid_yes=0.48,
            best_ask_yes=0.52,
            last_trade_price=0.48,
            last_trade_side="SELL",
            last_trade_size=2.0,
        )
    )
    assert len(second_update.partial_fill_orders) == 0
    assert len(second_update.filled_orders) == 0
    assert round(adapter.pending_order_states()[0].matched_shares, 6) == 2.0


def test_paper_matching_sweeps_buy_no_using_complement_yes_book_when_no_book_is_missing() -> None:
    adapter = PaperExecutionAdapter(ttl_seconds=30, taker_slippage_bps=0.0)
    submitted_at = datetime(2026, 3, 25, 0, 6, tzinfo=UTC)
    initial = _snapshot(
        timestamp=submitted_at,
        best_bid_yes=0.64,
        best_ask_yes=0.66,
        best_bid_no=None,
        best_ask_no=None,
        yes_bid_levels=(OrderBookLevel(price=0.64, size=12.0),),
        yes_ask_levels=(OrderBookLevel(price=0.66, size=10.0),),
        no_bid_levels=(),
        no_ask_levels=(),
    )
    adapter.reconcile_snapshot(initial)

    intent = OrderIntent(
        strategy_id="crypto.execution_sample",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="no-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_NO,
        price=0.36,
        size=8.0,
        time_in_force="GTC",
        created_at=submitted_at,
        notional=2.88,
    )
    asyncio.run(adapter.submit(intent))

    update = adapter.reconcile_snapshot(
        _snapshot(
            timestamp=submitted_at + timedelta(milliseconds=1),
            best_bid_yes=0.64,
            best_ask_yes=0.66,
            best_bid_no=None,
            best_ask_no=None,
            yes_bid_levels=initial.yes_bid_levels,
            yes_ask_levels=initial.yes_ask_levels,
            no_bid_levels=(),
            no_ask_levels=(),
        )
    )

    assert len(update.filled_orders) == 1
    position = adapter.position_states()[0]
    assert position.token_id == "no-token"
    assert position.shares == 8.0
    assert round(position.average_entry_price, 6) == 0.36
