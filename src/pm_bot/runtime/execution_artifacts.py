"""Shared helpers for paper/live comparable execution artifacts."""

from __future__ import annotations

from typing import Any

from pm_bot.core.types import MarketSnapshot


def tracked_order_payload(
    *,
    order: Any,
    snapshot: MarketSnapshot | None = None,
    fill_shares_delta: float = 0.0,
    fill_notional_delta: float = 0.0,
    fees_paid_delta: float = 0.0,
    fill_source: str | None = None,
) -> dict[str, object]:
    average_fill_price = 0.0
    if getattr(order, "matched_shares", 0.0) > 0:
        average_fill_price = getattr(order, "matched_notional", 0.0) / getattr(order, "matched_shares", 0.0)
    created_at = getattr(order, "created_at", None)
    updated_at = getattr(order, "updated_at", None)
    fill_age_ms = 0.0
    if created_at is not None and updated_at is not None:
        fill_age_ms = max(
            0.0,
            (
                updated_at.astimezone(created_at.tzinfo)
                - created_at.astimezone(created_at.tzinfo)
            ).total_seconds()
            * 1000,
        )

    status = getattr(getattr(order, "status", None), "value", getattr(order, "status", ""))
    return {
        "order_id": getattr(order, "order_id", ""),
        "intent_id": getattr(order, "intent_id", None),
        "time_in_force": getattr(order, "time_in_force", "GTC"),
        "market_id": getattr(order, "market_id", ""),
        "token_id": getattr(order, "token_id", ""),
        "strategy_id": getattr(order, "strategy_id", ""),
        "trade_side": getattr(order, "trade_side", ""),
        "status": status,
        "limit_price": getattr(order, "limit_price", 0.0),
        "requested_shares": getattr(order, "requested_shares", 0.0),
        "requested_notional": getattr(order, "requested_notional", 0.0),
        "quote_ttl_seconds": getattr(order, "quote_ttl_seconds", None),
        "signal_edge_bps": getattr(order, "signal_edge_bps", None),
        "matched_shares": getattr(order, "matched_shares", 0.0),
        "matched_notional": getattr(order, "matched_notional", 0.0),
        "average_fill_price": average_fill_price,
        "fill_shares_delta": fill_shares_delta,
        "fill_notional_delta": fill_notional_delta,
        "fill_source": fill_source or "",
        "fees_paid_delta": fees_paid_delta,
        "fees_paid_total": getattr(order, "fees_paid", 0.0),
        "mid_price": (
            snapshot_mid_price_for_token(snapshot=snapshot, token_id=getattr(order, "token_id", ""))
            if snapshot is not None
            else None
        ),
        "fill_age_ms": fill_age_ms,
        "last_event": getattr(order, "last_event", ""),
        "created_at": created_at.isoformat() if created_at is not None else "",
        "updated_at": updated_at.isoformat() if updated_at is not None else "",
    }


def snapshot_mid_price_for_token(
    *,
    snapshot: MarketSnapshot,
    token_id: str,
) -> float | None:
    no_token_id = snapshot.metadata.get("no_token_id")
    if token_id == snapshot.token_id:
        direct_mid = _mid_price(snapshot.best_bid_yes, snapshot.best_ask_yes)
        if direct_mid is not None:
            return direct_mid
        complement_mid = _mid_price(snapshot.best_bid_no, snapshot.best_ask_no)
        if complement_mid is None:
            return None
        return round(1.0 - complement_mid, 6)
    if no_token_id and token_id == no_token_id:
        direct_mid = _mid_price(snapshot.best_bid_no, snapshot.best_ask_no)
        if direct_mid is not None:
            return direct_mid
        complement_mid = _mid_price(snapshot.best_bid_yes, snapshot.best_ask_yes)
        if complement_mid is None:
            return None
        return round(1.0 - complement_mid, 6)
    return None


def _mid_price(best_bid: float | None, best_ask: float | None) -> float | None:
    if best_bid is None or best_ask is None:
        return None
    return (best_bid + best_ask) / 2
