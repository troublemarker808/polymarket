from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1 import classify_crypto_market, normalize_crypto_market


FIXTURE_PATH = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")


def test_normalize_crypto_market_parses_supported_eth_dip_ladder_snapshot() -> None:
    snapshot = load_market_snapshots(FIXTURE_PATH)[0]

    normalized = normalize_crypto_market(snapshot)

    assert normalized is not None
    assert normalized.normalized.market_family == "price_ladder_barrier"
    assert normalized.underlying == "ETH"
    assert normalized.event_family == "dip"
    assert normalized.direction == "down"
    assert normalized.barrier_price == 1500.0
    assert normalized.normalized.scope_key == "ETH:dip:2026-12-31"
    assert normalized.normalized.instrument_key == "ETH:dip:2026-12-31:1500"


def test_classify_crypto_market_rejects_unsupported_non_ladder_crypto_market() -> None:
    snapshot = load_market_snapshots(FIXTURE_PATH)[3]

    assert classify_crypto_market(snapshot) is None
