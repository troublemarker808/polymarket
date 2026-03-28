import asyncio
from datetime import UTC, datetime

import httpx

from pm_bot.adapters.polymarket.clob_client import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    enrich_snapshot_with_order_book,
    parse_clob_order_book,
)
from pm_bot.core.types import Category, MarketSnapshot


def _book_payload() -> dict[str, object]:
    return {
        "market": "0x8213d395e079614d6c4d7f4cbb9be9337ab51648a21cc2a334ae8f1966d164b4",
        "asset_id": "111128191581505463501777127559667396812474366956707382672202929745167742497287",
        "timestamp": "1774259408956",
        "hash": "7d36955e0c702a6c95f9f4f69801f94558ca7349",
        "bids": [
            {"price": "0.01", "size": "36244.09"},
            {"price": "0.11", "size": "736.38"},
            {"price": "0.09", "size": "4846.31"},
        ],
        "asks": [
            {"price": "0.99", "size": "14190"},
            {"price": "0.40", "size": "5342.5"},
            {"price": "0.15", "size": "1421.12"},
        ],
        "min_order_size": "5",
        "tick_size": "0.01",
        "neg_risk": False,
        "last_trade_price": "0.110",
    }


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
        metadata={"question": "MicroStrategy sells any Bitcoin by December 31, 2026?"},
    )


def test_parse_clob_order_book_uses_true_best_prices() -> None:
    book = parse_clob_order_book(_book_payload())

    assert book.best_bid == 0.11
    assert book.best_ask == 0.15
    assert book.bids[0].price == 0.11
    assert book.asks[0].price == 0.15
    assert book.timestamp == datetime.fromtimestamp(1774259408956 / 1000, tz=UTC)


def test_enrich_snapshot_with_order_book_overrides_prices() -> None:
    enriched = enrich_snapshot_with_order_book(
        snapshot=_snapshot(),
        book=parse_clob_order_book(_book_payload()),
    )

    assert enriched.best_bid_yes == 0.11
    assert enriched.best_ask_yes == 0.15
    assert enriched.best_bid_no == 0.85
    assert enriched.best_ask_no == 0.89
    assert enriched.best_bid_yes_size == 736.38
    assert enriched.best_ask_yes_size == 1421.12
    assert enriched.last_traded_price == 0.11
    assert enriched.tick_size == 0.01
    assert enriched.min_order_size == 5.0
    assert len(enriched.yes_bid_levels) == 3
    assert len(enriched.no_ask_levels) == 3
    assert enriched.metadata["tick_size"] == "0.01"
    assert enriched.metadata["min_order_size"] == "5.0"


def test_clob_snapshot_enricher_fetches_public_book() -> None:
    payload = _book_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/book"
        return httpx.Response(status_code=200, json=payload)

    transport = httpx.MockTransport(handler)
    client = ClobPublicClient(
        client=httpx.AsyncClient(
            base_url="https://clob.polymarket.com",
            transport=transport,
        )
    )
    enricher = ClobSnapshotEnricher(client=client)

    async def run() -> float | None:
        enriched = await enricher.enrich_snapshot(_snapshot())
        return enriched.best_ask_yes

    best_ask = asyncio.run(run())

    assert best_ask == 0.15
