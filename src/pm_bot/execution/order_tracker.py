"""Live order lifecycle tracking."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from pm_bot.adapters.polymarket.user_ws_client import UserOrderEvent, UserTradeEvent
from pm_bot.core.types import Category, OrderIntent, SignalSide


class OrderLifecycleStatus(str, Enum):
    PENDING = "pending"
    LIVE = "live"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class TrackedOrder:
    order_id: str
    market_id: str
    token_id: str
    category: Category
    strategy_id: str
    trade_side: str
    limit_price: float
    requested_shares: float
    requested_notional: float
    matched_shares: float
    matched_notional: float
    fees_paid: float
    created_at: datetime
    updated_at: datetime
    status: OrderLifecycleStatus
    last_event: str
    intent_id: str | None = None
    quote_ttl_seconds: int | None = None
    signal_edge_bps: float | None = None
    exposure_group_id: str | None = None
    thesis_group_id: str | None = None
    underlying_group_id: str | None = None
    time_in_force: str = "GTC"


class OrderLifecycleTracker:
    """Track local order submissions and apply exchange lifecycle events."""

    def __init__(self) -> None:
        self._orders: dict[str, TrackedOrder] = {}

    def register_submission(self, order_id: str, intent: OrderIntent) -> TrackedOrder:
        if intent.price is None:
            raise ValueError("Tracked live orders require a limit price")

        tracked = TrackedOrder(
            order_id=order_id,
            intent_id=intent.intent_id,
            market_id=intent.market_id,
            token_id=intent.token_id,
            category=intent.category,
            strategy_id=intent.strategy_id,
            trade_side=_trade_side_from_signal_side(intent.side),
            limit_price=float(intent.price),
            requested_shares=float(intent.size),
            requested_notional=float(intent.notional or (intent.price * intent.size)),
            quote_ttl_seconds=int(intent.quote_ttl_seconds) if intent.quote_ttl_seconds is not None else None,
            signal_edge_bps=float(intent.signal_edge_bps) if intent.signal_edge_bps is not None else None,
            exposure_group_id=intent.exposure_group_id,
            thesis_group_id=intent.thesis_group_id,
            underlying_group_id=intent.underlying_group_id,
            time_in_force=str(intent.time_in_force or "GTC"),
            matched_shares=0.0,
            matched_notional=0.0,
            fees_paid=0.0,
            created_at=intent.created_at,
            updated_at=intent.created_at,
            status=OrderLifecycleStatus.PENDING,
            last_event="submission",
        )
        self._orders[order_id] = tracked
        return tracked

    def apply_order_event(self, event: UserOrderEvent) -> TrackedOrder | None:
        tracked = self._orders.get(event.id)
        if tracked is None:
            return None

        matched_notional = max(tracked.matched_notional, event.size_matched * event.price)
        updated = replace(
            tracked,
            matched_shares=max(tracked.matched_shares, event.size_matched),
            matched_notional=matched_notional,
            updated_at=event.timestamp or event.created_at or tracked.updated_at,
            status=_status_from_order_event(event.status, event.size_matched, tracked.requested_shares),
            last_event=f"order:{event.type.lower() or 'update'}",
        )
        self._orders[event.id] = updated
        return updated

    def apply_trade_event(self, event: UserTradeEvent) -> tuple[TrackedOrder, ...]:
        updates: list[TrackedOrder] = []

        if event.taker_order_id:
            existing = self._orders.get(event.taker_order_id)
            updated = self.apply_fill(
                order_id=event.taker_order_id,
                market_id=event.market,
                token_id=event.asset_id,
                category=existing.category if existing is not None else Category.CRYPTO,
                strategy_id=existing.strategy_id if existing is not None else "recovered.live",
                trade_side=event.side,
                requested_shares=existing.requested_shares if existing is not None else event.size,
                limit_price=existing.limit_price if existing is not None else event.price,
                fill_shares=event.size,
                fill_price=event.price,
                fee_rate_bps=event.fee_rate_bps,
                event_time=event.timestamp or event.last_update,
                last_event="trade:taker",
            )
            updates.append(updated)

        for maker_order in event.maker_orders:
            existing = self._orders.get(maker_order.order_id)
            updated = self.apply_fill(
                order_id=maker_order.order_id,
                market_id=event.market,
                token_id=maker_order.asset_id,
                category=existing.category if existing is not None else Category.CRYPTO,
                strategy_id=existing.strategy_id if existing is not None else "recovered.live",
                trade_side=maker_order.side,
                requested_shares=existing.requested_shares if existing is not None else maker_order.matched_amount,
                limit_price=existing.limit_price if existing is not None else maker_order.price,
                fill_shares=maker_order.matched_amount,
                fill_price=maker_order.price,
                fee_rate_bps=maker_order.fee_rate_bps,
                event_time=event.timestamp or event.last_update,
                last_event="trade:maker",
            )
            updates.append(updated)

        return tuple(updates)

    def restore_order(
        self,
        *,
        order_id: str,
        intent_id: str | None,
        market_id: str,
        token_id: str,
        category: Category,
        strategy_id: str,
        trade_side: str,
        limit_price: float,
        requested_shares: float,
        requested_notional: float,
        quote_ttl_seconds: int | None,
        signal_edge_bps: float | None = None,
        exposure_group_id: str | None = None,
        thesis_group_id: str | None = None,
        underlying_group_id: str | None = None,
        time_in_force: str = "GTC",
        matched_shares: float,
        matched_notional: float,
        fees_paid: float,
        created_at: datetime,
        updated_at: datetime,
        status: OrderLifecycleStatus,
        last_event: str,
    ) -> TrackedOrder:
        existing = self._orders.get(order_id)
        normalized_trade_side = _normalize_trade_side(trade_side)
        if existing is None:
            tracked = TrackedOrder(
                order_id=order_id,
                intent_id=intent_id,
                market_id=market_id,
                token_id=token_id,
                category=category,
                strategy_id=strategy_id,
                trade_side=normalized_trade_side,
                limit_price=limit_price,
                requested_shares=requested_shares,
                requested_notional=requested_notional,
                quote_ttl_seconds=quote_ttl_seconds,
                signal_edge_bps=signal_edge_bps,
                exposure_group_id=exposure_group_id,
                thesis_group_id=thesis_group_id,
                underlying_group_id=underlying_group_id,
                time_in_force=time_in_force,
                matched_shares=matched_shares,
                matched_notional=matched_notional,
                fees_paid=fees_paid,
                created_at=created_at,
                updated_at=updated_at,
                status=status,
                last_event=last_event,
            )
            self._orders[order_id] = tracked
            return tracked

        updated = replace(
            existing,
            market_id=market_id,
            intent_id=intent_id if intent_id is not None else existing.intent_id,
            token_id=token_id,
            category=category,
            strategy_id=strategy_id or existing.strategy_id,
            trade_side=normalized_trade_side or existing.trade_side,
            limit_price=limit_price or existing.limit_price,
            requested_shares=max(existing.requested_shares, requested_shares),
            requested_notional=max(existing.requested_notional, requested_notional),
            quote_ttl_seconds=quote_ttl_seconds if quote_ttl_seconds is not None else existing.quote_ttl_seconds,
            signal_edge_bps=signal_edge_bps if signal_edge_bps is not None else existing.signal_edge_bps,
            exposure_group_id=exposure_group_id if exposure_group_id is not None else existing.exposure_group_id,
            thesis_group_id=thesis_group_id if thesis_group_id is not None else existing.thesis_group_id,
            underlying_group_id=underlying_group_id if underlying_group_id is not None else existing.underlying_group_id,
            time_in_force=str(time_in_force or existing.time_in_force),
            matched_shares=max(existing.matched_shares, matched_shares),
            matched_notional=max(existing.matched_notional, matched_notional),
            fees_paid=max(existing.fees_paid, fees_paid),
            created_at=min(existing.created_at, created_at),
            updated_at=max(existing.updated_at, updated_at),
            status=status if status != OrderLifecycleStatus.UNKNOWN else existing.status,
            last_event=last_event,
        )
        self._orders[order_id] = updated
        return updated

    def mark_canceled(self, order_id: str, at: datetime | None = None) -> TrackedOrder | None:
        tracked = self._orders.get(order_id)
        if tracked is None:
            return None
        if tracked.status in {
            OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
        }:
            return None
        effective_at = at or datetime.now(tz=timezone.utc)
        if effective_at < tracked.created_at:
            effective_at = tracked.created_at
        if effective_at < tracked.updated_at:
            effective_at = tracked.updated_at
        updated = replace(
            tracked,
            status=OrderLifecycleStatus.CANCELED,
            updated_at=effective_at,
            last_event="cancel",
        )
        self._orders[order_id] = updated
        return updated

    def stale_order_ids(self, *, now: datetime, ttl_seconds: int) -> tuple[str, ...]:
        stale: list[str] = []
        for tracked in self._orders.values():
            if tracked.status in {
                OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
            }:
                continue
            effective_ttl = tracked.quote_ttl_seconds if tracked.quote_ttl_seconds is not None else ttl_seconds
            if (now - tracked.created_at).total_seconds() >= effective_ttl:
                stale.append(tracked.order_id)
        return tuple(stale)

    def get(self, order_id: str) -> TrackedOrder | None:
        return self._orders.get(order_id)

    def snapshot(self) -> tuple[TrackedOrder, ...]:
        return tuple(self._orders.values())

    def apply_fill(
        self,
        *,
        order_id: str,
        market_id: str,
        token_id: str,
        category: Category,
        strategy_id: str,
        trade_side: str,
        requested_shares: float,
        limit_price: float,
        fill_shares: float,
        fill_price: float,
        fee_rate_bps: float | None,
        event_time: datetime | None,
        last_event: str,
        exposure_group_id: str | None = None,
        thesis_group_id: str | None = None,
        underlying_group_id: str | None = None,
    ) -> TrackedOrder:
        tracked = self._orders.get(order_id)
        normalized_trade_side = _normalize_trade_side(trade_side)
        if tracked is None:
            created_at = event_time or datetime.now(tz=timezone.utc)
            tracked = TrackedOrder(
                order_id=order_id,
                intent_id=None,
                market_id=market_id,
                token_id=token_id,
                category=category,
                strategy_id=strategy_id,
                trade_side=normalized_trade_side,
                limit_price=limit_price,
                requested_shares=max(requested_shares, fill_shares),
                requested_notional=max(requested_shares, fill_shares) * limit_price,
                quote_ttl_seconds=None,
                signal_edge_bps=None,
                exposure_group_id=exposure_group_id,
                thesis_group_id=thesis_group_id,
                underlying_group_id=underlying_group_id,
                time_in_force="GTC",
                matched_shares=0.0,
                matched_notional=0.0,
                fees_paid=0.0,
                created_at=created_at,
                updated_at=created_at,
                status=OrderLifecycleStatus.PENDING,
                last_event="restore",
            )

        fill_notional = fill_shares * fill_price
        incremental_fee = fill_notional * ((fee_rate_bps or 0.0) / 10000)
        next_matched_shares = tracked.matched_shares + fill_shares
        next_matched_notional = tracked.matched_notional + fill_notional
        next_fees = tracked.fees_paid + incremental_fee
        status = (
            OrderLifecycleStatus.FILLED
            if next_matched_shares >= tracked.requested_shares
            else OrderLifecycleStatus.PARTIALLY_FILLED
        )
        updated = replace(
            tracked,
            trade_side=normalized_trade_side,
            matched_shares=next_matched_shares,
            matched_notional=next_matched_notional,
            fees_paid=next_fees,
            exposure_group_id=exposure_group_id if exposure_group_id is not None else tracked.exposure_group_id,
            thesis_group_id=thesis_group_id if thesis_group_id is not None else tracked.thesis_group_id,
            underlying_group_id=underlying_group_id if underlying_group_id is not None else tracked.underlying_group_id,
            updated_at=event_time or tracked.updated_at,
            status=status,
            last_event=last_event,
        )
        self._orders[order_id] = updated
        return updated


def _status_from_order_event(
    raw_status: str,
    matched_shares: float,
    requested_shares: float,
) -> OrderLifecycleStatus:
    normalized = raw_status.strip().upper()
    if normalized in {"LIVE", "OPEN"}:
        return (
            OrderLifecycleStatus.PARTIALLY_FILLED
            if matched_shares > 0
            else OrderLifecycleStatus.LIVE
        )
    if normalized in {"CANCELED", "CANCELLED"}:
        return OrderLifecycleStatus.CANCELED
    if normalized in {"MATCHED", "FILLED"}:
        return OrderLifecycleStatus.FILLED
    if normalized in {"REJECTED", "FAILED"}:
        return OrderLifecycleStatus.REJECTED
    if matched_shares >= requested_shares and requested_shares > 0:
        return OrderLifecycleStatus.FILLED
    if matched_shares > 0:
        return OrderLifecycleStatus.PARTIALLY_FILLED
    return OrderLifecycleStatus.UNKNOWN


def _trade_side_from_signal_side(side: SignalSide) -> str:
    if side in {SignalSide.BUY_YES, SignalSide.BUY_NO}:
        return "BUY"
    if side in {SignalSide.SELL_YES, SignalSide.SELL_NO}:
        return "SELL"
    raise ValueError(f"Unsupported signal side for live order tracking: {side.value}")


def _normalize_trade_side(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {"BUY", "SELL"}:
        return normalized
    return normalized or "BUY"
