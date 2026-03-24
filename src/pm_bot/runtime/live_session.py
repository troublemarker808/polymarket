"""Long-running live crypto session runner with reconnect supervision."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pm_bot.adapters.polymarket import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    GammaMarketsClient,
    MarketChannelClient,
    PolymarketLiveMarketDataAdapter,
    UserChannelClient,
    UserChannelEvent,
    UserOrderEvent,
    UserTradeEvent,
)
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import MarketSnapshot, RuntimeMode
from pm_bot.execution.factory import build_execution_adapter
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_reconcile import LiveRecoveryStats, recover_live_state
from pm_bot.runtime.live_sync import sync_live_execution_state
from pm_bot.storage.recorder import JsonlRecorder
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore

if TYPE_CHECKING:
    from pm_bot.core.interfaces import EventRecorder, RiskManager


CRYPTO_GAMMA_TAG_ID = 21


class UserEventStream(Protocol):
    def stream_events(
        self,
        *,
        auth: object,
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
    ) -> None:
        self.router = router
        self.execution = execution
        self.risk_manager = risk_manager
        self.recorder = recorder
        self.market_snapshot_stream = market_snapshot_stream
        self.user_event_stream = user_event_stream
        self.snapshots_by_market_id = {snapshot.market_id: snapshot for snapshot in market_snapshots}
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

        async def pump_market() -> None:
            processed = 0
            try:
                async for snapshot in self.market_snapshot_stream:
                    await queue.put(("market", snapshot))
                    processed += 1
                    if max_market_snapshots is not None and processed >= max_market_snapshots:
                        break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await queue.put(("error", ("market", exc)))
            finally:
                await queue.put(("done", "market"))

        async def pump_user() -> None:
            processed = 0
            try:
                async for event in self.user_event_stream:
                    await queue.put(("user", event))
                    processed += 1
                    if max_user_events is not None and processed >= max_user_events:
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

        try:
            while done_streams < 2:
                kind, payload = await queue.get()
                if kind == "done":
                    done_streams += 1
                    continue
                if kind == "error":
                    stream_name, error = payload
                    assert isinstance(stream_name, str)
                    assert isinstance(error, Exception)
                    raise LiveSessionStreamError(stream_name) from error
                if kind == "market":
                    assert isinstance(payload, MarketSnapshot)
                    await self._handle_market_snapshot(payload)
                    continue
                assert isinstance(payload, (UserOrderEvent, UserTradeEvent))
                await self._handle_user_event(payload)
        finally:
            for task in (market_task, user_task):
                task.cancel()
            await asyncio.gather(market_task, user_task, return_exceptions=True)

        return self.stats

    async def _handle_market_snapshot(self, snapshot: MarketSnapshot) -> None:
        self.snapshots_by_market_id[snapshot.market_id] = snapshot
        _record_data_success(self.risk_manager, snapshot.timestamp)
        submitted = await self.router.run_once(snapshot=snapshot)
        cancelled = await self.execution.cancel_stale()
        await sync_live_execution_state(
            risk_manager=self.risk_manager,
            execution=self.execution,
            snapshots=tuple(self.snapshots_by_market_id.values()),
        )

        self.stats = LiveSessionStats(
            market_snapshots_processed=self.stats.market_snapshots_processed + 1,
            user_events_processed=self.stats.user_events_processed,
            submitted_orders=self.stats.submitted_orders + len(submitted),
            stale_orders_cancelled=self.stats.stale_orders_cancelled + cancelled,
            recovered_open_orders=self.stats.recovered_open_orders,
            replayed_trades=self.stats.replayed_trades,
            rebuilt_positions=self.stats.rebuilt_positions,
            reconnects=self.stats.reconnects,
        )
        await self._record(
            "market.snapshot_processed",
            {
                "market_id": snapshot.market_id,
                "submitted_orders": len(submitted),
                "stale_orders_cancelled": cancelled,
            },
        )

    async def _handle_user_event(self, event: UserChannelEvent) -> None:
        if isinstance(event, UserOrderEvent):
            tracked = self.execution.apply_user_order_event(event)
            await self._record(
                "user.order_event",
                {
                    "order_id": event.id,
                    "status": event.status,
                    "tracked": tracked is not None,
                },
            )
        else:
            positions = self.execution.apply_user_trade_event(event)
            await sync_live_execution_state(
                risk_manager=self.risk_manager,
                execution=self.execution,
                snapshots=tuple(self.snapshots_by_market_id.values()),
            )
            closed_trades = self.execution.drain_closed_trades()
            for closed_trade in closed_trades:
                await self.risk_manager.record_trade_close(closed_trade)
                await self._record(
                    "trade.closed",
                    {
                        "market_id": closed_trade.market_id,
                        "token_id": closed_trade.token_id,
                        "realized_pnl": closed_trade.realized_pnl,
                        "fees_paid": closed_trade.fees_paid,
                        "net_pnl": closed_trade.net_pnl,
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
) -> LiveSessionStats:
    current_snapshots = list(initial_snapshots or await market_data.bootstrap_snapshots())
    if current_snapshots:
        _record_data_success(risk_manager, max(snapshot.timestamp for snapshot in current_snapshots))
    aggregate = LiveSessionStats()
    include_initial = True

    while True:
        recovery_stats = await recover_live_state(
            risk_manager=risk_manager,
            execution=execution,
            snapshots=tuple(current_snapshots),
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
        _record_data_failure(risk_manager, reason=f"{type(exc).__name__}: {exc}")
        await _record_supervisor_event(
            recorder=recorder,
            event_type="market_data.failure",
            payload={"error": f"{type(exc).__name__}: {exc}"},
        )
        if not fallback_snapshots:
            raise
        return tuple(fallback_snapshots)

    if refreshed:
        _record_data_success(risk_manager, max(snapshot.timestamp for snapshot in refreshed))

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


def _record_data_success(risk_manager: RiskManager, timestamp) -> None:
    callback = getattr(risk_manager, "record_data_success", None)
    if callable(callback):
        callback(timestamp)


def _record_data_failure(risk_manager: RiskManager, *, reason: str) -> None:
    callback = getattr(risk_manager, "record_data_failure", None)
    if callable(callback):
        callback(reason=reason)


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
    market_done = max_market_snapshots is None or stats.market_snapshots_processed >= max_market_snapshots
    user_done = max_user_events is None or stats.user_events_processed >= max_user_events
    return market_done and user_done


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
    by_market_id.update({snapshot.market_id: snapshot for snapshot in primary})
    return tuple(by_market_id.values())


async def run_crypto_live_session(
    *,
    config_dir: str = "configs",
    state_path: str = "data/runtime/runtime_state.json",
    recorder_path: str | Path = "data/runtime/live-events.jsonl",
    max_pages: int = 1,
    max_market_snapshots: int | None = None,
    max_user_events: int | None = None,
    gamma_tag_id: int = CRYPTO_GAMMA_TAG_ID,
) -> LiveSessionStats:
    settings = load_settings_from_directory(config_dir)
    if settings.app.mode != RuntimeMode.LIVE:
        raise ValueError("Live session runner requires app.mode=live")

    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    state_store = JsonRuntimeStateStore(state_path)
    risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state_store=state_store,
    )
    execution = build_execution_adapter(settings=settings)
    if not isinstance(execution, PolymarketLiveExecutionAdapter):
        raise TypeError("Live session runner requires PolymarketLiveExecutionAdapter")

    recorder = JsonlRecorder(path=recorder_path)

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
        )
        try:
            seed_snapshots = await market_data.bootstrap_snapshots()
        except Exception as exc:
            _record_data_failure(risk_manager, reason=f"{type(exc).__name__}: {exc}")
            await recorder.record(
                event_type="market_data.failure",
                payload={"error": f"{type(exc).__name__}: {exc}"},
            )
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
        return await supervise_live_session(
            market_data=market_data,
            user_client=user_client,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=seed_snapshots,
            max_market_snapshots=max_market_snapshots,
            max_user_events=max_user_events,
        )
