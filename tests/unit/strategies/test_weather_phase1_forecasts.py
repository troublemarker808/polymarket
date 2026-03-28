import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.weather.phase1 import build_forecast_run_calendar, ingest_forecast_runs, normalize_weather_market


FIXTURE_SNAPSHOTS = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")
FIXTURE_RUNS = Path("tests/fixtures/weather_phase1/forecast_runs.json")


def test_ingest_forecast_runs_filters_station_and_computes_horizon() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_weather_market(snapshot)
    assert market is not None

    payload = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    runs = ingest_forecast_runs(market=market, run_payloads=payload)

    assert len(runs) == 2
    assert runs[0].model_name == "gfs"
    assert runs[0].station_id == "KNYC"
    assert runs[0].horizon_hours == 24.0
    assert runs[1].model_name == "ecmwf"
    assert runs[1].horizon_hours == 18.0


def test_build_forecast_run_calendar_returns_sorted_issue_times() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_weather_market(snapshot)
    assert market is not None

    payload = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    calendar = build_forecast_run_calendar(market=market, run_payloads=payload)

    assert len(calendar) == 2
    assert calendar[0].isoformat() == "2026-03-23T00:00:00+00:00"
    assert calendar[1].isoformat() == "2026-03-23T06:00:00+00:00"
