from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.runtime.market_universe import (
    MarketUniversePolicy,
    build_snapshot_selector,
    select_market_snapshots,
)


def _snapshot(
    *,
    market_id: str,
    slug: str,
    event_slug: str,
    event_title: str,
    question: str,
    liquidity_score: float,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=slug,
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 26, 0, 0, tzinfo=UTC),
        resolution_time=None,
        liquidity_score=liquidity_score,
        metadata={
            "event_slug": event_slug,
            "event_title": event_title,
            "question": question,
            "no_token_id": f"{market_id}-no",
        },
    )


def test_market_universe_asset_matching_uses_tokens_not_substrings() -> None:
    eth_snapshot = _snapshot(
        market_id="eth-1",
        slug="will-ethereum-reach-5000",
        event_slug="ethereum-prices",
        event_title="Ethereum prices",
        question="Will Ethereum reach 5000?",
        liquidity_score=0.9,
    )
    ethena_snapshot = _snapshot(
        market_id="ethena-1",
        slug="will-ethena-reach-1",
        event_slug="ethena-prices",
        event_title="Ethena prices",
        question="Will Ethena reach 1?",
        liquidity_score=0.95,
    )
    policy = MarketUniversePolicy(asset_keywords=("eth",))

    selected = select_market_snapshots(
        snapshots=(eth_snapshot, ethena_snapshot),
        policy=policy,
    )

    assert [snapshot.market_id for snapshot in selected] == ["eth-1"]


def test_market_universe_prefers_grouped_markets_and_respects_limits() -> None:
    snapshots = (
        _snapshot(
            market_id="btc-1",
            slug="will-bitcoin-reach-120k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin reach 120k?",
            liquidity_score=0.92,
        ),
        _snapshot(
            market_id="btc-2",
            slug="will-bitcoin-reach-150k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin reach 150k?",
            liquidity_score=0.91,
        ),
        _snapshot(
            market_id="btc-3",
            slug="will-bitcoin-reach-200k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin reach 200k?",
            liquidity_score=0.9,
        ),
        _snapshot(
            market_id="eth-1",
            slug="will-ethereum-reach-5k",
            event_slug="ethereum-prices",
            event_title="Ethereum prices",
            question="Will Ethereum reach 5000?",
            liquidity_score=0.89,
        ),
        _snapshot(
            market_id="eth-2",
            slug="will-ethereum-reach-6k",
            event_slug="ethereum-prices",
            event_title="Ethereum prices",
            question="Will Ethereum reach 6000?",
            liquidity_score=0.88,
        ),
        _snapshot(
            market_id="single-1",
            slug="will-solana-reach-500",
            event_slug="solana-price",
            event_title="Solana price",
            question="Will Solana reach 500?",
            liquidity_score=0.99,
        ),
    )
    policy = MarketUniversePolicy(
        min_liquidity_score=0.8,
        max_active_markets=4,
        max_markets_per_event=2,
        min_markets_per_event=2,
    )

    selected = select_market_snapshots(snapshots=snapshots, policy=policy)

    assert [snapshot.market_id for snapshot in selected] == [
        "btc-1",
        "eth-1",
        "btc-2",
        "eth-2",
    ]


def test_build_snapshot_selector_returns_none_when_config_is_empty() -> None:
    assert build_snapshot_selector({}) is None


def test_build_snapshot_selector_creates_callable_from_markets_config() -> None:
    selector = build_snapshot_selector(
        {
            "assets": ["BTC"],
            "max_active_markets": 1,
            "max_markets_per_event": 1,
        }
    )
    assert selector is not None

    snapshots = (
        _snapshot(
            market_id="btc-1",
            slug="will-bitcoin-reach-120k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin reach 120k?",
            liquidity_score=0.92,
        ),
        _snapshot(
            market_id="eth-1",
            slug="will-ethereum-reach-5k",
            event_slug="ethereum-prices",
            event_title="Ethereum prices",
            question="Will Ethereum reach 5000?",
            liquidity_score=0.95,
        ),
    )

    selected = selector(snapshots)

    assert [snapshot.market_id for snapshot in selected] == ["btc-1"]
