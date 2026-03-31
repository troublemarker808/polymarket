"""Helpers for deriving portfolio concentration keys from market metadata."""

from __future__ import annotations

from dataclasses import dataclass
import re

from pm_bot.core.types import MarketSnapshot, SignalSide

_DOWNWARD_TOKENS = ("dip", "drop", "fall", "below", "under")
_UPWARD_TOKENS = ("reach", "hit", "above", "over")
_PRICE_PATTERN = re.compile(
    r"(?:dip\s+to|drop\s+to|fall\s+to|reach(?:es)?|hit(?:s)?|above|below|under|over|to)\s*\$?([0-9][0-9,]*(?:\.[0-9]+)?)",
    re.IGNORECASE,
)


@dataclass(slots=True, frozen=True)
class ExposureKeys:
    exposure_group_id: str
    thesis_group_id: str | None
    underlying_group_id: str | None


def derive_exposure_keys(
    snapshot: MarketSnapshot,
    *,
    side: SignalSide | str | None = None,
) -> ExposureKeys:
    exposure_source = (
        snapshot.metadata.get("event_slug")
        or snapshot.metadata.get("series_key")
        or snapshot.metadata.get("condition_id")
    )
    source = exposure_source or snapshot.slug or snapshot.market_id
    normalized_source = _normalize_component(exposure_source) or snapshot.market_id
    exposure_group_id = f"{snapshot.category.value}:{normalized_source}"

    crypto_semantic = _normalize_crypto_snapshot(snapshot) if snapshot.category.value == "crypto" else None
    underlying = (
        crypto_semantic["underlying"]
        if crypto_semantic is not None
        else _normalize_component(snapshot.metadata.get("underlying") or _guess_underlying(source=source))
    )
    event_family = (
        crypto_semantic["event_family"]
        if crypto_semantic is not None
        else _normalize_component(snapshot.metadata.get("event_family") or _guess_event_family(source=source))
    )
    thesis_group_id = _derive_thesis_group_id(
        snapshot=snapshot,
        underlying=underlying,
        event_family=event_family,
        side=side,
    )
    underlying_group_id = (
        f"{snapshot.category.value}:{underlying}"
        if underlying
        else None
    )
    return ExposureKeys(
        exposure_group_id=exposure_group_id,
        thesis_group_id=thesis_group_id,
        underlying_group_id=underlying_group_id,
    )


def normalize_group_id(value: str | None) -> str | None:
    normalized = _normalize_component(value)
    return normalized or None


def _derive_thesis_group_id(
    *,
    snapshot: MarketSnapshot,
    underlying: str,
    event_family: str,
    side: SignalSide | str | None,
) -> str | None:
    if not underlying:
        return None
    if snapshot.category.value == "crypto":
        crypto_group = _derive_crypto_thesis_group_id(snapshot=snapshot, side=side)
        if crypto_group is not None:
            return crypto_group
    if event_family:
        return f"{snapshot.category.value}:{underlying}:{event_family}"
    return None


def _derive_crypto_thesis_group_id(
    *,
    snapshot: MarketSnapshot,
    side: SignalSide | str | None,
) -> str | None:
    normalized = _normalize_crypto_snapshot(snapshot)
    if normalized is None:
        return None
    thesis_polarity = _crypto_thesis_polarity(
        event_family=normalized["event_family"],
        side=side,
    )
    if thesis_polarity is None:
        return f"{snapshot.category.value}:{normalized['underlying']}:{normalized['event_family']}"
    return f"{snapshot.category.value}:{normalized['underlying']}:{thesis_polarity}"


def _crypto_thesis_polarity(
    *,
    event_family: str,
    side: SignalSide | str | None,
) -> str | None:
    normalized_side = _normalize_signal_side(side)
    if normalized_side is None:
        return None
    if event_family == "dip":
        if normalized_side in {SignalSide.BUY_NO.value, SignalSide.SELL_NO.value}:
            return "bullish"
        if normalized_side in {SignalSide.BUY_YES.value, SignalSide.SELL_YES.value}:
            return "bearish"
    if event_family == "reach":
        if normalized_side in {SignalSide.BUY_YES.value, SignalSide.SELL_YES.value}:
            return "bullish"
        if normalized_side in {SignalSide.BUY_NO.value, SignalSide.SELL_NO.value}:
            return "bearish"
    return None


def _normalize_signal_side(side: SignalSide | str | None) -> str | None:
    if side is None:
        return None
    if isinstance(side, SignalSide):
        return side.value
    normalized = str(side).strip().lower()
    return normalized or None


def _normalize_crypto_snapshot(snapshot: MarketSnapshot) -> dict[str, str] | None:
    combined = _combined_text(snapshot)
    underlying = _parse_crypto_underlying(combined)
    if underlying is None:
        return None
    event_family = _parse_crypto_event_family(combined)
    if event_family is None:
        return None
    if _parse_barrier_price(combined) is None:
        return None
    return {
        "underlying": underlying.lower(),
        "event_family": event_family,
    }


def _combined_text(snapshot: MarketSnapshot) -> str:
    return " ".join(
        (
            snapshot.metadata.get("question", ""),
            snapshot.slug,
            snapshot.metadata.get("event_title", ""),
        )
    ).lower()


def _parse_crypto_underlying(combined: str) -> str | None:
    if "bitcoin" in combined or "btc" in combined:
        return "BTC"
    if "ethereum" in combined or "eth" in combined:
        return "ETH"
    return None


def _parse_crypto_event_family(combined: str) -> str | None:
    if any(token in combined for token in _DOWNWARD_TOKENS):
        return "dip"
    if any(token in combined for token in _UPWARD_TOKENS):
        return "reach"
    return None


def _parse_barrier_price(combined: str) -> float | None:
    match = _PRICE_PATTERN.search(combined)
    if match is None:
        return None
    return float(match.group(1).replace(",", ""))


def _guess_underlying(*, source: str) -> str | None:
    tokens = _source_tokens(source)
    for token in tokens:
        if token in {"btc", "bitcoin"}:
            return "btc"
        if token in {"eth", "ethereum"}:
            return "eth"
        if token in {"sol", "solana"}:
            return "sol"
    if not tokens:
        return None
    candidate = tokens[0]
    if candidate.isalpha():
        return candidate
    return None


def _guess_event_family(*, source: str) -> str | None:
    tokens = _source_tokens(source)
    for token in tokens:
        if token in _DOWNWARD_TOKENS:
            return "dip"
        if token in _UPWARD_TOKENS:
            return "reach"
    if len(tokens) < 2:
        return None
    candidate = tokens[1]
    if candidate.isalpha():
        return candidate
    return None


def _source_tokens(source: str) -> list[str]:
    normalized = _normalize_component(source)
    if not normalized:
        return []
    return [token for token in normalized.replace("_", "-").split("-") if token]


def _normalize_component(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "-")
    return normalized
