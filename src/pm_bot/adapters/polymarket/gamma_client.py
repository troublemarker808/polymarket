"""Gamma API client and market discovery normalization.

The Gamma API is used for market discovery. This module translates event and
market payloads into the normalized domain model used by the rest of the bot.
Strategy logic does not belong here.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from pm_bot.core.types import Category, MarketSnapshot

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
HttpQueryScalar = str | int | float | bool | None
HttpQueryValue = HttpQueryScalar | Sequence[HttpQueryScalar]
HttpQueryParams = dict[str, HttpQueryValue]

_SPORTS_TAGS = {
    "sports",
    "soccer",
    "football",
    "nfl",
    "nba",
    "mlb",
    "nhl",
    "tennis",
    "golf",
    "ufc",
    "mma",
    "boxing",
    "cricket",
    "march-madness",
}
_CRYPTO_TAGS = {
    "crypto",
    "bitcoin",
    "ethereum",
    "solana",
    "defi",
    "memecoins",
    "nfts",
}
_WEATHER_TAGS = {
    "weather",
    "temperature",
    "rain",
    "snow",
    "storm",
    "storms",
    "hurricane",
}


class GammaMarketsClient:
    """Read-only Gamma client for event and market discovery."""

    def __init__(
        self,
        base_url: str = GAMMA_BASE_URL,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(max_retries, 0)
        self.retry_backoff_seconds = max(retry_backoff_seconds, 0.0)
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "GammaMarketsClient":
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()

    async def fetch_events(
        self,
        *,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        tag_id: int | None = None,
    ) -> list[dict[str, Any]]:
        await self._ensure_client()
        params: HttpQueryParams = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }
        if tag_id is not None:
            params["tag_id"] = tag_id

        payload = await self._get_json("/events", params=params)
        if not isinstance(payload, list):
            raise ValueError("Gamma /events response was not a list")

        return [event for event in payload if isinstance(event, dict)]

    async def fetch_market_by_slug(self, slug: str) -> list[MarketSnapshot]:
        await self._ensure_client()
        payload = await self._get_json("/markets", params={"slug": slug})
        if not isinstance(payload, list):
            raise ValueError("Gamma /markets response was not a list")

        snapshots: list[MarketSnapshot] = []
        for market in payload:
            if not isinstance(market, dict):
                continue
            normalized = normalize_gamma_market(market=market, event=None)
            if normalized is not None:
                snapshots.append(normalized)

        return snapshots

    async def fetch_active_binary_market_snapshots(
        self,
        *,
        page_size: int = 100,
        max_pages: int = 1,
        tag_id: int | None = None,
    ) -> list[MarketSnapshot]:
        snapshots: list[MarketSnapshot] = []

        for page_index in range(max_pages):
            offset = page_index * page_size
            events = await self.fetch_events(
                active=True,
                closed=False,
                limit=page_size,
                offset=offset,
                tag_id=tag_id,
            )
            if not events:
                break

            for event in events:
                for market in event.get("markets", []):
                    if not isinstance(market, dict):
                        continue
                    normalized = normalize_gamma_market(market=market, event=event)
                    if normalized is not None:
                        snapshots.append(normalized)

            if len(events) < page_size:
                break

        return snapshots

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)
            self._owns_client = True
        return self._client

    async def _get_json(
        self,
        path: str,
        *,
        params: HttpQueryParams,
    ) -> Any:
        client = await self._ensure_client()
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = await client.get(path, params=params)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    response.raise_for_status()
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if not _is_retryable_status(exc.response.status_code) or attempt == attempts - 1:
                    raise
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise

            await asyncio.sleep(self.retry_backoff_seconds * (attempt + 1))

        assert last_error is not None
        raise last_error


class GammaMarketDataAdapter:
    """Polling adapter backed by Gamma market discovery."""

    def __init__(
        self,
        client: GammaMarketsClient,
        *,
        page_size: int = 100,
        max_pages: int = 1,
        tag_id: int | None = None,
        poll_interval_seconds: float = 30.0,
        one_shot: bool = True,
    ) -> None:
        self.client = client
        self.page_size = page_size
        self.max_pages = max_pages
        self.tag_id = tag_id
        self.poll_interval_seconds = poll_interval_seconds
        self.one_shot = one_shot
        self._last_versions: dict[str, str] = {}

    async def stream_snapshots(self) -> AsyncIterator[MarketSnapshot]:
        while True:
            snapshots = await self.client.fetch_active_binary_market_snapshots(
                page_size=self.page_size,
                max_pages=self.max_pages,
                tag_id=self.tag_id,
            )

            for snapshot in snapshots:
                version = snapshot.metadata.get("updated_at", snapshot.timestamp.isoformat())
                if self._last_versions.get(snapshot.market_id) == version:
                    continue
                self._last_versions[snapshot.market_id] = version
                yield snapshot

            if self.one_shot:
                break

            await asyncio.sleep(self.poll_interval_seconds)


def normalize_gamma_market(
    *,
    market: dict[str, Any],
    event: dict[str, Any] | None,
) -> MarketSnapshot | None:
    """Normalize a raw Gamma market into a MarketSnapshot.

    V1 only supports binary Yes/No markets inside the supported categories.
    Unsupported categories and non-binary markets are intentionally skipped.
    """

    if not _is_tradable_market(market):
        return None

    outcomes = _parse_json_list(market.get("outcomes"))
    if not _is_binary_yes_no(outcomes):
        return None

    token_ids = _parse_json_list(market.get("clobTokenIds"))
    if len(token_ids) != 2:
        return None

    supported_category = _infer_supported_category(event=event, market=market)
    if supported_category is None:
        return None

    yes_index = outcomes.index("Yes")
    no_index = 1 - yes_index
    yes_token_id = token_ids[yes_index]
    no_token_id = token_ids[no_index]
    best_bid_yes = _parse_optional_float(market.get("bestBid"))
    best_ask_yes = _parse_optional_float(market.get("bestAsk"))
    last_trade_yes = _parse_optional_float(market.get("lastTradePrice"))
    liquidity_score = _infer_liquidity_score(event=event, market=market)
    updated_at = _parse_datetime(market.get("updatedAt")) or datetime.now(tz=UTC)

    metadata = {
        "question": str(market.get("question", "")),
        "condition_id": str(market.get("conditionId", "")),
        "no_token_id": no_token_id,
        "event_id": str((event or {}).get("id", "")),
        "event_slug": str((event or {}).get("slug", "")),
        "event_title": str((event or {}).get("title", "")),
        "resolution_source": str(market.get("resolutionSource", "")),
        "group_item_title": str(market.get("groupItemTitle", "")),
        "group_item_threshold": str(market.get("groupItemThreshold", "")),
        "accepting_orders": str(bool(market.get("acceptingOrders", False))).lower(),
        "updated_at": updated_at.isoformat(),
        "fees_enabled": str(bool(market.get("feesEnabled", False))).lower(),
    }
    if event is not None:
        metadata["tag_slugs"] = ",".join(dict.fromkeys(_extract_tag_keys(event.get("tags", []))))

    return MarketSnapshot(
        market_id=str(market["id"]),
        token_id=yes_token_id,
        slug=str(market.get("slug", "")),
        category=supported_category,
        timestamp=updated_at,
        resolution_time=_parse_datetime(market.get("endDate")),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=_infer_complement_bid(best_ask_yes),
        best_ask_no=_infer_complement_ask(best_bid_yes),
        last_traded_price=last_trade_yes,
        liquidity_score=liquidity_score,
        metadata=metadata,
    )


def _is_tradable_market(market: dict[str, Any]) -> bool:
    return bool(market.get("active")) and not bool(market.get("closed")) and bool(
        market.get("enableOrderBook", False)
    )


def _is_binary_yes_no(outcomes: Sequence[str]) -> bool:
    normalized = [outcome.strip() for outcome in outcomes]
    return len(normalized) == 2 and set(normalized) == {"Yes", "No"}


def _parse_json_list(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value]
    if isinstance(raw_value, str):
        parsed = json.loads(raw_value)
        if not isinstance(parsed, list):
            raise ValueError("Expected JSON list encoded string")
        return [str(item) for item in parsed]
    raise TypeError(f"Unsupported list payload type: {type(raw_value)!r}")


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None

    raw = str(value).replace("Z", "+00:00").replace(" ", "T")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _infer_supported_category(
    *,
    event: dict[str, Any] | None,
    market: dict[str, Any],
) -> Category | None:
    tag_keys = set(_extract_tag_keys((event or {}).get("tags", [])))
    slug_tokens = _tokenize(f"{(event or {}).get('slug', '')} {market.get('slug', '')}")
    question_tokens = _tokenize(str(market.get("question", "")))
    keys = tag_keys.union(slug_tokens).union(question_tokens)

    if keys & _SPORTS_TAGS:
        return Category.SPORTS
    if keys & _CRYPTO_TAGS:
        return Category.CRYPTO
    if keys & _WEATHER_TAGS:
        return Category.WEATHER
    return None


def _extract_tag_keys(raw_tags: Iterable[Any]) -> list[str]:
    keys: list[str] = []
    for tag in raw_tags:
        if not isinstance(tag, dict):
            continue
        for field_name in ("slug", "label"):
            raw_value = tag.get(field_name)
            if raw_value is not None:
                keys.extend(_tokenize(str(raw_value)))
    return keys


def _tokenize(raw_value: str) -> set[str]:
    lowered = raw_value.lower().replace("/", " ").replace("-", " ").replace("_", " ")
    return {token for token in lowered.split() if token}


def _infer_liquidity_score(*, event: dict[str, Any] | None, market: dict[str, Any]) -> float:
    for candidate in (market.get("competitive"), (event or {}).get("competitive")):
        if candidate is not None:
            return float(candidate)
    return 0.0


def _infer_complement_bid(best_ask_yes: float | None) -> float | None:
    if best_ask_yes is None:
        return None
    return round(1.0 - best_ask_yes, 6)


def _infer_complement_ask(best_bid_yes: float | None) -> float | None:
    if best_bid_yes is None:
        return None
    return round(1.0 - best_bid_yes, 6)


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600
