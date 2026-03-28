import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.weather.phase1 import (
    apply_bias_corrections,
    build_forecast_distribution,
    build_weather_peer_probability_map,
    estimate_strip_consistency,
    estimate_threshold_probability,
    ingest_forecast_runs,
    load_model_skill_store,
    normalize_weather_market,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")
FIXTURE_RUNS = Path("tests/fixtures/weather_phase1/forecast_runs.json")
FIXTURE_SKILLS = Path("tests/fixtures/weather_phase1/model_skill_cases.json")
FIXTURE_CASES = Path("tests/fixtures/weather_phase1/threshold_cases.json")


def test_build_forecast_distribution_and_threshold_probability() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_weather_market(snapshot)
    assert market is not None

    run_payload = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    skill_payload = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]
    runs = ingest_forecast_runs(market=market, run_payloads=run_payload)
    skills = load_model_skill_store(market=market, skill_payloads=skill_payload)
    corrected = apply_bias_corrections(market=market, forecast_runs=runs, skill_store=skills)

    distribution = build_forecast_distribution(market=market, corrected_forecasts=corrected)

    assert distribution is not None
    assert round(distribution.weighted_mean_temp_f, 4) == 73.3929
    assert round(distribution.weighted_sigma_f, 4) == 2.6912

    threshold = estimate_threshold_probability(market=market, distribution=distribution)

    assert round(threshold.fair_probability, 4) == 0.8963
    assert round(threshold.implied_z_score, 4) == -1.2607


def test_estimate_strip_consistency_respects_above_threshold_ordering() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)[:2]
    markets = [normalize_weather_market(snapshot) for snapshot in snapshots]
    assert all(market is not None for market in markets)
    typed_markets = [market for market in markets if market is not None]

    peer_map = build_weather_peer_probability_map(
        markets=typed_markets,
        snapshots=((typed_markets[0], 0.70), (typed_markets[1], 0.73)),
    )
    strip = estimate_strip_consistency(
        series_key=typed_markets[0].series_key,
        market=typed_markets[0],
        observed_probability=0.70,
        peer_probabilities=peer_map,
        ordered_markets=typed_markets,
    )

    assert strip.local_lower_bound == 0.73
    assert strip.local_upper_bound is None
    assert strip.fair_probability == 0.73
    assert strip.monotonicity_gap_bps == 300.0
