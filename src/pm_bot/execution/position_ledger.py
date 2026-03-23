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

    def __init__(self) -> None:
        self._positions: dict[tuple[str, str], LivePosition] = {}
        self._applied_progress: dict[str, AppliedOrderProgress] = {}
        self._closed_trades: list[ClosedTrade] = []

    def apply_tracked_order(self, tracked: TrackedOrder) -> LivePosition | None:
        """Apply the incremental fill delta from a tracked order."""

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

        snapshots_by_market = {snapshot.market_id: snapshot for snapshot in snapshots}
        updated_positions: list[LivePosition] = []

        for key, position in list(self._positions.items()):
            snapshot = snapshots_by_market.get(position.market_id)
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
        if existing is None:
            raise ValueError("Cannot apply sell fill without an existing position")
        if delta_shares - existing.shares > 1e-9:
            raise ValueError("Sell fill exceeds current position size")

        average_cost = existing.cost_basis / existing.shares if existing.shares > 0 else 0.0
        relieved_cost_basis = average_cost * delta_shares
        realized_pnl = delta_notional - relieved_cost_basis
        self._closed_trades.append(
            ClosedTrade(
                market_id=tracked.market_id,
                token_id=tracked.token_id,
                category=tracked.category,
                strategy_id=tracked.strategy_id,
                realized_pnl=realized_pnl,
                fees_paid=delta_fees,
                closed_at=tracked.updated_at,
            )
        )

        remaining_shares = existing.shares - delta_shares
        remaining_cost_basis = existing.cost_basis - relieved_cost_basis
        if remaining_shares <= 1e-9:
            self._positions.pop(key, None)
            return None

        updated = replace(
            existing,
            shares=remaining_shares,
            cost_basis=max(remaining_cost_basis, 0.0),
            average_entry_price=max(remaining_cost_basis, 0.0) / remaining_shares,
            total_fees=existing.total_fees + delta_fees,
            updated_at=tracked.updated_at,
        )
        self._positions[key] = updated
        return updated


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
    if snapshot.best_bid_yes is None and snapshot.best_ask_yes is not None:
        return snapshot.best_ask_yes
    return snapshot.last_traded_price


def _no_mark_price(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_no is not None:
        return snapshot.best_bid_no
    if snapshot.best_bid_no is None and snapshot.best_ask_no is not None:
        return snapshot.best_ask_no
    return None
