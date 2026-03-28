"""Position accounting for live execution fills and mark-to-market updates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.order_tracker import TrackedOrder
from pm_bot.runtime.state import ClosedTrade


@dataclass(slots=True, frozen=True)
class LivePosition:
    market_id: str
    token_id: str
    category: Category
    strategy_id: str
    shares: float
    cost_basis: float
    average_entry_price: float
    total_fees: float
    mark_price: float | None
    unrealized_pnl: float
    opened_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class AppliedOrderProgress:
    matched_shares: float
    matched_notional: float
    fees_paid: float


class PositionLedger:
    """Keep local positions in sync with cumulative tracked-order fills."""

    def __init__(self, *, allow_synthetic_complement_on_sell: bool = True) -> None:
        self._positions: dict[tuple[str, str], LivePosition] = {}
        self._applied_progress: dict[str, AppliedOrderProgress] = {}
        self._closed_trades: list[ClosedTrade] = []
        self._canonical_market_by_token: dict[str, str] = {}
        self._complement_by_token: dict[str, str] = {}
        self._allow_synthetic_complement_on_sell = allow_synthetic_complement_on_sell

    def apply_tracked_order(self, tracked: TrackedOrder) -> LivePosition | None:
        """Apply the incremental fill delta from a tracked order."""

        tracked = self._canonicalize_tracked_order(tracked)
        previous = self._applied_progress.get(
            tracked.order_id,
            AppliedOrderProgress(
                matched_shares=0.0,
                matched_notional=0.0,
                fees_paid=0.0,
            ),
        )
        delta_shares = tracked.matched_shares - previous.matched_shares
        delta_notional = tracked.matched_notional - previous.matched_notional
        delta_fees = tracked.fees_paid - previous.fees_paid

        if delta_shares < -1e-9 or delta_notional < -1e-9 or delta_fees < -1e-9:
            raise ValueError("Tracked order fill progress regressed")

        self._applied_progress[tracked.order_id] = AppliedOrderProgress(
            matched_shares=tracked.matched_shares,
            matched_notional=tracked.matched_notional,
            fees_paid=tracked.fees_paid,
        )

        if delta_shares <= 0 and delta_fees <= 0:
            return None

        if tracked.trade_side == "SELL":
            return self._apply_sell_fill(
                tracked=tracked,
                delta_shares=delta_shares,
                delta_notional=delta_notional,
                delta_fees=delta_fees,
            )

        return self._apply_buy_fill(
            tracked=tracked,
            delta_shares=delta_shares,
            delta_notional=delta_notional,
            delta_fees=delta_fees,
        )

    def mark_to_market(self, snapshots: list[MarketSnapshot] | tuple[MarketSnapshot, ...]) -> tuple[LivePosition, ...]:
        """Update position marks using current market snapshots."""

        self.register_snapshots(snapshots)
        snapshots_by_market = {snapshot.market_id: snapshot for snapshot in snapshots}
        snapshots_by_token = {
            token_id: snapshot
            for snapshot in snapshots
            for token_id in (
                snapshot.token_id,
                snapshot.metadata.get("no_token_id"),
            )
            if token_id
        }
        updated_positions: list[LivePosition] = []

        for key, position in list(self._positions.items()):
            snapshot = snapshots_by_market.get(position.market_id) or snapshots_by_token.get(position.token_id)
            if snapshot is None:
                continue

            mark_price = _mark_price_for_token(snapshot=snapshot, token_id=position.token_id)
            unrealized_pnl = 0.0
            if mark_price is not None:
                unrealized_pnl = (position.shares * mark_price) - position.cost_basis

            updated = replace(
                position,
                mark_price=mark_price,
                unrealized_pnl=unrealized_pnl,
                updated_at=snapshot.timestamp,
            )
            self._positions[key] = updated
            updated_positions.append(updated)

        return tuple(updated_positions)

    def total_unrealized_pnl(self) -> float:
        return sum(position.unrealized_pnl for position in self._positions.values())

    def snapshot(self) -> tuple[LivePosition, ...]:
        return tuple(self._positions.values())

    def drain_closed_trades(self) -> tuple[ClosedTrade, ...]:
        drained = tuple(self._closed_trades)
        self._closed_trades.clear()
        return drained

    def register_snapshots(
        self,
        snapshots: list[MarketSnapshot] | tuple[MarketSnapshot, ...],
    ) -> None:
        for snapshot in snapshots:
            self._canonical_market_by_token[snapshot.token_id] = snapshot.market_id
            no_token_id = snapshot.metadata.get("no_token_id")
            if no_token_id:
                self._canonical_market_by_token[no_token_id] = snapshot.market_id
                self._complement_by_token[snapshot.token_id] = no_token_id
                self._complement_by_token[no_token_id] = snapshot.token_id

    def _apply_buy_fill(
        self,
        *,
        tracked: TrackedOrder,
        delta_shares: float,
        delta_notional: float,
        delta_fees: float,
    ) -> LivePosition | None:
        key = (tracked.market_id, tracked.token_id)
        existing = self._positions.get(key)
        if existing is None:
            total_shares = delta_shares
            total_cost_basis = delta_notional + delta_fees
            if total_shares <= 0:
                return None
            updated = LivePosition(
                market_id=tracked.market_id,
                token_id=tracked.token_id,
                category=tracked.category,
                strategy_id=tracked.strategy_id,
                shares=total_shares,
                cost_basis=total_cost_basis,
                average_entry_price=total_cost_basis / total_shares,
                total_fees=delta_fees,
                mark_price=None,
                unrealized_pnl=0.0,
                opened_at=tracked.created_at,
                updated_at=tracked.updated_at,
            )
            self._positions[key] = updated
            return updated

        total_shares = existing.shares + delta_shares
        total_cost_basis = existing.cost_basis + delta_notional + delta_fees
        updated = replace(
            existing,
            shares=total_shares,
            cost_basis=total_cost_basis,
            average_entry_price=(total_cost_basis / total_shares) if total_shares > 0 else 0.0,
            total_fees=existing.total_fees + delta_fees,
            updated_at=tracked.updated_at,
        )
        self._positions[key] = updated
        return updated

    def _apply_sell_fill(
        self,
        *,
        tracked: TrackedOrder,
        delta_shares: float,
        delta_notional: float,
        delta_fees: float,
    ) -> LivePosition | None:
        key = (tracked.market_id, tracked.token_id)
        existing = self._positions.get(key)
        fill_price = (delta_notional / delta_shares) if delta_shares > 0 else tracked.limit_price

        closed_shares = min(existing.shares, delta_shares) if existing is not None else 0.0
        closed_fees = delta_fees * (closed_shares / delta_shares) if delta_shares > 0 else 0.0
        updated_existing: LivePosition | None = existing

        if closed_shares > 0 and existing is not None:
            average_cost = existing.cost_basis / existing.shares if existing.shares > 0 else 0.0
            relieved_cost_basis = average_cost * closed_shares
            realized_pnl = (fill_price * closed_shares) - relieved_cost_basis
            self._closed_trades.append(
                ClosedTrade(
                    market_id=tracked.market_id,
                    token_id=tracked.token_id,
                    category=tracked.category,
                    strategy_id=tracked.strategy_id,
                    intent_id=tracked.intent_id,
                    realized_pnl=realized_pnl,
                    fees_paid=closed_fees,
                    closed_at=tracked.updated_at,
                )
            )

            remaining_shares = existing.shares - closed_shares
            remaining_cost_basis = existing.cost_basis - relieved_cost_basis
            if remaining_shares <= 1e-9:
                self._positions.pop(key, None)
                updated_existing = None
            else:
                updated_existing = replace(
                    existing,
                    shares=remaining_shares,
                    cost_basis=max(remaining_cost_basis, 0.0),
                    average_entry_price=max(remaining_cost_basis, 0.0) / remaining_shares,
                    total_fees=existing.total_fees + closed_fees,
                    updated_at=tracked.updated_at,
                )
                self._positions[key] = updated_existing

        synthetic_open_shares = delta_shares - closed_shares
        if synthetic_open_shares <= 1e-9:
            return updated_existing
        if not self._allow_synthetic_complement_on_sell:
            return updated_existing

        complement_token_id = self._complement_by_token.get(tracked.token_id)
        if not complement_token_id:
            if existing is None:
                raise ValueError("Cannot apply sell fill without an existing position")
            raise ValueError("Sell fill exceeds current position size")

        synthetic_open_fees = delta_fees - closed_fees
        complement_price = max(0.0, 1.0 - fill_price)
        synthetic_open_notional = synthetic_open_shares * complement_price
        synthetic_market_id = self._canonical_market_by_token.get(tracked.token_id, tracked.market_id)
        synthetic_tracked = replace(
            tracked,
            market_id=synthetic_market_id,
            token_id=complement_token_id,
            trade_side="BUY",
            limit_price=complement_price,
            requested_shares=synthetic_open_shares,
            requested_notional=synthetic_open_notional,
            matched_shares=synthetic_open_shares,
            matched_notional=synthetic_open_notional,
            fees_paid=synthetic_open_fees,
        )
        return self._apply_buy_fill(
            tracked=synthetic_tracked,
            delta_shares=synthetic_open_shares,
            delta_notional=synthetic_open_notional,
            delta_fees=synthetic_open_fees,
        )

    def _canonicalize_tracked_order(self, tracked: TrackedOrder) -> TrackedOrder:
        canonical_market_id = self._canonical_market_by_token.get(tracked.token_id)
        if not canonical_market_id or canonical_market_id == tracked.market_id:
            return tracked
        return replace(tracked, market_id=canonical_market_id)


def _mark_price_for_token(snapshot: MarketSnapshot, token_id: str) -> float | None:
    if token_id == snapshot.token_id:
        return _yes_mark_price(snapshot)

    no_token_id = snapshot.metadata.get("no_token_id")
    if token_id == no_token_id:
        return _no_mark_price(snapshot)

    return None


def _yes_mark_price(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_yes is not None:
        return snapshot.best_bid_yes
    if snapshot.best_bid_yes is None and snapshot.best_ask_no is not None:
        return _infer_complement_bid(snapshot.best_ask_no)
    if snapshot.best_bid_yes is None and snapshot.best_ask_yes is not None:
        return snapshot.best_ask_yes
    if snapshot.best_bid_yes is None and snapshot.best_ask_yes is None and snapshot.best_bid_no is not None:
        return _infer_complement_ask(snapshot.best_bid_no)
    return snapshot.last_traded_price


def _no_mark_price(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_no is not None:
        return snapshot.best_bid_no
    if snapshot.best_bid_no is None and snapshot.best_ask_yes is not None:
        return _infer_complement_bid(snapshot.best_ask_yes)
    if snapshot.best_bid_no is None and snapshot.best_ask_no is not None:
        return snapshot.best_ask_no
    if snapshot.best_bid_no is None and snapshot.best_ask_no is None and snapshot.best_bid_yes is not None:
        return _infer_complement_ask(snapshot.best_bid_yes)
    if snapshot.last_traded_price is not None:
        return max(0.0, 1.0 - snapshot.last_traded_price)
    return None


def _infer_complement_bid(best_ask: float | None) -> float | None:
    if best_ask is None:
        return None
    return round(1.0 - best_ask, 6)


def _infer_complement_ask(best_bid: float | None) -> float | None:
    if best_bid is None:
        return None
    return round(1.0 - best_bid, 6)
