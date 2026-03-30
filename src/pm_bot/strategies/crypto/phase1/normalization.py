"""Normalization helpers for supported crypto Phase 1 market families."""

from __future__ import annotations

from datetime import datetime
import re

from pm_bot.core.research_types import NormalizedMarketDefinition
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.strategies.crypto.phase1.models import CryptoMarketDefinition

_DOWNWARD_TOKENS = ("dip", "drop", "fall", "below", "under")
_UPWARD_TOKENS = ("reach", "hit", "above", "over")
_PRICE_PATTERN = re.compile(
    r"(?:dip\s+to|drop\s+to|fall\s+to|reach(?:es)?|hit(?:s)?|above|below|under|over|to)\s*\$?([0-9][0-9,]*(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
_UNSUPPORTED_DERIVED_MARKET_PATTERNS = (
    "volatility index",
    "realized volatility",
    "dominance",
    "kimchi premium",
)


def classify_crypto_market(snapshot: MarketSnapshot) -> str | None:
    normalized = normalize_crypto_market(snapshot)
    if normalized is None:
        return None
    return normalized.normalized.market_family


def normalize_crypto_market(snapshot: MarketSnapshot) -> CryptoMarketDefinition | None:
    if snapshot.category != Category.CRYPTO:
        return None

    combined = _combined_text(snapshot)
    if _is_unsupported_derived_crypto_market(combined):
        return None
    underlying = _parse_underlying(combined)
    if underlying is None:
        return None

    direction = _parse_direction(combined)
    if direction is None:
        return None

    barrier_price = _parse_barrier_price(combined)
    if barrier_price is None:
        return None

    event_family = "dip" if direction == "down" else "reach"
    scope_key = _scope_key(
        underlying=underlying,
        event_family=event_family,
        resolution_time=snapshot.resolution_time,
    )
    instrument_key = f"{scope_key}:{_format_barrier_price(barrier_price)}"
    series_key = snapshot.metadata.get("event_slug") or scope_key
    normalized = NormalizedMarketDefinition(
        market_id=snapshot.market_id,
        category=Category.CRYPTO,
        market_family="price_ladder_barrier",
        scope_key=scope_key,
        instrument_key=instrument_key,
        resolution_time=snapshot.resolution_time,
        attributes={
            "underlying": underlying,
            "event_family": event_family,
            "direction": direction,
            "barrier_price": barrier_price,
            "series_key": series_key,
        },
    )
    return CryptoMarketDefinition(
        normalized=normalized,
        underlying=underlying,
        event_family=event_family,
        direction=direction,
        barrier_price=barrier_price,
        series_key=series_key,
    )


def _combined_text(snapshot: MarketSnapshot) -> str:
    return " ".join(
        (
            snapshot.metadata.get("question", ""),
            snapshot.slug,
            snapshot.metadata.get("event_title", ""),
        )
    ).lower()


def _parse_underlying(combined: str) -> str | None:
    if "bitcoin" in combined or "btc" in combined:
        return "BTC"
    if "ethereum" in combined or "eth" in combined:
        return "ETH"
    return None


def _parse_direction(combined: str) -> str | None:
    if any(token in combined for token in _DOWNWARD_TOKENS):
        return "down"
    if any(token in combined for token in _UPWARD_TOKENS):
        return "up"
    return None


def _parse_barrier_price(combined: str) -> float | None:
    match = _PRICE_PATTERN.search(combined)
    if match is None:
        return None
    return float(match.group(1).replace(",", ""))


def _is_unsupported_derived_crypto_market(combined: str) -> bool:
    return any(pattern in combined for pattern in _UNSUPPORTED_DERIVED_MARKET_PATTERNS)


def _scope_key(
    *,
    underlying: str,
    event_family: str,
    resolution_time: datetime | None,
) -> str:
    expiry_key = resolution_time.date().isoformat() if resolution_time is not None else "open"
    return f"{underlying}:{event_family}:{expiry_key}"


def _format_barrier_price(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
