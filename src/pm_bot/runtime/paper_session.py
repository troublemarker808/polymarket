"""Paper session runners for one-shot and continuous paper trading."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pm_bot.adapters.polymarket import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    GammaMarketsClient,
    MarketChannelClient,
    PolymarketLiveMarketDataAdapter,
)
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import Category, MarketSnapshot, RuntimeMode
from pm_bot.execution.factory import build_execution_adapter
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.paper_matching import PaperMatchEvent
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.market_universe import build_snapshot_selector
from pm_bot.runtime.paper_sync import order_payload_from_match_event, sync_paper_execution_state
from pm_bot.runtime.state import DashboardState
from pm_bot.storage.recorder import PaperRuntimeRecorder
from pm_bot.storage.recorder import JsonlRecorder
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore
from pm_bot.strategies.crypto.phase2.runtime_context import CryptoPhase2PaperContextBuilder

CRYPTO_GAMMA_TAG_ID = 21


class PaperSessionStreamError(RuntimeError):
    """Raised when the paper market stream fails unexpectedly."""


@dataclass(slots=True, frozen=True)
class PaperSessionStats:
    market_snapshots_processed: int = 0
    submitted_orders: int = 0
    reconnects: int = 0


class PaperSessionRunner:
    """Run one continuous paper session over a market snapshot stream."""

    def __init__(
        self,
        *,
        router: EventRouter,
        execution: PaperExecutionAdapter,
        risk_manager: BasicRiskManager,
        recorder: PaperRuntimeRecorder,
        market_snapshots: Sequence[MarketSnapshot],
        market_snapshot_stream: AsyncIterator[MarketSnapshot],
        summary_every_snapshots: int | None = None,
        snapshot_capture_recorder: JsonlRecorder | None = None,
        runtime_context_builder=None,
        cancel_pending_orders_on_stop: bool = False,
    ) -> None:
        self.router = router
        self.execution = execution
        self.risk_manager = risk_manager
        self.recorder = recorder
        self.market_snapshot_stream = market_snapshot_stream
        self.snapshots_by_market_id = {snapshot.market_id: snapshot for snapshot in market_snapshots}
        self.summary_every_snapshots = summary_every_snapshots
        self.snapshot_capture_recorder = snapshot_capture_recorder
        self.runtime_context_builder = runtime_context_builder
        self.cancel_pending_orders_on_stop = cancel_pending_orders_on_stop
        self.stats = PaperSessionStats()

    def current_snapshots(self) -> tuple[MarketSnapshot, ...]:
        return tuple(self.snapshots_by_market_id.values())

    async def run(
        self,
        *,
        max_market_snapshots: int | None = None,
    ) -> PaperSessionStats:
        processed = 0
        try:
            async for snapshot in self.market_snapshot_stream:
                await self._handle_market_snapshot(snapshot)
                processed += 1
                if max_market_snapshots is not None and processed >= max_market_snapshots:
                    break
        except Exception as exc:
            raise PaperSessionStreamError(str(exc)) from exc

        if self.cancel_pending_orders_on_stop and self.snapshots_by_market_id:
            final_timestamp = max(snapshot.timestamp for snapshot in self.snapshots_by_market_id.values())
            await self._cancel_pending_orders_on_stop(final_timestamp=final_timestamp)

        return self.stats

    async def _handle_market_snapshot(self, snapshot: MarketSnapshot) -> None:
        self.snapshots_by_market_id[snapshot.market_id] = snapshot
        if self.snapshot_capture_recorder is not None:
            await self.snapshot_capture_recorder.record(
                event_type="market.snapshot",
                payload=_snapshot_payload(snapshot),
            )
        self.risk_manager.record_data_success(snapshot.timestamp)
        self.recorder.note_snapshot(timestamp=snapshot.timestamp)
        await sync_paper_execution_state(
            risk_manager=self.risk_manager,
            execution=self.execution,
            snapshot=snapshot,
            ttl_seconds=self.execution.ttl_seconds,
            recorder=self.recorder,
        )
        runtime_context = None
        if self.runtime_context_builder is not None:
            runtime_context = self.runtime_context_builder(
                snapshot=snapshot,
                snapshots_by_market_id=dict(self.snapshots_by_market_id),
                recorder=self.recorder,
            )
        submitted = await self.router.run_once(snapshot=snapshot, context=runtime_context)
        expired_orders = await self.execution.cancel_stale_orders(now=snapshot.timestamp)
        for order in expired_orders:
            match_event = PaperMatchEvent(event_type="order.expired", order=order)
            await self.recorder.record(
                event_type=match_event.event_type,
                payload=order_payload_from_match_event(
                    order=order,
                    snapshot=snapshot,
                    match_event=match_event,
                ),
            )
        post_order_update = await sync_paper_execution_state(
            risk_manager=self.risk_manager,
            execution=self.execution,
            snapshot=snapshot,
            ttl_seconds=self.execution.ttl_seconds,
            recorder=self.recorder,
        )
        follow_up_submitted: list[str] = []
        if post_order_update.filled_orders or post_order_update.partial_fill_orders:
            if self.runtime_context_builder is not None:
                runtime_context = self.runtime_context_builder(
                    snapshot=snapshot,
                    snapshots_by_market_id=dict(self.snapshots_by_market_id),
                    recorder=self.recorder,
                )
            follow_up_submitted = await self.router.run_once(snapshot=snapshot, context=runtime_context)
        active_market_follow_up_submitted: list[str] = []
        if self.runtime_context_builder is not None:
            active_market_follow_up_submitted = await self._refresh_active_markets(
                trigger_snapshot=snapshot,
            )
        self.stats = PaperSessionStats(
            market_snapshots_processed=self.stats.market_snapshots_processed + 1,
            submitted_orders=(
                self.stats.submitted_orders
                + len(submitted)
                + len(follow_up_submitted)
                + len(active_market_follow_up_submitted)
            ),
            reconnects=self.stats.reconnects,
        )
        await self.recorder.record(
            event_type="market.snapshot_processed",
            payload={
                "market_id": snapshot.market_id,
                "processed_snapshots": self.stats.market_snapshots_processed,
                "submitted_orders": (
                    len(submitted)
                    + len(follow_up_submitted)
                    + len(active_market_follow_up_submitted)
                ),
                "stale_orders_cancelled": len(expired_orders),
                "updated_at": snapshot.timestamp.isoformat(),
            },
        )
        if (
            self.summary_every_snapshots is not None
            and self.summary_every_snapshots > 0
            and self.stats.market_snapshots_processed % self.summary_every_snapshots == 0
        ):
            print(
                format_paper_session_stats(
                    {
                        "processed_snapshots": self.stats.market_snapshots_processed,
                        "submitted_orders": self.stats.submitted_orders,
                        "events_recorded": len(self.recorder.events),
                        "metrics": self.recorder.metrics.to_dict(),
                        "dashboard": self.risk_manager.dashboard_state(),
                    }
                )
            )

    async def _refresh_active_markets(
        self,
        *,
        trigger_snapshot: MarketSnapshot,
    ) -> list[str]:
        dashboard = self.risk_manager.dashboard_state()
        active_market_ids = {
            position.market_id
            for position in dashboard.open_positions
        }.union(order.market_id for order in dashboard.pending_orders)
        if not active_market_ids:
            return []

        submitted_order_ids: list[str] = []
        for market_id in active_market_ids:
            if market_id == trigger_snapshot.market_id:
                continue
            position_snapshot = self.snapshots_by_market_id.get(market_id)
            if position_snapshot is None:
                continue
            refreshed_snapshot = replace(position_snapshot, timestamp=trigger_snapshot.timestamp)

            await sync_paper_execution_state(
                risk_manager=self.risk_manager,
                execution=self.execution,
                snapshot=refreshed_snapshot,
                ttl_seconds=self.execution.ttl_seconds,
                recorder=self.recorder,
            )
            runtime_context = self.runtime_context_builder(
                snapshot=refreshed_snapshot,
                snapshots_by_market_id=dict(self.snapshots_by_market_id),
                recorder=self.recorder,
            )
            submitted_order_ids.extend(
                await self.router.run_once(snapshot=refreshed_snapshot, context=runtime_context)
            )
            expired_orders = await self.execution.cancel_stale_orders(now=refreshed_snapshot.timestamp)
            for order in expired_orders:
                match_event = PaperMatchEvent(event_type="order.expired", order=order)
                await self.recorder.record(
                    event_type=match_event.event_type,
                    payload=order_payload_from_match_event(
                        order=order,
                        snapshot=refreshed_snapshot,
                        match_event=match_event,
                    ),
                )
            post_order_update = await sync_paper_execution_state(
                risk_manager=self.risk_manager,
                execution=self.execution,
                snapshot=refreshed_snapshot,
                ttl_seconds=self.execution.ttl_seconds,
                recorder=self.recorder,
            )
            if post_order_update.filled_orders or post_order_update.partial_fill_orders:
                runtime_context = self.runtime_context_builder(
                    snapshot=refreshed_snapshot,
                    snapshots_by_market_id=dict(self.snapshots_by_market_id),
                    recorder=self.recorder,
                )
                submitted_order_ids.extend(
                    await self.router.run_once(snapshot=refreshed_snapshot, context=runtime_context)
                )
        return submitted_order_ids

    async def _cancel_pending_orders_on_stop(
        self,
        *,
        final_timestamp,
    ) -> None:
        pending_orders = tuple(self.execution.pending_order_states())
        for pending_order in pending_orders:
            canceled = await self.execution.cancel_order(
                pending_order.order_id,
                now=final_timestamp,
            )
            if canceled is None:
                continue
            snapshot = self.snapshots_by_market_id.get(pending_order.market_id)
            if snapshot is None:
                continue
            cancel_snapshot = replace(snapshot, timestamp=final_timestamp)
            match_event = PaperMatchEvent(event_type="order.canceled", order=canceled)
            await self.recorder.record(
                event_type=match_event.event_type,
                payload=order_payload_from_match_event(
                    order=canceled,
                    snapshot=cancel_snapshot,
                    match_event=match_event,
                ),
            )
            await sync_paper_execution_state(
                risk_manager=self.risk_manager,
                execution=self.execution,
                snapshot=cancel_snapshot,
                ttl_seconds=self.execution.ttl_seconds,
                recorder=self.recorder,
            )


async def supervise_paper_session(
    *,
    market_data,
    router: EventRouter,
    execution: PaperExecutionAdapter,
    risk_manager: BasicRiskManager,
    recorder: PaperRuntimeRecorder,
    initial_snapshots: Sequence[MarketSnapshot] | None = None,
    max_market_snapshots: int | None = None,
    reconnect_delay_seconds: float = 1.0,
    max_reconnects: int | None = None,
    summary_every_snapshots: int | None = None,
    snapshot_capture_path: str | Path | None = None,
    count_initial_snapshots_toward_limit: bool = True,
    runtime_context_builder=None,
    cancel_pending_orders_on_stop: bool = False,
) -> PaperSessionStats:
    current_snapshots = list(initial_snapshots or await market_data.bootstrap_snapshots())
    if current_snapshots:
        risk_manager.record_data_success(max(snapshot.timestamp for snapshot in current_snapshots))
    aggregate = PaperSessionStats()
    include_initial = True
    snapshot_capture_recorder = JsonlRecorder(snapshot_capture_path) if snapshot_capture_path is not None else None

    while True:
        runner = PaperSessionRunner(
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            market_snapshots=current_snapshots,
            market_snapshot_stream=market_data.stream_from_snapshots(
                list(current_snapshots),
                include_initial=include_initial,
            ),
            summary_every_snapshots=summary_every_snapshots,
            snapshot_capture_recorder=snapshot_capture_recorder,
            runtime_context_builder=runtime_context_builder,
            cancel_pending_orders_on_stop=cancel_pending_orders_on_stop,
        )

        stream_error: PaperSessionStreamError | None = None
        try:
            cycle_stats = await runner.run(
                max_market_snapshots=_cycle_limit(
                    max_market_snapshots=max_market_snapshots,
                    aggregate_processed=aggregate.market_snapshots_processed,
                    initial_snapshot_count=(len(current_snapshots) if include_initial else 0),
                    count_initial_snapshots_toward_limit=count_initial_snapshots_toward_limit,
                )
            )
        except PaperSessionStreamError as exc:
            cycle_stats = runner.stats
            stream_error = exc

        aggregate = PaperSessionStats(
            market_snapshots_processed=aggregate.market_snapshots_processed + cycle_stats.market_snapshots_processed,
            submitted_orders=aggregate.submitted_orders + cycle_stats.submitted_orders,
            reconnects=aggregate.reconnects,
        )
        current_snapshots = list(_merge_snapshots(primary=runner.current_snapshots(), fallback=current_snapshots))
        if max_market_snapshots is not None and aggregate.market_snapshots_processed >= max_market_snapshots:
            return aggregate
        if stream_error is None:
            return aggregate

        reconnect_number = aggregate.reconnects + 1
        if max_reconnects is not None and reconnect_number > max_reconnects:
            raise RuntimeError("Paper session exceeded reconnect budget") from stream_error

        aggregate = PaperSessionStats(
            market_snapshots_processed=aggregate.market_snapshots_processed,
            submitted_orders=aggregate.submitted_orders,
            reconnects=reconnect_number,
        )
        await recorder.record(
            event_type="paper.reconnect",
            payload={
                "reconnect_count": reconnect_number,
                "reason": str(stream_error),
            },
        )
        if reconnect_delay_seconds > 0:
            await asyncio.sleep(reconnect_delay_seconds)
        try:
            refreshed = await market_data.bootstrap_snapshots()
        except Exception as exc:
            risk_manager.record_data_failure(reason=f"{type(exc).__name__}: {exc}")
            await recorder.record(
                event_type="market_data.failure",
                payload={"error": f"{type(exc).__name__}: {exc}"},
            )
            if not current_snapshots:
                raise
        else:
            current_snapshots = list(_merge_snapshots(primary=refreshed, fallback=current_snapshots))
            if refreshed:
                risk_manager.record_data_success(max(snapshot.timestamp for snapshot in refreshed))
                await recorder.record(
                    event_type="market_data.recovered",
                    payload={"updated_at": max(snapshot.timestamp for snapshot in refreshed).isoformat()},
                )
        include_initial = False


async def run_crypto_paper_session_once(
    *,
    config_dir: str = "configs",
    limit: int = 50,
    max_pages: int = 1,
    tag_id: int = CRYPTO_GAMMA_TAG_ID,
    state_path: str = "data/runtime/runtime_state.json",
    event_path: str | Path | None = None,
    metrics_path: str | Path | None = None,
    snapshot_capture_path: str | Path | None = None,
) -> dict[str, object]:
    return await _run_crypto_paper_session(
        config_dir=config_dir,
        state_path=state_path,
        max_pages=max_pages,
        tag_id=tag_id,
        max_market_snapshots=limit,
        event_path=event_path,
        metrics_path=metrics_path,
        snapshot_capture_path=snapshot_capture_path,
        use_market_ws=False,
        summary_every_snapshots=None,
    )


async def run_crypto_paper_session(
    *,
    config_dir: str = "configs",
    state_path: str = "data/runtime/runtime_state.json",
    recorder_path: str | Path = "data/runtime/paper-events.current.jsonl",
    metrics_path: str | Path = "data/runtime/paper-metrics.latest.json",
    max_pages: int = 1,
    max_market_snapshots: int | None = None,
    tag_id: int = CRYPTO_GAMMA_TAG_ID,
    summary_every_snapshots: int | None = 50,
    snapshot_capture_path: str | Path | None = None,
    count_initial_snapshots_toward_limit: bool = True,
    runtime_context_builder=None,
    cancel_pending_orders_on_stop: bool = False,
) -> dict[str, object]:
    return await _run_crypto_paper_session(
        config_dir=config_dir,
        state_path=state_path,
        max_pages=max_pages,
        tag_id=tag_id,
        max_market_snapshots=max_market_snapshots,
        event_path=recorder_path,
        metrics_path=metrics_path,
        snapshot_capture_path=snapshot_capture_path,
        use_market_ws=True,
        summary_every_snapshots=summary_every_snapshots,
        count_initial_snapshots_toward_limit=count_initial_snapshots_toward_limit,
        runtime_context_builder=runtime_context_builder,
        cancel_pending_orders_on_stop=cancel_pending_orders_on_stop,
    )


async def run_crypto_phase2_paper_session(
    *,
    config_dir: str = "configs/profiles/paper-crypto-phase2-v1",
    state_path: str = "data/runtime/runtime_state.json",
    underlying_state_path: str,
    recorder_path: str | Path = "data/runtime/paper-events.current.jsonl",
    metrics_path: str | Path = "data/runtime/paper-metrics.latest.json",
    max_pages: int = 1,
    max_market_snapshots: int | None = None,
    tag_id: int = CRYPTO_GAMMA_TAG_ID,
    summary_every_snapshots: int | None = 50,
    snapshot_capture_path: str | Path | None = None,
    count_initial_snapshots_toward_limit: bool = True,
    cancel_pending_orders_on_stop: bool = False,
) -> dict[str, object]:
    context_builder = CryptoPhase2PaperContextBuilder(
        underlying_state_path=underlying_state_path,
        apply_series_filter=True,
    )
    return await _run_crypto_paper_session(
        config_dir=config_dir,
        state_path=state_path,
        max_pages=max_pages,
        tag_id=tag_id,
        max_market_snapshots=max_market_snapshots,
        event_path=recorder_path,
        metrics_path=metrics_path,
        snapshot_capture_path=snapshot_capture_path,
        use_market_ws=True,
        summary_every_snapshots=summary_every_snapshots,
        count_initial_snapshots_toward_limit=count_initial_snapshots_toward_limit,
        cancel_pending_orders_on_stop=cancel_pending_orders_on_stop,
        runtime_context_builder=lambda **kwargs: context_builder.build_context(
            snapshot_cache=kwargs["snapshots_by_market_id"].values(),
            recorder=kwargs["recorder"],
        ),
    )


async def _run_crypto_paper_session(
    *,
    config_dir: str,
    state_path: str,
    max_pages: int,
    tag_id: int,
    max_market_snapshots: int | None,
    event_path: str | Path | None,
    metrics_path: str | Path | None,
    snapshot_capture_path: str | Path | None,
    use_market_ws: bool,
    summary_every_snapshots: int | None,
    count_initial_snapshots_toward_limit: bool = True,
    runtime_context_builder=None,
    cancel_pending_orders_on_stop: bool = False,
) -> dict[str, object]:
    settings = load_settings_from_directory(config_dir)
    if settings.app.mode != RuntimeMode.PAPER:
        raise ValueError("Paper session runner requires app.mode=paper")

    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
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
    if not isinstance(execution, PaperExecutionAdapter):
        raise TypeError("Paper session runner requires PaperExecutionAdapter")
    recorder = PaperRuntimeRecorder(event_path=event_path, metrics_path=metrics_path)

    async with GammaMarketsClient(
        base_url=settings.polymarket.gamma_url,
    ) as gamma_client, ClobPublicClient(
        base_url=settings.polymarket.api_url,
    ) as clob_client:
        market_data = PolymarketLiveMarketDataAdapter(
            gamma_client=gamma_client,
            clob_enricher=ClobSnapshotEnricher(clob_client),
            market_event_stream=MarketChannelClient(settings.polymarket.market_ws_url) if use_market_ws else None,
            max_pages=max_pages,
            tag_id=tag_id,
            snapshot_selector=snapshot_selector,
        )
        try:
            seed_snapshots = await market_data.bootstrap_snapshots()
        except Exception as exc:
            risk_manager.record_data_failure(reason=f"{type(exc).__name__}: {exc}")
            await recorder.record(
                event_type="market_data.failure",
                payload={"error": f"{type(exc).__name__}: {exc}"},
            )
            raise
        if seed_snapshots:
            risk_manager.record_data_success(max(snapshot.timestamp for snapshot in seed_snapshots))

        router = EventRouter(
            market_data=market_data,
            strategies=strategies,
            risk_manager=risk_manager,
            execution=execution,
            recorder=recorder,
            default_order_size=settings.trading.default_order_notional,
        )
        stats = await supervise_paper_session(
            market_data=market_data,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=seed_snapshots,
            max_market_snapshots=max_market_snapshots,
            summary_every_snapshots=summary_every_snapshots,
            snapshot_capture_path=snapshot_capture_path,
            count_initial_snapshots_toward_limit=count_initial_snapshots_toward_limit,
            runtime_context_builder=runtime_context_builder,
            cancel_pending_orders_on_stop=cancel_pending_orders_on_stop,
        )

    dashboard = risk_manager.dashboard_state()
    return {
        "processed_snapshots": stats.market_snapshots_processed,
        "submitted_orders": stats.submitted_orders,
        "events_recorded": len(recorder.events),
        "metrics": recorder.metrics.to_dict(),
        "dashboard": dashboard,
    }


def format_dashboard_summary(result: dict[str, object]) -> str:
    return format_paper_session_stats(result)


def format_paper_session_stats(result: dict[str, object]) -> str:
    dashboard = result["dashboard"]
    if not isinstance(dashboard, DashboardState):
        raise TypeError("dashboard result must be a DashboardState")

    metrics = result.get("metrics")
    metrics_map = metrics if isinstance(metrics, Mapping) else {}
    return "\n".join(
        [
            f"processed_snapshots={result['processed_snapshots']}",
            f"submitted_orders={result['submitted_orders']}",
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
            render_dashboard(dashboard),
        ]
    )


def _remaining_limit(limit: int | None, processed: int) -> int | None:
    if limit is None:
        return None
    remaining = limit - processed
    return max(remaining, 0)


def _cycle_limit(
    *,
    max_market_snapshots: int | None,
    aggregate_processed: int,
    initial_snapshot_count: int,
    count_initial_snapshots_toward_limit: bool,
) -> int | None:
    remaining = _remaining_limit(max_market_snapshots, aggregate_processed)
    if (
        remaining is None
        or count_initial_snapshots_toward_limit
        or initial_snapshot_count <= 0
    ):
        return remaining
    return remaining + initial_snapshot_count


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


def _snapshot_payload(snapshot: MarketSnapshot) -> dict[str, object]:
    return {
        "market_id": snapshot.market_id,
        "token_id": snapshot.token_id,
        "slug": snapshot.slug,
        "category": snapshot.category.value,
        "timestamp": snapshot.timestamp.isoformat(),
        "resolution_time": snapshot.resolution_time.isoformat() if snapshot.resolution_time is not None else None,
        "best_bid_yes": snapshot.best_bid_yes,
        "best_ask_yes": snapshot.best_ask_yes,
        "best_bid_no": snapshot.best_bid_no,
        "best_ask_no": snapshot.best_ask_no,
        "best_bid_yes_size": snapshot.best_bid_yes_size,
        "best_ask_yes_size": snapshot.best_ask_yes_size,
        "best_bid_no_size": snapshot.best_bid_no_size,
        "best_ask_no_size": snapshot.best_ask_no_size,
        "tick_size": snapshot.tick_size,
        "min_order_size": snapshot.min_order_size,
        "last_traded_price": snapshot.last_traded_price,
        "last_trade_side": snapshot.last_trade_side,
        "last_trade_size": snapshot.last_trade_size,
        "yes_bid_levels": _level_payload(snapshot.yes_bid_levels),
        "yes_ask_levels": _level_payload(snapshot.yes_ask_levels),
        "no_bid_levels": _level_payload(snapshot.no_bid_levels),
        "no_ask_levels": _level_payload(snapshot.no_ask_levels),
        "liquidity_score": snapshot.liquidity_score,
        "metadata": dict(snapshot.metadata),
    }


def _level_payload(levels) -> list[dict[str, float]]:
    return [{"price": level.price, "size": level.size} for level in levels]
