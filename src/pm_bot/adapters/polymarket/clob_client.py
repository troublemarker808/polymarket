"""Read-only CLOB client for orderbook enrichment.

V1 uses the public CLOB endpoints for best bid/ask and orderbook state before
writing any trading logic. This module stays read-only for now.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

import httpx

from pm_bot.core.types import MarketSnapshot

CLOB_BASE_URL = "https://clob.polymarket.com"


@dataclass(slots=True, frozen=True)
class OrderBookLevel:
    price: float
    size: float


@dataclass(slots=True, frozen=True)
class ClobOrderBook:
    market: str
    asset_id: str
    timestamp: datetime | None
    hash: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    min_order_size: float | None
    tick_size: float | None
    neg_risk: bool
    last_trade_price: float | None

    @property
    def best_bid(self) -> float | None:
        if not self.bids:
            return None
        return max(level.price for level in self.bids)

    @property
    def best_ask(self) -> float | None:
        if not self.asks:
            return None
        return min(level.price for level in self.asks)


class ClobPublicClient:
    """Read-only CLOB client for public order book endpoints."""

    def __init__(
        self,
        base_url: str = CLOB_BASE_URL,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "ClobPublicClient":
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()

    async def fetch_order_book(self, token_id: str) -> ClobOrderBook:
        client = await self._ensure_client()
        response = await client.get("/book", params={"token_id": token_id})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("CLOB /book response was not an object")
        return parse_clob_order_book(payload)

    async def fetch_order_books(self, token_ids: list[str]) -> list[ClobOrderBook]:
        if not token_ids:
            return []

        client = await self._ensure_client()
        response = await client.post(
            "/books",
            json=[{"token_id": token_id} for token_id in token_ids],
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("CLOB /books response was not a list")

        books: list[ClobOrderBook] = []
        for item in payload:
            if isinstance(item, dict):
                books.append(parse_clob_order_book(item))
        return books

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)
            self._owns_client = True
        return self._client


class ClobSnapshotEnricher:
    """Merge CLOB order books into normalized market snapshots."""

    def __init__(self, client: ClobPublicClient) -> None:
        self.client = client

    async def enrich_snapshot(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        book = await self.client.fetch_order_book(snapshot.token_id)
        return enrich_snapshot_with_order_book(snapshot=snapshot, book=book)

    async def enrich_snapshots(self, snapshots: list[MarketSnapshot]) -> list[MarketSnapshot]:
        if not snapshots:
            return []

        books = await self.client.fetch_order_books([snapshot.token_id for snapshot in snapshots])
        books_by_token = {book.asset_id: book for book in books}

        enriched: list[MarketSnapshot] = []
        for snapshot in snapshots:
            book = books_by_token.get(snapshot.token_id)
            enriched.append(
                enrich_snapshot_with_order_book(snapshot=snapshot, book=book)
                if book is not None
                else snapshot
            )
        return enriched


def parse_clob_order_book(payload: dict[str, Any]) -> ClobOrderBook:
    """Parse a public CLOB order book payload into a normalized structure."""

    bids = tuple(
        sorted(
            (_parse_level(level) for level in payload.get("bids", [])),
            key=lambda level: level.price,
            reverse=True,
        )
    )
    asks = tuple(sorted((_parse_level(level) for level in payload.get("asks", [])), key=lambda level: level.price))

    return ClobOrderBook(
        market=str(payload["market"]),
        asset_id=str(payload["asset_id"]),
        timestamp=_parse_clob_timestamp(payload.get("timestamp")),
        hash=str(payload.get("hash", "")),
        bids=bids,
        asks=asks,
        min_order_size=_parse_optional_float(payload.get("min_order_size")),
        tick_size=_parse_optional_float(payload.get("tick_size")),
        neg_risk=bool(payload.get("neg_risk", False)),
        last_trade_price=_parse_optional_float(payload.get("last_trade_price")),
    )


def enrich_snapshot_with_order_book(
    *,
    snapshot: MarketSnapshot,
    book: ClobOrderBook,
) -> MarketSnapshot:
    """Overlay CLOB orderbook data on top of a discovery snapshot."""

    metadata = dict(snapshot.metadata)
    metadata["clob_market_id"] = book.market
    metadata["clob_hash"] = book.hash
    metadata["clob_timestamp"] = book.timestamp.isoformat() if book.timestamp is not None else ""
    metadata["tick_size"] = "" if book.tick_size is None else str(book.tick_size)
    metadata["min_order_size"] = "" if book.min_order_size is None else str(book.min_order_size)
    metadata["neg_risk"] = str(book.neg_risk).lower()

    timestamp = book.timestamp or snapshot.timestamp

    return replace(
        snapshot,
        timestamp=timestamp,
        best_bid_yes=book.best_bid,
        best_ask_yes=book.best_ask,
        best_bid_no=_infer_complement_bid(book.best_ask),
        best_ask_no=_infer_complement_ask(book.best_bid),
        last_traded_price=book.last_trade_price,
        metadata=metadata,
    )


def _parse_level(raw_level: Any) -> OrderBookLevel:
    if not isinstance(raw_level, dict):
        raise TypeError("Order book level must be a mapping")
    return OrderBookLevel(
        price=float(raw_level["price"]),
        size=float(raw_level["size"]),
    )


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_clob_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None

    raw = str(value)
    if raw.isdigit():
        scale = 1000 if len(raw) > 10 else 1
        return datetime.fromtimestamp(int(raw) / scale, tz=UTC)

    normalized = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _infer_complement_bid(best_ask_yes: float | None) -> float | None:
    if best_ask_yes is None:
        return None
    return round(1.0 - best_ask_yes, 6)


def _infer_complement_ask(best_bid_yes: float | None) -> float | None:
    if best_bid_yes is None:
        return None
    return round(1.0 - best_bid_yes, 6)
