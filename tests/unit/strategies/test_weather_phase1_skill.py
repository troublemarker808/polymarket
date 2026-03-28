import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.weather.phase1 import (
    apply_bias_correction,
    apply_bias_corrections,
    ingest_forecast_runs,
    load_model_skill_store,
    normalize_weather_market,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")
FIXTURE_RUNS = Path("tests/fixtures/weather_phase1/forecast_runs.json")
FIXTURE_SKILLS = Path("tests/fixtures/weather_phase1/model_skill_cases.json")


def test_load_model_skill_store_filters_to_supported_station() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_weather_market(snapshot)
    assert market is not None

    payload = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]
    skills = load_model_skill_store(market=market, skill_payloads=payload)

    assert len(skills) == 2
    assert skills[0].model_name == "ecmwf"
    assert skills[1].model_name == "gfs"


def test_apply_bias_correction_uses_matching_model_skill() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_weather_market(snapshot)
    assert market is not None

    run_payload = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    skill_payload = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]
    runs = ingest_forecast_runs(market=market, run_payloads=run_payload)
    skills = load_model_skill_store(market=market, skill_payloads=skill_payload)

    corrected = apply_bias_correction(market=market, forecast_run=runs[0], skill_store=skills)

    assert corrected.forecast_run.model_name == "gfs"
    assert corrected.bias_adjustment_f == -1.5
    assert corrected.corrected_high_temp_f == 72.0
    assert corrected.corrected_sigma_f == 2.8
    assert corrected.skill_weight == 0.62


def test_apply_bias_corrections_returns_one_row_per_forecast() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_weather_market(snapshot)
    assert market is not None

    run_payload = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    skill_payload = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]
    runs = ingest_forecast_runs(market=market, run_payloads=run_payload)
    skills = load_model_skill_store(market=market, skill_payloads=skill_payload)

    corrected = apply_bias_corrections(market=market, forecast_runs=runs, skill_store=skills)

    assert len(corrected) == 2
    assert corrected[1].forecast_run.model_name == "ecmwf"
    assert corrected[1].bias_adjustment_f == 0.5
    assert corrected[1].corrected_high_temp_f == 74.5
