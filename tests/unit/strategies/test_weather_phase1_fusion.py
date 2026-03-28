import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.common import implied_yes_probability
from pm_bot.strategies.weather.phase1 import (
    apply_bias_corrections,
    build_forecast_distribution,
    estimate_strip_consistency,
    estimate_threshold_probability,
    fuse_weather_fair_value,
    ingest_forecast_runs,
    load_model_skill_store,
    normalize_weather_market,
    to_fair_value_estimate,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")
FIXTURE_RUNS = Path("tests/fixtures/weather_phase1/forecast_runs.json")
FIXTURE_SKILLS = Path("tests/fixtures/weather_phase1/model_skill_cases.json")


def test_fuse_weather_fair_value_combines_threshold_and_strip_views() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)[:2]
    market = normalize_weather_market(snapshots[0])
    peer_market = normalize_weather_market(snapshots[1])
    assert market is not None
    assert peer_market is not None

    run_payload = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    skill_payload = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]
    runs = ingest_forecast_runs(market=market, run_payloads=run_payload)
    skills = load_model_skill_store(market=market, skill_payloads=skill_payload)
    corrected = apply_bias_corrections(market=market, forecast_runs=runs, skill_store=skills)
    distribution = build_forecast_distribution(market=market, corrected_forecasts=corrected)
    assert distribution is not None
    threshold = estimate_threshold_probability(market=market, distribution=distribution)
    strip = estimate_strip_consistency(
        series_key=market.series_key,
        market=market,
        observed_probability=0.70,
        peer_probabilities={
            market.normalized.market_id: 0.70,
            peer_market.normalized.market_id: 0.73,
        },
        ordered_markets=(market, peer_market),
    )

    observed_probability = implied_yes_probability(snapshots[0])
    fused = fuse_weather_fair_value(
        market=market,
        distribution=distribution,
        threshold_estimate=threshold,
        strip_estimate=strip,
        observed_probability=observed_probability,
    )

    assert round(fused.fair_probability, 4) == 0.8464
    assert fused.confidence == 0.77
    assert fused.half_life_seconds == 7200
    assert fused.strip_probability == 0.73


def test_to_fair_value_estimate_emits_weather_research_row() -> None:
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
    threshold = estimate_threshold_probability(market=market, distribution=distribution)
    fused = fuse_weather_fair_value(
        market=market,
        distribution=distribution,
        threshold_estimate=threshold,
        observed_probability=0.79,
    )

    estimate = to_fair_value_estimate(
        market=market,
        fused=fused,
        distribution=distribution,
        observed_probability=0.79,
    )

    assert estimate.market_id == "w70"
    assert estimate.model_id == "weather.phase1.fused"
    assert estimate.rationale_tags == ("forecast_distribution", "threshold_probability")
    assert round(float(estimate.supporting_values["weighted_mean_temp_f"]), 4) == 73.3929
