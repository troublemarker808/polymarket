"""Portfolio exposure helpers for paper and live runtime state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from pm_bot.core.types import Category
from pm_bot.runtime.state import DashboardState, PendingOrderState, PositionState


@dataclass(slots=True, frozen=True)
class MarketExposure:
    market_id: str
    category: Category
    open_notional: float
    pending_notional: float

    @property
    def gross_notional(self) -> float:
        return self.open_notional + self.pending_notional


@dataclass(slots=True, frozen=True)
class CategoryExposure:
    category: Category
    open_notional: float
    pending_notional: float
    market_count: int

    @property
    def gross_notional(self) -> float:
        return self.open_notional + self.pending_notional


@dataclass(slots=True, frozen=True)
class PortfolioState:
    total_open_notional: float
    total_pending_notional: float
    by_category: tuple[CategoryExposure, ...]
    by_market: tuple[MarketExposure, ...]

    @property
    def total_gross_notional(self) -> float:
        return self.total_open_notional + self.total_pending_notional


def build_portfolio_state(
    *,
    open_positions: Sequence[PositionState],
    pending_orders: Sequence[PendingOrderState],
) -> PortfolioState:
    market_open_notional: dict[tuple[Category, str], float] = defaultdict(float)
    market_pending_notional: dict[tuple[Category, str], float] = defaultdict(float)

    for position in open_positions:
        market_open_notional[(position.category, position.market_id)] += position.notional

    for order in pending_orders:
        market_pending_notional[(order.category, order.market_id)] += order.requested_notional

    market_keys = sorted(
        set(market_open_notional).union(market_pending_notional),
        key=lambda item: (item[0].value, item[1]),
    )
    market_exposures = tuple(
        MarketExposure(
            market_id=market_id,
            category=category,
            open_notional=market_open_notional.get((category, market_id), 0.0),
            pending_notional=market_pending_notional.get((category, market_id), 0.0),
        )
        for category, market_id in market_keys
    )

    category_open_notional: dict[Category, float] = defaultdict(float)
    category_pending_notional: dict[Category, float] = defaultdict(float)
    category_market_ids: dict[Category, set[str]] = defaultdict(set)
    for exposure in market_exposures:
        category_open_notional[exposure.category] += exposure.open_notional
        category_pending_notional[exposure.category] += exposure.pending_notional
        category_market_ids[exposure.category].add(exposure.market_id)

    category_exposures = tuple(
        CategoryExposure(
            category=category,
            open_notional=category_open_notional[category],
            pending_notional=category_pending_notional[category],
            market_count=len(category_market_ids[category]),
        )
        for category in sorted(category_market_ids, key=lambda item: item.value)
    )

    return PortfolioState(
        total_open_notional=sum(exposure.open_notional for exposure in market_exposures),
        total_pending_notional=sum(exposure.pending_notional for exposure in market_exposures),
        by_category=category_exposures,
        by_market=market_exposures,
    )


def portfolio_state_from_dashboard(dashboard: DashboardState) -> PortfolioState:
    return build_portfolio_state(
        open_positions=dashboard.open_positions,
        pending_orders=dashboard.pending_orders,
    )
