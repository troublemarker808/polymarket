from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1 import build_crypto_ladder_series


FIXTURE_PATH = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")


def test_build_crypto_ladder_series_groups_and_orders_supported_markets() -> None:
    snapshots = load_market_snapshots(FIXTURE_PATH)

    series = build_crypto_ladder_series(snapshots)

    assert len(series) == 1
    ladder = series[0]
    assert ladder.series_key == "ETH:dip:2026-12-31"
    assert ladder.underlying == "ETH"
    assert ladder.event_family == "dip"
    assert tuple(market.barrier_price for market in ladder.markets) == (1500.0, 1000.0, 800.0)
