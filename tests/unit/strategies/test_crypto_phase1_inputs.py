from datetime import datetime
import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.inputs import (
    build_pricing_inputs,
    build_underlying_state,
    build_volatility_regime,
    compute_time_to_expiry,
    effective_trading_horizon_days,
)
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market


FIXTURE_SNAPSHOTS = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")
FIXTURE_UNDERLYING = Path("tests/fixtures/crypto_phase1/underlying_state.json")


def test_build_volatility_regime_prefers_implied_vol_and_labels_band() -> None:
    regime = build_volatility_regime(realized_volatility=0.62, implied_volatility=0.71)

    assert regime.label == "normal"
    assert regime.sigma_estimate == 0.71
    assert 0.0 <= regime.jump_risk_score <= 1.0


def test_build_pricing_inputs_computes_distance_and_time_fields() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    market = normalize_crypto_market(snapshot)
    assert market is not None
    payload = json.loads(FIXTURE_UNDERLYING.read_text(encoding="utf-8"))
    state = build_underlying_state(
        underlying=payload["underlying"],
        as_of=datetime.fromisoformat(payload["as_of"].replace("Z", "+00:00")),
        spot_price=float(payload["spot_price"]),
        daily_return=float(payload["daily_return"]),
        realized_volatility=float(payload["realized_volatility"]),
        implied_volatility=float(payload["implied_volatility"]),
    )

    pricing_inputs = build_pricing_inputs(market=market, underlying_state=state)

    assert pricing_inputs.market.barrier_price == 1500.0
    assert pricing_inputs.underlying_state.spot_price == 1850.0
    assert pricing_inputs.distance_to_barrier == -350.0
    assert round(pricing_inputs.distance_ratio, 6) == round(350.0 / 1850.0, 6)
    assert pricing_inputs.time_to_expiry_seconds > 0
    assert pricing_inputs.time_to_expiry_days > 0
    assert pricing_inputs.effective_horizon_days > 0


def test_compute_time_to_expiry_and_effective_horizon_handle_expired_and_long_dated_cases() -> None:
    seconds, days = compute_time_to_expiry(
        resolution_time=datetime.fromisoformat("2026-03-25T00:00:00+00:00"),
        as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
    )

    assert seconds == 129600.0
    assert days == 1.5
    assert effective_trading_horizon_days(days) == 1.5
    assert effective_trading_horizon_days(20.0) == 16.0
    assert effective_trading_horizon_days(120.0) == 78.0
    assert effective_trading_horizon_days(0.0) == 0.0
