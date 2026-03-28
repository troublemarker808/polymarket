"""Sports Phase 1 board-specific dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pm_bot.core.research_types import NormalizedMarketDefinition


@dataclass(slots=True, frozen=True)
class SportsEventDefinition:
    normalized: NormalizedMarketDefinition
    league: str
    market_family: str
    home_team: str
    away_team: str
    start_time: datetime
    event_key: str


@dataclass(slots=True, frozen=True)
class SportsEventGroup:
    event_key: str
    league: str
    market_family: str
    start_time: datetime
    markets: tuple[SportsEventDefinition, ...]


@dataclass(slots=True, frozen=True)
class SportsPregameFeatures:
    event: SportsEventDefinition
    observed_probability: float
    start_time: datetime
    minutes_to_start: float
    anchor_probability: float | None
    public_probability: float | None
    injury_adjustment_bps: float
    lineup_adjustment_bps: float
    travel_adjustment_bps: float
    rest_adjustment_bps: float
    feature_values: dict[str, float | str]


@dataclass(slots=True, frozen=True)
class SportsAnchorEstimate:
    anchor_probability: float
    source: str


@dataclass(slots=True, frozen=True)
class SportsAdjustmentEstimate:
    total_adjustment_bps: float
    injury_adjustment_bps: float
    lineup_adjustment_bps: float
    travel_adjustment_bps: float
    rest_adjustment_bps: float


@dataclass(slots=True, frozen=True)
class SportsFairValue:
    fair_probability: float
    confidence: float
    model_adjustment_bps: float
    anchor_probability: float
    rationale_tags: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class SportsDislocationEstimate:
    observed_probability: float
    fair_probability: float
    raw_edge_bps: float
    context_adjusted_edge_bps: float


@dataclass(slots=True, frozen=True)
class SportsClosingLineReview:
    market_id: str
    open_probability: float
    fair_probability: float
    close_probability: float
    clv_bps: float
    moved_toward_fair: bool
