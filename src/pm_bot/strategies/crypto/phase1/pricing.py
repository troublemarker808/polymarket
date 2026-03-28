"""Pricing helpers for Crypto Phase 1 ladder research."""

from __future__ import annotations

from collections.abc import Sequence
from math import exp

from pm_bot.strategies.crypto.phase1.models import (
    CryptoBarrierEstimate,
    CryptoBarrierModelConfig,
    CryptoLadderSeries,
    CryptoMarketDefinition,
    CryptoPricingInputs,
    CryptoSurfaceEstimate,
)


def estimate_barrier_probability(
    inputs: CryptoPricingInputs,
    model_config: CryptoBarrierModelConfig | None = None,
) -> CryptoBarrierEstimate:
    config = model_config or CryptoBarrierModelConfig()
    direction_sign = -1.0 if inputs.market.direction == "down" else 1.0
    signed_distance_ratio = (inputs.distance_to_barrier / max(inputs.underlying_state.spot_price, 1e-9)) * direction_sign
    sigma = max(inputs.volatility_regime.sigma_estimate, 1e-6)
    time_scale = max(inputs.effective_horizon_days / 365.0, 1e-6)
    volatility_scale = sigma * (time_scale ** 0.5)
    distance_score = signed_distance_ratio / max(volatility_scale, 1e-6)
    fair_probability = 1.0 / (1.0 + exp(config.steepness * distance_score))
    fair_probability = max(config.probability_floor, min(config.probability_ceiling, fair_probability))
    return CryptoBarrierEstimate(
        fair_probability=fair_probability,
        distance_score=distance_score,
        volatility_scale=volatility_scale,
        time_scale=time_scale,
    )


def estimate_surface_consistency(
    *,
    series: CryptoLadderSeries,
    market: CryptoMarketDefinition,
    observed_probability: float,
    peer_probabilities: dict[str, float],
) -> CryptoSurfaceEstimate:
    ordered = series.markets
    current_index = next((idx for idx, item in enumerate(ordered) if item.normalized.market_id == market.normalized.market_id), None)
    if current_index is None:
        return CryptoSurfaceEstimate(
            series_key=series.series_key,
            local_lower_bound=None,
            local_upper_bound=None,
            fair_probability=observed_probability,
            mispricing_bps=0.0,
            monotonicity_gap_bps=0.0,
        )

    previous = [peer_probabilities[item.normalized.market_id] for item in ordered[:current_index] if item.normalized.market_id in peer_probabilities]
    following = [peer_probabilities[item.normalized.market_id] for item in ordered[current_index + 1 :] if item.normalized.market_id in peer_probabilities]

    if market.direction == "down":
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
    monotonicity_gap_bps = abs(fair_probability - observed_probability) * 10000
    return CryptoSurfaceEstimate(
        series_key=series.series_key,
        local_lower_bound=lower_bound,
        local_upper_bound=upper_bound,
        fair_probability=fair_probability,
        mispricing_bps=(fair_probability - observed_probability) * 10000,
        monotonicity_gap_bps=monotonicity_gap_bps,
    )


def observed_mid_probability(best_bid_yes: float | None, best_ask_yes: float | None, last_traded_price: float | None = None) -> float | None:
    if best_bid_yes is not None and best_ask_yes is not None:
        return (best_bid_yes + best_ask_yes) / 2
    if last_traded_price is not None:
        return last_traded_price
    if best_ask_yes is not None:
        return best_ask_yes
    if best_bid_yes is not None:
        return best_bid_yes
    return None


def build_peer_probability_map(
    *,
    series: CryptoLadderSeries,
    snapshots: Sequence[tuple[CryptoMarketDefinition, float]],
) -> dict[str, float]:
    allowed_market_ids = {market.normalized.market_id for market in series.markets}
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
