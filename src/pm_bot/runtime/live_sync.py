"""Helpers for syncing live execution state into runtime risk state."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pm_bot.core.types import MarketSnapshot
from pm_bot.execution.order_tracker import OrderLifecycleStatus, TrackedOrder
from pm_bot.execution.position_ledger import LivePosition
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.runtime.state import PendingOrderState, PositionState

if TYPE_CHECKING:
    from pm_bot.core.interfaces import RiskManager


async def sync_live_execution_state(
    *,
    risk_manager: RiskManager,
    execution: PolymarketLiveExecutionAdapter,
    snapshots: Sequence[MarketSnapshot],
) -> tuple[LivePosition, ...]:
    """Mark live positions to market and push them into risk/dashboard state."""

    marked_positions = execution.mark_positions_to_market(tuple(snapshots))
    await risk_manager.sync_pending_orders(
        pending_order_states_from_tracked_orders(execution.tracker.snapshot())
    )
    await risk_manager.sync_open_positions(
        [_position_state_from_live_position(position) for position in execution.position_ledger.snapshot()]
    )
    return marked_positions


def position_states_from_live_positions(
    positions: Sequence[LivePosition],
) -> tuple[PositionState, ...]:
    return tuple(_position_state_from_live_position(position) for position in positions)


def pending_order_states_from_tracked_orders(
    orders: Sequence[TrackedOrder],
) -> tuple[PendingOrderState, ...]:
    return tuple(
        _pending_order_state_from_tracked_order(order)
        for order in orders
        if order.status in {
            OrderLifecycleStatus.PENDING,
            OrderLifecycleStatus.LIVE,
            OrderLifecycleStatus.PARTIALLY_FILLED,
        }
    )


def _position_state_from_live_position(position: LivePosition) -> PositionState:
    return PositionState(
        market_id=position.market_id,
        token_id=position.token_id,
        category=position.category,
        strategy_id=position.strategy_id,
        notional=position.cost_basis,
        shares=position.shares,
        average_entry_price=position.average_entry_price,
        mark_price=position.mark_price,
        unrealized_pnl=position.unrealized_pnl,
        opened_at=position.opened_at,
        exposure_group_id=position.exposure_group_id,
        thesis_group_id=position.thesis_group_id,
        underlying_group_id=position.underlying_group_id,
    )


def _pending_order_state_from_tracked_order(order: TrackedOrder) -> PendingOrderState:
    return PendingOrderState(
        order_id=order.order_id,
        intent_id=order.intent_id,
        market_id=order.market_id,
        token_id=order.token_id,
        category=order.category,
        strategy_id=order.strategy_id,
        side=order.trade_side.lower(),
        limit_price=order.limit_price,
        requested_shares=order.requested_shares,
        requested_notional=order.requested_notional,
        quote_ttl_seconds=order.quote_ttl_seconds,
        matched_shares=order.matched_shares,
        matched_notional=order.matched_notional,
        fees_paid=order.fees_paid,
        status=order.status.value,
        created_at=order.created_at,
        updated_at=order.updated_at,
        exposure_group_id=order.exposure_group_id,
        thesis_group_id=order.thesis_group_id,
        underlying_group_id=order.underlying_group_id,
    )
