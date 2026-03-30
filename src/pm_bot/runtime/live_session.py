"""Long-running live crypto session runner with reconnect supervision."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from pm_bot.adapters.polymarket import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    GammaMarketsClient,
    MarketChannelClient,
    PolymarketLiveMarketDataAdapter,
    UserChannelClient,
    UserChannelAuth,
    UserChannelEvent,
    UserOrderEvent,
    UserTradeEvent,
)
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.settings import TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, RuntimeMode
from pm_bot.execution.order_tracker import OrderLifecycleStatus, TrackedOrder
from pm_bot.execution.factory import build_execution_adapter
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.execution_artifacts import tracked_order_payload
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_reconcile import LiveRecoveryStats, recover_live_state
from pm_bot.runtime.market_universe import build_snapshot_selector
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.runtime.live_sync import sync_live_execution_state
from pm_bot.storage.recorder import LiveRuntimeRecorder
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore
from pm_bot.strategies.crypto.phase2.runtime_context import CryptoPhase2PaperContextBuilder

if TYPE_CHECKING:
    from pm_bot.core.interfaces import EventRecorder, RiskManager


CRYPTO_GAMMA_TAG_ID = 21


class UserEventStream(Protocol):
    def stream_events(
        self,
        *,
        auth: UserChannelAuth,
        markets: Sequence[str] = (),
    ) -> AsyncIterator[UserChannelEvent]:
        ...


class LiveMarketDataSource(Protocol):
    async def bootstrap_snapshots(self) -> list[MarketSnapshot]:
        ...

    def stream_from_snapshots(
        self,
        snapshots: list[MarketSnapshot],
        *,
        include_initial: bool,
    ) -> AsyncIterator[MarketSnapshot]:
        ...


class LiveRuntimeContextBuilder(Protocol):
    def __call__(
        self,
        *,
        snapshot: MarketSnapshot,
        snapshots_by_market_id: Mapping[str, MarketSnapshot],
        recorder: EventRecorder | None,
    ) -> Mapping[str, object]:
        ...


class LiveSessionStreamError(RuntimeError):
    """Raised when one of the live session streams fails unexpectedly."""

    def __init__(self, stream_name: str) -> None:
        super().__init__(f"Live session {stream_name} stream failed")
        self.stream_name = stream_name


@dataclass(slots=True, frozen=True)
class LiveSessionStats:
    market_snapshots_processed: int = 0
    user_events_processed: int = 0
    submitted_orders: int = 0
    stale_orders_cancelled: int = 0
    recovered_open_orders: int = 0
    replayed_trades: int = 0
    rebuilt_positions: int = 0
    reconnects: int = 0


def format_live_session_stats(stats: LiveSessionStats) -> str:
    return "\n".join(
        [
            f"market_snapshots_processed={stats.market_snapshots_processed}",
            f"user_events_processed={stats.user_events_processed}",
            f"submitted_orders={stats.submitted_orders}",
            f"stale_orders_cancelled={stats.stale_orders_cancelled}",
            f"recovered_open_orders={stats.recovered_open_orders}",
            f"replayed_trades={stats.replayed_trades}",
            f"rebuilt_positions={stats.rebuilt_positions}",
            f"reconnects={stats.reconnects}",
        ]
    )


def format_live_session_summary(result: dict[str, object]) -> str:
    metrics = result.get("metrics")
    metrics_map = metrics if isinstance(metrics, Mapping) else {}
    dashboard = result.get("dashboard")
    dashboard_state = dashboard if isinstance(dashboard, DashboardState) else None
    trading_settings = result.get("trading_settings")
    typed_trading_settings = (
        trading_settings if isinstance(trading_settings, TradingSettings) else None
    )
    lines = [
        f"processed_snapshots={result['processed_snapshots']}",
        f"user_events_processed={result['user_events_processed']}",
        f"submitted_orders={result['submitted_orders']}",
        f"stale_orders_cancelled={result['stale_orders_cancelled']}",
        f"recovered_open_orders={result['recovered_open_orders']}",
        f"replayed_trades={result['replayed_trades']}",
        f"rebuilt_positions={result['rebuilt_positions']}",
        f"reconnects={result['reconnects']}",
        f"signals_generated={metrics_map.get('signals_generated', 0)}",
        f"signals_rejected={metrics_map.get('signals_rejected', 0)}",
        f"orders_rejected={metrics_map.get('orders_rejected', 0)}",
        f"orders_filled={metrics_map.get('orders_filled', 0)}",
        f"orders_partially_filled={metrics_map.get('orders_partially_filled', 0)}",
        f"orders_expired={metrics_map.get('orders_expired', 0)}",
        f"orders_canceled={metrics_map.get('orders_canceled', 0)}",
        f"trades_closed={metrics_map.get('trades_closed', 0)}",
        f"fill_rate={float(metrics_map.get('fill_rate', 0.0)):.4f}",
        f"cancel_rate={float(metrics_map.get('cancel_rate', 0.0)):.4f}",
        f"avg_time_to_fill_ms={float(metrics_map.get('avg_time_to_fill_ms', 0.0)):.2f}",
        f"avg_fill_price_vs_mid_bps={float(metrics_map.get('avg_fill_price_vs_mid_bps', 0.0)):.2f}",
        f"maker_fill_share={float(metrics_map.get('maker_fill_share', 0.0)):.4f}",
        f"taker_fill_share={float(metrics_map.get('taker_fill_share', 0.0)):.4f}",
        f"market_data_failures={metrics_map.get('market_data_failures', 0)}",
        f"market_data_recoveries={metrics_map.get('market_data_recoveries', 0)}",
        f"events_recorded={result['events_recorded']}",
    ]
    if dashboard_state is not None:
        lines.append(
            render_dashboard(
                dashboard_state,
                trading_settings=typed_trading_settings,
            )
        )
    return "\n".join(lines)


class LiveSessionRunner:
    """Run market updates and user updates through one live runtime loop."""

    def __init__(
        self,
        *,
        router: EventRouter,
        execution: PolymarketLiveExecutionAdapter,
        risk_manager: RiskManager,
        recorder: EventRecorder | None,
        market_snapshots: Sequence[MarketSnapshot],
        market_snapshot_stream: AsyncIterator[MarketSnapshot],
        user_event_stream: AsyncIterator[UserChannelEvent],
        summary_every_snapshots: int | None = None,
        session_started_at: datetime | None = None,
        shadow_coordinator: object | None = None,
        runtime_context_builder: LiveRuntimeContextBuilder | None = None,
    ) -> None:
        self.router = router
        self.execution = execution
        self.risk_manager = risk_manager
        self.recorder = recorder
        self.market_snapshot_stream = market_snapshot_stream
        self.user_event_stream = user_event_stream
        self.snapshots_by_market_id = {snapshot.market_id: snapshot for snapshot in market_snapshots}
        self.summary_every_snapshots = summary_every_snapshots
        self.session_started_at = session_started_at
        self.shadow_coordinator = shadow_coordinator
        self.runtime_context_builder = runtime_context_builder
        self.stats = LiveSessionStats()

    def current_snapshots(self) -> tuple[MarketSnapshot, ...]:
        return tuple(self.snapshots_by_market_id.values())

    async def run(
        self,
        *,
        max_market_snapshots: int | None = None,
        max_user_events: int | None = None,
        recovery_stats: LiveRecoveryStats | None = None,
    ) -> LiveSessionStats:
        if recovery_stats is not None:
            self.stats = LiveSessionStats(
                market_snapshots_processed=self.stats.market_snapshots_processed,
                user_events_processed=self.stats.user_events_processed,
                submitted_orders=self.stats.submitted_orders,
                stale_orders_cancelled=self.stats.stale_orders_cancelled,
                recovered_open_orders=recovery_stats.open_orders_recovered,
                replayed_trades=recovery_stats.trades_replayed,
                rebuilt_positions=recovery_stats.positions_rebuilt,
                reconnects=self.stats.reconnects,
            )
        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        market_limit_reached = False
        user_limit_reached = False

        async def pump_market() -> None:
            nonlocal market_limit_reached
            processed = 0
            try:
                async for snapshot in self.market_snapshot_stream:
                    await queue.put(("market", snapshot))
                    processed += 1
                    if max_market_snapshots is not None and processed >= max_market_snapshots:
                        market_limit_reached = True
                        break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await queue.put(("error", ("market", exc)))
            finally:
                await queue.put(("done", "market"))

        async def pump_user() -> None:
            nonlocal user_limit_reached
            processed = 0
            try:
                async for event in self.user_event_stream:
                    await queue.put(("user", event))
                    processed += 1
                    if max_user_events is not None and processed >= max_user_events:
                        user_limit_reached = True
                        break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await queue.put(("error", ("user", exc)))
            finally:
                await queue.put(("done", "user"))

        market_task = asyncio.create_task(pump_market())
        user_task = asyncio.create_task(pump_user())
        done_streams = 0
        market_stream_done = False
        user_stream_done = False

        try:
            while done_streams < 2:
                if await _halt_if_data_health_breached(
                    risk_manager=self.risk_manager,
                    recorder=self.recorder,
                ):
                    break
                poll_timeout = _data_health_poll_interval(self.risk_manager)
                try:
                    if poll_timeout is None:
                        kind, payload = await queue.get()
                    else:
                        kind, payload = await asyncio.wait_for(queue.get(), timeout=poll_timeout)
                except asyncio.TimeoutError:
                    if _should_stop_after_limit(
                        queue_empty=queue.empty(),
                        market_limit_reached=market_limit_reached,
                        user_limit_reached=user_limit_reached,
                        market_stream_done=market_stream_done,
                        user_stream_done=user_stream_done,
                    ):
                        break
                    continue
                if kind == "done":
                    if payload == "market":
                        market_stream_done = True
                    elif payload == "user":
                        user_stream_done = True
                    done_streams += 1
                    if _should_stop_after_limit(
                        queue_empty=queue.empty(),
                        market_limit_reached=market_limit_reached,
                        user_limit_reached=user_limit_reached,
                        market_stream_done=market_stream_done,
                        user_stream_done=user_stream_done,
                    ):
                        break
                    continue
                if kind == "error":
                    if not isinstance(payload, tuple) or len(payload) != 2:
                        raise RuntimeError("Live session received malformed stream error payload")
                    stream_name, error = payload
                    if not isinstance(stream_name, str) or not isinstance(error, Exception):
                        raise RuntimeError("Live session received malformed stream error payload")
                    raise LiveSessionStreamError(stream_name) from error
                if kind == "market":
                    assert isinstance(payload, MarketSnapshot)
                    await self._handle_market_snapshot(payload)
                    if _should_stop_after_limit(
                        queue_empty=queue.empty(),
                        market_limit_reached=market_limit_reached,
                        user_limit_reached=user_limit_reached,
                        market_stream_done=market_stream_done,
                        user_stream_done=user_stream_done,
                    ):
                        break
                    continue
                assert isinstance(payload, (UserOrderEvent, UserTradeEvent))
                await self._handle_user_event(payload)
                if _should_stop_after_limit(
                    queue_empty=queue.empty(),
                    market_limit_reached=market_limit_reached,
                    user_limit_reached=user_limit_reached,
                    market_stream_done=market_stream_done,
                    user_stream_done=user_stream_done,
                ):
                    break
        finally:
            for task in (market_task, user_task):
                task.cancel()
            await asyncio.gather(market_task, user_task, return_exceptions=True)

        return self.stats

    async def _handle_market_snapshot(self, snapshot: MarketSnapshot) -> None:
        self.snapshots_by_market_id[snapshot.market_id] = snapshot
        _record_data_success(self.risk_manager, snapshot.timestamp)
        _note_snapshot(recorder=self.recorder, timestamp=snapshot.timestamp)
        await _shadow_before_market_snapshot(
            shadow_coordinator=self.shadow_coordinator,
            snapshot=snapshot,
        )
        runtime_context = None
        if self.runtime_context_builder is not None:
            runtime_context = self.runtime_context_builder(
                snapshot=snapshot,
                snapshots_by_market_id=dict(self.snapshots_by_market_id),
                recorder=self.recorder,
            )
        submitted = await self.router.run_once(snapshot=snapshot, context=runtime_context)
        cancelled_orders = await self.execution.cancel_stale_orders()
        await _shadow_after_market_snapshot(
            shadow_coordinator=self.shadow_coordinator,
            snapshot=snapshot,
        )
        await sync_live_execution_state(
            risk_manager=self.risk_manager,
            execution=self.execution,
            snapshots=tuple(self.snapshots_by_market_id.values()),
        )

        next_stats = LiveSessionStats(
            market_snapshots_processed=self.stats.market_snapshots_processed + 1,
            user_events_processed=self.stats.user_events_processed,
            submitted_orders=self.stats.submitted_orders + len(submitted),
            stale_orders_cancelled=self.stats.stale_orders_cancelled + len(cancelled_orders),
            recovered_open_orders=self.stats.recovered_open_orders,
            replayed_trades=self.stats.replayed_trades,
            rebuilt_positions=self.stats.rebuilt_positions,
            reconnects=self.stats.reconnects,
        )
        for order in cancelled_orders:
            assert isinstance(order, TrackedOrder)
            await self._record(
                "order.canceled",
                {
                    **tracked_order_payload(
                        order=order,
                        snapshot=_snapshot_for_order(
                            order=order,
                            snapshots=self.snapshots_by_market_id,
                        ),
                    ),
                    "reason": "stale_ttl_cancel",
                },
            )
        await self._record(
            "market.snapshot_processed",
            {
                "market_id": snapshot.market_id,
                "processed_snapshots": next_stats.market_snapshots_processed,
                "submitted_orders": len(submitted),
                "stale_orders_cancelled": len(cancelled_orders),
                "updated_at": snapshot.timestamp.isoformat(),
            },
        )
        self.stats = next_stats
        if (
            self.summary_every_snapshots is not None
            and self.summary_every_snapshots > 0
            and self.stats.market_snapshots_processed % self.summary_every_snapshots == 0
        ):
            print(
                format_live_session_summary(
                    {
                        "processed_snapshots": self.stats.market_snapshots_processed,
                        "user_events_processed": self.stats.user_events_processed,
                        "submitted_orders": self.stats.submitted_orders,
                        "stale_orders_cancelled": self.stats.stale_orders_cancelled,
                        "recovered_open_orders": self.stats.recovered_open_orders,
                        "replayed_trades": self.stats.replayed_trades,
                        "rebuilt_positions": self.stats.rebuilt_positions,
                        "reconnects": self.stats.reconnects,
                        "events_recorded": len(getattr(self.recorder, "events", [])),
                        "metrics": getattr(getattr(self.recorder, "metrics", None), "to_dict", lambda: {})(),
                        "dashboard": self.risk_manager.dashboard_state(),
                    }
                )
            )

    async def _handle_user_event(self, event: UserChannelEvent) -> None:
        if _should_ignore_historical_user_event(
            event=event,
            session_started_at=self.session_started_at,
            execution=self.execution,
        ):
            await self._record(
                "user.event_ignored",
                {
                    "reason": "historical_before_session_start",
                    "event_type": "trade" if isinstance(event, UserTradeEvent) else "order",
                    "event_id": event.id,
                },
            )
            self.stats = LiveSessionStats(
                market_snapshots_processed=self.stats.market_snapshots_processed,
                user_events_processed=self.stats.user_events_processed + 1,
                submitted_orders=self.stats.submitted_orders,
                stale_orders_cancelled=self.stats.stale_orders_cancelled,
                recovered_open_orders=self.stats.recovered_open_orders,
                replayed_trades=self.stats.replayed_trades,
                rebuilt_positions=self.stats.rebuilt_positions,
                reconnects=self.stats.reconnects,
            )
            return
        if isinstance(event, UserOrderEvent):
            previous_order = self.execution.tracker.get(event.id)
            tracked = self.execution.apply_user_order_event(event)
            if tracked is not None:
                await sync_live_execution_state(
                    risk_manager=self.risk_manager,
                    execution=self.execution,
                    snapshots=tuple(self.snapshots_by_market_id.values()),
                )
                standardized = _standardized_order_event_from_user_event(
                    previous_order=previous_order,
                    tracked_order=tracked,
                    event=event,
                    snapshots=self.snapshots_by_market_id,
                )
                if standardized is not None:
                    event_type, payload = standardized
                    await self._record(event_type, payload)
            await self._record(
                "user.order_event",
                {
                    "order_id": event.id,
                    "status": event.status,
                    "tracked": tracked is not None,
                },
            )
        else:
            tracked_orders_before = {
                order_id: (fill_source, self.execution.tracker.get(order_id))
                for order_id, fill_source in self.execution.tracked_order_ids_for_trade_event(event)
            }
            positions = self.execution.apply_user_trade_event(event)
            state = getattr(self.risk_manager, "state", None)
            if state is not None:
                state.processed_trade_ids = tuple(sorted(self.execution.processed_trade_ids))
            await sync_live_execution_state(
                risk_manager=self.risk_manager,
                execution=self.execution,
                snapshots=tuple(self.snapshots_by_market_id.values()),
            )
            for order_id, (fill_source, previous_order) in tracked_orders_before.items():
                tracked_order = self.execution.tracker.get(order_id)
                standardized = _standardized_fill_event(
                    previous_order=previous_order,
                    tracked_order=tracked_order,
                    fill_source=fill_source,
                    snapshots=self.snapshots_by_market_id,
                )
                if standardized is None:
                    continue
                event_type, payload = standardized
                await self._record(event_type, payload)
            closed_trades = self.execution.drain_closed_trades()
            for closed_trade in closed_trades:
                await self.risk_manager.record_trade_close(closed_trade)
                await self._record(
                    "trade.closed",
                    {
                        "market_id": closed_trade.market_id,
                        "token_id": closed_trade.token_id,
                        "strategy_id": closed_trade.strategy_id,
                        "intent_id": closed_trade.intent_id,
                        "realized_pnl": closed_trade.realized_pnl,
                        "fees_paid": closed_trade.fees_paid,
                        "net_pnl": closed_trade.net_pnl,
                        "closed_at": closed_trade.closed_at.isoformat(),
                    },
                )
            await self._record(
                "user.trade_event",
                {
                    "trade_id": event.id,
                    "taker_order_id": event.taker_order_id,
                    "positions_updated": len(positions),
                    "closed_trades": len(closed_trades),
                },
            )

        self.stats = LiveSessionStats(
            market_snapshots_processed=self.stats.market_snapshots_processed,
            user_events_processed=self.stats.user_events_processed + 1,
            submitted_orders=self.stats.submitted_orders,
            stale_orders_cancelled=self.stats.stale_orders_cancelled,
            recovered_open_orders=self.stats.recovered_open_orders,
            replayed_trades=self.stats.replayed_trades,
            rebuilt_positions=self.stats.rebuilt_positions,
            reconnects=self.stats.reconnects,
        )

    async def _record(self, event_type: str, payload: Mapping[str, object]) -> None:
        if self.recorder is None:
            return
        await self.recorder.record(event_type=event_type, payload=payload)


async def supervise_live_session(
    *,
    market_data: LiveMarketDataSource,
    user_client: UserEventStream,
    router: EventRouter,
    execution: PolymarketLiveExecutionAdapter,
    risk_manager: RiskManager,
    recorder: EventRecorder | None,
    initial_snapshots: Sequence[MarketSnapshot] | None = None,
    max_market_snapshots: int | None = None,
    max_user_events: int | None = None,
    reconnect_delay_seconds: float = 1.0,
    max_reconnects: int | None = None,
    summary_every_snapshots: int | None = None,
    recovery_scope: str = "full",
    session_started_at: datetime | None = None,
    shadow_coordinator: object | None = None,
    runtime_context_builder: LiveRuntimeContextBuilder | None = None,
) -> LiveSessionStats:
    current_snapshots = list(initial_snapshots or await market_data.bootstrap_snapshots())
    if current_snapshots:
        _record_data_success(risk_manager, max(snapshot.timestamp for snapshot in current_snapshots))
    aggregate = LiveSessionStats()
    include_initial = True
    run_started_at = session_started_at or datetime.now(tz=UTC)

    while True:
        recovery_stats = await recover_live_state(
            risk_manager=risk_manager,
            execution=execution,
            snapshots=tuple(current_snapshots),
            recovery_scope=recovery_scope,
            session_started_at=run_started_at,
        )
        if recovery_stats.historical_open_orders_skipped > 0 or recovery_stats.historical_trades_skipped > 0:
            await _record_supervisor_event(
                recorder=recorder,
                event_type="live.recovery.filtered_history",
                payload={
                    "recovery_scope": recovery_scope,
                    "session_started_at": run_started_at.isoformat(),
                    "historical_open_orders_skipped": recovery_stats.historical_open_orders_skipped,
                    "historical_trades_skipped": recovery_stats.historical_trades_skipped,
                },
            )
        runner = LiveSessionRunner(
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            market_snapshots=current_snapshots,
            market_snapshot_stream=market_data.stream_from_snapshots(
                list(current_snapshots),
                include_initial=include_initial,
            ),
            user_event_stream=user_client.stream_events(
                auth=execution.user_channel_auth,
                markets=_subscribed_markets(current_snapshots),
            ),
            summary_every_snapshots=summary_every_snapshots,
            session_started_at=run_started_at,
            shadow_coordinator=shadow_coordinator,
            runtime_context_builder=runtime_context_builder,
        )

        stream_error: LiveSessionStreamError | None = None
        try:
            cycle_stats = await runner.run(
                max_market_snapshots=_remaining_limit(max_market_snapshots, aggregate.market_snapshots_processed),
                max_user_events=_remaining_limit(max_user_events, aggregate.user_events_processed),
                recovery_stats=recovery_stats,
            )
        except LiveSessionStreamError as exc:
            cycle_stats = runner.stats
            stream_error = exc

        aggregate = _merge_stats(aggregate, cycle_stats)
        current_snapshots = list(_merge_snapshots(primary=runner.current_snapshots(), fallback=current_snapshots))
        if _data_health_halt_reason(risk_manager) is not None:
            return aggregate
        if _any_limit_reached(
            stats=aggregate,
            max_market_snapshots=max_market_snapshots,
            max_user_events=max_user_events,
        ):
            return aggregate
        if _limits_satisfied(
            stats=aggregate,
            max_market_snapshots=max_market_snapshots,
            max_user_events=max_user_events,
        ):
            return aggregate

        reconnect_number = aggregate.reconnects + 1
        if max_reconnects is not None and reconnect_number > max_reconnects:
            if stream_error is not None:
                raise RuntimeError(
                    f"Live session exceeded reconnect budget after {stream_error.stream_name} stream failure"
                ) from stream_error
            raise RuntimeError("Live session ended before requested limits and reconnect budget was exhausted")

        aggregate = LiveSessionStats(
            market_snapshots_processed=aggregate.market_snapshots_processed,
            user_events_processed=aggregate.user_events_processed,
            submitted_orders=aggregate.submitted_orders,
            stale_orders_cancelled=aggregate.stale_orders_cancelled,
            recovered_open_orders=aggregate.recovered_open_orders,
            replayed_trades=aggregate.replayed_trades,
            rebuilt_positions=aggregate.rebuilt_positions,
            reconnects=reconnect_number,
        )
        await _record_supervisor_event(
            recorder=recorder,
            event_type="live.reconnect",
            payload={
                "reconnect_count": reconnect_number,
                "reason": stream_error.stream_name if stream_error is not None else "stream_ended",
            },
        )
        if reconnect_delay_seconds > 0:
            await asyncio.sleep(reconnect_delay_seconds)
        current_snapshots = list(
            await _refresh_snapshots(
                market_data=market_data,
                fallback_snapshots=current_snapshots,
                risk_manager=risk_manager,
                recorder=recorder,
            )
        )
        if _data_health_halt_reason(risk_manager) is not None:
            return aggregate
        include_initial = False


def _subscribed_markets(snapshots: Sequence[MarketSnapshot]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            snapshot.metadata.get("condition_id", "")
            for snapshot in snapshots
            if snapshot.metadata.get("condition_id")
        )
    )


async def _refresh_snapshots(
    *,
    market_data: LiveMarketDataSource,
    fallback_snapshots: Sequence[MarketSnapshot],
    risk_manager: RiskManager,
    recorder: EventRecorder | None,
) -> tuple[MarketSnapshot, ...]:
    try:
        refreshed = await market_data.bootstrap_snapshots()
    except Exception as exc:
        halt_triggered = _record_data_failure(risk_manager, reason=f"{type(exc).__name__}: {exc}")
        await _record_supervisor_event(
            recorder=recorder,
            event_type="market_data.failure",
            payload={"error": f"{type(exc).__name__}: {exc}"},
        )
        if halt_triggered:
            await _record_runtime_halt_event(recorder=recorder, risk_manager=risk_manager)
        if not fallback_snapshots:
            raise
        return tuple(fallback_snapshots)

    if refreshed:
        had_failures = _consecutive_data_failures(risk_manager) > 0
        _record_data_success(risk_manager, max(snapshot.timestamp for snapshot in refreshed))
        if had_failures:
            await _record_supervisor_event(
                recorder=recorder,
                event_type="market_data.recovered",
                payload={"updated_at": max(snapshot.timestamp for snapshot in refreshed).isoformat()},
            )

    return _merge_snapshots(primary=refreshed, fallback=fallback_snapshots)


async def _record_supervisor_event(
    *,
    recorder: EventRecorder | None,
    event_type: str,
    payload: Mapping[str, object],
) -> None:
    if recorder is None:
        return
    await recorder.record(event_type=event_type, payload=payload)


def _record_data_success(risk_manager: RiskManager, timestamp: datetime) -> None:
    callback = getattr(risk_manager, "record_data_success", None)
    if callable(callback):
        callback(timestamp)


def _record_data_failure(risk_manager: RiskManager, *, reason: str) -> bool:
    callback = getattr(risk_manager, "record_data_failure", None)
    if callable(callback):
        return bool(callback(reason=reason))
    return False


def _remaining_limit(limit: int | None, processed: int) -> int | None:
    if limit is None:
        return None
    remaining = limit - processed
    return max(remaining, 0)


def _limits_satisfied(
    *,
    stats: LiveSessionStats,
    max_market_snapshots: int | None,
    max_user_events: int | None,
) -> bool:
    if max_market_snapshots is None and max_user_events is None:
        return False
    market_done = max_market_snapshots is None or stats.market_snapshots_processed >= max_market_snapshots
    user_done = max_user_events is None or stats.user_events_processed >= max_user_events
    return market_done and user_done


def _should_stop_after_limit(
    *,
    queue_empty: bool,
    market_limit_reached: bool,
    user_limit_reached: bool,
    market_stream_done: bool,
    user_stream_done: bool,
) -> bool:
    if not queue_empty:
        return False
    if market_limit_reached and market_stream_done:
        return True
    if user_limit_reached and user_stream_done:
        return True
    return False


def _any_limit_reached(
    *,
    stats: LiveSessionStats,
    max_market_snapshots: int | None,
    max_user_events: int | None,
) -> bool:
    market_reached = (
        max_market_snapshots is not None
        and stats.market_snapshots_processed >= max_market_snapshots
    )
    user_reached = (
        max_user_events is not None
        and stats.user_events_processed >= max_user_events
    )
    return market_reached or user_reached


def _merge_stats(left: LiveSessionStats, right: LiveSessionStats) -> LiveSessionStats:
    return LiveSessionStats(
        market_snapshots_processed=left.market_snapshots_processed + right.market_snapshots_processed,
        user_events_processed=left.user_events_processed + right.user_events_processed,
        submitted_orders=left.submitted_orders + right.submitted_orders,
        stale_orders_cancelled=left.stale_orders_cancelled + right.stale_orders_cancelled,
        recovered_open_orders=left.recovered_open_orders + right.recovered_open_orders,
        replayed_trades=left.replayed_trades + right.replayed_trades,
        rebuilt_positions=left.rebuilt_positions + right.rebuilt_positions,
        reconnects=left.reconnects + right.reconnects,
    )


def _merge_snapshots(
    *,
    primary: Sequence[MarketSnapshot],
    fallback: Sequence[MarketSnapshot],
) -> tuple[MarketSnapshot, ...]:
    by_market_id = {snapshot.market_id: snapshot for snapshot in fallback}
    for snapshot in primary:
        existing = by_market_id.get(snapshot.market_id)
        if existing is None or snapshot.timestamp >= existing.timestamp:
            by_market_id[snapshot.market_id] = snapshot
    return tuple(by_market_id.values())


async def run_crypto_live_session(
    *,
    config_dir: str = "configs",
    state_path: str = "data/runtime/runtime_state.json",
    recorder_path: str | Path = "data/runtime/live-events.jsonl",
    metrics_path: str | Path | None = "data/runtime/live-metrics.latest.json",
    max_pages: int = 1,
    max_market_snapshots: int | None = None,
    max_user_events: int | None = None,
    gamma_tag_id: int = CRYPTO_GAMMA_TAG_ID,
    summary_every_snapshots: int | None = 50,
    underlying_state_path: str | None = None,
) -> dict[str, object]:
    settings = load_settings_from_directory(config_dir)
    if settings.app.mode != RuntimeMode.LIVE:
        raise ValueError("Live session runner requires app.mode=live")

    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    enabled_strategy_ids = {
        strategy_id
        for category_config in settings.category_configs.values()
        for strategy_id in category_config.enabled_strategies
    }
    crypto_config = settings.category_configs.get(Category.CRYPTO)
    snapshot_selector = build_snapshot_selector(
        crypto_config.markets if crypto_config is not None else None
    )
    state_store = JsonRuntimeStateStore(state_path)
    risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state_store=state_store,
    )
    execution = build_execution_adapter(settings=settings)
    if not isinstance(execution, PolymarketLiveExecutionAdapter):
        raise TypeError("Live session runner requires PolymarketLiveExecutionAdapter")
    execution.restore_processed_trade_ids(risk_manager.state.processed_trade_ids)

    recorder = LiveRuntimeRecorder(event_path=recorder_path, metrics_path=metrics_path)
    session_started_at = datetime.now(tz=UTC)
    runtime_context_builder = None
    if "crypto.phase2" in enabled_strategy_ids:
        if underlying_state_path is None:
            raise ValueError(
                "run_crypto_live_session requires underlying_state_path when crypto.phase2 is enabled"
            )
        phase2_context_builder = CryptoPhase2PaperContextBuilder(
            underlying_state_path=underlying_state_path,
            apply_series_filter=True,
        )
        def runtime_context_builder(
            *,
            snapshot: MarketSnapshot,
            snapshots_by_market_id: Mapping[str, MarketSnapshot],
            recorder: EventRecorder | None,
        ) -> Mapping[str, object]:
            del snapshot
            return phase2_context_builder.build_context(
                snapshot_cache=tuple(snapshots_by_market_id.values()),
                recorder=cast(LiveRuntimeRecorder, recorder),
            )
    await recorder.record(
        event_type="live.session_started",
        payload={
            "started_at": session_started_at.isoformat(),
            "recovery_scope": settings.polymarket.live_recovery_scope,
            "configured_signature_type": settings.polymarket.signature_type,
            "resolved_signature_type": execution.signature_type,
        },
    )

    async with GammaMarketsClient(
        base_url=settings.polymarket.gamma_url,
    ) as gamma_client, ClobPublicClient(
        base_url=settings.polymarket.api_url,
    ) as clob_client:
        market_data = PolymarketLiveMarketDataAdapter(
            gamma_client=gamma_client,
            clob_enricher=ClobSnapshotEnricher(clob_client),
            market_event_stream=MarketChannelClient(settings.polymarket.market_ws_url),
            max_pages=max_pages,
            tag_id=gamma_tag_id,
            snapshot_selector=snapshot_selector,
        )
        try:
            seed_snapshots = await market_data.bootstrap_snapshots()
        except Exception as exc:
            halt_triggered = _record_data_failure(risk_manager, reason=f"{type(exc).__name__}: {exc}")
            await recorder.record(
                event_type="market_data.failure",
                payload={"error": f"{type(exc).__name__}: {exc}"},
            )
            if halt_triggered:
                await _record_runtime_halt_event(recorder=recorder, risk_manager=risk_manager)
            raise
        if seed_snapshots:
            _record_data_success(risk_manager, max(snapshot.timestamp for snapshot in seed_snapshots))
        router = EventRouter(
            market_data=market_data,
            strategies=strategies,
            risk_manager=risk_manager,
            execution=execution,
            recorder=recorder,
            default_order_size=settings.trading.default_order_notional,
        )
        user_client = UserChannelClient(settings.polymarket.user_ws_url)
        stats = await supervise_live_session(
            market_data=market_data,
            user_client=user_client,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=seed_snapshots,
            max_market_snapshots=max_market_snapshots,
            max_user_events=max_user_events,
            summary_every_snapshots=summary_every_snapshots,
            recovery_scope=settings.polymarket.live_recovery_scope,
            session_started_at=session_started_at,
            runtime_context_builder=runtime_context_builder,
        )
    dashboard = risk_manager.dashboard_state()
    return {
        "processed_snapshots": stats.market_snapshots_processed,
        "user_events_processed": stats.user_events_processed,
        "submitted_orders": stats.submitted_orders,
        "stale_orders_cancelled": stats.stale_orders_cancelled,
        "recovered_open_orders": stats.recovered_open_orders,
        "replayed_trades": stats.replayed_trades,
        "rebuilt_positions": stats.rebuilt_positions,
        "reconnects": stats.reconnects,
        "events_recorded": len(recorder.events),
        "metrics": recorder.metrics.to_dict(),
        "dashboard": dashboard,
        "trading_settings": settings.trading,
    }


def _note_snapshot(*, recorder: EventRecorder | None, timestamp: datetime) -> None:
    note_snapshot = getattr(recorder, "note_snapshot", None)
    if callable(note_snapshot):
        note_snapshot(timestamp=timestamp, payload={"updated_at": timestamp.isoformat()})


def _standardized_order_event_from_user_event(
    *,
    previous_order: TrackedOrder | None,
    tracked_order: TrackedOrder,
    event: UserOrderEvent,
    snapshots: Mapping[str, MarketSnapshot],
) -> tuple[str, dict[str, object]] | None:
    previous_status = previous_order.status if previous_order is not None else None
    snapshot = _snapshot_for_order(order=tracked_order, snapshots=snapshots)
    if (
        tracked_order.status == OrderLifecycleStatus.CANCELED
        and previous_status != OrderLifecycleStatus.CANCELED
    ):
        return (
            "order.canceled",
            {
                **tracked_order_payload(order=tracked_order, snapshot=snapshot),
                "reason": "exchange_canceled",
                "exchange_status": event.status,
            },
        )
    if (
        tracked_order.status == OrderLifecycleStatus.REJECTED
        and previous_status != OrderLifecycleStatus.REJECTED
    ):
        return (
            "order.rejected",
            {
                **tracked_order_payload(order=tracked_order, snapshot=snapshot),
                "reason": "exchange_rejected",
                "exchange_status": event.status,
            },
        )
    return None


def _standardized_fill_event(
    *,
    previous_order: TrackedOrder | None,
    tracked_order: TrackedOrder | None,
    fill_source: str,
    snapshots: Mapping[str, MarketSnapshot],
) -> tuple[str, dict[str, object]] | None:
    if tracked_order is None:
        return None
    previous_matched_shares = previous_order.matched_shares if previous_order is not None else 0.0
    previous_matched_notional = previous_order.matched_notional if previous_order is not None else 0.0
    previous_fees_paid = previous_order.fees_paid if previous_order is not None else 0.0
    fill_shares_delta = tracked_order.matched_shares - previous_matched_shares
    fill_notional_delta = tracked_order.matched_notional - previous_matched_notional
    fees_paid_delta = tracked_order.fees_paid - previous_fees_paid
    if fill_shares_delta <= 1e-9 and fees_paid_delta <= 1e-9:
        return None
    event_type = (
        "order.filled"
        if tracked_order.status == OrderLifecycleStatus.FILLED
        else "order.partially_filled"
    )
    return (
        event_type,
        tracked_order_payload(
            order=tracked_order,
            snapshot=_snapshot_for_order(order=tracked_order, snapshots=snapshots),
            fill_shares_delta=fill_shares_delta,
            fill_notional_delta=fill_notional_delta,
            fees_paid_delta=fees_paid_delta,
            fill_source=fill_source,
        ),
    )


def _snapshot_for_order(
    *,
    order: TrackedOrder,
    snapshots: Mapping[str, MarketSnapshot],
) -> MarketSnapshot | None:
    direct = snapshots.get(order.market_id)
    if direct is not None:
        return direct
    for snapshot in snapshots.values():
        if order.token_id == snapshot.token_id or order.token_id == snapshot.metadata.get("no_token_id"):
            return snapshot
    return None


def _consecutive_data_failures(risk_manager: RiskManager) -> int:
    dashboard = getattr(risk_manager, "dashboard_state", None)
    if not callable(dashboard):
        return 0
    return int(getattr(dashboard(), "consecutive_data_failures", 0))


def _data_health_poll_interval(risk_manager: RiskManager) -> float | None:
    settings = getattr(risk_manager, "settings", None)
    timeout = getattr(settings, "kill_switch_on_stale_data_seconds", None)
    if timeout is None:
        return None
    timeout_seconds = float(timeout)
    if timeout_seconds <= 0:
        return None
    return min(1.0, timeout_seconds)


def _data_health_halt_reason(risk_manager: RiskManager) -> HaltReason | None:
    dashboard = getattr(risk_manager, "dashboard_state", None)
    if not callable(dashboard):
        return None
    snapshot = dashboard()
    if getattr(snapshot, "status", None) != RuntimeStatus.HALTED:
        return None
    reason = getattr(snapshot, "halt_reason", HaltReason.NONE)
    if reason not in {HaltReason.STALE_DATA, HaltReason.DATA_SOURCE_FAILURE}:
        return None
    return reason


async def _halt_if_data_health_breached(
    *,
    risk_manager: RiskManager,
    recorder: EventRecorder | None,
) -> bool:
    callback = getattr(risk_manager, "enforce_data_freshness", None)
    halt_triggered = bool(callback()) if callable(callback) else False
    if halt_triggered:
        await _record_runtime_halt_event(recorder=recorder, risk_manager=risk_manager)
    return _data_health_halt_reason(risk_manager) is not None


async def _record_runtime_halt_event(
    *,
    recorder: EventRecorder | None,
    risk_manager: RiskManager,
) -> None:
    if recorder is None:
        return
    dashboard = getattr(risk_manager, "dashboard_state", None)
    if not callable(dashboard):
        return
    snapshot = dashboard()
    if getattr(snapshot, "status", None) != RuntimeStatus.HALTED:
        return
    await recorder.record(
        event_type="runtime.halted",
        payload={
            "halt_reason": snapshot.halt_reason.value,
            "halt_message": snapshot.halt_message or "",
            "last_data_success_at": (
                snapshot.last_data_success_at.isoformat()
                if snapshot.last_data_success_at is not None
                else ""
            ),
            "last_data_error": snapshot.last_data_error or "",
            "consecutive_data_failures": snapshot.consecutive_data_failures,
        },
    )


async def _shadow_before_market_snapshot(
    *,
    shadow_coordinator: object | None,
    snapshot: MarketSnapshot,
) -> None:
    if shadow_coordinator is None:
        return
    callback = getattr(shadow_coordinator, "before_market_snapshot", None)
    if callable(callback):
        await callback(snapshot=snapshot)


async def _shadow_after_market_snapshot(
    *,
    shadow_coordinator: object | None,
    snapshot: MarketSnapshot,
) -> None:
    if shadow_coordinator is None:
        return
    callback = getattr(shadow_coordinator, "after_market_snapshot", None)
    if callable(callback):
        await callback(snapshot=snapshot)


def _should_ignore_historical_user_event(
    *,
    event: UserChannelEvent,
    session_started_at: datetime | None,
    execution: PolymarketLiveExecutionAdapter,
) -> bool:
    if session_started_at is None:
        return False
    session_start = session_started_at.astimezone(UTC)
    if isinstance(event, UserOrderEvent):
        if execution.tracker.get(event.id) is not None:
            return False
        event_time = event.timestamp or event.created_at
        return event_time is not None and event_time.astimezone(UTC) < session_start

    if execution.has_processed_trade_id(str(event.id or "")):
        return True
    if event.taker_order_id and execution.tracker.get(event.taker_order_id) is not None:
        return False
    if any(execution.tracker.get(maker_order.order_id) is not None for maker_order in event.maker_orders):
        return False
    event_time = event.timestamp or event.last_update or event.matchtime
    return event_time is not None and event_time.astimezone(UTC) < session_start
