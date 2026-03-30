"""Startup reconciliation for live execution state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pm_bot.core.interfaces import RiskManager
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.exposure_keys import derive_exposure_keys
from pm_bot.execution.order_tracker import OrderLifecycleStatus
from pm_bot.execution.polymarket_live import (
    PolymarketLiveExecutionAdapter,
    canonical_trade_fingerprint,
)
from pm_bot.runtime.live_sync import sync_live_execution_state


@dataclass(slots=True, frozen=True)
class LiveRecoveryStats:
    open_orders_recovered: int = 0
    trades_replayed: int = 0
    positions_rebuilt: int = 0
    historical_open_orders_skipped: int = 0
    historical_trades_skipped: int = 0


async def recover_live_state(
    *,
    risk_manager: RiskManager,
    execution: PolymarketLiveExecutionAdapter,
    snapshots: tuple[MarketSnapshot, ...] | list[MarketSnapshot],
    recovery_scope: str = "full",
    session_started_at: datetime | None = None,
) -> LiveRecoveryStats:
    """Rebuild local live state from authenticated CLOB order and trade history."""

    trades = await execution.fetch_trade_history()
    open_orders = await execution.fetch_open_orders()
    if recovery_scope not in {"full", "session"}:
        raise ValueError(f"Unsupported live recovery scope: {recovery_scope}")
    if recovery_scope == "session":
        if session_started_at is None:
            raise ValueError("session_started_at is required when recovery_scope='session'")
        replayable_trades = [
            trade
            for trade in trades
            if _trade_within_session(trade=trade, session_started_at=session_started_at)
        ]
        replayable_open_orders = [
            raw_order
            for raw_order in open_orders
            if _open_order_within_session(raw_order=raw_order, session_started_at=session_started_at)
        ]
    else:
        replayable_trades = list(trades)
        replayable_open_orders = list(open_orders)
    snapshot_index = _SnapshotIndex(tuple(snapshots))
    snapshot_index.hydrate_from_history(
        trades=tuple(replayable_trades),
        open_orders=tuple(replayable_open_orders),
    )
    execution.position_ledger.register_snapshots(snapshot_index.snapshots())

    trades_replayed = 0
    for trade in sorted(replayable_trades, key=_trade_sort_key):
        if _replay_trade(trade=trade, execution=execution, snapshot_index=snapshot_index):
            trades_replayed += 1

    open_orders_recovered = 0
    for raw_order in replayable_open_orders:
        if _restore_open_order(raw_order=raw_order, execution=execution, snapshot_index=snapshot_index):
            open_orders_recovered += 1

    state = getattr(risk_manager, "state", None)
    if state is not None:
        state.processed_trade_ids = tuple(sorted(execution.processed_trade_ids))
    marked_positions = await sync_live_execution_state(
        risk_manager=risk_manager,
        execution=execution,
        snapshots=tuple(snapshots),
    )
    recovery_date = datetime.now(tz=UTC).date()
    for closed_trade in execution.drain_closed_trades():
        if closed_trade.closed_at.astimezone(UTC).date() != recovery_date:
            continue
        await risk_manager.record_trade_close(closed_trade)
    return LiveRecoveryStats(
        open_orders_recovered=open_orders_recovered,
        trades_replayed=trades_replayed,
        positions_rebuilt=len(marked_positions),
        historical_open_orders_skipped=len(open_orders) - len(replayable_open_orders),
        historical_trades_skipped=len(trades) - len(replayable_trades),
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
    if execution.tracker.get(order_id) is not None:
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
        intent_id=None,
        market_id=market_id,
        token_id=asset_id,
        category=category,
        strategy_id="recovered.live",
        trade_side=str(raw_order.get("side") or "BUY"),
        limit_price=price,
        requested_shares=original_size,
        requested_notional=original_size * price,
        quote_ttl_seconds=None,
        exposure_group_id=_snapshot_exposure_group_id(snapshot),
        thesis_group_id=_snapshot_thesis_group_id(
            snapshot,
            trade_side=raw_order.get("side"),
            token_id=asset_id,
        ),
        underlying_group_id=_snapshot_underlying_group_id(snapshot),
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
    trade_id = _trade_identifier(trade)
    if trade_id and execution.has_processed_trade_id(trade_id):
        return False

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
    trader_side = str(trade.get("trader_side") or "").strip().upper()

    if trader_side != "MAKER" and taker_order_id and asset_id and size > 0 and price > 0:
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
            exposure_group_id=_snapshot_exposure_group_id(snapshot),
            thesis_group_id=_snapshot_thesis_group_id(
                snapshot,
                trade_side=trade.get("side"),
                token_id=asset_id,
            ),
            underlying_group_id=_snapshot_underlying_group_id(snapshot),
        )
        execution.position_ledger.apply_tracked_order(tracked)
        replayed = True

    if trader_side != "MAKER":
        if replayed and trade_id:
            execution.mark_processed_trade_id(trade_id)
        return replayed

    maker_orders = _select_local_maker_orders(
        maker_orders=trade.get("maker_orders", []) or [],
        execution=execution,
    )
    for maker_order in maker_orders:
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
            exposure_group_id=_snapshot_exposure_group_id(snapshot),
            thesis_group_id=_snapshot_thesis_group_id(
                snapshot,
                trade_side=maker_order.get("side"),
                token_id=asset_id,
            ),
            underlying_group_id=_snapshot_underlying_group_id(snapshot),
        )
        execution.position_ledger.apply_tracked_order(tracked)
        replayed = True

    if replayed and trade_id:
        execution.mark_processed_trade_id(trade_id)
    return replayed


def _select_local_maker_orders(
    *,
    maker_orders: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    execution: PolymarketLiveExecutionAdapter,
) -> tuple[dict[str, Any], ...]:
    normalized_orders = tuple(order for order in maker_orders if isinstance(order, dict))
    if not normalized_orders:
        return ()
    if execution.account_addresses:
        return tuple(
            order
            for order in normalized_orders
            if execution.matches_account_address(order.get("maker_address"))
        )
    if len(normalized_orders) == 1:
        return normalized_orders
    return ()


class _SnapshotIndex:
    def __init__(self, snapshots: tuple[MarketSnapshot, ...]) -> None:
        self._snapshots_by_market_id: dict[str, MarketSnapshot] = {}
        self.by_condition_id: dict[str, MarketSnapshot] = {
            snapshot.metadata.get("condition_id", ""): snapshot
            for snapshot in snapshots
            if snapshot.metadata.get("condition_id")
        }
        self.by_asset_id: dict[str, MarketSnapshot] = {}
        for snapshot in snapshots:
            self._register_snapshot(snapshot)

    def resolve(self, *, asset_id: str, market_key: str) -> MarketSnapshot | None:
        if asset_id in self.by_asset_id:
            return self.by_asset_id[asset_id]
        if market_key in self.by_condition_id:
            return self.by_condition_id[market_key]
        return None

    def snapshots(self) -> tuple[MarketSnapshot, ...]:
        return tuple(self._snapshots_by_market_id.values())

    def hydrate_from_history(
        self,
        *,
        trades: tuple[dict[str, Any], ...],
        open_orders: tuple[dict[str, Any], ...],
    ) -> None:
        asset_ids_by_market: dict[str, set[str]] = {}

        for trade in trades:
            market_key = str(trade.get("market") or "")
            if market_key:
                asset_ids_by_market.setdefault(market_key, set())
                asset_id = str(trade.get("asset_id") or "")
                if asset_id:
                    asset_ids_by_market[market_key].add(asset_id)
                for maker_order in trade.get("maker_orders", []) or []:
                    if not isinstance(maker_order, dict):
                        continue
                    maker_asset_id = str(maker_order.get("asset_id") or "")
                    if maker_asset_id:
                        asset_ids_by_market[market_key].add(maker_asset_id)

        for raw_order in open_orders:
            market_key = str(raw_order.get("market") or raw_order.get("condition_id") or "")
            asset_id = str(raw_order.get("asset_id") or raw_order.get("assetId") or "")
            if not market_key or not asset_id:
                continue
            asset_ids_by_market.setdefault(market_key, set()).add(asset_id)

        now = datetime.now(tz=UTC)
        for market_key, asset_ids in asset_ids_by_market.items():
            if market_key in self.by_condition_id or len(asset_ids) < 2:
                continue
            primary_token_id, complement_token_id = sorted(asset_ids)[:2]
            synthetic_snapshot = MarketSnapshot(
                market_id=market_key,
                token_id=primary_token_id,
                slug=market_key,
                category=Category.CRYPTO,
                timestamp=now,
                resolution_time=None,
                best_bid_yes=None,
                best_ask_yes=None,
                best_bid_no=None,
                best_ask_no=None,
                last_traded_price=None,
                metadata={
                    "condition_id": market_key,
                    "no_token_id": complement_token_id,
                    "synthetic_history_market": "true",
                },
            )
            self._register_snapshot(synthetic_snapshot)

    def _register_snapshot(self, snapshot: MarketSnapshot) -> None:
        self._snapshots_by_market_id[snapshot.market_id] = snapshot
        condition_id = snapshot.metadata.get("condition_id", "")
        if condition_id:
            self.by_condition_id[condition_id] = snapshot
        self.by_asset_id[snapshot.token_id] = snapshot
        no_token_id = snapshot.metadata.get("no_token_id")
        if no_token_id:
            self.by_asset_id[no_token_id] = snapshot


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


def _trade_identifier(trade: dict[str, Any]) -> str:
    explicit_trade_id = str(
        trade.get("id")
        or trade.get("trade_id")
        or trade.get("match_id")
        or ""
    )
    if explicit_trade_id.strip():
        return explicit_trade_id.strip()
    return canonical_trade_fingerprint(
        trader_side=trade.get("trader_side"),
        taker_order_id=trade.get("taker_order_id"),
        asset_id=trade.get("asset_id"),
        side=trade.get("side"),
        price=trade.get("price"),
        size=trade.get("size"),
    )


def _trade_within_session(
    *,
    trade: dict[str, Any],
    session_started_at: datetime,
) -> bool:
    return _trade_sort_key(trade) >= session_started_at.astimezone(UTC)


def _open_order_within_session(
    *,
    raw_order: dict[str, Any],
    session_started_at: datetime,
) -> bool:
    created_at = _parse_timestamp(raw_order.get("created_at"))
    if created_at is None:
        created_at = _parse_timestamp(raw_order.get("timestamp"))
    if created_at is None:
        return False
    return created_at >= session_started_at.astimezone(UTC)


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


def _snapshot_exposure_group_id(snapshot: MarketSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    return derive_exposure_keys(snapshot).exposure_group_id


def _snapshot_thesis_group_id(
    snapshot: MarketSnapshot | None,
    *,
    trade_side: Any = None,
    token_id: str | None = None,
) -> str | None:
    if snapshot is None:
        return None
    return derive_exposure_keys(
        snapshot,
        side=_normalize_reconcile_side(
            trade_side=trade_side,
            snapshot=snapshot,
            token_id=token_id,
        ),
    ).thesis_group_id


def _snapshot_underlying_group_id(snapshot: MarketSnapshot | None) -> str | None:
    if snapshot is None:
        return None
    return derive_exposure_keys(snapshot).underlying_group_id


def _normalize_reconcile_side(
    *,
    trade_side: Any,
    snapshot: MarketSnapshot | None,
    token_id: str | None,
) -> str | None:
    if trade_side is None or trade_side == "":
        return None
    normalized = str(trade_side).strip().upper()
    is_no_token = bool(
        snapshot is not None
        and token_id
        and token_id == snapshot.metadata.get("no_token_id")
    )
    if normalized == "BUY":
        return "buy_no" if is_no_token else "buy_yes"
    if normalized == "SELL":
        return "sell_no" if is_no_token else "sell_yes"
    lowered = normalized.lower()
    return lowered or None
