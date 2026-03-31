from datetime import UTC, datetime

import pytest

from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.order_tracker import TrackedOrder, OrderLifecycleStatus
from pm_bot.execution.position_ledger import PositionLedger


def _tracked_order(
    *,
    order_id: str = "order-1",
    token_id: str = "yes-token",
    matched_shares: float = 10.0,
    matched_notional: float = 5.0,
    fees_paid: float = 0.01,
    trade_side: str = "BUY",
    exposure_group_id: str | None = None,
    thesis_group_id: str | None = None,
    underlying_group_id: str | None = None,
) -> TrackedOrder:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    return TrackedOrder(
        order_id=order_id,
        market_id="m1",
        token_id=token_id,
        category=Category.CRYPTO,
        strategy_id="crypto.surface",
        trade_side=trade_side,
        limit_price=0.5,
        requested_shares=10.0,
        requested_notional=5.0,
        matched_shares=matched_shares,
        matched_notional=matched_notional,
        fees_paid=fees_paid,
        created_at=now,
        updated_at=now,
        status=OrderLifecycleStatus.FILLED,
        last_event="trade:taker",
        exposure_group_id=exposure_group_id,
        thesis_group_id=thesis_group_id,
        underlying_group_id=underlying_group_id,
    )


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.62,
        best_ask_yes=0.64,
        best_bid_no=0.35,
        best_ask_no=0.38,
        last_traded_price=0.63,
        metadata={"no_token_id": "no-token"},
    )


def _snapshot_yes_only() -> MarketSnapshot:
    return MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.61,
        best_ask_yes=0.62,
        best_bid_no=None,
        best_ask_no=None,
        last_traded_price=0.63,
        metadata={"no_token_id": "no-token"},
    )


def test_position_ledger_applies_incremental_fill_once() -> None:
    ledger = PositionLedger()

    first = ledger.apply_tracked_order(_tracked_order(matched_shares=4.0, matched_notional=2.0, fees_paid=0.01))
    second = ledger.apply_tracked_order(_tracked_order(matched_shares=10.0, matched_notional=5.0, fees_paid=0.02))

    assert first is not None
    assert second is not None
    assert second.shares == 10.0
    assert second.cost_basis == 5.02
    assert second.average_entry_price == 0.502


def test_position_ledger_marks_yes_token_to_market() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(_tracked_order())

    marked = ledger.mark_to_market([_snapshot()])

    assert len(marked) == 1
    assert marked[0].mark_price == 0.62
    assert marked[0].unrealized_pnl == pytest.approx(1.19)


def test_position_ledger_marks_no_token_to_market() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(_tracked_order(token_id="no-token", matched_notional=3.6, fees_paid=0.0))

    marked = ledger.mark_to_market([_snapshot()])

    assert len(marked) == 1
    assert marked[0].mark_price == 0.35
    assert marked[0].unrealized_pnl == pytest.approx(-0.1)


def test_position_ledger_marks_no_token_from_yes_quotes_when_no_quotes_are_missing() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(_tracked_order(token_id="no-token", matched_notional=3.8, fees_paid=0.0))

    marked = ledger.mark_to_market([_snapshot_yes_only()])

    assert len(marked) == 1
    assert marked[0].mark_price == 0.38
    assert marked[0].unrealized_pnl == pytest.approx(0.0)


def test_position_ledger_realizes_pnl_when_position_is_fully_sold() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(_tracked_order())

    remaining = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-1",
            matched_shares=10.0,
            matched_notional=6.2,
            fees_paid=0.02,
            trade_side="SELL",
        )
    )

    assert remaining is None
    assert ledger.snapshot() == ()
    closed_trades = ledger.drain_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].realized_pnl == pytest.approx(1.19)
    assert closed_trades[0].fees_paid == pytest.approx(0.02)
    assert closed_trades[0].net_pnl == pytest.approx(1.17)


def test_position_ledger_carries_group_ids_into_closed_trade() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(
        _tracked_order(
            exposure_group_id="crypto:btc-march-31",
            thesis_group_id="crypto:btc:bullish",
            underlying_group_id="crypto:btc",
        )
    )

    ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-1",
            matched_shares=10.0,
            matched_notional=6.2,
            fees_paid=0.02,
            trade_side="SELL",
            exposure_group_id="crypto:btc-march-31",
            thesis_group_id="crypto:btc:bullish",
            underlying_group_id="crypto:btc",
        )
    )

    closed_trades = ledger.drain_closed_trades()

    assert len(closed_trades) == 1
    assert closed_trades[0].exposure_group_id == "crypto:btc-march-31"
    assert closed_trades[0].thesis_group_id == "crypto:btc:bullish"
    assert closed_trades[0].underlying_group_id == "crypto:btc"


def test_position_ledger_realizes_partial_pnl_and_keeps_remaining_position() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(_tracked_order())

    remaining = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-1",
            matched_shares=4.0,
            matched_notional=2.6,
            fees_paid=0.01,
            trade_side="SELL",
        )
    )

    assert remaining is not None
    assert remaining.shares == pytest.approx(6.0)
    assert remaining.cost_basis == pytest.approx(3.006)
    closed_trades = ledger.drain_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].realized_pnl == pytest.approx(0.596)
    assert closed_trades[0].net_pnl == pytest.approx(0.586)


def test_position_ledger_preserves_existing_strategy_on_recovered_live_close() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(_tracked_order())

    ledger.apply_tracked_order(
        TrackedOrder(
            order_id="sell-legacy-1",
            market_id="m1",
            token_id="yes-token",
            category=Category.CRYPTO,
            strategy_id="recovered.live",
            trade_side="SELL",
            limit_price=0.62,
            requested_shares=10.0,
            requested_notional=6.2,
            matched_shares=10.0,
            matched_notional=6.2,
            fees_paid=0.02,
            created_at=datetime(2026, 3, 23, 12, 5, tzinfo=UTC),
            updated_at=datetime(2026, 3, 23, 12, 5, tzinfo=UTC),
            status=OrderLifecycleStatus.FILLED,
            last_event="trade:taker",
        )
    )

    closed_trades = ledger.drain_closed_trades()

    assert len(closed_trades) == 1
    assert closed_trades[0].strategy_id == "crypto.surface"


def test_position_ledger_realizes_pnl_when_no_position_is_sold() -> None:
    ledger = PositionLedger()
    ledger.apply_tracked_order(
        _tracked_order(
            token_id="no-token",
            matched_shares=10.0,
            matched_notional=3.6,
            fees_paid=0.0,
        )
    )

    remaining = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-no-1",
            token_id="no-token",
            matched_shares=10.0,
            matched_notional=4.1,
            fees_paid=0.02,
            trade_side="SELL",
        )
    )

    assert remaining is None
    assert ledger.snapshot() == ()
    closed_trades = ledger.drain_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].realized_pnl == pytest.approx(0.5)
    assert closed_trades[0].net_pnl == pytest.approx(0.48)


def test_position_ledger_opens_complement_position_when_selling_without_inventory() -> None:
    ledger = PositionLedger()
    ledger.register_snapshots([_snapshot()])

    opened = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-open-1",
            matched_shares=10.0,
            matched_notional=6.2,
            fees_paid=0.02,
            trade_side="SELL",
        )
    )

    assert opened is not None
    assert opened.token_id == "no-token"
    assert opened.shares == pytest.approx(10.0)
    assert opened.cost_basis == pytest.approx(3.82)
    assert opened.average_entry_price == pytest.approx(0.382)
    assert ledger.drain_closed_trades() == ()


def test_position_ledger_splits_oversell_between_close_and_complement_open() -> None:
    ledger = PositionLedger()
    ledger.register_snapshots([_snapshot()])
    ledger.apply_tracked_order(
        _tracked_order(
            matched_shares=4.0,
            matched_notional=2.0,
            fees_paid=0.01,
        )
    )

    opened = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-flip-1",
            matched_shares=10.0,
            matched_notional=6.2,
            fees_paid=0.02,
            trade_side="SELL",
        )
    )

    assert opened is not None
    assert opened.token_id == "no-token"
    assert opened.shares == pytest.approx(6.0)
    assert opened.cost_basis == pytest.approx(2.292)
    closed_trades = ledger.drain_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].realized_pnl == pytest.approx(0.47)
    assert closed_trades[0].net_pnl == pytest.approx(0.462)


def test_position_ledger_can_disable_synthetic_complement_opens() -> None:
    ledger = PositionLedger(allow_synthetic_complement_on_sell=False)
    ledger.register_snapshots([_snapshot()])
    ledger.apply_tracked_order(
        _tracked_order(
            token_id="no-token",
            matched_shares=0.01,
            matched_notional=0.0054,
            fees_paid=0.0,
        )
    )

    first_close = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-no-1",
            token_id="no-token",
            matched_shares=0.01,
            matched_notional=0.0046,
            fees_paid=0.0,
            trade_side="SELL",
        )
    )
    second_close = ledger.apply_tracked_order(
        _tracked_order(
            order_id="sell-no-2",
            token_id="no-token",
            matched_shares=0.01,
            matched_notional=0.0046,
            fees_paid=0.0,
            trade_side="SELL",
        )
    )

    assert first_close is None
    assert second_close is None
    assert ledger.snapshot() == ()
    closed_trades = ledger.drain_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].token_id == "no-token"
