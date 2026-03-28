"""Queue-aware paper matching helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pm_bot.core.types import MarketSnapshot, OrderBookLevel, OrderIntent
from pm_bot.execution.order_tracker import (
    OrderLifecycleStatus,
    OrderLifecycleTracker,
    TrackedOrder,
)

_PRICE_EPSILON = 1e-9
_UNBOUNDED_SIZE = 1_000_000_000.0


@dataclass(slots=True)
class PaperOrderState:
    order_id: str
    eligible_at: datetime
    queue_ahead_shares: float
    cancel_requested_at: datetime | None = None
    last_trade_signature: str | None = None


@dataclass(slots=True, frozen=True)
class PaperMatchEvent:
    event_type: str
    order: TrackedOrder
    fill_shares: float = 0.0
    fill_notional: float = 0.0
    fill_source: str | None = None
    fee_paid: float = 0.0


class PaperMatchingEngine:
    """Approximate maker/taker matching using public book and trade updates."""

    def __init__(
        self,
        *,
        place_latency_ms: int = 0,
        cancel_latency_ms: int = 0,
        fee_bps: float = 0.0,
        taker_slippage_bps: float = 0.0,
    ) -> None:
        self.place_latency_ms = max(place_latency_ms, 0)
        self.cancel_latency_ms = max(cancel_latency_ms, 0)
        self.fee_bps = max(fee_bps, 0.0)
        self.taker_slippage_bps = max(taker_slippage_bps, 0.0)
        self._order_states: dict[str, PaperOrderState] = {}

    def register_submission(
        self,
        *,
        order_id: str,
        intent: OrderIntent,
        snapshot: MarketSnapshot | None,
    ) -> None:
        eligible_at = intent.created_at.astimezone(timezone.utc) + timedelta(milliseconds=self.place_latency_ms)
        queue_ahead = 0.0
        if snapshot is not None and intent.price is not None:
            queue_ahead = _initial_queue_ahead(snapshot=snapshot, intent=intent)
        self._order_states[order_id] = PaperOrderState(
            order_id=order_id,
            eligible_at=eligible_at,
            queue_ahead_shares=queue_ahead,
        )

    def reconcile_snapshot(
        self,
        *,
        tracker: OrderLifecycleTracker,
        snapshot: MarketSnapshot,
        ttl_seconds: int,
    ) -> tuple[PaperMatchEvent, ...]:
        snapshot_time = snapshot.timestamp.astimezone(timezone.utc)
        events: list[PaperMatchEvent] = []

        for tracked in tracker.snapshot():
            state = self._order_states.setdefault(
                tracked.order_id,
                PaperOrderState(
                    order_id=tracked.order_id,
                    eligible_at=tracked.created_at.astimezone(timezone.utc),
                    queue_ahead_shares=0.0,
                ),
            )

            if tracked.status in {
                OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
            }:
                continue

            age_seconds = (snapshot_time - tracked.created_at.astimezone(timezone.utc)).total_seconds()
            effective_ttl = tracked.quote_ttl_seconds if tracked.quote_ttl_seconds is not None else ttl_seconds
            if age_seconds >= effective_ttl and state.cancel_requested_at is None:
                state.cancel_requested_at = snapshot_time

            if tracked.market_id == snapshot.market_id and snapshot_time >= state.eligible_at:
                events.extend(
                    self._apply_passive_trade_fill(
                        tracker=tracker,
                        tracked=tracked,
                        state=state,
                        snapshot=snapshot,
                    )
                )
                refreshed = tracker.get(tracked.order_id)
                if refreshed is None:
                    continue
                tracked = refreshed
                if tracked.status not in {
                    OrderLifecycleStatus.FILLED,
                    OrderLifecycleStatus.CANCELED,
                    OrderLifecycleStatus.REJECTED,
                }:
                    taker_event = self._apply_marketable_sweep(
                        tracker=tracker,
                        tracked=tracked,
                        snapshot=snapshot,
                    )
                    if taker_event is not None:
                        events.append(taker_event)
                        refreshed = tracker.get(tracked.order_id)
                        if refreshed is not None:
                            tracked = refreshed
                if (
                    tracked.time_in_force.upper() == "IOC"
                    and tracked.market_id == snapshot.market_id
                    and snapshot_time >= state.eligible_at
                ):
                    latest = tracker.get(tracked.order_id)
                    if latest is not None and latest.status not in {
                        OrderLifecycleStatus.CANCELED,
                        OrderLifecycleStatus.FILLED,
                        OrderLifecycleStatus.REJECTED,
                    }:
                        canceled = tracker.mark_canceled(tracked.order_id, at=snapshot.timestamp)
                        if canceled is not None:
                            events.append(PaperMatchEvent(event_type="order.canceled", order=canceled))

            if state.cancel_requested_at is None:
                continue
            cancel_effective_at = state.cancel_requested_at + timedelta(milliseconds=self.cancel_latency_ms)
            if snapshot_time + timedelta(microseconds=1) < cancel_effective_at:
                continue
            latest = tracker.get(tracked.order_id)
            if latest is None or latest.status in {
                OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
            }:
                continue
            canceled = tracker.mark_canceled(tracked.order_id, at=cancel_effective_at)
            if canceled is not None:
                events.append(PaperMatchEvent(event_type="order.expired", order=canceled))

        return tuple(events)

    def request_cancel_stale(
        self,
        *,
        tracker: OrderLifecycleTracker,
        now: datetime,
        ttl_seconds: int,
    ) -> int:
        requested = 0
        for tracked in tracker.snapshot():
            if tracked.status in {
                OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
            }:
                continue
            effective_ttl = tracked.quote_ttl_seconds if tracked.quote_ttl_seconds is not None else ttl_seconds
            if (now - tracked.created_at.astimezone(timezone.utc)).total_seconds() < effective_ttl:
                continue
            state = self._order_states.setdefault(
                tracked.order_id,
                PaperOrderState(
                    order_id=tracked.order_id,
                    eligible_at=tracked.created_at.astimezone(timezone.utc),
                    queue_ahead_shares=0.0,
                ),
            )
            if state.cancel_requested_at is None:
                state.cancel_requested_at = now
                requested += 1
        return requested

    def apply_immediate_cancellations(
        self,
        *,
        tracker: OrderLifecycleTracker,
        now: datetime,
    ) -> tuple[TrackedOrder, ...]:
        canceled: list[TrackedOrder] = []
        for tracked in tracker.snapshot():
            state = self._order_states.get(tracked.order_id)
            if state is None or state.cancel_requested_at is None:
                continue
            if tracked.status in {
                OrderLifecycleStatus.CANCELED,
                OrderLifecycleStatus.FILLED,
                OrderLifecycleStatus.REJECTED,
            }:
                continue
            cancel_effective_at = state.cancel_requested_at + timedelta(milliseconds=self.cancel_latency_ms)
            if now + timedelta(microseconds=1) < cancel_effective_at:
                continue
            updated = tracker.mark_canceled(tracked.order_id, at=cancel_effective_at)
            if updated is not None:
                canceled.append(updated)
        return tuple(canceled)

    def cancel_order(
        self,
        *,
        tracker: OrderLifecycleTracker,
        order_id: str,
        now: datetime,
    ) -> TrackedOrder | None:
        self._order_states.pop(order_id, None)
        return tracker.mark_canceled(order_id, at=now)

    def last_known_states(self) -> dict[str, PaperOrderState]:
        return {
            order_id: PaperOrderState(
                order_id=state.order_id,
                eligible_at=state.eligible_at,
                queue_ahead_shares=state.queue_ahead_shares,
                cancel_requested_at=state.cancel_requested_at,
                last_trade_signature=state.last_trade_signature,
            )
            for order_id, state in self._order_states.items()
        }

    def _apply_passive_trade_fill(
        self,
        *,
        tracker: OrderLifecycleTracker,
        tracked: TrackedOrder,
        state: PaperOrderState,
        snapshot: MarketSnapshot,
    ) -> tuple[PaperMatchEvent, ...]:
        signature = _trade_signature(snapshot)
        if signature is None or signature == state.last_trade_signature:
            return ()

        last_trade_price = _trade_price_for_token(snapshot=snapshot, token_id=tracked.token_id)
        last_trade_size = snapshot.last_trade_size
        last_trade_side = _trade_side_for_token(snapshot=snapshot, token_id=tracked.token_id)
        if last_trade_price is None or last_trade_size is None or last_trade_size <= 0:
            state.last_trade_signature = signature
            return ()

        if tracked.trade_side == "BUY":
            trade_is_compatible = last_trade_side == "SELL" and tracked.limit_price + _PRICE_EPSILON >= last_trade_price
        else:
            trade_is_compatible = last_trade_side == "BUY" and tracked.limit_price - _PRICE_EPSILON <= last_trade_price

        state.last_trade_signature = signature
        if not trade_is_compatible:
            return ()

        remaining_trade_volume = last_trade_size
        if state.queue_ahead_shares > 0:
            if remaining_trade_volume <= state.queue_ahead_shares + _PRICE_EPSILON:
                state.queue_ahead_shares = max(0.0, state.queue_ahead_shares - remaining_trade_volume)
                return ()
            remaining_trade_volume -= state.queue_ahead_shares
            state.queue_ahead_shares = 0.0

        remaining_shares = max(tracked.requested_shares - tracked.matched_shares, 0.0)
        fill_shares = min(remaining_shares, remaining_trade_volume)
        if fill_shares <= 0:
            return ()

        updated = tracker.apply_fill(
            order_id=tracked.order_id,
            market_id=tracked.market_id,
            token_id=tracked.token_id,
            category=tracked.category,
            strategy_id=tracked.strategy_id,
            trade_side=tracked.trade_side,
            requested_shares=tracked.requested_shares,
            limit_price=tracked.limit_price,
            fill_shares=fill_shares,
            fill_price=last_trade_price,
            fee_rate_bps=self.fee_bps,
            event_time=snapshot.timestamp,
            last_event="paper:maker_fill",
        )
        event_type = "order.filled" if updated.status == OrderLifecycleStatus.FILLED else "order.partially_filled"
        fill_notional = fill_shares * last_trade_price
        return (
            PaperMatchEvent(
                event_type=event_type,
                order=updated,
                fill_shares=fill_shares,
                fill_notional=fill_notional,
                fill_source="maker",
                fee_paid=fill_notional * (self.fee_bps / 10000),
            ),
        )

    def _apply_marketable_sweep(
        self,
        *,
        tracker: OrderLifecycleTracker,
        tracked: TrackedOrder,
        snapshot: MarketSnapshot,
    ) -> PaperMatchEvent | None:
        remaining_shares = max(tracked.requested_shares - tracked.matched_shares, 0.0)
        if remaining_shares <= 0:
            return None

        levels = _opposite_book_levels(snapshot=snapshot, token_id=tracked.token_id, trade_side=tracked.trade_side)
        if not levels:
            levels = _fallback_levels(snapshot=snapshot, token_id=tracked.token_id, trade_side=tracked.trade_side)

        compatible_levels: list[OrderBookLevel] = []
        for level in levels:
            if tracked.trade_side == "BUY":
                if level.price - tracked.limit_price > _PRICE_EPSILON:
                    break
            else:
                if tracked.limit_price - level.price > _PRICE_EPSILON:
                    break
            if level.size > 0:
                compatible_levels.append(level)

        if not compatible_levels:
            return None

        filled = 0.0
        notional = 0.0
        for level in compatible_levels:
            take = min(remaining_shares - filled, level.size)
            if take <= 0:
                break
            price = _apply_slippage(price=level.price, trade_side=tracked.trade_side, slippage_bps=self.taker_slippage_bps)
            filled += take
            notional += take * price
            if filled + _PRICE_EPSILON >= remaining_shares:
                break

        if filled <= 0:
            return None

        average_price = notional / filled
        updated = tracker.apply_fill(
            order_id=tracked.order_id,
            market_id=tracked.market_id,
            token_id=tracked.token_id,
            category=tracked.category,
            strategy_id=tracked.strategy_id,
            trade_side=tracked.trade_side,
            requested_shares=tracked.requested_shares,
            limit_price=tracked.limit_price,
            fill_shares=filled,
            fill_price=average_price,
            fee_rate_bps=self.fee_bps,
            event_time=snapshot.timestamp,
            last_event="paper:taker_fill",
        )
        event_type = "order.filled" if updated.status == OrderLifecycleStatus.FILLED else "order.partially_filled"
        return PaperMatchEvent(
            event_type=event_type,
            order=updated,
            fill_shares=filled,
            fill_notional=notional,
            fill_source="taker",
            fee_paid=notional * (self.fee_bps / 10000),
        )


def _initial_queue_ahead(*, snapshot: MarketSnapshot, intent: OrderIntent) -> float:
    if intent.price is None:
        return 0.0
    same_side_levels = _same_side_book_levels(snapshot=snapshot, token_id=intent.token_id, signal_side=intent.side.value)
    if not same_side_levels:
        return 0.0

    queue = 0.0
    is_buy = intent.side.value.startswith("buy")
    for level in same_side_levels:
        if is_buy:
            if level.price > intent.price + _PRICE_EPSILON:
                queue += level.size
                continue
            if abs(level.price - intent.price) <= _PRICE_EPSILON:
                queue += level.size
            break
        if level.price + _PRICE_EPSILON < intent.price:
            queue += level.size
            continue
        if abs(level.price - intent.price) <= _PRICE_EPSILON:
            queue += level.size
        break
    return queue


def _same_side_book_levels(
    *,
    snapshot: MarketSnapshot,
    token_id: str,
    signal_side: str,
) -> tuple[OrderBookLevel, ...]:
    is_buy = signal_side.startswith("buy")
    levels = _bid_levels_for_token(snapshot=snapshot, token_id=token_id) if is_buy else _ask_levels_for_token(
        snapshot=snapshot,
        token_id=token_id,
    )
    summary_price = _best_bid_for_token(snapshot=snapshot, token_id=token_id) if is_buy else _best_ask_for_token(
        snapshot=snapshot,
        token_id=token_id,
    )
    if not _levels_match_summary(levels=levels, summary_price=summary_price):
        return ()
    return levels


def _opposite_book_levels(
    *,
    snapshot: MarketSnapshot,
    token_id: str,
    trade_side: str,
) -> tuple[OrderBookLevel, ...]:
    is_buy = trade_side == "BUY"
    levels = _ask_levels_for_token(snapshot=snapshot, token_id=token_id) if is_buy else _bid_levels_for_token(
        snapshot=snapshot,
        token_id=token_id,
    )
    summary_price = _best_ask_for_token(snapshot=snapshot, token_id=token_id) if is_buy else _best_bid_for_token(
        snapshot=snapshot,
        token_id=token_id,
    )
    if not _levels_match_summary(levels=levels, summary_price=summary_price):
        return ()
    return levels


def _fallback_levels(
    *,
    snapshot: MarketSnapshot,
    token_id: str,
    trade_side: str,
) -> tuple[OrderBookLevel, ...]:
    is_buy = trade_side == "BUY"
    if is_buy:
        best_ask = _best_ask_for_token(snapshot=snapshot, token_id=token_id)
        if best_ask is not None:
            return (
                OrderBookLevel(
                    price=best_ask,
                    size=_best_ask_size_for_token(snapshot=snapshot, token_id=token_id) or _UNBOUNDED_SIZE,
                ),
            )
        return ()
    best_bid = _best_bid_for_token(snapshot=snapshot, token_id=token_id)
    if best_bid is not None:
        return (
            OrderBookLevel(
                price=best_bid,
                size=_best_bid_size_for_token(snapshot=snapshot, token_id=token_id) or _UNBOUNDED_SIZE,
            ),
        )
    return ()


def _best_bid_for_token(*, snapshot: MarketSnapshot, token_id: str) -> float | None:
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        if snapshot.best_bid_no is not None:
            return snapshot.best_bid_no
        return _infer_complement_bid(snapshot.best_ask_yes)
    if snapshot.best_bid_yes is not None:
        return snapshot.best_bid_yes
    return _infer_complement_bid(snapshot.best_ask_no)


def _best_ask_for_token(*, snapshot: MarketSnapshot, token_id: str) -> float | None:
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        if snapshot.best_ask_no is not None:
            return snapshot.best_ask_no
        return _infer_complement_ask(snapshot.best_bid_yes)
    if snapshot.best_ask_yes is not None:
        return snapshot.best_ask_yes
    return _infer_complement_ask(snapshot.best_bid_no)


def _best_bid_size_for_token(*, snapshot: MarketSnapshot, token_id: str) -> float | None:
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        if snapshot.best_bid_no_size is not None:
            return snapshot.best_bid_no_size
        bid_levels = _bid_levels_for_token(snapshot=snapshot, token_id=token_id)
        return bid_levels[0].size if bid_levels else None
    if snapshot.best_bid_yes_size is not None:
        return snapshot.best_bid_yes_size
    bid_levels = _bid_levels_for_token(snapshot=snapshot, token_id=token_id)
    return bid_levels[0].size if bid_levels else None


def _best_ask_size_for_token(*, snapshot: MarketSnapshot, token_id: str) -> float | None:
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        if snapshot.best_ask_no_size is not None:
            return snapshot.best_ask_no_size
        ask_levels = _ask_levels_for_token(snapshot=snapshot, token_id=token_id)
        return ask_levels[0].size if ask_levels else None
    if snapshot.best_ask_yes_size is not None:
        return snapshot.best_ask_yes_size
    ask_levels = _ask_levels_for_token(snapshot=snapshot, token_id=token_id)
    return ask_levels[0].size if ask_levels else None


def _bid_levels_for_token(*, snapshot: MarketSnapshot, token_id: str) -> tuple[OrderBookLevel, ...]:
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        if snapshot.no_bid_levels:
            return snapshot.no_bid_levels
        if snapshot.yes_ask_levels:
            return _complement_bid_levels(snapshot.yes_ask_levels)
        return ()
    if snapshot.yes_bid_levels:
        return snapshot.yes_bid_levels
    if snapshot.no_ask_levels:
        return _complement_bid_levels(snapshot.no_ask_levels)
    return ()


def _ask_levels_for_token(*, snapshot: MarketSnapshot, token_id: str) -> tuple[OrderBookLevel, ...]:
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        if snapshot.no_ask_levels:
            return snapshot.no_ask_levels
        if snapshot.yes_bid_levels:
            return _complement_ask_levels(snapshot.yes_bid_levels)
        return ()
    if snapshot.yes_ask_levels:
        return snapshot.yes_ask_levels
    if snapshot.no_bid_levels:
        return _complement_ask_levels(snapshot.no_bid_levels)
    return ()
    return ()


def _apply_slippage(*, price: float, trade_side: str, slippage_bps: float) -> float:
    if slippage_bps <= 0:
        return price
    if trade_side == "BUY":
        return min(1.0, price * (1 + (slippage_bps / 10000)))
    return max(0.0, price * (1 - (slippage_bps / 10000)))


def _levels_match_summary(
    *,
    levels: tuple[OrderBookLevel, ...],
    summary_price: float | None,
) -> bool:
    if not levels:
        return True
    if summary_price is None:
        return False
    return abs(levels[0].price - summary_price) <= _PRICE_EPSILON


def _infer_complement_bid(best_ask: float | None) -> float | None:
    if best_ask is None:
        return None
    return round(1.0 - best_ask, 6)


def _infer_complement_ask(best_bid: float | None) -> float | None:
    if best_bid is None:
        return None
    return round(1.0 - best_bid, 6)


def _complement_bid_levels(levels: tuple[OrderBookLevel, ...]) -> tuple[OrderBookLevel, ...]:
    return tuple(
        sorted(
            (OrderBookLevel(price=round(1.0 - level.price, 6), size=level.size) for level in levels),
            key=lambda level: level.price,
            reverse=True,
        )
    )


def _complement_ask_levels(levels: tuple[OrderBookLevel, ...]) -> tuple[OrderBookLevel, ...]:
    return tuple(
        sorted(
            (OrderBookLevel(price=round(1.0 - level.price, 6), size=level.size) for level in levels),
            key=lambda level: level.price,
        )
    )


def _trade_signature(snapshot: MarketSnapshot) -> str | None:
    if snapshot.last_traded_price is None or snapshot.last_trade_side is None or snapshot.last_trade_size is None:
        return None
    event_timestamp = snapshot.metadata.get("last_trade_event_at")
    return "|".join(
        (
            str(event_timestamp or ""),
            f"{snapshot.last_traded_price:.10f}",
            str(snapshot.last_trade_side).upper(),
            f"{snapshot.last_trade_size:.10f}",
        )
    )


def _trade_price_for_token(*, snapshot: MarketSnapshot, token_id: str) -> float | None:
    if snapshot.last_traded_price is None:
        return None
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        return max(0.0, 1.0 - snapshot.last_traded_price)
    return snapshot.last_traded_price


def _trade_side_for_token(*, snapshot: MarketSnapshot, token_id: str) -> str:
    trade_side = (snapshot.last_trade_side or "").upper()
    if not trade_side:
        return ""
    no_token_id = snapshot.metadata.get("no_token_id")
    if no_token_id and token_id == no_token_id:
        return "SELL" if trade_side == "BUY" else "BUY" if trade_side == "SELL" else trade_side
    return trade_side
