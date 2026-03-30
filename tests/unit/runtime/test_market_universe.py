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
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
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


def test_market_universe_can_filter_by_event_slug() -> None:
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
            slug="microstrategy-sells-any-bitcoin",
            event_slug="microstrategy-bitcoin",
            event_title="MicroStrategy Bitcoin",
            question="Will MicroStrategy sell any Bitcoin?",
            liquidity_score=0.95,
        ),
    )

    selector = build_snapshot_selector(
        {
            "assets": ["BTC"],
            "event_slugs": ["bitcoin-prices"],
        }
    )

    assert selector is not None
    selected = selector(snapshots)

    assert [snapshot.market_id for snapshot in selected] == ["btc-1"]


def test_market_universe_event_slug_filter_is_strict() -> None:
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
            slug="microstrategy-sells-any-bitcoin",
            event_slug="microstrategy-bitcoin",
            event_title="MicroStrategy Bitcoin",
            question="Will MicroStrategy sell any Bitcoin?",
            liquidity_score=0.95,
        ),
    )

    selector = build_snapshot_selector(
        {
            "assets": ["BTC"],
            "event_slugs": ["non-existent-event"],
        }
    )

    assert selector is not None
    selected = selector(snapshots)

    assert selected == []


def test_market_universe_prefers_explicit_market_ids_over_liquidity() -> None:
    snapshots = (
        _snapshot(
            market_id="preferred-1",
            slug="will-bitcoin-dip-to-40k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin dip to 40000?",
            liquidity_score=0.80,
        ),
        _snapshot(
            market_id="preferred-2",
            slug="will-bitcoin-dip-to-45k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin dip to 45000?",
            liquidity_score=0.81,
        ),
        _snapshot(
            market_id="liquid-1",
            slug="will-bitcoin-hit-90k",
            event_slug="bitcoin-prices",
            event_title="Bitcoin prices",
            question="Will Bitcoin hit 90000?",
            liquidity_score=0.99,
        ),
    )

    selector = build_snapshot_selector(
        {
            "assets": ["BTC"],
            "event_slugs": ["bitcoin-prices"],
            "preferred_market_ids": ["preferred-1", "preferred-2"],
            "max_active_markets": 2,
            "max_markets_per_event": 2,
        }
    )

    assert selector is not None
    selected = selector(snapshots)

    assert [snapshot.market_id for snapshot in selected] == ["preferred-1", "preferred-2"]


def test_market_universe_can_filter_by_expiry_bucket() -> None:
    short_snapshot = _snapshot(
        market_id="btc-short",
        slug="will-bitcoin-hit-80k-by-april-10-2026",
        event_slug="bitcoin-short",
        event_title="Bitcoin short horizon",
        question="Will Bitcoin hit 80000 by April 10, 2026?",
        liquidity_score=0.9,
    )
    short_snapshot.resolution_time = datetime(2026, 4, 10, 0, 0, tzinfo=UTC)
    long_snapshot = _snapshot(
        market_id="btc-long",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        event_slug="bitcoin-long",
        event_title="Bitcoin long horizon",
        question="Will Bitcoin hit 150000 by December 31, 2026?",
        liquidity_score=0.9,
    )
    long_snapshot.resolution_time = datetime(2026, 12, 31, 0, 0, tzinfo=UTC)

    selector = build_snapshot_selector({"assets": ["BTC"], "expiries": ["short"]})

    assert selector is not None
    selected = selector((short_snapshot, long_snapshot))

    assert [snapshot.market_id for snapshot in selected] == ["btc-short"]


def test_market_universe_can_filter_by_next_3d_bucket() -> None:
    near_snapshot = _snapshot(
        market_id="btc-near",
        slug="will-bitcoin-hit-80k-by-march-31-2026",
        event_slug="bitcoin-near",
        event_title="Bitcoin near horizon",
        question="Will Bitcoin hit 80000 by March 31, 2026?",
        liquidity_score=0.9,
    )
    near_snapshot.timestamp = datetime(2026, 3, 29, 0, 0, tzinfo=UTC)
    near_snapshot.resolution_time = datetime(2026, 3, 31, 0, 0, tzinfo=UTC)
    far_snapshot = _snapshot(
        market_id="btc-far",
        slug="will-bitcoin-hit-80k-by-april-10-2026",
        event_slug="bitcoin-far",
        event_title="Bitcoin far horizon",
        question="Will Bitcoin hit 80000 by April 10, 2026?",
        liquidity_score=0.9,
    )
    far_snapshot.timestamp = datetime(2026, 3, 29, 0, 0, tzinfo=UTC)
    far_snapshot.resolution_time = datetime(2026, 4, 10, 0, 0, tzinfo=UTC)

    selector = build_snapshot_selector({"assets": ["BTC"], "expiries": ["next_3d"]})

    assert selector is not None
    selected = selector((near_snapshot, far_snapshot))

    assert [snapshot.market_id for snapshot in selected] == ["btc-near"]


def test_market_universe_can_exclude_derived_crypto_keywords() -> None:
    price_snapshot = _snapshot(
        market_id="btc-price",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        event_slug="bitcoin-prices",
        event_title="Bitcoin prices",
        question="Will Bitcoin hit 150000 by December 31, 2026?",
        liquidity_score=0.92,
    )
    derived_snapshot = _snapshot(
        market_id="btc-vol",
        slug="will-the-bitcoin-volatility-index-hit-80-by-april-30",
        event_slug="bitcoin-volatility",
        event_title="Bitcoin volatility",
        question="Will the Bitcoin volatility index hit 80 by April 30?",
        liquidity_score=0.95,
    )

    selector = build_snapshot_selector(
        {
            "assets": ["BTC"],
            "exclude_keywords": ["volatility", "dominance", "premium"],
        }
    )

    assert selector is not None
    selected = selector((price_snapshot, derived_snapshot))

    assert [snapshot.market_id for snapshot in selected] == ["btc-price"]


def test_market_universe_can_require_price_barrier_keywords() -> None:
    barrier_snapshot = _snapshot(
        market_id="btc-barrier",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        event_slug="bitcoin-prices",
        event_title="Bitcoin prices",
        question="Will Bitcoin hit 150000 by December 31, 2026?",
        liquidity_score=0.92,
    )
    non_barrier_snapshot = _snapshot(
        market_id="btc-best-month",
        slug="will-december-be-the-best-month-for-bitcoin-in-2026",
        event_slug="bitcoin-best-month",
        event_title="Bitcoin monthly performance",
        question="Will December be the best month for Bitcoin in 2026?",
        liquidity_score=0.95,
    )

    selector = build_snapshot_selector(
        {
            "assets": ["BTC"],
            "include_keywords": ["dip", "reach", "hit", "above", "below", "under", "over"],
        }
    )

    assert selector is not None
    selected = selector((barrier_snapshot, non_barrier_snapshot))

    assert [snapshot.market_id for snapshot in selected] == ["btc-barrier"]
