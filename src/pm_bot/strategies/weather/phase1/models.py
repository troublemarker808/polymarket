"""Weather Phase 1 board-specific dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pm_bot.core.research_types import NormalizedMarketDefinition


@dataclass(slots=True, frozen=True)
class WeatherLocationDefinition:
    city: str
    region: str
    country: str
    station_id: str
    settlement_source: str


@dataclass(slots=True, frozen=True)
class WeatherMarketDefinition:
    normalized: NormalizedMarketDefinition
    event_family: str
    threshold: float
    comparator: str
    event_date: datetime
    location: WeatherLocationDefinition
    series_key: str


@dataclass(slots=True, frozen=True)
class WeatherForecastRun:
    model_name: str
    station_id: str
    issued_at: datetime
    target_date: datetime
    horizon_hours: float
    predicted_high_temp_f: float
    distribution_sigma_f: float
    metadata: dict[str, float | str]


@dataclass(slots=True, frozen=True)
class WeatherModelSkill:
    model_name: str
    station_id: str
    horizon_bucket_hours: int
    mean_bias_f: float
    mae_f: float
    skill_score: float


@dataclass(slots=True, frozen=True)
class BiasCorrectedForecast:
    forecast_run: WeatherForecastRun
    bias_adjustment_f: float
    corrected_high_temp_f: float
    corrected_sigma_f: float
    skill_weight: float


@dataclass(slots=True, frozen=True)
class WeatherForecastDistribution:
    market_id: str
    weighted_mean_temp_f: float
    weighted_sigma_f: float
    contributing_models: tuple[str, ...]
    total_weight: float


@dataclass(slots=True, frozen=True)
class WeatherThresholdEstimate:
    fair_probability: float
    implied_z_score: float
    weighted_mean_temp_f: float
    weighted_sigma_f: float


@dataclass(slots=True, frozen=True)
class WeatherStripEstimate:
    series_key: str
    local_lower_bound: float | None
    local_upper_bound: float | None
    fair_probability: float
    monotonicity_gap_bps: float


@dataclass(slots=True, frozen=True)
class WeatherFusedFairValue:
    fair_probability: float
    confidence: float
    half_life_seconds: int
    threshold_probability: float
    strip_probability: float | None
    rationale_tags: tuple[str, ...]
