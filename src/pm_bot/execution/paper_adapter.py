"""Paper execution adapter with queue-aware matching and runtime state sync."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pm_bot.core.types import MarketSnapshot, OrderIntent, SignalSide
from pm_bot.execution.order_tracker import (
    OrderLifecycleStatus,
    OrderLifecycleTracker,
    TrackedOrder,
)
from pm_bot.execution.paper_matching import PaperMatchEvent, PaperMatchingEngine
from pm_bot.execution.position_ledger import LivePosition, PositionLedger
from pm_bot.runtime.state import ClosedTrade, PendingOrderState, PositionState


@dataclass(slots=True, frozen=True)
class PaperReconcileUpdate:
    events: tuple[PaperMatchEvent, ...]
    filled_orders: tuple[TrackedOrder, ...]
    partial_fill_orders: tuple[TrackedOrder, ...]
    expired_orders: tuple[TrackedOrder, ...]
    canceled_orders: tuple[TrackedOrder, ...]
    marked_positions: tuple[LivePosition, ...]


class PaperExecutionAdapter:
    """In-memory paper execution adapter with queue-aware matching."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 30,
        place_latency_ms: int = 0,
        cancel_latency_ms: int = 0,
        fee_bps: float = 0.0,
        taker_slippage_bps: float = 0.0,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.submitted_orders: list[OrderIntent] = []
        self.tracker = OrderLifecycleTracker()
        self.position_ledger = PositionLedger()
        self.matcher = PaperMatchingEngine(
            place_latency_ms=place_latency_ms,
            cancel_latency_ms=cancel_latency_ms,
            fee_bps=fee_bps,
            taker_slippage_bps=taker_slippage_bps,
        )
        self._signal_sides: dict[str, SignalSide] = {}
        self._latest_snapshots: dict[str, MarketSnapshot] = {}

    async def submit(self, intent: OrderIntent) -> str:
        order_id = f"paper-{len(self.submitted_orders) + 1}"
        self.submitted_orders.append(intent)
        self.tracker.register_submission(order_id, intent)
        self.matcher.register_submission(
            order_id=order_id,
            intent=intent,
            snapshot=self._latest_snapshots.get(intent.market_id),
        )
        self._signal_sides[order_id] = intent.side
        return order_id

    async def cancel_order(
        self,
        order_id: str,
        *,
        now: datetime | None = None,
    ) -> TrackedOrder | None:
        effective_now = now or datetime.now(tz=timezone.utc)
        canceled = self.matcher.cancel_order(
            tracker=self.tracker,
            order_id=order_id,
            now=effective_now,
        )
        if canceled is not None:
            self._signal_sides.pop(order_id, None)
        return canceled

    async def cancel_stale(self) -> int:
        return len(await self.cancel_stale_orders())

    async def cancel_stale_orders(
        self,
        *,
        now: datetime | None = None,
    ) -> tuple[TrackedOrder, ...]:
        effective_now = now or datetime.now(tz=timezone.utc)
        self.matcher.request_cancel_stale(
            tracker=self.tracker,
            now=effective_now,
            ttl_seconds=self.ttl_seconds,
        )
        return self.matcher.apply_immediate_cancellations(
            tracker=self.tracker,
            now=effective_now,
        )

    def reconcile_snapshot(
        self,
        snapshot: MarketSnapshot,
        *,
        ttl_seconds: int | None = None,
    ) -> PaperReconcileUpdate:
        effective_ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        self._latest_snapshots[snapshot.market_id] = snapshot
        self.position_ledger.register_snapshots((snapshot,))

        events: list[PaperMatchEvent] = []
        filled_orders: list[TrackedOrder] = []
        partial_fill_orders: list[TrackedOrder] = []
        expired_orders: list[TrackedOrder] = []
        canceled_orders: list[TrackedOrder] = []

        for event in self.matcher.reconcile_snapshot(
            tracker=self.tracker,
            snapshot=snapshot,
            ttl_seconds=effective_ttl,
        ):
            events.append(event)
            if event.event_type in {"order.filled", "order.partially_filled"}:
                self.position_ledger.apply_tracked_order(event.order)

            if event.event_type == "order.filled":
                filled_orders.append(event.order)
            elif event.event_type == "order.partially_filled":
                partial_fill_orders.append(event.order)
            elif event.event_type == "order.expired":
                expired_orders.append(event.order)
            elif event.event_type == "order.canceled":
                canceled_orders.append(event.order)

        marked_positions = self.position_ledger.mark_to_market((snapshot,))
        return PaperReconcileUpdate(
            events=tuple(events),
            filled_orders=tuple(filled_orders),
            partial_fill_orders=tuple(partial_fill_orders),
            expired_orders=tuple(expired_orders),
            canceled_orders=tuple(canceled_orders),
            marked_positions=tuple(marked_positions),
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
        intent_id=order.intent_id,
        time_in_force=order.time_in_force,
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
        quote_ttl_seconds=order.quote_ttl_seconds,
        signal_edge_bps=order.signal_edge_bps,
    )
