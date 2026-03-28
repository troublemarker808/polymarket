"""Fusion helpers for Weather Phase 1 fair-value estimation."""

from __future__ import annotations

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.weather.phase1.models import (
    WeatherFusedFairValue,
    WeatherForecastDistribution,
    WeatherMarketDefinition,
    WeatherStripEstimate,
    WeatherThresholdEstimate,
)


def fuse_weather_fair_value(
    *,
    market: WeatherMarketDefinition,
    distribution: WeatherForecastDistribution,
    threshold_estimate: WeatherThresholdEstimate,
    strip_estimate: WeatherStripEstimate | None = None,
    observed_probability: float | None = None,
) -> WeatherFusedFairValue:
    if strip_estimate is None:
        fair_probability = threshold_estimate.fair_probability
        strip_probability = None
        rationale_tags = ("forecast_distribution", "threshold_probability")
        confidence = _confidence_from_distribution(distribution=distribution, has_strip=False)
    else:
        fair_probability = (threshold_estimate.fair_probability * 0.7) + (strip_estimate.fair_probability * 0.3)
        strip_probability = strip_estimate.fair_probability
        rationale_tags = ("forecast_distribution", "threshold_probability", "strip_consistency")
        confidence = _confidence_from_distribution(distribution=distribution, has_strip=True)

    fair_probability = max(0.01, min(0.99, fair_probability))
    return WeatherFusedFairValue(
        fair_probability=fair_probability,
        confidence=confidence,
        half_life_seconds=_half_life_seconds(
            market=market,
            observed_probability=observed_probability,
            fair_probability=fair_probability,
        ),
        threshold_probability=threshold_estimate.fair_probability,
        strip_probability=strip_probability,
        rationale_tags=rationale_tags,
    )


def to_fair_value_estimate(
    *,
    market: WeatherMarketDefinition,
    fused: WeatherFusedFairValue,
    distribution: WeatherForecastDistribution,
    observed_probability: float | None = None,
) -> FairValueEstimate:
    return FairValueEstimate(
        market_id=market.normalized.market_id,
        category=Category.WEATHER,
        fair_probability=fused.fair_probability,
        confidence=fused.confidence,
        half_life_seconds=fused.half_life_seconds,
        observed_probability=observed_probability,
        model_id="weather.phase1.fused",
        rationale_tags=fused.rationale_tags,
        supporting_values={
            "threshold": market.threshold,
            "comparator": market.comparator,
            "weighted_mean_temp_f": distribution.weighted_mean_temp_f,
            "weighted_sigma_f": distribution.weighted_sigma_f,
            "threshold_probability": fused.threshold_probability,
            "strip_probability": fused.strip_probability,
        },
    )


def _confidence_from_distribution(
    *,
    distribution: WeatherForecastDistribution,
    has_strip: bool,
) -> float:
    base = 0.58
    if len(distribution.contributing_models) >= 2:
        base += 0.08
    if distribution.weighted_sigma_f <= 3.0:
        base += 0.06
    elif distribution.weighted_sigma_f >= 5.0:
        base -= 0.04
    if has_strip:
        base += 0.05
    return max(0.5, min(0.85, base))


def _half_life_seconds(
    *,
    market: WeatherMarketDefinition,
    observed_probability: float | None,
    fair_probability: float,
) -> int:
    probability_gap = abs((observed_probability if observed_probability is not None else fair_probability) - fair_probability)
    if probability_gap >= 0.04:
        return 2 * 3600
    if market.normalized.resolution_time is not None:
        return 6 * 3600
    return 12 * 3600
