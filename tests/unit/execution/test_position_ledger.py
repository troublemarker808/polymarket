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
