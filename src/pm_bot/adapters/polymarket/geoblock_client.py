"""Geographic eligibility checks for Polymarket trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

GEOBLOCK_URL = "https://polymarket.com/api/geoblock"


@dataclass(slots=True, frozen=True)
class GeoblockStatus:
    blocked: bool
    country: str
    region: str
    ip: str


class GeoblockClient:
    """HTTP client for Polymarket geoblock checks."""

    def __init__(
        self,
        url: str = GEOBLOCK_URL,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "GeoblockClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()

    async def fetch_status(self) -> GeoblockStatus:
        client = await self._ensure_client()
        response = await client.get(self.url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Polymarket geoblock response was not an object")
        return parse_geoblock_status(payload)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
            self._owns_client = True
        return self._client


def fetch_geoblock_status_sync(
    url: str = GEOBLOCK_URL,
    timeout_seconds: float = 10.0,
) -> GeoblockStatus:
    """Fetch geoblock status with a synchronous request."""

    response = httpx.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Polymarket geoblock response was not an object")
    return parse_geoblock_status(payload)


def parse_geoblock_status(payload: dict[str, Any]) -> GeoblockStatus:
    """Parse a geoblock payload into a typed status."""

    return GeoblockStatus(
        blocked=bool(payload.get("blocked", False)),
        country=str(payload.get("country", "")),
        region=str(payload.get("region", "")),
        ip=str(payload.get("ip", "")),
    )
