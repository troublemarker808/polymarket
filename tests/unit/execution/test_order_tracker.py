from datetime import datetime, timedelta, timezone

from pm_bot.adapters.polymarket.user_ws_client import UserOrderEvent, UserTradeEvent
from pm_bot.core.types import Category, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.order_tracker import OrderLifecycleStatus, OrderLifecycleTracker


def _intent() -> OrderIntent:
    return OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.4,
        size=12.5,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc) - timedelta(seconds=20),
        notional=5.0,
    )


def test_order_tracker_registers_and_marks_stale() -> None:
    tracker = OrderLifecycleTracker()
    tracked = tracker.register_submission("order-1", _intent())

    assert tracked.status == OrderLifecycleStatus.PENDING
    assert tracked.trade_side == "BUY"
    assert tracker.stale_order_ids(
        now=datetime.now(tz=timezone.utc),
        ttl_seconds=15,
    ) == ("order-1",)


def test_order_tracker_applies_order_event() -> None:
    tracker = OrderLifecycleTracker()
    tracker.register_submission("order-1", _intent())

    tracked = tracker.apply_order_event(
        UserOrderEvent(
            id="order-1",
            owner="owner-1",
            market="m1",
            asset_id="yes-token",
            side="BUY",
            order_owner="owner-1",
            original_size=12.5,
            size_matched=3.0,
            price=0.4,
            outcome="YES",
            order_type="GTC",
            type="UPDATE",
            status="LIVE",
            created_at=datetime.now(tz=timezone.utc),
            expiration=None,
            timestamp=datetime.now(tz=timezone.utc),
            associate_trades=("trade-1",),
            maker_address="0x1234",
        )
    )

    assert tracked is not None
    assert tracked.status == OrderLifecycleStatus.PARTIALLY_FILLED
    assert tracked.matched_shares == 3.0


def test_order_tracker_applies_trade_event_for_taker() -> None:
    tracker = OrderLifecycleTracker()
    tracker.register_submission("order-1", _intent())

    updates = tracker.apply_trade_event(
        UserTradeEvent(
            id="trade-1",
            type="TRADE",
            taker_order_id="order-1",
            market="m1",
            asset_id="yes-token",
            side="BUY",
            size=12.5,
            price=0.4,
            fee_rate_bps=25.0,
            status="MATCHED",
            matchtime=datetime.now(tz=timezone.utc),
            last_update=datetime.now(tz=timezone.utc),
            outcome="YES",
            owner="owner-1",
            trade_owner="owner-1",
            maker_address="0x1234",
            transaction_hash="",
            bucket_index=0,
            maker_orders=(),
            trader_side="TAKER",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )

    assert len(updates) == 1
    assert updates[0].status == OrderLifecycleStatus.FILLED
    assert updates[0].matched_notional == 5.0
    assert updates[0].fees_paid == 0.0125


def test_order_tracker_accumulates_multiple_trade_events() -> None:
    tracker = OrderLifecycleTracker()
    tracker.register_submission("order-1", _intent())

    tracker.apply_trade_event(
        UserTradeEvent(
            id="trade-1",
            type="TRADE",
            taker_order_id="order-1",
            market="m1",
            asset_id="yes-token",
            side="BUY",
            size=4.0,
            price=0.4,
            fee_rate_bps=0.0,
            status="MATCHED",
            matchtime=datetime.now(tz=timezone.utc),
            last_update=datetime.now(tz=timezone.utc),
            outcome="YES",
            owner="owner-1",
            trade_owner="owner-1",
            maker_address="0x1234",
            transaction_hash="",
            bucket_index=0,
            maker_orders=(),
            trader_side="TAKER",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    updates = tracker.apply_trade_event(
        UserTradeEvent(
            id="trade-2",
            type="TRADE",
            taker_order_id="order-1",
            market="m1",
            asset_id="yes-token",
            side="BUY",
            size=8.5,
            price=0.4,
            fee_rate_bps=0.0,
            status="MATCHED",
            matchtime=datetime.now(tz=timezone.utc),
            last_update=datetime.now(tz=timezone.utc),
            outcome="YES",
            owner="owner-1",
            trade_owner="owner-1",
            maker_address="0x1234",
            transaction_hash="",
            bucket_index=0,
            maker_orders=(),
            trader_side="TAKER",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )

    assert len(updates) == 1
    assert updates[0].matched_shares == 12.5
    assert updates[0].matched_notional == 5.0
    assert updates[0].status == OrderLifecycleStatus.FILLED
