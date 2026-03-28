"""Pricing helpers for Weather Phase 1 threshold research."""

from __future__ import annotations

from collections.abc import Sequence
from math import erf, sqrt

from pm_bot.strategies.weather.phase1.models import (
    BiasCorrectedForecast,
    WeatherForecastDistribution,
    WeatherMarketDefinition,
    WeatherStripEstimate,
    WeatherThresholdEstimate,
)


def build_forecast_distribution(
    *,
    market: WeatherMarketDefinition,
    corrected_forecasts: Sequence[BiasCorrectedForecast],
) -> WeatherForecastDistribution | None:
    relevant = [
        forecast
        for forecast in corrected_forecasts
        if forecast.forecast_run.station_id == market.location.station_id
    ]
    if not relevant:
        return None

    total_weight = sum(forecast.skill_weight for forecast in relevant)
    if total_weight <= 0:
        return None

    weighted_mean = sum(
        forecast.corrected_high_temp_f * forecast.skill_weight for forecast in relevant
    ) / total_weight
    weighted_second_moment = sum(
        ((forecast.corrected_sigma_f ** 2) + ((forecast.corrected_high_temp_f - weighted_mean) ** 2))
        * forecast.skill_weight
        for forecast in relevant
    ) / total_weight
    weighted_sigma = max(0.5, weighted_second_moment ** 0.5)

    return WeatherForecastDistribution(
        market_id=market.normalized.market_id,
        weighted_mean_temp_f=weighted_mean,
        weighted_sigma_f=weighted_sigma,
        contributing_models=tuple(forecast.forecast_run.model_name for forecast in relevant),
        total_weight=total_weight,
    )


def estimate_threshold_probability(
    *,
    market: WeatherMarketDefinition,
    distribution: WeatherForecastDistribution,
) -> WeatherThresholdEstimate:
    sigma = max(distribution.weighted_sigma_f, 1e-6)
    z_score = (market.threshold - distribution.weighted_mean_temp_f) / sigma
    cdf = 0.5 * (1.0 + erf(z_score / sqrt(2.0)))
    if market.comparator == "above":
        fair_probability = 1.0 - cdf
    else:
        fair_probability = cdf
    fair_probability = max(0.01, min(0.99, fair_probability))
    return WeatherThresholdEstimate(
        fair_probability=fair_probability,
        implied_z_score=z_score,
        weighted_mean_temp_f=distribution.weighted_mean_temp_f,
        weighted_sigma_f=distribution.weighted_sigma_f,
    )


def estimate_strip_consistency(
    *,
    series_key: str,
    market: WeatherMarketDefinition,
    observed_probability: float,
    peer_probabilities: dict[str, float],
    ordered_markets: Sequence[WeatherMarketDefinition],
) -> WeatherStripEstimate:
    current_index = next(
        (idx for idx, item in enumerate(ordered_markets) if item.normalized.market_id == market.normalized.market_id),
        None,
    )
    if current_index is None:
        return WeatherStripEstimate(
            series_key=series_key,
            local_lower_bound=None,
            local_upper_bound=None,
            fair_probability=observed_probability,
            monotonicity_gap_bps=0.0,
        )

    previous = [
        peer_probabilities[item.normalized.market_id]
        for item in ordered_markets[:current_index]
        if item.normalized.market_id in peer_probabilities
    ]
    following = [
        peer_probabilities[item.normalized.market_id]
        for item in ordered_markets[current_index + 1 :]
        if item.normalized.market_id in peer_probabilities
    ]

    if market.comparator == "above":
        lower_bound = following[0] if following else None
        upper_bound = previous[-1] if previous else None
    else:
        lower_bound = previous[-1] if previous else None
        upper_bound = following[0] if following else None

    fair_probability = _project_probability(
        observed_probability=observed_probability,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )
    return WeatherStripEstimate(
        series_key=series_key,
        local_lower_bound=lower_bound,
        local_upper_bound=upper_bound,
        fair_probability=fair_probability,
        monotonicity_gap_bps=round(abs(fair_probability - observed_probability) * 10000, 6),
    )


def build_weather_peer_probability_map(
    *,
    markets: Sequence[WeatherMarketDefinition],
    snapshots: Sequence[tuple[WeatherMarketDefinition, float]],
) -> dict[str, float]:
    allowed_market_ids = {market.normalized.market_id for market in markets}
    return {
        market.normalized.market_id: probability
        for market, probability in snapshots
        if market.normalized.market_id in allowed_market_ids
    }


def _project_probability(
    *,
    observed_probability: float,
    lower_bound: float | None,
    upper_bound: float | None,
) -> float:
    if lower_bound is not None and upper_bound is not None and lower_bound > upper_bound:
        midpoint = (lower_bound + upper_bound) / 2
        return max(0.01, min(0.99, midpoint))
    if lower_bound is not None and observed_probability < lower_bound:
        return lower_bound
    if upper_bound is not None and observed_probability > upper_bound:
        return upper_bound
    return observed_probability
