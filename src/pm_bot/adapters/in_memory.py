"""In-memory market data adapter for tests and local wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from pm_bot.core.types import MarketSnapshot


class InMemoryMarketDataAdapter:
    """Yield a predefined sequence of normalized market snapshots."""

    def __init__(self, snapshots: Sequence[MarketSnapshot]) -> None:
        self.snapshots = snapshots

    async def stream_snapshots(self) -> AsyncIterator[MarketSnapshot]:
        for snapshot in self.snapshots:
            yield snapshot

