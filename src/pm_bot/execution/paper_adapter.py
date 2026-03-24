"""Paper execution adapter with a minimal in-memory order lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pm_bot.core.types import MarketSnapshot, OrderIntent, SignalSide
from pm_bot.execution.order_tracker import (
    OrderLifecycleStatus,
    OrderLifecycleTracker,
    TrackedOrder,
)
from pm_bot.execution.position_ledger import LivePosition, PositionLedger
from pm_bot.runtime.state import ClosedTrade, PendingOrderState, PositionState


@dataclass(slots=True, frozen=True)
class PaperReconcileUpdate:
    filled_orders: tuple[TrackedOrder, ...]
    expired_orders: tuple[TrackedOrder, ...]
    marked_positions: tuple[LivePosition, ...]


class PaperExecutionAdapter:
    """In-memory execution adapter for research, paper, and tests."""

    def __init__(self, *, ttl_seconds: int = 30) -> None:
        self.ttl_seconds = ttl_seconds
        self.submitted_orders: list[OrderIntent] = []
        self.tracker = OrderLifecycleTracker()
        self.position_ledger = PositionLedger()
        self._signal_sides: dict[str, SignalSide] = {}

    async def submit(self, intent: OrderIntent) -> str:
        order_id = f"paper-{len(self.submitted_orders) + 1}"
        self.submitted_orders.append(intent)
        self.tracker.register_submission(order_id, intent)
        self._signal_sides[order_id] = intent.side
        return order_id

    async def cancel_stale(self) -> int:
        now = datetime.now(tz=timezone.utc)
        cancelled = 0
        for order_id in self.tracker.stale_order_ids(now=now, ttl_seconds=self.ttl_seconds):
            if self.tracker.mark_canceled(order_id, at=now) is not None:
                cancelled += 1
        return cancelled

    def reconcile_snapshot(
        self,
        snapshot: MarketSnapshot,
        *,
        ttl_seconds: int | None = None,
    ) -> PaperReconcileUpdate:
        """Apply fills, expiries, and fresh marks for one market snapshot."""

        effective_ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        snapshot_time = snapshot.timestamp.astimezone(timezone.utc)
        self.position_ledger.register_snapshots((snapshot,))
        filled_orders: list[TrackedOrder] = []
        expired_orders: list[TrackedOrder] = []

        for tracked in self.tracker.snapshot():
            if tracked.status in {
                OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
            }:
                continue

            fill_price = _paper_fill_price(tracked=tracked, snapshot=snapshot)
            if fill_price is not None:
                remaining_shares = max(tracked.requested_shares - tracked.matched_shares, 0.0)
                if remaining_shares > 0:
                    updated = self.tracker.apply_fill(
                        order_id=tracked.order_id,
                        market_id=tracked.market_id,
                        token_id=tracked.token_id,
                        category=tracked.category,
                        strategy_id=tracked.strategy_id,
                        trade_side=tracked.trade_side,
                        requested_shares=tracked.requested_shares,
                        limit_price=tracked.limit_price,
                        fill_shares=remaining_shares,
                        fill_price=fill_price,
                        fee_rate_bps=0.0,
                        event_time=snapshot_time,
                        last_event="paper:fill",
                    )
                    self.position_ledger.apply_tracked_order(updated)
                    filled_orders.append(updated)
                continue

            if tracked.market_id != snapshot.market_id:
                continue

            age_seconds = (snapshot_time - tracked.created_at.astimezone(timezone.utc)).total_seconds()
            if age_seconds < effective_ttl:
                continue

            expired = self.tracker.mark_canceled(tracked.order_id, at=snapshot_time)
            if expired is not None:
                expired_orders.append(expired)

        marked_positions = self.position_ledger.mark_to_market((snapshot,))
        return PaperReconcileUpdate(
            filled_orders=tuple(filled_orders),
            expired_orders=tuple(expired_orders),
            marked_positions=marked_positions,
        )

    def pending_order_states(self) -> tuple[PendingOrderState, ...]:
        return tuple(
            _pending_order_state_from_tracked_order(
                order=order,
                signal_side=self._signal_sides.get(order.order_id),
            )
            for order in self.tracker.snapshot()
            if order.status in {
                OrderLifecycleStatus.PENDING,
                OrderLifecycleStatus.LIVE,
                OrderLifecycleStatus.PARTIALLY_FILLED,
                OrderLifecycleStatus.UNKNOWN,
            }
        )

    def position_states(self) -> tuple[PositionState, ...]:
        return tuple(_position_state_from_live_position(position) for position in self.position_ledger.snapshot())

    def drain_closed_trades(self) -> tuple[ClosedTrade, ...]:
        return self.position_ledger.drain_closed_trades()


def _paper_fill_price(*, tracked: TrackedOrder, snapshot: MarketSnapshot) -> float | None:
    if tracked.market_id != snapshot.market_id:
        return None

    no_token_id = snapshot.metadata.get("no_token_id")
    if tracked.token_id == snapshot.token_id:
        if tracked.trade_side == "BUY":
            return _marketable_buy_price(limit_price=tracked.limit_price, best_ask=snapshot.best_ask_yes)
        return _marketable_sell_price(limit_price=tracked.limit_price, best_bid=snapshot.best_bid_yes)

    if no_token_id and tracked.token_id == no_token_id:
        if tracked.trade_side == "BUY":
            return _marketable_buy_price(limit_price=tracked.limit_price, best_ask=snapshot.best_ask_no)
        return _marketable_sell_price(limit_price=tracked.limit_price, best_bid=snapshot.best_bid_no)

    return None


def _marketable_buy_price(*, limit_price: float, best_ask: float | None) -> float | None:
    if best_ask is None or limit_price + 1e-9 < best_ask:
        return None
    return best_ask


def _marketable_sell_price(*, limit_price: float, best_bid: float | None) -> float | None:
    if best_bid is None or limit_price - 1e-9 > best_bid:
        return None
    return best_bid


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
    )


def _pending_order_state_from_tracked_order(
    *,
    order: TrackedOrder,
    signal_side: SignalSide | None,
) -> PendingOrderState:
    return PendingOrderState(
        order_id=order.order_id,
        market_id=order.market_id,
        token_id=order.token_id,
        category=order.category,
        strategy_id=order.strategy_id,
        side=(signal_side.value if signal_side is not None else order.trade_side.lower()),
        limit_price=order.limit_price,
        requested_shares=order.requested_shares,
        requested_notional=order.requested_notional,
        matched_shares=order.matched_shares,
        matched_notional=order.matched_notional,
        fees_paid=order.fees_paid,
        status=order.status.value,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
