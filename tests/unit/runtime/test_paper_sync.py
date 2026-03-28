from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.order_tracker import OrderLifecycleStatus, TrackedOrder
from pm_bot.execution.paper_matching import PaperMatchEvent
from pm_bot.runtime.paper_sync import order_payload_from_match_event


def test_order_payload_uses_complement_mid_for_no_token_when_no_quotes_are_missing() -> None:
    created_at = datetime(2026, 3, 25, 0, 0, tzinfo=UTC)
    updated_at = datetime(2026, 3, 25, 0, 0, 2, tzinfo=UTC)
    order = TrackedOrder(
        order_id="paper-1",
        market_id="m1",
        token_id="no-token",
        category=Category.CRYPTO,
        strategy_id="crypto.execution_sample",
        trade_side="BUY",
        limit_price=0.39,
        requested_shares=10.0,
        requested_notional=3.9,
        matched_shares=10.0,
        matched_notional=3.9,
        fees_paid=0.0,
        created_at=created_at,
        updated_at=updated_at,
        status=OrderLifecycleStatus.FILLED,
        last_event="paper:taker_fill",
    )
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=updated_at,
        resolution_time=None,
        best_bid_yes=0.61,
        best_ask_yes=0.62,
        best_bid_no=None,
        best_ask_no=None,
        metadata={"no_token_id": "no-token"},
    )

    payload = order_payload_from_match_event(
        order=order,
        snapshot=snapshot,
        match_event=PaperMatchEvent(
            event_type="order.filled",
            order=order,
            fill_shares=10.0,
            fill_notional=3.9,
            fill_source="taker",
        ),
    )

    assert payload["mid_price"] == 0.385
