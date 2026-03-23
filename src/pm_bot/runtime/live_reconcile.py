"""Startup reconciliation for live execution state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pm_bot.core.interfaces import RiskManager
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.order_tracker import OrderLifecycleStatus
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.runtime.live_sync import sync_live_execution_state


@dataclass(slots=True, frozen=True)
class LiveRecoveryStats:
    open_orders_recovered: int = 0
    trades_replayed: int = 0
    positions_rebuilt: int = 0


async def recover_live_state(
    *,
    risk_manager: RiskManager,
    execution: PolymarketLiveExecutionAdapter,
    snapshots: tuple[MarketSnapshot, ...] | list[MarketSnapshot],
) -> LiveRecoveryStats:
    """Rebuild local live state from authenticated CLOB order and trade history."""

    snapshot_index = _SnapshotIndex(tuple(snapshots))
    trades = await execution.fetch_trade_history()
    open_orders = await execution.fetch_open_orders()

    trades_replayed = 0
    for trade in sorted(trades, key=_trade_sort_key):
        if _replay_trade(trade=trade, execution=execution, snapshot_index=snapshot_index):
            trades_replayed += 1

    open_orders_recovered = 0
    for raw_order in open_orders:
        if _restore_open_order(raw_order=raw_order, execution=execution, snapshot_index=snapshot_index):
            open_orders_recovered += 1

    marked_positions = await sync_live_execution_state(
        risk_manager=risk_manager,
        execution=execution,
        snapshots=tuple(snapshots),
    )
    execution.drain_closed_trades()
    return LiveRecoveryStats(
        open_orders_recovered=open_orders_recovered,
        trades_replayed=trades_replayed,
        positions_rebuilt=len(marked_positions),
    )


def _restore_open_order(
    *,
    raw_order: dict[str, Any],
    execution: PolymarketLiveExecutionAdapter,
    snapshot_index: "_SnapshotIndex",
) -> bool:
    order_id = str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "")
    asset_id = str(raw_order.get("asset_id") or raw_order.get("assetId") or "")
    market_key = str(raw_order.get("market") or raw_order.get("condition_id") or "")
    if not order_id or not asset_id:
        return False

    snapshot = snapshot_index.resolve(asset_id=asset_id, market_key=market_key)
    category = snapshot.category if snapshot is not None else Category.CRYPTO
    market_id = snapshot.market_id if snapshot is not None else market_key or order_id
    created_at = _parse_timestamp(raw_order.get("created_at")) or _parse_timestamp(raw_order.get("timestamp"))
    updated_at = _parse_timestamp(raw_order.get("timestamp")) or created_at
    price = float(raw_order.get("price") or 0.0)
    original_size = float(raw_order.get("original_size") or raw_order.get("size") or 0.0)
    size_matched = float(raw_order.get("size_matched") or 0.0)
    status = _order_status(raw_order.get("status"))

    execution.tracker.restore_order(
        order_id=order_id,
        market_id=market_id,
        token_id=asset_id,
        category=category,
        strategy_id="recovered.live",
        trade_side=str(raw_order.get("side") or "BUY"),
        limit_price=price,
        requested_shares=original_size,
        requested_notional=original_size * price,
        matched_shares=size_matched,
        matched_notional=size_matched * price,
        fees_paid=0.0,
        created_at=created_at or datetime.now(tz=UTC),
        updated_at=updated_at or created_at or datetime.now(tz=UTC),
        status=status,
        last_event="reconcile:order",
    )
    return True


def _replay_trade(
    *,
    trade: dict[str, Any],
    execution: PolymarketLiveExecutionAdapter,
    snapshot_index: "_SnapshotIndex",
) -> bool:
    market_key = str(trade.get("market") or "")
    trade_time = (
        _parse_timestamp(trade.get("timestamp"))
        or _parse_timestamp(trade.get("last_update"))
        or _parse_timestamp(trade.get("matchtime"))
        or datetime.now(tz=UTC)
    )
    replayed = False

    taker_order_id = str(trade.get("taker_order_id") or "")
    asset_id = str(trade.get("asset_id") or "")
    price = float(trade.get("price") or 0.0)
    size = float(trade.get("size") or 0.0)
    if taker_order_id and asset_id and size > 0 and price > 0:
        snapshot = snapshot_index.resolve(asset_id=asset_id, market_key=market_key)
        category = snapshot.category if snapshot is not None else Category.CRYPTO
        market_id = snapshot.market_id if snapshot is not None else market_key or taker_order_id
        tracked = execution.tracker.apply_fill(
            order_id=taker_order_id,
            market_id=market_id,
            token_id=asset_id,
            category=category,
            strategy_id="recovered.live",
            trade_side=str(trade.get("side") or "BUY"),
            requested_shares=size,
            limit_price=price,
            fill_shares=size,
            fill_price=price,
            fee_rate_bps=_parse_optional_float(trade.get("fee_rate_bps")),
            event_time=trade_time,
            last_event="reconcile:trade:taker",
        )
        execution.position_ledger.apply_tracked_order(tracked)
        replayed = True

    for maker_order in trade.get("maker_orders", []) or []:
        if not isinstance(maker_order, dict):
            continue
        order_id = str(maker_order.get("order_id") or "")
        asset_id = str(maker_order.get("asset_id") or "")
        matched_amount = float(maker_order.get("matched_amount") or 0.0)
        order_price = float(maker_order.get("price") or 0.0)
        if not order_id or not asset_id or matched_amount <= 0 or order_price <= 0:
            continue
        snapshot = snapshot_index.resolve(asset_id=asset_id, market_key=market_key)
        category = snapshot.category if snapshot is not None else Category.CRYPTO
        market_id = snapshot.market_id if snapshot is not None else market_key or order_id
        tracked = execution.tracker.apply_fill(
            order_id=order_id,
            market_id=market_id,
            token_id=asset_id,
            category=category,
            strategy_id="recovered.live",
            trade_side=str(maker_order.get("side") or "BUY"),
            requested_shares=matched_amount,
            limit_price=order_price,
            fill_shares=matched_amount,
            fill_price=order_price,
            fee_rate_bps=_parse_optional_float(maker_order.get("fee_rate_bps")),
            event_time=trade_time,
            last_event="reconcile:trade:maker",
        )
        execution.position_ledger.apply_tracked_order(tracked)
        replayed = True

    return replayed


class _SnapshotIndex:
    def __init__(self, snapshots: tuple[MarketSnapshot, ...]) -> None:
        self.by_condition_id = {
            snapshot.metadata.get("condition_id", ""): snapshot
            for snapshot in snapshots
            if snapshot.metadata.get("condition_id")
        }
        self.by_asset_id = {}
        for snapshot in snapshots:
            self.by_asset_id[snapshot.token_id] = snapshot
            no_token_id = snapshot.metadata.get("no_token_id")
            if no_token_id:
                self.by_asset_id[no_token_id] = snapshot

    def resolve(self, *, asset_id: str, market_key: str) -> MarketSnapshot | None:
        if asset_id in self.by_asset_id:
            return self.by_asset_id[asset_id]
        if market_key in self.by_condition_id:
            return self.by_condition_id[market_key]
        return None


def _trade_sort_key(trade: dict[str, Any]) -> datetime:
    return (
        _parse_timestamp(trade.get("timestamp"))
        or _parse_timestamp(trade.get("last_update"))
        or _parse_timestamp(trade.get("matchtime"))
        or datetime.fromtimestamp(0, tz=UTC)
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    raw = str(value)
    if raw.isdigit():
        scale = 1000 if len(raw) > 10 else 1
        return datetime.fromtimestamp(int(raw) / scale, tz=UTC)
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _order_status(value: Any) -> OrderLifecycleStatus:
    normalized = str(value or "").strip().upper()
    if normalized in {"LIVE", "OPEN"}:
        return OrderLifecycleStatus.LIVE
    if normalized in {"CANCELED", "CANCELLED"}:
        return OrderLifecycleStatus.CANCELED
    if normalized in {"FILLED", "MATCHED"}:
        return OrderLifecycleStatus.FILLED
    if normalized in {"REJECTED", "FAILED"}:
        return OrderLifecycleStatus.REJECTED
    return OrderLifecycleStatus.UNKNOWN
