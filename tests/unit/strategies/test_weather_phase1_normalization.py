from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.weather.phase1 import classify_weather_market, normalize_weather_market


FIXTURE_PATH = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")


def test_normalize_weather_market_parses_supported_daily_high_temperature_threshold() -> None:
    snapshot = load_market_snapshots(FIXTURE_PATH)[0]

    normalized = normalize_weather_market(snapshot)

    assert normalized is not None
    assert normalized.event_family == "daily_high_temperature_threshold"
    assert normalized.threshold == 70.0
    assert normalized.comparator == "above"
    assert normalized.location.city == "New York City"
    assert normalized.location.station_id == "KNYC"
    assert normalized.location.settlement_source == "nws_noaa_daily_climate"
    assert normalized.normalized.market_family == "daily_high_temperature_threshold"


def test_classify_weather_market_rejects_unsupported_non_temperature_market() -> None:
    snapshot = load_market_snapshots(FIXTURE_PATH)[2]

    assert classify_weather_market(snapshot) is None
