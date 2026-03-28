from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.weather.phase1 import normalize_weather_settlement


FIXTURE_PATH = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")


def test_normalize_weather_settlement_returns_explicit_station_mapping() -> None:
    snapshot = load_market_snapshots(FIXTURE_PATH)[1]

    settlement = normalize_weather_settlement(snapshot)

    assert settlement is not None
    assert settlement.city == "New York City"
    assert settlement.station_id == "KNYC"
    assert settlement.settlement_source == "nws_noaa_daily_climate"
