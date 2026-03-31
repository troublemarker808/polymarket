"""Helpers for syncing paper execution state into runtime risk state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING

from pm_bot.core.types import MarketSnapshot
from pm_bot.execution.paper_adapter import PaperExecutionAdapter, PaperReconcileUpdate
from pm_bot.execution.paper_matching import PaperMatchEvent
from pm_bot.runtime.execution_artifacts import tracked_order_payload

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
        for event in update.events:
            await _record(
                recorder=recorder,
                event_type=event.event_type,
                payload=order_payload_from_match_event(order=event.order, snapshot=snapshot, match_event=event),
            )
        for trade in closed_trades:
            await _record(
                recorder=recorder,
                event_type="trade.closed",
                payload={
                    "market_id": trade.market_id,
                    "token_id": trade.token_id,
                    "strategy_id": trade.strategy_id,
                    "intent_id": trade.intent_id,
                    "realized_pnl": trade.realized_pnl,
                    "fees_paid": trade.fees_paid,
                    "net_pnl": trade.net_pnl,
                    "exposure_group_id": trade.exposure_group_id,
                    "thesis_group_id": trade.thesis_group_id,
                    "underlying_group_id": trade.underlying_group_id,
                    "closed_at": trade.closed_at.isoformat(),
                },
            )

    return update


def _advance_trading_day(*, risk_manager: RiskManager, timestamp: datetime) -> bool:
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


def order_payload_from_match_event(
    *,
    order: object,
    snapshot: MarketSnapshot,
    match_event: PaperMatchEvent,
) -> dict[str, object]:
    return tracked_order_payload(
        order=order,
        snapshot=snapshot,
        fill_shares_delta=match_event.fill_shares,
        fill_notional_delta=match_event.fill_notional,
        fees_paid_delta=match_event.fee_paid,
        fill_source=match_event.fill_source,
    )
