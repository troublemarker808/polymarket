"""Helpers for syncing paper execution state into runtime risk state."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from pm_bot.core.types import MarketSnapshot
from pm_bot.execution.paper_adapter import PaperExecutionAdapter, PaperReconcileUpdate

if TYPE_CHECKING:
    from pm_bot.core.interfaces import EventRecorder, RiskManager


async def sync_paper_execution_state(
    *,
    risk_manager: RiskManager,
    execution: PaperExecutionAdapter,
    snapshot: MarketSnapshot,
    ttl_seconds: int,
    recorder: EventRecorder | None = None,
) -> PaperReconcileUpdate:
    rollover_applied = _advance_trading_day(risk_manager=risk_manager, timestamp=snapshot.timestamp)
    update = execution.reconcile_snapshot(snapshot, ttl_seconds=ttl_seconds)
    await risk_manager.sync_pending_orders(execution.pending_order_states())
    await risk_manager.sync_open_positions(execution.position_states())
    closed_trades = execution.drain_closed_trades()
    for trade in closed_trades:
        await risk_manager.record_trade_close(trade)

    if recorder is not None:
        if rollover_applied:
            await _record(
                recorder=recorder,
                event_type="runtime.day_rollover",
                payload={"effective_at": snapshot.timestamp.isoformat()},
            )
        for order in update.filled_orders:
            await _record(
                recorder=recorder,
                event_type="order.filled",
                payload=_order_payload(order),
            )
        for order in update.expired_orders:
            await _record(
                recorder=recorder,
                event_type="order.expired",
                payload=_order_payload(order),
            )
        for trade in closed_trades:
            await _record(
                recorder=recorder,
                event_type="trade.closed",
                payload={
                    "market_id": trade.market_id,
                    "token_id": trade.token_id,
                    "realized_pnl": trade.realized_pnl,
                    "fees_paid": trade.fees_paid,
                    "net_pnl": trade.net_pnl,
                },
            )

    return update


def _advance_trading_day(*, risk_manager: RiskManager, timestamp) -> bool:
    advance = getattr(risk_manager, "advance_trading_day", None)
    if callable(advance):
        return bool(advance(timestamp))
    return False


async def _record(
    *,
    recorder: EventRecorder,
    event_type: str,
    payload: Mapping[str, object],
) -> None:
    await recorder.record(event_type=event_type, payload=dict(payload))


def _order_payload(order) -> dict[str, object]:
    average_fill_price = 0.0
    if order.matched_shares > 0:
        average_fill_price = order.matched_notional / order.matched_shares
    return {
        "order_id": order.order_id,
        "market_id": order.market_id,
        "token_id": order.token_id,
        "strategy_id": order.strategy_id,
        "status": order.status.value,
        "matched_shares": order.matched_shares,
        "matched_notional": order.matched_notional,
        "average_fill_price": average_fill_price,
    }
