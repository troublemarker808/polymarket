import asyncio
import json
from datetime import UTC, datetime

import httpx

from pm_bot.adapters.polymarket.gamma_client import (
    GammaMarketDataAdapter,
    GammaMarketsClient,
    normalize_gamma_market,
)
from pm_bot.core.types import Category


def _crypto_event_payload() -> dict[str, object]:
    return {
        "id": "16167",
        "slug": "microstrategy-sell-any-bitcoin-in-2025",
        "title": "MicroStrategy sells any Bitcoin by ___ ?",
        "competitive": 0.8795848359574281,
        "tags": [
            {"id": "21", "label": "Crypto", "slug": "crypto"},
            {"id": "120", "label": "Finance", "slug": "finance"},
        ],
        "markets": [
            {
                "id": "824952",
                "question": "MicroStrategy sells any Bitcoin by December 31, 2026?",
                "conditionId": "0x8213d395e079614d6c4d7f4cbb9be9337ab51648a21cc2a334ae8f1966d164b4",
                "slug": "microstrategy-sells-any-bitcoin-by-december-31-2026",
                "resolutionSource": "",
                "endDate": "2026-07-01T04:00:00Z",
                "active": True,
                "closed": False,
                "enableOrderBook": True,
                "acceptingOrders": True,
                "bestBid": 0.11,
                "bestAsk": 0.15,
                "lastTradePrice": 0.11,
                "updatedAt": "2026-03-23T09:42:51.763712Z",
                "outcomes": json.dumps(["Yes", "No"]),
                "clobTokenIds": json.dumps(
                    [
                        "111128191581505463501777127559667396812474366956707382672202929745167742497287",
                        "99807503632459517030616292055983105381849115736225256331133222076990620978808",
                    ]
                ),
                "feesEnabled": False,
            }
        ],
    }


def test_normalize_gamma_market_for_supported_binary_market() -> None:
    event = _crypto_event_payload()
    market = event["markets"][0]

    snapshot = normalize_gamma_market(market=market, event=event)

    assert snapshot is not None
    assert snapshot.category == Category.CRYPTO
    assert snapshot.market_id == "824952"
    assert snapshot.token_id == "111128191581505463501777127559667396812474366956707382672202929745167742497287"
    assert snapshot.best_bid_yes == 0.11
    assert snapshot.best_ask_yes == 0.15
    assert snapshot.best_bid_no == 0.85
    assert snapshot.best_ask_no == 0.89
    assert snapshot.metadata["no_token_id"] == "99807503632459517030616292055983105381849115736225256331133222076990620978808"
    assert snapshot.metadata["tag_slugs"] == "crypto,finance"
    assert snapshot.timestamp == datetime(2026, 3, 23, 9, 42, 51, 763712, tzinfo=UTC)


def test_normalize_gamma_market_skips_non_binary_yes_no_market() -> None:
    event = _crypto_event_payload()
    market = dict(event["markets"][0])
    market["outcomes"] = json.dumps(["Team A", "Team B"])

    snapshot = normalize_gamma_market(market=market, event=event)

    assert snapshot is None


def test_gamma_market_data_adapter_streams_one_shot_snapshots() -> None:
    payload = [_crypto_event_payload()]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/events"
        return httpx.Response(status_code=200, json=payload)

    transport = httpx.MockTransport(handler)
    client = GammaMarketsClient(
        client=httpx.AsyncClient(
            base_url="https://gamma-api.polymarket.com",
            transport=transport,
        )
    )
    adapter = GammaMarketDataAdapter(client=client, one_shot=True)

    async def collect() -> list[str]:
        market_ids: list[str] = []
        async for snapshot in adapter.stream_snapshots():
            market_ids.append(snapshot.market_id)
        return market_ids

    market_ids = asyncio.run(collect())

    assert market_ids == ["824952"]
