"""Crypto Phase 1 board-specific dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pm_bot.core.research_types import NormalizedMarketDefinition


@dataclass(slots=True, frozen=True)
class CryptoMarketDefinition:
    normalized: NormalizedMarketDefinition
    underlying: str
    event_family: str
    direction: str
    barrier_price: float
    series_key: str


@dataclass(slots=True, frozen=True)
class CryptoLadderSeries:
    series_key: str
    underlying: str
    event_family: str
    direction: str
    markets: tuple[CryptoMarketDefinition, ...]


@dataclass(slots=True, frozen=True)
class CryptoUnderlyingState:
    underlying: str
    as_of: datetime
    spot_price: float
    daily_return: float = 0.0
    realized_volatility: float = 0.0
    implied_volatility: float | None = None


@dataclass(slots=True, frozen=True)
class CryptoVolatilityRegime:
    label: str
    sigma_estimate: float
    jump_risk_score: float


@dataclass(slots=True, frozen=True)
class CryptoPricingInputs:
    market: CryptoMarketDefinition
    underlying_state: CryptoUnderlyingState
    volatility_regime: CryptoVolatilityRegime
    distance_to_barrier: float
    distance_ratio: float
    time_to_expiry_seconds: float
    time_to_expiry_days: float
    effective_horizon_days: float


@dataclass(slots=True, frozen=True)
class CryptoBarrierEstimate:
    fair_probability: float
    distance_score: float
    volatility_scale: float
    time_scale: float


@dataclass(slots=True, frozen=True)
class CryptoBarrierModelConfig:
    steepness: float = 2.4
    probability_floor: float = 0.01
    probability_ceiling: float = 0.99


@dataclass(slots=True, frozen=True)
class CryptoSurfaceEstimate:
    series_key: str
    local_lower_bound: float | None
    local_upper_bound: float | None
    fair_probability: float
    mispricing_bps: float
    monotonicity_gap_bps: float


@dataclass(slots=True, frozen=True)
class CryptoFusedFairValue:
    fair_probability: float
    confidence: float
    half_life_seconds: int
    barrier_probability: float
    surface_probability: float | None
    rationale_tags: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoFusionModelConfig:
    barrier_weight: float = 0.65
    surface_weight: float = 0.35
    probability_floor: float = 0.01
    probability_ceiling: float = 0.99
