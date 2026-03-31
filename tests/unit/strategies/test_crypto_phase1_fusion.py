from datetime import datetime
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.fusion import fuse_crypto_fair_value, to_fair_value_estimate
from pm_bot.strategies.crypto.phase1.inputs import build_pricing_inputs, build_underlying_state, build_volatility_regime
from pm_bot.strategies.crypto.phase1.models import CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.models import CryptoResidualModelConfig
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.pricing import estimate_barrier_probability
from pm_bot.strategies.crypto.phase1.series import build_crypto_ladder_series
from pm_bot.strategies.crypto.phase1.pricing import estimate_surface_consistency


FIXTURE_SNAPSHOTS = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")


def test_fuse_crypto_fair_value_blends_barrier_and_surface_estimates() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    market = normalize_crypto_market(snapshots[1])
    assert market is not None
    series = build_crypto_ladder_series(snapshots[:3])[0]
    state = build_underlying_state(
        underlying="ETH",
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
        spot_price=1850.0,
        realized_volatility=0.62,
        implied_volatility=0.71,
    )
    regime = build_volatility_regime(realized_volatility=0.62, implied_volatility=0.71)
    inputs = build_pricing_inputs(market=market, underlying_state=state, volatility_regime=regime)
    barrier = estimate_barrier_probability(inputs)
    surface = estimate_surface_consistency(
        series=series,
        market=market,
        observed_probability=0.09,
        peer_probabilities={
            "eth-dip-1500": 0.71,
            "eth-dip-1000": 0.09,
            "eth-dip-800": 0.195,
        },
    )

    fused = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.09,
    )
    estimate = to_fair_value_estimate(inputs=inputs, fused=fused, observed_probability=0.09)

    assert 0.09 < fused.fair_probability < 0.30
    assert fused.surface_probability == 0.195
    assert fused.half_life_seconds == 3600
    assert estimate.category.value == "crypto"
    assert estimate.model_id == "crypto.phase1.fused"
    assert "barrier_probability" in estimate.supporting_values


def test_fuse_crypto_fair_value_respects_weight_override() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    market = normalize_crypto_market(snapshots[1])
    assert market is not None
    series = build_crypto_ladder_series(snapshots[:3])[0]
    state = build_underlying_state(
        underlying="ETH",
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
        spot_price=1850.0,
        realized_volatility=0.62,
        implied_volatility=0.71,
    )
    inputs = build_pricing_inputs(market=market, underlying_state=state)
    barrier = estimate_barrier_probability(inputs)
    surface = estimate_surface_consistency(
        series=series,
        market=market,
        observed_probability=0.09,
        peer_probabilities={
            "eth-dip-1500": 0.71,
            "eth-dip-1000": 0.09,
            "eth-dip-800": 0.195,
        },
    )

    baseline = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.09,
    )
    surface_heavier = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.09,
        model_config=CryptoFusionModelConfig(barrier_weight=0.5, surface_weight=0.5),
    )

    assert surface_heavier.fair_probability > baseline.fair_probability


def test_fuse_crypto_fair_value_applies_residual_correction_for_matching_bucket() -> None:
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"))
    market = normalize_crypto_market(snapshots[0])
    assert market is not None
    series = build_crypto_ladder_series(snapshots[:3])[0]
    state = build_underlying_state(
        underlying="BTC",
        as_of=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
        spot_price=79000.0,
        realized_volatility=0.58,
        implied_volatility=0.66,
    )
    inputs = build_pricing_inputs(market=market, underlying_state=state, as_of=snapshots[0].timestamp)
    barrier = estimate_barrier_probability(inputs)
    surface = estimate_surface_consistency(
        series=series,
        market=market,
        observed_probability=0.5,
        peer_probabilities={
            item.normalized.market_id: 0.5
            for item in series.markets
        },
    )
    base = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.5,
    )
    corrected = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.5,
        residual_model_config=CryptoResidualModelConfig(
            enabled=True,
            min_confidence=0.5,
            max_abs_correction_bps=120.0,
            corrections=((f"{market.underlying}:{market.event_family}:gt_180d", 90.0),),
        ),
    )

    assert corrected.fair_probability > base.fair_probability
    assert corrected.residual_applied is True
    assert corrected.residual_diagnostic_tag == "residual_applied"


def test_fuse_crypto_fair_value_falls_back_when_bucket_unknown_or_payload_corrupted() -> None:
    snapshots = load_market_snapshots(FIXTURE_SNAPSHOTS)
    market = normalize_crypto_market(snapshots[1])
    assert market is not None
    series = build_crypto_ladder_series(snapshots[:3])[0]
    state = build_underlying_state(
        underlying="ETH",
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
        spot_price=1850.0,
        realized_volatility=0.62,
        implied_volatility=0.71,
    )
    inputs = build_pricing_inputs(market=market, underlying_state=state)
    barrier = estimate_barrier_probability(inputs)
    surface = estimate_surface_consistency(
        series=series,
        market=market,
        observed_probability=0.09,
        peer_probabilities={
            "eth-dip-1500": 0.71,
            "eth-dip-1000": 0.09,
            "eth-dip-800": 0.195,
        },
    )

    baseline = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.09,
    )
    unknown_bucket = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.09,
        residual_model_config=CryptoResidualModelConfig(
            enabled=True,
            corrections=(("BTC:dip:gt_180d", 50.0),),
        ),
    )
    corrupted = fuse_crypto_fair_value(
        inputs=inputs,
        barrier_estimate=barrier,
        surface_estimate=surface,
        observed_probability=0.09,
        residual_model_config=CryptoResidualModelConfig(
            enabled=True,
            corrections=((f"{market.underlying}:{market.event_family}:gt_180d", "bad"),),
        ),
    )

    assert unknown_bucket.fair_probability == baseline.fair_probability
    assert unknown_bucket.residual_applied is False
    assert unknown_bucket.residual_diagnostic_tag == "residual_bucket_missing"
    assert corrupted.fair_probability == baseline.fair_probability
    assert corrupted.residual_applied is False
    assert corrupted.residual_diagnostic_tag == "residual_payload_invalid"
