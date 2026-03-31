from datetime import datetime
import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.inputs import build_pricing_inputs, build_underlying_state, build_volatility_regime
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.pricing import (
    build_residual_bucket_key,
    build_peer_probability_map,
    estimate_barrier_probability,
    estimate_surface_consistency,
    observed_mid_probability,
)
from pm_bot.strategies.crypto.phase1.series import build_crypto_ladder_series


FIXTURE_SNAPSHOTS = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")
FIXTURE_CASES = Path("tests/fixtures/crypto_phase1/fair_value_cases.json")


def test_estimate_barrier_probability_returns_lower_probability_for_more_distant_downside_barrier() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    markets = [normalize_crypto_market(snapshot) for snapshot in snapshots[:3]]
    assert all(market is not None for market in markets)
    state = build_underlying_state(
        underlying="ETH",
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
        spot_price=1850.0,
        realized_volatility=0.62,
        implied_volatility=0.71,
    )
    regime = build_volatility_regime(realized_volatility=0.62, implied_volatility=0.71)

    near_inputs = build_pricing_inputs(market=markets[0], underlying_state=state, volatility_regime=regime)
    far_inputs = build_pricing_inputs(market=markets[2], underlying_state=state, volatility_regime=regime)

    near_estimate = estimate_barrier_probability(near_inputs)
    far_estimate = estimate_barrier_probability(far_inputs)

    assert 0.0 < far_estimate.fair_probability < near_estimate.fair_probability < 1.0


def test_estimate_barrier_probability_respects_steepness_override() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    market = normalize_crypto_market(snapshots[1])
    assert market is not None
    state = build_underlying_state(
        underlying="ETH",
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
        spot_price=1850.0,
        realized_volatility=0.62,
        implied_volatility=0.71,
    )
    inputs = build_pricing_inputs(market=market, underlying_state=state)

    baseline = estimate_barrier_probability(inputs)
    shallower = estimate_barrier_probability(inputs, CryptoBarrierModelConfig(steepness=1.8))

    assert shallower.fair_probability > baseline.fair_probability


def test_estimate_surface_consistency_projects_probability_back_inside_monotonic_bounds() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    markets = [normalize_crypto_market(snapshot) for snapshot in snapshots[:3]]
    assert all(market is not None for market in markets)
    series = build_crypto_ladder_series(snapshots[:3])[0]
    peer_probability_map = {
        markets[0].normalized.market_id: 0.71,
        markets[1].normalized.market_id: 0.09,
        markets[2].normalized.market_id: 0.195,
    }

    surface = estimate_surface_consistency(
        series=series,
        market=markets[1],
        observed_probability=0.09,
        peer_probabilities=peer_probability_map,
    )

    assert round(surface.local_lower_bound or 0.0, 3) == 0.195
    assert round(surface.local_upper_bound or 0.0, 2) == 0.71
    assert round(surface.fair_probability, 3) == 0.195
    assert round(surface.mispricing_bps, 1) == 1050.0


def test_observed_mid_probability_and_peer_map_use_only_in_series_markets() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    series = build_crypto_ladder_series(snapshots[:3])[0]
    markets = [normalize_crypto_market(snapshot) for snapshot in snapshots]
    assert all(market is not None for market in markets[:3])
    cases = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))
    probabilities = cases["eth_down_ladder"]["observed_probabilities"]

    mid = observed_mid_probability(0.25, 0.26)
    peer_map = build_peer_probability_map(
        series=series,
        snapshots=(
            (markets[0], probabilities["eth-dip-1500"]),
            (markets[1], probabilities["eth-dip-1000"]),
            (markets[2], probabilities["eth-dip-800"]),
        ),
    )

    assert round(mid or 0.0, 3) == 0.255
    assert set(peer_map) == {"eth-dip-1500", "eth-dip-1000", "eth-dip-800"}


def test_build_residual_bucket_key_uses_underlying_family_and_expiry_bucket() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    market = normalize_crypto_market(snapshots[0])
    assert market is not None
    state = build_underlying_state(
        underlying="ETH",
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
        spot_price=1850.0,
        realized_volatility=0.62,
        implied_volatility=0.71,
    )
    inputs = build_pricing_inputs(market=market, underlying_state=state, as_of=snapshots[0].timestamp)

    key = build_residual_bucket_key(inputs)

    assert key.startswith("ETH:dip:")
