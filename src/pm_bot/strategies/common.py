"""Shared strategy helpers that stay category-agnostic."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import json
from typing import Any

from pm_bot.core.types import MarketSnapshot
from pm_bot.runtime.state import DashboardState, PositionState


def clamp_probability(value: float) -> float:
    return min(0.99, max(0.01, value))


def implied_yes_probability(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_yes is not None and snapshot.best_ask_yes is not None:
        return (snapshot.best_bid_yes + snapshot.best_ask_yes) / 2
    if snapshot.last_traded_price is not None:
        return snapshot.last_traded_price
    if snapshot.best_ask_yes is not None:
        return snapshot.best_ask_yes
    if snapshot.best_bid_yes is not None:
        return snapshot.best_bid_yes
    return None


def dashboard_state(context: Mapping[str, object]) -> DashboardState | None:
    dashboard = context.get("dashboard_state")
    if isinstance(dashboard, DashboardState):
        return dashboard
    return None


def recent_runtime_events(context: Mapping[str, object]) -> tuple[Mapping[str, Any], ...]:
    raw_events = context.get("recent_events")
    if not isinstance(raw_events, Sequence) or isinstance(raw_events, (str, bytes, bytearray)):
        return ()
    events: list[Mapping[str, Any]] = []
    for event in raw_events:
        if isinstance(event, Mapping):
            events.append(event)
    return tuple(events)


def current_position(
    *,
    snapshot: MarketSnapshot,
    dashboard: DashboardState | None,
) -> PositionState | None:
    if dashboard is None:
        return None
    return next(
        (
            position
            for position in dashboard.open_positions
            if position.market_id == snapshot.market_id
        ),
        None,
    )


def has_pending_order(
    *,
    snapshot: MarketSnapshot,
    dashboard: DashboardState | None,
) -> bool:
    if dashboard is None:
        return False
    return any(order.market_id == snapshot.market_id for order in dashboard.pending_orders)


def parse_float(metadata: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        raw_value = metadata.get(key)
        value = _coerce_float(raw_value)
        if value is not None:
            return value
    return None


def parse_probability(metadata: Mapping[str, Any], *keys: str) -> float | None:
    value = parse_float(metadata, *keys)
    if value is None:
        return None
    if value > 1:
        value = value / 100
    return clamp_probability(value)


def parse_datetime(metadata: Mapping[str, Any], *keys: str) -> datetime | None:
    for key in keys:
        raw_value = metadata.get(key)
        if not raw_value:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def parse_float_list(metadata: Mapping[str, Any], *keys: str) -> tuple[float, ...]:
    for key in keys:
        raw_value = metadata.get(key)
        parsed = _coerce_float_list(raw_value)
        if parsed:
            return parsed
    return ()


def parse_string_list(metadata: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        raw_value = metadata.get(key)
        if raw_value is None:
            continue
        if isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes, bytearray)):
            values = tuple(str(item).strip() for item in raw_value if str(item).strip())
            if values:
                return values
        text = str(raw_value).strip()
        if not text:
            continue
        if text.startswith("[") and text.endswith("]"):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, list):
                values = tuple(str(item).strip() for item in decoded if str(item).strip())
                if values:
                    return values
        values = tuple(part.strip() for part in text.replace("|", ",").split(",") if part.strip())
        if values:
            return values
    return ()


def _coerce_float(raw_value: Any) -> float | None:
    if raw_value is None or raw_value == "":
        return None
    if isinstance(raw_value, bool):
        return None
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def _coerce_float_list(raw_value: Any) -> tuple[float, ...]:
    if raw_value is None or raw_value == "":
        return ()
    if isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes, bytearray)):
        return tuple(
            value
            for item in raw_value
            if (value := _coerce_float(item)) is not None
        )

    text = str(raw_value).strip()
    if not text:
        return ()
    if text.startswith("[") and text.endswith("]"):
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return tuple(
                value
                for item in decoded
                if (value := _coerce_float(item)) is not None
            )

    return tuple(
        value
        for part in text.replace("|", ",").split(",")
        if (value := _coerce_float(part.strip())) is not None
    )
