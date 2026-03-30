from datetime import UTC, datetime
from pathlib import Path

from pm_bot.core.types import Category, MarketSnapshot
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


def test_normalize_crypto_market_rejects_derived_metric_markets() -> None:
    snapshot = MarketSnapshot(
        market_id="btc-vol",
        token_id="btc-vol-yes",
        slug="will-the-bitcoin-volatility-index-hit-80-by-april-30",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 0, 0, tzinfo=UTC),
        resolution_time=datetime(2026, 5, 1, 4, 0, tzinfo=UTC),
        metadata={
            "question": "Will the Bitcoin volatility index hit 80 by April 30?",
            "event_title": "Bitcoin volatility",
        },
    )

    assert normalize_crypto_market(snapshot) is None
    assert classify_crypto_market(snapshot) is None
