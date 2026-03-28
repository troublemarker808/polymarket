"""Input builders for Crypto Phase 1 pricing and replay work."""

from __future__ import annotations

from datetime import datetime, timezone
from math import fabs

from pm_bot.strategies.crypto.phase1.models import (
    CryptoMarketDefinition,
    CryptoPricingInputs,
    CryptoUnderlyingState,
    CryptoVolatilityRegime,
)


def build_underlying_state(
    *,
    underlying: str,
    as_of: datetime,
    spot_price: float,
    daily_return: float = 0.0,
    realized_volatility: float = 0.0,
    implied_volatility: float | None = None,
) -> CryptoUnderlyingState:
    return CryptoUnderlyingState(
        underlying=underlying,
        as_of=_normalize_datetime(as_of),
        spot_price=spot_price,
        daily_return=daily_return,
        realized_volatility=realized_volatility,
        implied_volatility=implied_volatility,
    )


def build_volatility_regime(
    *,
    realized_volatility: float,
    implied_volatility: float | None = None,
    jump_risk_score: float | None = None,
) -> CryptoVolatilityRegime:
    sigma_estimate = implied_volatility if implied_volatility is not None else realized_volatility
    clamped_jump_risk = max(0.0, min(jump_risk_score if jump_risk_score is not None else _default_jump_risk(realized_volatility), 1.0))

    if sigma_estimate < 0.35:
        label = "low"
    elif sigma_estimate < 0.75:
        label = "normal"
    else:
        label = "high"

    return CryptoVolatilityRegime(
        label=label,
        sigma_estimate=sigma_estimate,
        jump_risk_score=clamped_jump_risk,
    )


def build_pricing_inputs(
    *,
    market: CryptoMarketDefinition,
    underlying_state: CryptoUnderlyingState,
    volatility_regime: CryptoVolatilityRegime | None = None,
    as_of: datetime | None = None,
) -> CryptoPricingInputs:
    normalized_as_of = _normalize_datetime(as_of or underlying_state.as_of)
    regime = volatility_regime or build_volatility_regime(
        realized_volatility=underlying_state.realized_volatility,
        implied_volatility=underlying_state.implied_volatility,
    )
    distance_to_barrier = market.barrier_price - underlying_state.spot_price
    distance_ratio = fabs(distance_to_barrier) / max(underlying_state.spot_price, 1e-9)
    time_to_expiry_seconds, time_to_expiry_days = compute_time_to_expiry(
        resolution_time=market.normalized.resolution_time,
        as_of=normalized_as_of,
    )
    effective_horizon_days = effective_trading_horizon_days(time_to_expiry_days)
    return CryptoPricingInputs(
        market=market,
        underlying_state=underlying_state,
        volatility_regime=regime,
        distance_to_barrier=distance_to_barrier,
        distance_ratio=distance_ratio,
        time_to_expiry_seconds=time_to_expiry_seconds,
        time_to_expiry_days=time_to_expiry_days,
        effective_horizon_days=effective_horizon_days,
    )


def compute_time_to_expiry(
    *,
    resolution_time: datetime | None,
    as_of: datetime,
) -> tuple[float, float]:
    normalized_as_of = _normalize_datetime(as_of)
    if resolution_time is None:
        return (0.0, 0.0)
    normalized_resolution = _normalize_datetime(resolution_time)
    seconds = max((normalized_resolution - normalized_as_of).total_seconds(), 0.0)
    return (seconds, seconds / 86400.0)


def effective_trading_horizon_days(time_to_expiry_days: float) -> float:
    if time_to_expiry_days <= 0:
        return 0.0
    if time_to_expiry_days <= 7:
        return time_to_expiry_days
    if time_to_expiry_days <= 30:
        return max(7.0, time_to_expiry_days * 0.8)
    return max(14.0, time_to_expiry_days * 0.65)


def _default_jump_risk(realized_volatility: float) -> float:
    if realized_volatility < 0.35:
        return 0.15
    if realized_volatility < 0.75:
        return 0.35
    return 0.6


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
