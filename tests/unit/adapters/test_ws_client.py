import asyncio
import json
from datetime import UTC, datetime

from pm_bot.adapters.polymarket.ws_client import (
    BestBidAskEvent,
    EventMessageSummary,
    LastTradePriceEvent,
    MarketChannelSnapshotFeed,
    MarketResolvedEvent,
    parse_market_channel_payload,
)
from pm_bot.core.types import Category, MarketSnapshot


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        market_id="824952",
        token_id="111128191581505463501777127559667396812474366956707382672202929745167742497287",
        slug="microstrategy-sells-any-bitcoin-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 9, 42, 51, 763712, tzinfo=UTC),
        resolution_time=datetime(2026, 7, 1, 4, 0, tzinfo=UTC),
        best_bid_yes=0.11,
        best_ask_yes=0.15,
        last_traded_price=0.11,
        metadata={"condition_id": "0x8213d395e079614d6c4d7f4cbb9be9337ab51648a21cc2a334ae8f1966d164b4"},
    )


class FakeEventStream:
    def __init__(self, events):
        self.events = events

    async def stream_events(self, asset_ids):
        for event in self.events:
            yield event


def test_parse_market_channel_payload_best_bid_ask() -> None:
    raw = json.dumps(
        {
            "event_type": "best_bid_ask",
            "market": "0x0005c0d312de0be897668695bae9f32b624b4a1ae8b140c49f08447fcc74f442",
            "asset_id": "85354956062430465315924116860125388538595433819574542752031640332592237464430",
            "best_bid": "0.73",
            "best_ask": "0.77",
            "spread": "0.04",
            "timestamp": "1766789469958",
        }
    )

    events = parse_market_channel_payload(raw)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, BestBidAskEvent)
    assert event.best_bid == 0.73
    assert event.best_ask == 0.77
    assert event.timestamp == datetime.fromtimestamp(1766789469958 / 1000, tz=UTC)


def test_market_channel_snapshot_feed_applies_best_bid_ask_and_last_trade() -> None:
    feed = MarketChannelSnapshotFeed(
        seed_snapshots=[_snapshot()],
        event_stream=FakeEventStream(
            [
                BestBidAskEvent(
                    asset_id=_snapshot().token_id,
                    market="0xmarket",
                    best_bid=0.12,
                    best_ask=0.18,
                    spread=0.06,
                    timestamp=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                ),
                LastTradePriceEvent(
                    asset_id=_snapshot().token_id,
                    market="0xmarket",
                    fee_rate_bps=0.0,
                    price=0.17,
                    side="BUY",
                    size=25.0,
                    timestamp=datetime(2026, 3, 23, 10, 0, 1, tzinfo=UTC),
                ),
            ]
        ),
    )

    async def collect():
        snapshots = []
        async for snapshot in feed.stream_snapshots(include_initial=False):
            snapshots.append(snapshot)
        return snapshots

    snapshots = asyncio.run(collect())

    assert len(snapshots) == 2
    assert snapshots[0].best_bid_yes == 0.12
    assert snapshots[0].best_ask_yes == 0.18
    assert snapshots[0].best_bid_no == 0.82
    assert snapshots[0].best_ask_no == 0.88
    assert snapshots[1].last_traded_price == 0.17
    assert snapshots[1].metadata["last_trade_side"] == "BUY"


def test_market_channel_snapshot_feed_marks_market_resolved() -> None:
    token_id = _snapshot().token_id
    feed = MarketChannelSnapshotFeed(
        seed_snapshots=[_snapshot()],
        event_stream=FakeEventStream(
            [
                MarketResolvedEvent(
                    id="1031769",
                    question="Will NVIDIA (NVDA) close above $240 end of January?",
                    market="0xmarket",
                    slug="nvda-above-240-on-january-30-2026",
                    description="This market will resolve to yes on official close.",
                    asset_ids=(token_id, "no-token"),
                outcomes=("Yes", "No"),
                winning_asset_id=token_id,
                winning_outcome="Yes",
                    event_message=EventMessageSummary(
                        id="125819",
                        slug="nvda-above-in-january-2026",
                        title="Will NVIDIA (NVDA) close above ___ end of January?",
                        description="This market will resolve to yes on official close.",
                    ),
                    timestamp=datetime(2026, 3, 23, 10, 0, 2, tzinfo=UTC),
                )
            ]
        ),
    )

    async def collect():
        async for snapshot in feed.stream_snapshots(include_initial=False):
            return snapshot
        return None

    snapshot = asyncio.run(collect())

    assert snapshot is not None
    assert snapshot.metadata["resolved"] == "true"
    assert snapshot.metadata["winning_outcome"] == "Yes"
