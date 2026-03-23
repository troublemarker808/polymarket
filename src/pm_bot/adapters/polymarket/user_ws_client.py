"""Authenticated Polymarket user-channel WebSocket client."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import websockets

USER_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"


@dataclass(slots=True, frozen=True)
class UserChannelAuth:
    api_key: str
    secret: str
    passphrase: str


@dataclass(slots=True, frozen=True)
class UserOrderEvent:
    id: str
    owner: str
    market: str
    asset_id: str
    side: str
    order_owner: str
    original_size: float
    size_matched: float
    price: float
    outcome: str
    order_type: str
    type: str
    status: str
    created_at: datetime | None
    expiration: datetime | None
    timestamp: datetime | None
    associate_trades: tuple[str, ...]
    maker_address: str


@dataclass(slots=True, frozen=True)
class UserMakerOrder:
    order_id: str
    owner: str
    maker_address: str
    matched_amount: float
    price: float
    fee_rate_bps: float | None
    asset_id: str
    outcome: str
    side: str


@dataclass(slots=True, frozen=True)
class UserTradeEvent:
    id: str
    type: str
    taker_order_id: str
    market: str
    asset_id: str
    side: str
    size: float
    price: float
    fee_rate_bps: float | None
    status: str
    matchtime: datetime | None
    last_update: datetime | None
    outcome: str
    owner: str
    trade_owner: str
    maker_address: str
    transaction_hash: str
    bucket_index: int | None
    maker_orders: tuple[UserMakerOrder, ...]
    trader_side: str
    timestamp: datetime | None


UserChannelEvent = UserOrderEvent | UserTradeEvent


class UserChannelClient:
    """Authenticated websocket client for user order and trade updates."""

    def __init__(self, url: str = USER_WS_URL, heartbeat_seconds: float = 10.0) -> None:
        self.url = url
        self.heartbeat_seconds = heartbeat_seconds

    async def stream_events(
        self,
        *,
        auth: UserChannelAuth,
        markets: Sequence[str] = (),
    ) -> AsyncIterator[UserChannelEvent]:
        async with websockets.connect(self.url) as websocket:
            await websocket.send(
                json.dumps(
                    {
                        "auth": {
                            "apiKey": auth.api_key,
                            "secret": auth.secret,
                            "passphrase": auth.passphrase,
                        },
                        "type": "user",
                    }
                )
            )

            if markets:
                await websocket.send(
                    json.dumps(
                        {
                            "operation": "subscribe",
                            "markets": list(markets),
                        }
                    )
                )

            heartbeat_task = asyncio.create_task(self._heartbeat(websocket))
            try:
                async for raw_message in websocket:
                    for event in parse_user_channel_payload(raw_message):
                        yield event
            finally:
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task

    async def _heartbeat(self, websocket: Any) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            await websocket.send("{}")


def parse_user_channel_payload(raw_message: str | bytes) -> list[UserChannelEvent]:
    """Parse a raw user-channel payload into typed order/trade events."""

    payload = json.loads(raw_message)
    if isinstance(payload, list):
        items = payload
    else:
        items = [payload]

    events: list[UserChannelEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event = parse_user_channel_event(item)
        if event is not None:
            events.append(event)
    return events


def parse_user_channel_event(payload: dict[str, Any]) -> UserChannelEvent | None:
    """Parse a single user-channel message."""

    event_type = payload.get("event_type")
    if event_type == "order":
        return UserOrderEvent(
            id=str(payload["id"]),
            owner=str(payload.get("owner", "")),
            market=str(payload["market"]),
            asset_id=str(payload["asset_id"]),
            side=str(payload["side"]),
            order_owner=str(payload.get("order_owner", "")),
            original_size=float(payload["original_size"]),
            size_matched=float(payload.get("size_matched", 0)),
            price=float(payload["price"]),
            outcome=str(payload.get("outcome", "")),
            order_type=str(payload.get("order_type", "")),
            type=str(payload.get("type", "")),
            status=str(payload.get("status", "")),
            created_at=_parse_ws_timestamp(payload.get("created_at")),
            expiration=_parse_ws_timestamp(payload.get("expiration")),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
            associate_trades=_parse_associated_trades(payload.get("associate_trades")),
            maker_address=str(payload.get("maker_address", "")),
        )

    if event_type == "trade":
        return UserTradeEvent(
            id=str(payload["id"]),
            type=str(payload.get("type", "")),
            taker_order_id=str(payload.get("taker_order_id", "")),
            market=str(payload["market"]),
            asset_id=str(payload["asset_id"]),
            side=str(payload["side"]),
            size=float(payload["size"]),
            price=float(payload["price"]),
            fee_rate_bps=_parse_optional_float(payload.get("fee_rate_bps")),
            status=str(payload.get("status", "")),
            matchtime=_parse_ws_timestamp(payload.get("matchtime")),
            last_update=_parse_ws_timestamp(payload.get("last_update")),
            outcome=str(payload.get("outcome", "")),
            owner=str(payload.get("owner", "")),
            trade_owner=str(payload.get("trade_owner", "")),
            maker_address=str(payload.get("maker_address", "")),
            transaction_hash=str(payload.get("transaction_hash", "")),
            bucket_index=_parse_optional_int(payload.get("bucket_index")),
            maker_orders=tuple(_parse_maker_orders(payload.get("maker_orders", []))),
            trader_side=str(payload.get("trader_side", "")),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )

    return None


def _parse_associated_trades(raw_value: Any) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if isinstance(raw_value, list):
        return tuple(str(item) for item in raw_value)
    return (str(raw_value),)


def _parse_maker_orders(raw_orders: Iterable[Any]) -> list[UserMakerOrder]:
    orders: list[UserMakerOrder] = []
    for raw_order in raw_orders:
        if not isinstance(raw_order, dict):
            continue
        orders.append(
            UserMakerOrder(
                order_id=str(raw_order["order_id"]),
                owner=str(raw_order.get("owner", "")),
                maker_address=str(raw_order.get("maker_address", "")),
                matched_amount=float(raw_order.get("matched_amount", 0)),
                price=float(raw_order["price"]),
                fee_rate_bps=_parse_optional_float(raw_order.get("fee_rate_bps")),
                asset_id=str(raw_order["asset_id"]),
                outcome=str(raw_order.get("outcome", "")),
                side=str(raw_order.get("side", "")),
            )
        )
    return orders


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_ws_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None

    raw = str(value)
    if raw.isdigit():
        scale = 1000 if len(raw) > 10 else 1
        return datetime.fromtimestamp(int(raw) / scale, tz=UTC)

    normalized = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
