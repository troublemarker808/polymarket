"""Unified Polymarket market-data adapter.

This adapter composes Gamma discovery, optional CLOB enrichment, and optional
WebSocket updates into a single MarketDataAdapter-compatible stream.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from pm_bot.adapters.polymarket.clob_client import ClobSnapshotEnricher
from pm_bot.adapters.polymarket.gamma_client import GammaMarketsClient
from pm_bot.adapters.polymarket.ws_client import MarketChannelSnapshotFeed, MarketEventStream
from pm_bot.core.types import MarketSnapshot


class PolymarketLiveMarketDataAdapter:
    """Compose discovery, orderbook enrichment, and live updates."""

    def __init__(
        self,
        gamma_client: GammaMarketsClient,
        *,
        clob_enricher: ClobSnapshotEnricher | None = None,
        market_event_stream: MarketEventStream | None = None,
        page_size: int = 100,
        max_pages: int = 1,
        tag_id: int | None = None,
    ) -> None:
        self.gamma_client = gamma_client
        self.clob_enricher = clob_enricher
        self.market_event_stream = market_event_stream
        self.page_size = page_size
        self.max_pages = max_pages
        self.tag_id = tag_id

    async def bootstrap_snapshots(self) -> list[MarketSnapshot]:
        snapshots = await self.gamma_client.fetch_active_binary_market_snapshots(
            page_size=self.page_size,
            max_pages=self.max_pages,
            tag_id=self.tag_id,
        )
        if self.clob_enricher is not None:
            snapshots = await self.clob_enricher.enrich_snapshots(snapshots)
        return snapshots

    async def stream_snapshots(self) -> AsyncIterator[MarketSnapshot]:
        snapshots = await self.bootstrap_snapshots()
        async for snapshot in self.stream_from_snapshots(snapshots, include_initial=True):
            yield snapshot

    async def stream_from_snapshots(
        self,
        snapshots: list[MarketSnapshot],
        *,
        include_initial: bool,
    ) -> AsyncIterator[MarketSnapshot]:
        if self.market_event_stream is None:
            if include_initial:
                for snapshot in snapshots:
                    yield snapshot
            return

        feed = MarketChannelSnapshotFeed(
            seed_snapshots=snapshots,
            event_stream=self.market_event_stream,
        )
        async for snapshot in feed.stream_snapshots(include_initial=include_initial):
            yield snapshot
