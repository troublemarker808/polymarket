"""Normalization helpers for supported weather Phase 1 market families."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from pm_bot.core.research_types import NormalizedMarketDefinition
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.strategies.weather.phase1.models import WeatherLocationDefinition, WeatherMarketDefinition

_SUPPORTED_LOCATIONS: dict[str, WeatherLocationDefinition] = {
    "nyc": WeatherLocationDefinition(
        city="New York City",
        region="NY",
        country="US",
        station_id="KNYC",
        settlement_source="nws_noaa_daily_climate",
    ),
    "new york city": WeatherLocationDefinition(
        city="New York City",
        region="NY",
        country="US",
        station_id="KNYC",
        settlement_source="nws_noaa_daily_climate",
    ),
}


def classify_weather_market(snapshot: MarketSnapshot) -> str | None:
    normalized = normalize_weather_market(snapshot)
    if normalized is None:
        return None
    return normalized.normalized.market_family


def normalize_weather_market(snapshot: MarketSnapshot) -> WeatherMarketDefinition | None:
    if snapshot.category != Category.WEATHER:
        return None

    combined = _combined_text(snapshot)
    if "high temperature" not in combined:
        return None

    comparator = _parse_comparator(combined)
    if comparator is None:
        return None

    threshold = _parse_threshold(snapshot)
    if threshold is None:
        return None

    location = _parse_location(snapshot)
    if location is None:
        return None

    event_date = _parse_event_date(snapshot)
    if event_date is None:
        return None

    series_key = (
        snapshot.metadata.get("event_slug")
        or snapshot.metadata.get("series_key")
        or f"{location.station_id}:{event_date.date().isoformat()}:daily_high_temperature"
    )
    normalized = NormalizedMarketDefinition(
        market_id=snapshot.market_id,
        category=Category.WEATHER,
        market_family="daily_high_temperature_threshold",
        scope_key=f"{location.station_id}:{event_date.date().isoformat()}",
        instrument_key=f"{location.station_id}:{event_date.date().isoformat()}:{comparator}:{_format_threshold(threshold)}",
        resolution_time=snapshot.resolution_time,
        attributes={
            "event_family": "daily_high_temperature_threshold",
            "threshold": threshold,
            "comparator": comparator,
            "city": location.city,
            "station_id": location.station_id,
            "settlement_source": location.settlement_source,
            "series_key": series_key,
        },
    )
    return WeatherMarketDefinition(
        normalized=normalized,
        event_family="daily_high_temperature_threshold",
        threshold=threshold,
        comparator=comparator,
        event_date=event_date,
        location=location,
        series_key=series_key,
    )


def normalize_weather_settlement(snapshot: MarketSnapshot) -> WeatherLocationDefinition | None:
    normalized = normalize_weather_market(snapshot)
    if normalized is None:
        return None
    return normalized.location


def _combined_text(snapshot: MarketSnapshot) -> str:
    return " ".join(
        (
            snapshot.metadata.get("question", ""),
            snapshot.metadata.get("event_title", ""),
            snapshot.slug,
        )
    ).lower()


def _parse_comparator(combined: str) -> str | None:
    if any(token in combined for token in ("above", "over", "hotter", "greater-than")):
        return "above"
    if any(token in combined for token in ("below", "under", "colder", "less-than")):
        return "below"
    return None


def _parse_threshold(snapshot: MarketSnapshot) -> float | None:
    raw_threshold = snapshot.metadata.get("group_item_threshold") or snapshot.metadata.get("threshold")
    if raw_threshold not in (None, ""):
        try:
            return float(raw_threshold)
        except ValueError:
            return None
    combined = _combined_text(snapshot)
    match = re.search(r"(\d+(?:\.\d+)?)\s*f\b", combined)
    if match is None:
        return None
    return float(match.group(1))


def _parse_location(snapshot: MarketSnapshot) -> WeatherLocationDefinition | None:
    for raw in (
        snapshot.metadata.get("location"),
        snapshot.metadata.get("city"),
        snapshot.metadata.get("location_name"),
        snapshot.metadata.get("event_slug", "").split("-high-temp")[0].replace("-", " "),
        snapshot.metadata.get("question", "").split(" high temperature")[0].replace("Will ", ""),
    ):
        text = str(raw).strip().lower()
        if not text:
            continue
        if text in _SUPPORTED_LOCATIONS:
            return _SUPPORTED_LOCATIONS[text]
    return None


def _parse_event_date(snapshot: MarketSnapshot) -> datetime | None:
    for raw in (
        snapshot.metadata.get("event_date"),
        snapshot.metadata.get("target_date"),
        snapshot.resolution_time,
    ):
        if raw in (None, ""):
            continue
        if isinstance(raw, datetime):
            return raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _format_threshold(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
