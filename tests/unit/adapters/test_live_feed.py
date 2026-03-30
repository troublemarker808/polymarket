import asyncio
from datetime import UTC, datetime

from pm_bot.adapters.polymarket.live_feed import PolymarketLiveMarketDataAdapter
from pm_bot.adapters.polymarket.ws_client import BestBidAskEvent
from pm_bot.core.types import Category, MarketSnapshot


class FakeGammaClient:
    async def fetch_active_binary_market_snapshots(self, **kwargs):
        return [
            MarketSnapshot(
                market_id="824952",
                token_id="yes-token",
                slug="microstrategy-sells-any-bitcoin-by-december-31-2026",
                category=Category.CRYPTO,
                timestamp=datetime(2026, 3, 23, 9, 42, 51, 763712, tzinfo=UTC),
                resolution_time=datetime(2026, 7, 1, 4, 0, tzinfo=UTC),
                best_bid_yes=0.11,
                best_ask_yes=0.15,
                last_traded_price=0.11,
                metadata={"condition_id": "0x8213d395e079614d6c4d7f4cbb9be9337ab51648a21cc2a334ae8f1966d164b4"},
            )
        ]


class FakeClobEnricher:
    def __init__(self) -> None:
        self.last_market_ids: list[str] = []

    async def enrich_snapshots(self, snapshots):
        self.last_market_ids = [snapshot.market_id for snapshot in snapshots]
        enriched = list(snapshots)
        enriched[0] = MarketSnapshot(
            market_id=enriched[0].market_id,
            token_id=enriched[0].token_id,
            slug=enriched[0].slug,
            category=enriched[0].category,
            timestamp=enriched[0].timestamp,
            resolution_time=enriched[0].resolution_time,
            best_bid_yes=0.12,
            best_ask_yes=0.16,
            last_traded_price=enriched[0].last_traded_price,
            metadata=dict(enriched[0].metadata),
        )
        return enriched


class FakeEventStream:
    async def stream_events(self, asset_ids):
        assert asset_ids == ["yes-token"]
        yield BestBidAskEvent(
            asset_id="yes-token",
            market="0xmarket",
            best_bid=0.13,
            best_ask=0.17,
            spread=0.04,
            timestamp=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
        )


def test_polymarket_live_market_data_adapter_bootstraps_and_streams_updates() -> None:
    enricher = FakeClobEnricher()
    adapter = PolymarketLiveMarketDataAdapter(
        gamma_client=FakeGammaClient(),
        clob_enricher=enricher,
        market_event_stream=FakeEventStream(),
        snapshot_selector=lambda snapshots: [snapshot for snapshot in snapshots if snapshot.market_id == "824952"],
    )

    async def collect():
        snapshots = []
        async for snapshot in adapter.stream_snapshots():
            snapshots.append(snapshot)
            if len(snapshots) == 2:
                break
        return snapshots

    snapshots = asyncio.run(collect())

    assert len(snapshots) == 2
    assert snapshots[0].best_bid_yes == 0.12
    assert snapshots[0].best_ask_yes == 0.16
    assert snapshots[1].best_bid_yes == 0.13
    assert snapshots[1].best_ask_yes == 0.17
    assert enricher.last_market_ids == ["824952"]
