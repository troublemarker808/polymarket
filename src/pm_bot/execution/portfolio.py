"""Portfolio exposure helpers for paper and live runtime state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from pm_bot.core.settings import TradingSettings
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
class ExposureGroupExposure:
    exposure_group_id: str
    category: Category
    open_notional: float
    pending_notional: float
    market_count: int

    @property
    def gross_notional(self) -> float:
        return self.open_notional + self.pending_notional


@dataclass(slots=True, frozen=True)
class ThesisGroupExposure:
    thesis_group_id: str
    category: Category
    open_notional: float
    pending_notional: float
    market_count: int

    @property
    def gross_notional(self) -> float:
        return self.open_notional + self.pending_notional


@dataclass(slots=True, frozen=True)
class UnderlyingGroupExposure:
    underlying_group_id: str
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
    by_exposure_group: tuple[ExposureGroupExposure, ...]
    by_thesis_group: tuple[ThesisGroupExposure, ...]
    by_underlying_group: tuple[UnderlyingGroupExposure, ...]
    by_market: tuple[MarketExposure, ...]

    @property
    def total_gross_notional(self) -> float:
        return self.total_open_notional + self.total_pending_notional


@dataclass(slots=True, frozen=True)
class CapUtilization:
    used_notional: float
    cap_notional: float

    @property
    def remaining_notional(self) -> float:
        return max(0.0, self.cap_notional - self.used_notional)

    @property
    def utilization_ratio(self) -> float:
        if self.cap_notional <= 0:
            return 0.0
        return self.used_notional / self.cap_notional


@dataclass(slots=True, frozen=True)
class CategoryCapUtilization:
    category: Category
    used_notional: float
    cap_notional: float
    market_count: int

    @property
    def remaining_notional(self) -> float:
        return max(0.0, self.cap_notional - self.used_notional)

    @property
    def utilization_ratio(self) -> float:
        if self.cap_notional <= 0:
            return 0.0
        return self.used_notional / self.cap_notional


@dataclass(slots=True, frozen=True)
class ExposureGroupCapUtilization:
    exposure_group_id: str
    category: Category
    used_notional: float
    cap_notional: float
    market_count: int

    @property
    def remaining_notional(self) -> float:
        return max(0.0, self.cap_notional - self.used_notional)

    @property
    def utilization_ratio(self) -> float:
        if self.cap_notional <= 0:
            return 0.0
        return self.used_notional / self.cap_notional


@dataclass(slots=True, frozen=True)
class PortfolioCapUtilization:
    total_gross: CapUtilization
    by_category: tuple[CategoryCapUtilization, ...]
    by_exposure_group: tuple[ExposureGroupCapUtilization, ...]
    by_thesis_group: tuple[ExposureGroupCapUtilization, ...]
    by_underlying_group: tuple[ExposureGroupCapUtilization, ...]


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

    group_open_notional: dict[tuple[Category, str], float] = defaultdict(float)
    group_pending_notional: dict[tuple[Category, str], float] = defaultdict(float)
    group_market_ids: dict[tuple[Category, str], set[str]] = defaultdict(set)

    for position in open_positions:
        exposure_group_id = _normalized_exposure_group_id(position.exposure_group_id, position.market_id)
        group_key = (position.category, exposure_group_id)
        group_open_notional[group_key] += position.notional
        group_market_ids[group_key].add(position.market_id)

    for order in pending_orders:
        exposure_group_id = _normalized_exposure_group_id(order.exposure_group_id, order.market_id)
        group_key = (order.category, exposure_group_id)
        group_pending_notional[group_key] += order.requested_notional
        group_market_ids[group_key].add(order.market_id)

    group_keys = sorted(
        set(group_open_notional).union(group_pending_notional),
        key=lambda item: (-(group_open_notional.get(item, 0.0) + group_pending_notional.get(item, 0.0)), item[0].value, item[1]),
    )
    exposure_group_exposures = tuple(
        ExposureGroupExposure(
            exposure_group_id=exposure_group_id,
            category=category,
            open_notional=group_open_notional.get((category, exposure_group_id), 0.0),
            pending_notional=group_pending_notional.get((category, exposure_group_id), 0.0),
            market_count=len(group_market_ids[(category, exposure_group_id)]),
        )
        for category, exposure_group_id in group_keys
    )

    thesis_open_notional: dict[tuple[Category, str], float] = defaultdict(float)
    thesis_pending_notional: dict[tuple[Category, str], float] = defaultdict(float)
    thesis_market_ids: dict[tuple[Category, str], set[str]] = defaultdict(set)
    for position in open_positions:
        thesis_group_id = _normalized_optional_group_id(position.thesis_group_id)
        if thesis_group_id is None:
            continue
        group_key = (position.category, thesis_group_id)
        thesis_open_notional[group_key] += position.notional
        thesis_market_ids[group_key].add(position.market_id)
    for order in pending_orders:
        thesis_group_id = _normalized_optional_group_id(order.thesis_group_id)
        if thesis_group_id is None:
            continue
        group_key = (order.category, thesis_group_id)
        thesis_pending_notional[group_key] += order.requested_notional
        thesis_market_ids[group_key].add(order.market_id)
    thesis_group_exposures = tuple(
        ThesisGroupExposure(
            thesis_group_id=thesis_group_id,
            category=category,
            open_notional=thesis_open_notional.get((category, thesis_group_id), 0.0),
            pending_notional=thesis_pending_notional.get((category, thesis_group_id), 0.0),
            market_count=len(thesis_market_ids[(category, thesis_group_id)]),
        )
        for category, thesis_group_id in sorted(
            set(thesis_open_notional).union(thesis_pending_notional),
            key=lambda item: (-(thesis_open_notional.get(item, 0.0) + thesis_pending_notional.get(item, 0.0)), item[0].value, item[1]),
        )
    )

    underlying_open_notional: dict[tuple[Category, str], float] = defaultdict(float)
    underlying_pending_notional: dict[tuple[Category, str], float] = defaultdict(float)
    underlying_market_ids: dict[tuple[Category, str], set[str]] = defaultdict(set)
    for position in open_positions:
        underlying_group_id = _normalized_optional_group_id(position.underlying_group_id)
        if underlying_group_id is None:
            continue
        group_key = (position.category, underlying_group_id)
        underlying_open_notional[group_key] += position.notional
        underlying_market_ids[group_key].add(position.market_id)
    for order in pending_orders:
        underlying_group_id = _normalized_optional_group_id(order.underlying_group_id)
        if underlying_group_id is None:
            continue
        group_key = (order.category, underlying_group_id)
        underlying_pending_notional[group_key] += order.requested_notional
        underlying_market_ids[group_key].add(order.market_id)
    underlying_group_exposures = tuple(
        UnderlyingGroupExposure(
            underlying_group_id=underlying_group_id,
            category=category,
            open_notional=underlying_open_notional.get((category, underlying_group_id), 0.0),
            pending_notional=underlying_pending_notional.get((category, underlying_group_id), 0.0),
            market_count=len(underlying_market_ids[(category, underlying_group_id)]),
        )
        for category, underlying_group_id in sorted(
            set(underlying_open_notional).union(underlying_pending_notional),
            key=lambda item: (-(underlying_open_notional.get(item, 0.0) + underlying_pending_notional.get(item, 0.0)), item[0].value, item[1]),
        )
    )

    return PortfolioState(
        total_open_notional=sum(exposure.open_notional for exposure in market_exposures),
        total_pending_notional=sum(exposure.pending_notional for exposure in market_exposures),
        by_category=category_exposures,
        by_exposure_group=exposure_group_exposures,
        by_thesis_group=thesis_group_exposures,
        by_underlying_group=underlying_group_exposures,
        by_market=market_exposures,
    )


def portfolio_state_from_dashboard(dashboard: DashboardState) -> PortfolioState:
    return build_portfolio_state(
        open_positions=dashboard.open_positions,
        pending_orders=dashboard.pending_orders,
    )


def build_portfolio_cap_utilization(
    *,
    portfolio: PortfolioState,
    trading_settings: TradingSettings,
) -> PortfolioCapUtilization:
    category_cap = trading_settings.max_notional_per_category
    group_cap = trading_settings.max_notional_per_exposure_group
    total_cap = trading_settings.max_total_gross_notional
    return PortfolioCapUtilization(
        total_gross=CapUtilization(
            used_notional=portfolio.total_gross_notional,
            cap_notional=total_cap,
        ),
        by_category=tuple(
            CategoryCapUtilization(
                category=exposure.category,
                used_notional=exposure.gross_notional,
                cap_notional=category_cap,
                market_count=exposure.market_count,
            )
            for exposure in sorted(
                portfolio.by_category,
                key=lambda item: (-item.gross_notional, item.category.value),
            )
        ),
        by_exposure_group=tuple(
            ExposureGroupCapUtilization(
                exposure_group_id=exposure.exposure_group_id,
                category=exposure.category,
                used_notional=exposure.gross_notional,
                cap_notional=group_cap,
                market_count=exposure.market_count,
            )
            for exposure in portfolio.by_exposure_group
        ),
        by_thesis_group=tuple(
            ExposureGroupCapUtilization(
                exposure_group_id=exposure.thesis_group_id,
                category=exposure.category,
                used_notional=exposure.gross_notional,
                cap_notional=trading_settings.max_notional_per_thesis_group,
                market_count=exposure.market_count,
            )
            for exposure in portfolio.by_thesis_group
        ),
        by_underlying_group=tuple(
            ExposureGroupCapUtilization(
                exposure_group_id=exposure.underlying_group_id,
                category=exposure.category,
                used_notional=exposure.gross_notional,
                cap_notional=trading_settings.max_notional_per_underlying_group,
                market_count=exposure.market_count,
            )
            for exposure in portfolio.by_underlying_group
        ),
    )


def _normalized_exposure_group_id(exposure_group_id: str | None, market_id: str) -> str:
    normalized = str(exposure_group_id or market_id).strip()
    return normalized or market_id


def _normalized_optional_group_id(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None
