"""Public market WebSocket client and snapshot updater.

This module is read-only in V1. It consumes Polymarket market-channel events and
applies them to normalized market snapshots.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol, TypedDict

import websockets

from pm_bot.core.types import MarketSnapshot, OrderBookLevel

MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
_PRICE_EPSILON = 1e-9


class TopOfBookDepthFields(TypedDict):
    best_bid_yes_size: float | None
    best_ask_yes_size: float | None
    best_bid_no_size: float | None
    best_ask_no_size: float | None
    yes_bid_levels: tuple[OrderBookLevel, ...]
    yes_ask_levels: tuple[OrderBookLevel, ...]
    no_bid_levels: tuple[OrderBookLevel, ...]
    no_ask_levels: tuple[OrderBookLevel, ...]


@dataclass(slots=True, frozen=True)
class BookEvent:
    asset_id: str
    market: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    timestamp: datetime | None
    hash: str


@dataclass(slots=True, frozen=True)
class PriceLevelChange:
    asset_id: str
    price: float
    size: float
    side: str
    hash: str
    best_bid: float | None
    best_ask: float | None


@dataclass(slots=True, frozen=True)
class PriceChangeEvent:
    market: str
    price_changes: tuple[PriceLevelChange, ...]
    timestamp: datetime | None


@dataclass(slots=True, frozen=True)
class TickSizeChangeEvent:
    asset_id: str
    market: str
    old_tick_size: float
    new_tick_size: float
    timestamp: datetime | None


@dataclass(slots=True, frozen=True)
class LastTradePriceEvent:
    asset_id: str
    market: str
    fee_rate_bps: float | None
    price: float
    side: str
    size: float
    timestamp: datetime | None


@dataclass(slots=True, frozen=True)
class BestBidAskEvent:
    asset_id: str
    market: str
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    timestamp: datetime | None


@dataclass(slots=True, frozen=True)
class EventMessageSummary:
    id: str
    slug: str
    title: str
    description: str


@dataclass(slots=True, frozen=True)
class NewMarketEvent:
    id: str
    question: str
    market: str
    slug: str
    description: str
    asset_ids: tuple[str, ...]
    outcomes: tuple[str, ...]
    event_message: EventMessageSummary
    timestamp: datetime | None


@dataclass(slots=True, frozen=True)
class MarketResolvedEvent:
    id: str
    question: str
    market: str
    slug: str
    description: str
    asset_ids: tuple[str, ...]
    outcomes: tuple[str, ...]
    winning_asset_id: str
    winning_outcome: str
    event_message: EventMessageSummary
    timestamp: datetime | None


MarketChannelEvent = (
    BookEvent
    | PriceChangeEvent
    | TickSizeChangeEvent
    | LastTradePriceEvent
    | BestBidAskEvent
    | NewMarketEvent
    | MarketResolvedEvent
)


class MarketEventStream(Protocol):
    def stream_events(self, asset_ids: Sequence[str]) -> AsyncIterator[MarketChannelEvent]:
        ...


class MarketChannelClient:
    """Read-only Polymarket market-channel WebSocket client."""

    def __init__(self, url: str = MARKET_WS_URL) -> None:
        self.url = url

    async def stream_events(self, asset_ids: Sequence[str]) -> AsyncIterator[MarketChannelEvent]:
        if not asset_ids:
            return

        async with websockets.connect(self.url) as websocket:
            await websocket.send(
                json.dumps(
                    {
                        "assets_ids": list(asset_ids),
                        "type": "market",
                        "custom_feature_enabled": True,
                    }
                )
            )

            async for raw_message in websocket:
                for event in parse_market_channel_payload(raw_message):
                    yield event


class MarketChannelSnapshotFeed:
    """Apply market-channel events to an in-memory set of snapshots."""

    def __init__(
        self,
        seed_snapshots: Sequence[MarketSnapshot],
        event_stream: MarketEventStream,
    ) -> None:
        self.event_stream = event_stream
        self.snapshots_by_token = {snapshot.token_id: snapshot for snapshot in seed_snapshots}
        self.market_to_token = {snapshot.metadata.get("condition_id", ""): snapshot.token_id for snapshot in seed_snapshots}

    async def stream_snapshots(self, include_initial: bool = True) -> AsyncIterator[MarketSnapshot]:
        if include_initial:
            for snapshot in self.snapshots_by_token.values():
                yield snapshot

        asset_ids = list(self.snapshots_by_token)
        async for event in self.event_stream.stream_events(asset_ids=asset_ids):
            updated = self._apply_event(event)
            if updated is not None:
                self.snapshots_by_token[updated.token_id] = updated
                yield updated

    def _apply_event(self, event: MarketChannelEvent) -> MarketSnapshot | None:
        if isinstance(event, BestBidAskEvent):
            return self._apply_best_bid_ask(event)
        if isinstance(event, LastTradePriceEvent):
            return self._apply_last_trade_price(event)
        if isinstance(event, BookEvent):
            return self._apply_book_event(event)
        if isinstance(event, PriceChangeEvent):
            return self._apply_price_change(event)
        if isinstance(event, TickSizeChangeEvent):
            return self._apply_tick_size_change(event)
        if isinstance(event, MarketResolvedEvent):
            return self._apply_market_resolved(event)
        return None

    def _apply_best_bid_ask(self, event: BestBidAskEvent) -> MarketSnapshot | None:
        snapshot = self.snapshots_by_token.get(event.asset_id)
        if snapshot is None:
            return None

        metadata = dict(snapshot.metadata)
        metadata["ws_event"] = "best_bid_ask"
        metadata["ws_market"] = event.market
        depth_fields = _depth_fields_for_top_of_book(
            snapshot=snapshot,
            best_bid=event.best_bid,
            best_ask=event.best_ask,
        )

        return replace(
            snapshot,
            timestamp=_coalesce_event_timestamp(snapshot=snapshot, event_timestamp=event.timestamp),
            best_bid_yes=event.best_bid,
            best_ask_yes=event.best_ask,
            best_bid_no=_infer_complement_bid(event.best_ask),
            best_ask_no=_infer_complement_ask(event.best_bid),
            best_bid_yes_size=depth_fields["best_bid_yes_size"],
            best_ask_yes_size=depth_fields["best_ask_yes_size"],
            best_bid_no_size=depth_fields["best_bid_no_size"],
            best_ask_no_size=depth_fields["best_ask_no_size"],
            yes_bid_levels=depth_fields["yes_bid_levels"],
            yes_ask_levels=depth_fields["yes_ask_levels"],
            no_bid_levels=depth_fields["no_bid_levels"],
            no_ask_levels=depth_fields["no_ask_levels"],
            metadata=metadata,
        )

    def _apply_last_trade_price(self, event: LastTradePriceEvent) -> MarketSnapshot | None:
        snapshot = self.snapshots_by_token.get(event.asset_id)
        if snapshot is None:
            return None

        event_timestamp = _coalesce_event_timestamp(snapshot=snapshot, event_timestamp=event.timestamp)
        metadata = dict(snapshot.metadata)
        metadata["ws_event"] = "last_trade_price"
        metadata["last_trade_side"] = event.side
        metadata["last_trade_size"] = str(event.size)
        metadata["last_trade_event_at"] = event_timestamp.isoformat()

        return replace(
            snapshot,
            timestamp=event_timestamp,
            last_traded_price=event.price,
            last_trade_side=event.side,
            last_trade_size=event.size,
            metadata=metadata,
        )

    def _apply_book_event(self, event: BookEvent) -> MarketSnapshot | None:
        snapshot = self.snapshots_by_token.get(event.asset_id)
        if snapshot is None:
            return None

        best_bid = max((level.price for level in event.bids), default=None)
        best_ask = min((level.price for level in event.asks), default=None)
        metadata = dict(snapshot.metadata)
        metadata["ws_event"] = "book"
        metadata["ws_book_hash"] = event.hash
        yes_bid_levels = tuple(sorted(event.bids, key=lambda level: level.price, reverse=True))
        yes_ask_levels = tuple(sorted(event.asks, key=lambda level: level.price))
        no_bid_levels = _complement_bid_levels(yes_ask_levels)
        no_ask_levels = _complement_ask_levels(yes_bid_levels)

        return replace(
            snapshot,
            timestamp=_coalesce_event_timestamp(snapshot=snapshot, event_timestamp=event.timestamp),
            best_bid_yes=best_bid,
            best_ask_yes=best_ask,
            best_bid_no=_infer_complement_bid(best_ask),
            best_ask_no=_infer_complement_ask(best_bid),
            best_bid_yes_size=_best_level_size(yes_bid_levels),
            best_ask_yes_size=_best_level_size(yes_ask_levels),
            best_bid_no_size=_best_level_size(no_bid_levels),
            best_ask_no_size=_best_level_size(no_ask_levels),
            yes_bid_levels=yes_bid_levels,
            yes_ask_levels=yes_ask_levels,
            no_bid_levels=no_bid_levels,
            no_ask_levels=no_ask_levels,
            metadata=metadata,
        )

    def _apply_price_change(self, event: PriceChangeEvent) -> MarketSnapshot | None:
        updated_snapshot: MarketSnapshot | None = None
        for change in event.price_changes:
            snapshot = self.snapshots_by_token.get(change.asset_id)
            if snapshot is None:
                continue

            metadata = dict(snapshot.metadata)
            metadata["ws_event"] = "price_change"
            metadata["ws_price_change_side"] = change.side
            metadata["ws_price_change_hash"] = change.hash
            depth_fields = _depth_fields_for_top_of_book(
                snapshot=snapshot,
                best_bid=change.best_bid,
                best_ask=change.best_ask,
            )

            updated_snapshot = replace(
                snapshot,
                timestamp=_coalesce_event_timestamp(snapshot=snapshot, event_timestamp=event.timestamp),
                best_bid_yes=change.best_bid,
                best_ask_yes=change.best_ask,
                best_bid_no=_infer_complement_bid(change.best_ask),
                best_ask_no=_infer_complement_ask(change.best_bid),
                best_bid_yes_size=depth_fields["best_bid_yes_size"],
                best_ask_yes_size=depth_fields["best_ask_yes_size"],
                best_bid_no_size=depth_fields["best_bid_no_size"],
                best_ask_no_size=depth_fields["best_ask_no_size"],
                yes_bid_levels=depth_fields["yes_bid_levels"],
                yes_ask_levels=depth_fields["yes_ask_levels"],
                no_bid_levels=depth_fields["no_bid_levels"],
                no_ask_levels=depth_fields["no_ask_levels"],
                metadata=metadata,
            )
            self.snapshots_by_token[change.asset_id] = updated_snapshot

        return updated_snapshot

    def _apply_tick_size_change(self, event: TickSizeChangeEvent) -> MarketSnapshot | None:
        snapshot = self.snapshots_by_token.get(event.asset_id)
        if snapshot is None:
            return None

        metadata = dict(snapshot.metadata)
        metadata["ws_event"] = "tick_size_change"
        metadata["tick_size"] = str(event.new_tick_size)
        metadata["old_tick_size"] = str(event.old_tick_size)

        return replace(
            snapshot,
            timestamp=_coalesce_event_timestamp(snapshot=snapshot, event_timestamp=event.timestamp),
            metadata=metadata,
        )

    def _apply_market_resolved(self, event: MarketResolvedEvent) -> MarketSnapshot | None:
        if event.winning_asset_id not in self.snapshots_by_token:
            return None

        snapshot = self.snapshots_by_token[event.winning_asset_id]
        metadata = dict(snapshot.metadata)
        metadata["ws_event"] = "market_resolved"
        metadata["resolved"] = "true"
        metadata["winning_outcome"] = event.winning_outcome
        metadata["winning_asset_id"] = event.winning_asset_id

        return replace(
            snapshot,
            timestamp=_coalesce_event_timestamp(snapshot=snapshot, event_timestamp=event.timestamp),
            metadata=metadata,
        )


def parse_market_channel_payload(raw_message: str | bytes) -> list[MarketChannelEvent]:
    """Parse a raw market-channel WebSocket payload into normalized events."""

    payload = json.loads(raw_message)
    if isinstance(payload, list):
        items = payload
    else:
        items = [payload]

    events: list[MarketChannelEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event = parse_market_channel_event(item)
        if event is not None:
            events.append(event)
    return events


def parse_market_channel_event(payload: dict[str, Any]) -> MarketChannelEvent | None:
    """Parse a single market-channel event object."""

    event_type = payload.get("event_type")
    if event_type == "book":
        return BookEvent(
            asset_id=str(payload["asset_id"]),
            market=str(payload["market"]),
            bids=tuple(sorted(_parse_levels(payload.get("bids", [])), key=lambda level: level.price, reverse=True)),
            asks=tuple(sorted(_parse_levels(payload.get("asks", [])), key=lambda level: level.price)),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
            hash=str(payload.get("hash", "")),
        )
    if event_type == "price_change":
        return PriceChangeEvent(
            market=str(payload["market"]),
            price_changes=tuple(_parse_price_changes(payload.get("price_changes", []))),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )
    if event_type == "tick_size_change":
        return TickSizeChangeEvent(
            asset_id=str(payload["asset_id"]),
            market=str(payload["market"]),
            old_tick_size=float(payload["old_tick_size"]),
            new_tick_size=float(payload["new_tick_size"]),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )
    if event_type == "last_trade_price":
        return LastTradePriceEvent(
            asset_id=str(payload["asset_id"]),
            market=str(payload["market"]),
            fee_rate_bps=_parse_optional_float(payload.get("fee_rate_bps")),
            price=float(payload["price"]),
            side=str(payload["side"]),
            size=float(payload["size"]),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )
    if event_type == "best_bid_ask":
        return BestBidAskEvent(
            asset_id=str(payload["asset_id"]),
            market=str(payload["market"]),
            best_bid=_parse_optional_float(payload.get("best_bid")),
            best_ask=_parse_optional_float(payload.get("best_ask")),
            spread=_parse_optional_float(payload.get("spread")),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )
    if event_type == "new_market":
        return NewMarketEvent(
            id=str(payload["id"]),
            question=str(payload["question"]),
            market=str(payload["market"]),
            slug=str(payload["slug"]),
            description=str(payload.get("description", "")),
            asset_ids=tuple(str(asset_id) for asset_id in payload.get("assets_ids", [])),
            outcomes=tuple(str(outcome) for outcome in payload.get("outcomes", [])),
            event_message=_parse_event_message(payload.get("event_message")),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )
    if event_type == "market_resolved":
        return MarketResolvedEvent(
            id=str(payload["id"]),
            question=str(payload["question"]),
            market=str(payload["market"]),
            slug=str(payload["slug"]),
            description=str(payload.get("description", "")),
            asset_ids=tuple(str(asset_id) for asset_id in payload.get("assets_ids", [])),
            outcomes=tuple(str(outcome) for outcome in payload.get("outcomes", [])),
            winning_asset_id=str(payload["winning_asset_id"]),
            winning_outcome=str(payload["winning_outcome"]),
            event_message=_parse_event_message(payload.get("event_message")),
            timestamp=_parse_ws_timestamp(payload.get("timestamp")),
        )
    return None


def _parse_levels(raw_levels: Iterable[Any]) -> list[OrderBookLevel]:
    levels: list[OrderBookLevel] = []
    for level in raw_levels:
        if not isinstance(level, dict):
            continue
        levels.append(OrderBookLevel(price=float(level["price"]), size=float(level["size"])))
    return levels


def _parse_price_changes(raw_changes: Iterable[Any]) -> list[PriceLevelChange]:
    changes: list[PriceLevelChange] = []
    for change in raw_changes:
        if not isinstance(change, dict):
            continue
        changes.append(
            PriceLevelChange(
                asset_id=str(change["asset_id"]),
                price=float(change["price"]),
                size=float(change["size"]),
                side=str(change["side"]),
                hash=str(change.get("hash", "")),
                best_bid=_parse_optional_float(change.get("best_bid")),
                best_ask=_parse_optional_float(change.get("best_ask")),
            )
        )
    return changes


def _parse_event_message(raw_summary: Any) -> EventMessageSummary:
    if not isinstance(raw_summary, dict):
        return EventMessageSummary(id="", slug="", title="", description="")
    return EventMessageSummary(
        id=str(raw_summary.get("id", "")),
        slug=str(raw_summary.get("slug", "")),
        title=str(raw_summary.get("title", "")),
        description=str(raw_summary.get("description", "")),
    )


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_ws_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None

    raw = str(value)
    if raw.isdigit():
        scale = 1000 if len(raw) > 10 else 1
        return datetime.fromtimestamp(int(raw) / scale, tz=UTC)

    normalized = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _coalesce_event_timestamp(
    *,
    snapshot: MarketSnapshot,
    event_timestamp: datetime | None,
) -> datetime:
    if event_timestamp is None or event_timestamp < snapshot.timestamp:
        return snapshot.timestamp
    return event_timestamp


def _infer_complement_bid(best_ask_yes: float | None) -> float | None:
    if best_ask_yes is None:
        return None
    return round(1.0 - best_ask_yes, 6)


def _infer_complement_ask(best_bid_yes: float | None) -> float | None:
    if best_bid_yes is None:
        return None
    return round(1.0 - best_bid_yes, 6)


def _depth_fields_for_top_of_book(
    *,
    snapshot: MarketSnapshot,
    best_bid: float | None,
    best_ask: float | None,
) -> TopOfBookDepthFields:
    if _book_depth_matches_top_of_book(snapshot=snapshot, best_bid=best_bid, best_ask=best_ask):
        return {
            "best_bid_yes_size": snapshot.best_bid_yes_size,
            "best_ask_yes_size": snapshot.best_ask_yes_size,
            "best_bid_no_size": snapshot.best_bid_no_size,
            "best_ask_no_size": snapshot.best_ask_no_size,
            "yes_bid_levels": snapshot.yes_bid_levels,
            "yes_ask_levels": snapshot.yes_ask_levels,
            "no_bid_levels": snapshot.no_bid_levels,
            "no_ask_levels": snapshot.no_ask_levels,
        }
    return {
        "best_bid_yes_size": None,
        "best_ask_yes_size": None,
        "best_bid_no_size": None,
        "best_ask_no_size": None,
        "yes_bid_levels": (),
        "yes_ask_levels": (),
        "no_bid_levels": (),
        "no_ask_levels": (),
    }


def _book_depth_matches_top_of_book(
    *,
    snapshot: MarketSnapshot,
    best_bid: float | None,
    best_ask: float | None,
) -> bool:
    return _levels_match_summary(
        levels=snapshot.yes_bid_levels,
        summary_price=best_bid,
    ) and _levels_match_summary(
        levels=snapshot.yes_ask_levels,
        summary_price=best_ask,
    )


def _levels_match_summary(
    *,
    levels: tuple[OrderBookLevel, ...],
    summary_price: float | None,
) -> bool:
    if not levels:
        return True
    if summary_price is None:
        return False
    return abs(levels[0].price - summary_price) <= _PRICE_EPSILON


def _best_level_size(levels: tuple[OrderBookLevel, ...]) -> float | None:
    if not levels:
        return None
    return levels[0].size


def _complement_bid_levels(levels: tuple[OrderBookLevel, ...]) -> tuple[OrderBookLevel, ...]:
    return tuple(
        sorted(
            (
                OrderBookLevel(price=round(1.0 - level.price, 6), size=level.size)
                for level in levels
            ),
            key=lambda level: level.price,
            reverse=True,
        )
    )


def _complement_ask_levels(levels: tuple[OrderBookLevel, ...]) -> tuple[OrderBookLevel, ...]:
    return tuple(
        sorted(
            (
                OrderBookLevel(price=round(1.0 - level.price, 6), size=level.size)
                for level in levels
            ),
            key=lambda level: level.price,
        )
    )
