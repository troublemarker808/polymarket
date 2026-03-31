"""Synchronized live + shadow-paper runtime for normal strategy validation."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import math
from pathlib import Path
import re
from typing import Any, cast

from pm_bot.adapters.polymarket import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    GammaMarketsClient,
    MarketChannelClient,
    PolymarketLiveMarketDataAdapter,
    UserChannelClient,
)
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, RuntimeMode, SignalSide
from pm_bot.execution.order_tracker import TrackedOrder
from pm_bot.execution.position_ledger import LivePosition
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.paper_matching import PaperMatchEvent
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.execution.order_tracker import OrderLifecycleStatus
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.execution_artifacts import tracked_order_payload
from pm_bot.runtime.live_session import supervise_live_session
from pm_bot.runtime.live_reconcile import recover_live_state
from pm_bot.runtime.market_universe import build_snapshot_selector
from pm_bot.runtime.paper_sync import order_payload_from_match_event, sync_paper_execution_state
from pm_bot.runtime.state import DashboardState, PositionState
from pm_bot.runtime.underlying_state import resolve_underlying_state_path
from pm_bot.storage.recorder import LiveRuntimeRecorder, PaperRuntimeRecorder
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.state_loader import load_underlying_states
from pm_bot.strategies.crypto.phase1.selection import load_runtime_preferred_market_ids
from pm_bot.strategies.crypto.phase2.runtime_context import CryptoPhase2PaperContextBuilder


CRYPTO_GAMMA_TAG_ID = 21
SYNC_SHADOW_DUST_NOTIONAL = 0.10
SYNC_SHADOW_DUST_SHARES = 0.10
_BALANCE_ERROR_PATTERN = re.compile(r"balance:\s*(\d+),\s*order amount:\s*(\d+)", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class SyncSessionResult:
    live_stats: dict[str, object]
    shadow_stats: dict[str, object]


class ShadowPaperCoordinator:
    """Mirror approved live intents into a paper shadow ledger and artifact stream."""

    def __init__(
        self,
        *,
        execution: PaperExecutionAdapter,
        risk_manager: BasicRiskManager,
        recorder: PaperRuntimeRecorder,
    ) -> None:
        self.execution = execution
        self.risk_manager = risk_manager
        self.recorder = recorder
        self._live_to_shadow_order_ids: dict[str, str] = {}
        self._snapshots_by_market_id: dict[str, MarketSnapshot] = {}
        self._submitted_since_snapshot = 0

    async def mirror_submission(self, *, live_order_id: str, intent: OrderIntent) -> str:
        shadow_order_id = await self.execution.submit(intent)
        self._live_to_shadow_order_ids[live_order_id] = shadow_order_id
        await self.risk_manager.record_order_submission(intent, shadow_order_id)
        await self.recorder.record(
            event_type="order.submitted",
            payload={
                "order_id": shadow_order_id,
                "intent_id": intent.intent_id,
                "live_order_id": live_order_id,
                "strategy_id": intent.strategy_id,
                "market_id": intent.market_id,
                "token_id": intent.token_id,
                "side": intent.side.value,
                "price": intent.price,
                "size": intent.size,
                "notional": intent.notional,
                "created_at": intent.created_at.isoformat(),
                "replaced_order_id": None,
            },
        )
        self._submitted_since_snapshot += 1
        return shadow_order_id

    async def mirror_cancellation(
        self,
        *,
        live_order_id: str,
        now: datetime | None,
        reason: str,
    ) -> None:
        shadow_order_id = self._live_to_shadow_order_ids.pop(live_order_id, None)
        if shadow_order_id is None:
            return
        canceled_order = await self.execution.cancel_order(shadow_order_id, now=now)
        if canceled_order is None:
            return
        await self.risk_manager.record_order_cancellation(shadow_order_id)
        await self.recorder.record(
            event_type="order.canceled",
            payload={
                **tracked_order_payload(
                    order=canceled_order,
                    snapshot=self._snapshot_for_order(canceled_order),
                ),
                "reason": reason,
                "live_order_id": live_order_id,
            },
        )

    async def before_market_snapshot(self, *, snapshot: MarketSnapshot) -> None:
        self._snapshots_by_market_id[snapshot.market_id] = snapshot
        self.risk_manager.record_data_success(snapshot.timestamp)
        self.recorder.note_snapshot(
            timestamp=snapshot.timestamp,
            payload={"updated_at": snapshot.timestamp.isoformat()},
        )
        await sync_paper_execution_state(
            risk_manager=self.risk_manager,
            execution=self.execution,
            snapshot=snapshot,
            ttl_seconds=self.execution.ttl_seconds,
            recorder=self.recorder,
        )

    async def after_market_snapshot(self, *, snapshot: MarketSnapshot) -> None:
        expired_orders = await self.execution.cancel_stale_orders(now=snapshot.timestamp)
        for order in expired_orders:
            await self.recorder.record(
                event_type="order.expired",
                payload=order_payload_from_match_event(
                    order=order,
                    snapshot=snapshot,
                    match_event=PaperMatchEvent(event_type="order.expired", order=order),
                ),
            )
        await sync_paper_execution_state(
            risk_manager=self.risk_manager,
            execution=self.execution,
            snapshot=snapshot,
            ttl_seconds=self.execution.ttl_seconds,
            recorder=self.recorder,
        )
        await self.recorder.record(
            event_type="market.snapshot_processed",
            payload={
                "market_id": snapshot.market_id,
                "processed_snapshots": self.recorder.metrics.processed_snapshots,
                "submitted_orders": self._submitted_since_snapshot,
                "stale_orders_cancelled": len(expired_orders),
                "updated_at": snapshot.timestamp.isoformat(),
            },
        )
        self._submitted_since_snapshot = 0

    def dashboard_state(self) -> DashboardState:
        return self.risk_manager.dashboard_state()

    def _snapshot_for_order(self, order: TrackedOrder) -> MarketSnapshot | None:
        direct = self._snapshots_by_market_id.get(order.market_id)
        if direct is not None:
            return direct
        for snapshot in self._snapshots_by_market_id.values():
            if order.token_id == snapshot.token_id or order.token_id == snapshot.metadata.get("no_token_id"):
                return snapshot
        return None


class SynchronizedLiveExecutionAdapter:
    """Live execution adapter that mirrors successful live intents into shadow paper."""

    def __init__(
        self,
        *,
        live_execution: PolymarketLiveExecutionAdapter,
        shadow_coordinator: ShadowPaperCoordinator,
    ) -> None:
        self.live_execution = live_execution
        self.shadow_coordinator = shadow_coordinator

    async def submit(self, intent: OrderIntent) -> str:
        live_order_id = await self.live_execution.submit(intent)
        await self.shadow_coordinator.mirror_submission(
            live_order_id=live_order_id,
            intent=intent,
        )
        return live_order_id

    async def cancel_order(self, order_id: str, *, now: datetime | None = None) -> TrackedOrder | None:
        canceled_order = await self.live_execution.cancel_order(order_id, now=now)
        if canceled_order is not None:
            await self.shadow_coordinator.mirror_cancellation(
                live_order_id=order_id,
                now=now,
                reason="live_canceled",
            )
        return canceled_order

    async def cancel_stale(self) -> int:
        return len(await self.cancel_stale_orders())

    async def cancel_stale_orders(self) -> tuple[TrackedOrder, ...]:
        canceled_orders = await self.live_execution.cancel_stale_orders()
        for order in canceled_orders:
            await self.shadow_coordinator.mirror_cancellation(
                live_order_id=order.order_id,
                now=order.updated_at,
                reason="stale_ttl_cancel",
            )
        return canceled_orders

    def __getattr__(self, name: str) -> Any:
        return getattr(self.live_execution, name)


def format_sync_session_summary(result: SyncSessionResult) -> str:
    live = _scalar_stats(result.live_stats)
    shadow = _scalar_stats(result.shadow_stats)
    return "\n".join(
        [
            "[live]",
            *(f"{key}={value}" for key, value in live.items()),
            "",
            "[shadow]",
            *(f"{key}={value}" for key, value in shadow.items()),
        ]
    )


def _scalar_stats(values: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in values.items()
        if isinstance(value, (str, int, float, bool))
    }


async def run_crypto_sync_session(
    *,
    config_dir: str = "configs",
    live_state_path: str = "data/runtime/sync-live-state.json",
    live_event_path: str | Path = "data/runtime/sync-live-events.jsonl",
    live_metrics_path: str | Path = "data/runtime/sync-live-metrics.json",
    shadow_state_path: str = "data/runtime/sync-shadow-state.json",
    shadow_event_path: str | Path = "data/runtime/sync-shadow-events.jsonl",
    shadow_metrics_path: str | Path = "data/runtime/sync-shadow-metrics.json",
    max_pages: int = 1,
    max_market_snapshots: int | None = None,
    max_user_events: int | None = None,
    gamma_tag_id: int = CRYPTO_GAMMA_TAG_ID,
    summary_every_snapshots: int | None = 50,
    underlying_state_path: str | None = None,
    selection_report_path: str | Path | None = None,
) -> SyncSessionResult:
    settings = load_settings_from_directory(config_dir)
    if settings.app.mode != RuntimeMode.LIVE:
        raise ValueError("Sync session runner requires app.mode=live")

    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    enabled_strategy_ids = {
        strategy_id
        for category_config in settings.category_configs.values()
        for strategy_id in category_config.enabled_strategies
    }
    resolved_underlying_state_path: str | None = None
    if "crypto.phase2" in enabled_strategy_ids:
        if underlying_state_path is None:
            raise ValueError(
                "run_crypto_sync_session requires underlying_state_path when crypto.phase2 is enabled"
            )
        resolved_underlying_state_path = str(resolve_underlying_state_path(underlying_state_path))
    crypto_config = settings.category_configs.get(Category.CRYPTO)
    markets_config = dict(crypto_config.markets) if crypto_config is not None else None
    if markets_config is not None and selection_report_path is not None:
        preferred_market_ids = load_runtime_preferred_market_ids(selection_report_path)
        if preferred_market_ids:
            markets_config["preferred_market_ids"] = list(preferred_market_ids)
    discovery_max_pages = max_pages
    if markets_config is not None:
        configured_max_pages = _parse_optional_int(markets_config.get("discovery_max_pages"))
        if configured_max_pages is not None:
            discovery_max_pages = max(discovery_max_pages, configured_max_pages)
    snapshot_selector = build_snapshot_selector(markets_config)
    if (
        "crypto.phase2" in enabled_strategy_ids
        and markets_config is not None
        and resolved_underlying_state_path is not None
    ):
        min_barrier_distance_ratio = _parse_optional_float(markets_config.get("min_barrier_distance_ratio"))
        max_barrier_distance_ratio = _parse_optional_float(markets_config.get("max_barrier_distance_ratio"))
        if min_barrier_distance_ratio is not None or max_barrier_distance_ratio is not None:
            underlying_states = load_underlying_states(resolved_underlying_state_path)
            base_selector = snapshot_selector

            def snapshot_selector(snapshots: Sequence[MarketSnapshot]) -> list[MarketSnapshot]:
                base_snapshots = list(base_selector(tuple(snapshots))) if base_selector is not None else list(snapshots)
                return _filter_snapshots_by_crypto_barrier_distance(
                    snapshots=base_snapshots,
                    underlying_states=underlying_states,
                    min_distance_ratio=min_barrier_distance_ratio,
                    max_distance_ratio=max_barrier_distance_ratio,
                )

    live_state_store = JsonRuntimeStateStore(live_state_path)
    live_risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state_store=live_state_store,
    )
    starting_runtime_open_positions = _filter_cleanup_runtime_positions(
        tuple(live_risk_manager.state.open_positions.values())
    )
    starting_runtime_pending_orders = tuple(live_risk_manager.state.pending_orders.values())
    cleanup_only_mode = bool(starting_runtime_open_positions) or bool(starting_runtime_pending_orders)
    shadow_state_store = JsonRuntimeStateStore(shadow_state_path)
    shadow_risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state_store=shadow_state_store,
    )

    live_execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=settings.polymarket,
        ttl_seconds=settings.trading.default_quote_ttl_seconds,
    )
    live_execution.restore_processed_trade_ids(live_risk_manager.state.processed_trade_ids)
    shadow_execution = PaperExecutionAdapter(
        ttl_seconds=settings.trading.default_quote_ttl_seconds,
        place_latency_ms=settings.trading.paper_place_latency_ms,
        cancel_latency_ms=settings.trading.paper_cancel_latency_ms,
        fee_bps=settings.trading.paper_fee_bps,
        taker_slippage_bps=settings.trading.paper_taker_slippage_bps,
    )
    live_recorder = LiveRuntimeRecorder(
        event_path=live_event_path,
        metrics_path=live_metrics_path,
    )
    shadow_recorder = PaperRuntimeRecorder(
        event_path=shadow_event_path,
        metrics_path=shadow_metrics_path,
    )
    shadow_coordinator = ShadowPaperCoordinator(
        execution=shadow_execution,
        risk_manager=shadow_risk_manager,
        recorder=shadow_recorder,
    )
    sync_execution = SynchronizedLiveExecutionAdapter(
        live_execution=live_execution,
        shadow_coordinator=shadow_coordinator,
    )
    runtime_context_builder = None
    if "crypto.phase2" in enabled_strategy_ids:
        phase2_context_builder = CryptoPhase2PaperContextBuilder(
            underlying_state_path=cast(str, resolved_underlying_state_path),
            apply_series_filter=True,
            selection_report_path=selection_report_path,
        )
        def runtime_context_builder(
            *,
            snapshot: MarketSnapshot,
            snapshots_by_market_id: Mapping[str, MarketSnapshot],
            recorder: object | None,
        ) -> Mapping[str, object]:
            del snapshot
            return phase2_context_builder.build_context(
                snapshot_cache=tuple(snapshots_by_market_id.values()),
                recorder=cast(PaperRuntimeRecorder, recorder),
            )

    session_started_at = datetime.now(tz=UTC)
    active_strategy_ids = tuple(
        str(getattr(strategy, "strategy_id", "")).strip()
        for strategy in (() if cleanup_only_mode else strategies)
        if str(getattr(strategy, "strategy_id", "")).strip()
    )
    await live_recorder.record(
        event_type="live.session_started",
        payload={
            "started_at": session_started_at.isoformat(),
            "mode": "sync_shadow",
            "recovery_scope": settings.polymarket.live_recovery_scope,
            "configured_signature_type": settings.polymarket.signature_type,
            "resolved_signature_type": live_execution.signature_type,
            "cleanup_only_mode": cleanup_only_mode,
            "strategies_enabled": bool(active_strategy_ids),
            "enabled_strategy_ids": sorted(enabled_strategy_ids),
            "active_strategy_ids": list(active_strategy_ids),
            "starting_runtime_open_positions": len(starting_runtime_open_positions),
            "starting_runtime_pending_orders": len(starting_runtime_pending_orders),
            "resolved_underlying_state_path": resolved_underlying_state_path,
        },
    )
    await shadow_recorder.record(
        event_type="shadow.session_started",
        payload={
            "started_at": session_started_at.isoformat(),
            "mode": "sync_shadow",
            "cleanup_only_mode": cleanup_only_mode,
            "strategies_enabled": bool(active_strategy_ids),
            "active_strategy_ids": list(active_strategy_ids),
            "starting_runtime_open_positions": len(starting_runtime_open_positions),
            "starting_runtime_pending_orders": len(starting_runtime_pending_orders),
            "resolved_underlying_state_path": resolved_underlying_state_path,
        },
    )

    current_snapshots: tuple[MarketSnapshot, ...] = ()
    async with GammaMarketsClient(
        base_url=settings.polymarket.gamma_url,
    ) as gamma_client, ClobPublicClient(
        base_url=settings.polymarket.api_url,
    ) as clob_client:
        market_data = PolymarketLiveMarketDataAdapter(
            gamma_client=gamma_client,
            clob_enricher=ClobSnapshotEnricher(clob_client),
            market_event_stream=MarketChannelClient(settings.polymarket.market_ws_url),
            max_pages=discovery_max_pages,
            tag_id=gamma_tag_id,
            snapshot_selector=snapshot_selector,
        )
        seed_snapshots = await market_data.bootstrap_snapshots()
        required_cleanup_snapshots = await _load_required_cleanup_snapshots(
            gamma_client=gamma_client,
            clob_enricher=market_data.clob_enricher,
            required_market_ids={
                *live_risk_manager.state.open_positions.keys(),
                *(pending.market_id for pending in live_risk_manager.state.pending_orders.values()),
            },
            page_size=market_data.page_size,
            max_pages=discovery_max_pages,
            tag_id=gamma_tag_id,
        )
        seed_snapshots = list(_merge_snapshots_by_market_id(seed_snapshots, required_cleanup_snapshots))
        if seed_snapshots:
            latest_seed = max(snapshot.timestamp for snapshot in seed_snapshots)
            live_risk_manager.record_data_success(latest_seed)
            shadow_risk_manager.record_data_success(latest_seed)
        await _preflight_cancel_sync_shadow_open_orders(
            execution=live_execution,
            snapshots=seed_snapshots,
            recorder=live_recorder,
        )
        router = EventRouter(
            market_data=market_data,
            strategies=() if cleanup_only_mode else strategies,
            risk_manager=live_risk_manager,
            execution=sync_execution,
            recorder=live_recorder,
            default_order_size=settings.trading.default_order_notional,
        )
        user_client = UserChannelClient(settings.polymarket.user_ws_url)
        live_stats = await supervise_live_session(
            market_data=market_data,
            user_client=user_client,
            router=router,
            execution=cast(PolymarketLiveExecutionAdapter, sync_execution),
            risk_manager=live_risk_manager,
            recorder=live_recorder,
            initial_snapshots=seed_snapshots,
            max_market_snapshots=max_market_snapshots,
            max_user_events=max_user_events,
            summary_every_snapshots=summary_every_snapshots,
            recovery_scope=settings.polymarket.live_recovery_scope,
            session_started_at=session_started_at,
            shadow_coordinator=shadow_coordinator,
            runtime_context_builder=runtime_context_builder,
        )
        current_snapshots = _merge_snapshots_by_market_id(seed_snapshots, tuple(router.snapshot_cache.values()))
        await recover_live_state(
            risk_manager=live_risk_manager,
            execution=live_execution,
            snapshots=current_snapshots,
            recovery_scope="session",
            session_started_at=session_started_at,
        )
        await _prune_runtime_dust_positions(
            risk_manager=live_risk_manager,
            recorder=live_recorder,
        )
        current_snapshots = await _refresh_cleanup_snapshots(
            snapshots=current_snapshots,
            clob_enricher=market_data.clob_enricher,
            runtime_open_positions=(
                *starting_runtime_open_positions,
                *tuple(_filter_cleanup_runtime_positions(tuple(live_risk_manager.state.open_positions.values()))),
            ),
        )
        await _cleanup_sync_shadow_session(
            execution=sync_execution,
            snapshots=current_snapshots,
            runtime_open_positions=(
                *starting_runtime_open_positions,
                *tuple(_filter_cleanup_runtime_positions(tuple(live_risk_manager.state.open_positions.values()))),
            ),
            recorder=live_recorder,
        )
    await recover_live_state(
        risk_manager=live_risk_manager,
        execution=live_execution,
        snapshots=current_snapshots,
        recovery_scope="session",
        session_started_at=session_started_at,
    )
    await _prune_runtime_dust_positions(
        risk_manager=live_risk_manager,
        recorder=live_recorder,
    )
    await _prune_runtime_dust_pending_orders(
        execution=live_execution,
        risk_manager=live_risk_manager,
        recorder=live_recorder,
    )

    return SyncSessionResult(
        live_stats={
            "processed_snapshots": live_stats.market_snapshots_processed,
            "user_events_processed": live_stats.user_events_processed,
            "submitted_orders": live_stats.submitted_orders,
            "stale_orders_cancelled": live_stats.stale_orders_cancelled,
            "recovered_open_orders": live_stats.recovered_open_orders,
            "replayed_trades": live_stats.replayed_trades,
            "rebuilt_positions": live_stats.rebuilt_positions,
            "reconnects": live_stats.reconnects,
            "events_recorded": len(live_recorder.events),
            "fill_rate": live_recorder.metrics.fill_rate,
            "cancel_rate": live_recorder.metrics.cancel_rate,
            "dashboard": live_risk_manager.dashboard_state(),
            "trading_settings": settings.trading,
            "dashboard_status": live_risk_manager.dashboard_state().status.value,
        },
        shadow_stats={
            "processed_snapshots": shadow_recorder.metrics.processed_snapshots,
            "submitted_orders": shadow_recorder.metrics.orders_submitted,
            "orders_filled": shadow_recorder.metrics.orders_filled,
            "orders_canceled": shadow_recorder.metrics.orders_canceled,
            "trades_closed": shadow_recorder.metrics.trades_closed,
            "events_recorded": len(shadow_recorder.events),
            "fill_rate": shadow_recorder.metrics.fill_rate,
            "cancel_rate": shadow_recorder.metrics.cancel_rate,
            "dashboard": shadow_risk_manager.dashboard_state(),
            "dashboard_status": shadow_risk_manager.dashboard_state().status.value,
        },
    )


def _merge_snapshots_by_market_id(*snapshot_groups: Sequence[MarketSnapshot]) -> tuple[MarketSnapshot, ...]:
    merged: dict[str, MarketSnapshot] = {}
    for snapshots in snapshot_groups:
        for snapshot in snapshots:
            merged[snapshot.market_id] = snapshot
    return tuple(merged.values())


async def _load_required_cleanup_snapshots(
    *,
    gamma_client: GammaMarketsClient,
    clob_enricher: ClobSnapshotEnricher | None,
    required_market_ids: set[str],
    page_size: int,
    max_pages: int,
    tag_id: int | None,
) -> tuple[MarketSnapshot, ...]:
    required_market_ids = {
        market_id.strip()
        for market_id in required_market_ids
        if market_id and market_id.strip()
    }
    if not required_market_ids:
        return ()

    snapshots = await gamma_client.fetch_active_binary_market_snapshots(
        page_size=page_size,
        max_pages=max_pages,
        tag_id=tag_id,
    )
    matched = [snapshot for snapshot in snapshots if snapshot.market_id in required_market_ids]
    if not matched:
        return ()
    if clob_enricher is not None:
        matched = await clob_enricher.enrich_snapshots(matched)
    return tuple(matched)


async def _refresh_cleanup_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    clob_enricher: ClobSnapshotEnricher | None,
    runtime_open_positions: Sequence[PositionState],
) -> tuple[MarketSnapshot, ...]:
    if clob_enricher is None:
        return tuple(snapshots)
    cleanup_market_ids = {
        position.market_id
        for position in runtime_open_positions
    }
    if not cleanup_market_ids:
        return tuple(snapshots)
    cleanup_snapshots = [
        snapshot
        for snapshot in snapshots
        if snapshot.market_id in cleanup_market_ids
    ]
    if not cleanup_snapshots:
        return tuple(snapshots)
    refreshed_cleanup_snapshots = await clob_enricher.enrich_snapshots(cleanup_snapshots)
    return _merge_snapshots_by_market_id(snapshots, refreshed_cleanup_snapshots)


async def _cleanup_sync_shadow_session(
    *,
    execution: SynchronizedLiveExecutionAdapter,
    snapshots: Sequence[MarketSnapshot],
    runtime_open_positions: Sequence[PositionState] = (),
    recorder: LiveRuntimeRecorder | None = None,
) -> None:
    snapshots_by_market_id = {snapshot.market_id: snapshot for snapshot in snapshots}
    cleanup_rounds = 6
    cleanup_round_pause_seconds = 2.0
    cleanup_quote_ttl_seconds = 5
    for _ in range(cleanup_rounds):
        await asyncio.sleep(cleanup_round_pause_seconds)
        pending_orders = tuple(
            order
            for order in execution.live_execution.tracker.snapshot()
            if order.status in {
                OrderLifecycleStatus.PENDING,
                OrderLifecycleStatus.LIVE,
                OrderLifecycleStatus.PARTIALLY_FILLED,
            }
        )
        for order in pending_orders:
            try:
                await execution.cancel_order(order.order_id, now=datetime.now(tz=UTC))
            except Exception:
                continue
        try:
            exchange_open_orders = await execution.live_execution.fetch_open_orders()
        except Exception:
            exchange_open_orders = []
        for raw_order in exchange_open_orders:
            order_id = str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
            if not order_id:
                continue
            try:
                await execution.cancel_order(order_id, now=datetime.now(tz=UTC))
            except Exception:
                continue
        if pending_orders or exchange_open_orders:
            continue

        positions = _cleanup_position_candidates(
            execution_positions=tuple(execution.live_execution.position_ledger.snapshot()),
            runtime_open_positions=runtime_open_positions,
        )
        if not positions and not pending_orders and not exchange_open_orders:
            break
        for position in positions:
            snapshot = snapshots_by_market_id.get(position.market_id)
            if snapshot is None:
                continue
            shares = _cleanup_safe_position_shares(_cleanup_position_shares(position))
            side, price, cleanup_size = _cleanup_exit_plan(
                snapshot=snapshot,
                token_id=position.token_id,
                desired_shares=shares,
            )
            if price is None or cleanup_size <= 0:
                continue
            intent = OrderIntent(
                strategy_id=position.strategy_id,
                category=position.category,
                market_id=position.market_id,
                token_id=position.token_id,
                action=OrderAction.PLACE,
                side=side,
                price=price,
                size=cleanup_size,
                time_in_force="IOC",
                created_at=datetime.now(tz=UTC),
                notional=cleanup_size * price,
                quote_ttl_seconds=cleanup_quote_ttl_seconds,
                signal_edge_bps=None,
                exposure_group_id=position.exposure_group_id,
                thesis_group_id=position.thesis_group_id,
                underlying_group_id=position.underlying_group_id,
            )
            try:
                live_order_id = await execution.submit(intent)
                if recorder is not None:
                    await recorder.record(
                        event_type="cleanup.order_submitted",
                        payload={
                            "market_id": position.market_id,
                            "token_id": position.token_id,
                            "side": side.value,
                            "price": price,
                            "size": cleanup_size,
                            "live_order_id": live_order_id,
                        },
                    )
            except Exception as exc:
                resized_cleanup_size = _cleanup_size_from_balance_error(
                    reason=str(exc),
                    requested_shares=cleanup_size,
                )
                if resized_cleanup_size is not None and resized_cleanup_size < cleanup_size:
                    resized_intent = OrderIntent(
                        strategy_id=intent.strategy_id,
                        category=intent.category,
                        market_id=intent.market_id,
                        token_id=intent.token_id,
                        action=intent.action,
                        side=intent.side,
                        price=intent.price,
                        size=resized_cleanup_size,
                        created_at=intent.created_at,
                        notional=resized_cleanup_size * price,
                        time_in_force=intent.time_in_force,
                        quote_ttl_seconds=intent.quote_ttl_seconds,
                        signal_edge_bps=intent.signal_edge_bps,
                        exposure_group_id=intent.exposure_group_id,
                        thesis_group_id=intent.thesis_group_id,
                        underlying_group_id=intent.underlying_group_id,
                        intent_id=intent.intent_id,
                    )
                    try:
                        live_order_id = await execution.submit(resized_intent)
                        if recorder is not None:
                            await recorder.record(
                                event_type="cleanup.order_submitted",
                                payload={
                                    "market_id": position.market_id,
                                    "token_id": position.token_id,
                                    "side": side.value,
                                    "price": price,
                                    "size": resized_cleanup_size,
                                    "live_order_id": live_order_id,
                                    "resized_from": cleanup_size,
                                    "resize_reason": "balance_allowance_limit",
                                },
                            )
                        continue
                    except Exception as retry_exc:
                        if recorder is not None:
                            await recorder.record(
                                event_type="cleanup.order_submit_failed",
                                payload={
                                    "market_id": position.market_id,
                                    "token_id": position.token_id,
                                    "side": side.value,
                                    "price": price,
                                    "size": resized_cleanup_size,
                                    "reason": str(retry_exc),
                                    "resized_from": cleanup_size,
                                },
                            )
                if recorder is not None:
                    await recorder.record(
                        event_type="cleanup.order_submit_failed",
                        payload={
                            "market_id": position.market_id,
                            "token_id": position.token_id,
                            "side": side.value,
                            "price": price,
                            "size": cleanup_size,
                            "reason": str(exc),
                        },
                    )
                continue

    await asyncio.sleep(cleanup_round_pause_seconds)
    try:
        remaining_open_orders = await execution.live_execution.fetch_open_orders()
    except Exception:
        remaining_open_orders = []
    remaining_open_order_ids = {
        str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
        for raw_order in remaining_open_orders
        if str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
    }
    for order_id in tuple(remaining_open_order_ids):
        try:
            await execution.cancel_order(order_id, now=datetime.now(tz=UTC))
        except Exception:
            continue
    try:
        remaining_open_orders = await execution.live_execution.fetch_open_orders()
    except Exception:
        remaining_open_orders = []
    remaining_open_order_ids = {
        str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
        for raw_order in remaining_open_orders
        if str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
    }
    for order in execution.live_execution.tracker.snapshot():
        if order.status not in {
            OrderLifecycleStatus.PENDING,
            OrderLifecycleStatus.LIVE,
            OrderLifecycleStatus.PARTIALLY_FILLED,
        }:
            continue
        if order.order_id in remaining_open_order_ids:
            continue
        execution.live_execution.tracker.mark_canceled(order.order_id, at=datetime.now(tz=UTC))


async def _preflight_cancel_sync_shadow_open_orders(
    *,
    execution: PolymarketLiveExecutionAdapter,
    snapshots: Sequence[MarketSnapshot],
    recorder: LiveRuntimeRecorder,
) -> None:
    target_market_ids = {snapshot.market_id for snapshot in snapshots}
    target_condition_ids = {
        str(snapshot.metadata.get("condition_id", "")).strip()
        for snapshot in snapshots
        if str(snapshot.metadata.get("condition_id", "")).strip()
    }
    target_asset_ids = {
        token_id
        for snapshot in snapshots
        for token_id in (
            str(snapshot.token_id).strip(),
            str(snapshot.metadata.get("no_token_id", "")).strip(),
        )
        if token_id
    }
    if not target_market_ids and not target_condition_ids and not target_asset_ids:
        return
    try:
        open_orders = await execution.fetch_open_orders()
    except Exception:
        return
    for raw_order in open_orders:
        market_key = str(raw_order.get("market") or raw_order.get("condition_id") or "").strip()
        asset_id = str(raw_order.get("asset_id") or raw_order.get("assetId") or "").strip()
        if (
            market_key not in target_market_ids
            and market_key not in target_condition_ids
            and asset_id not in target_asset_ids
        ):
            continue
        order_id = str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
        if not order_id:
            continue
        canceled_order = await execution.cancel_order(order_id, now=datetime.now(tz=UTC))
        if canceled_order is None:
            continue
        await recorder.record(
            event_type="order.canceled",
            payload={
                **tracked_order_payload(order=canceled_order, snapshot=None),
                "reason": "preflight_sync_shadow_cancel",
            },
        )


def _cleanup_exit_plan(
    *,
    snapshot: MarketSnapshot,
    token_id: str,
    desired_shares: float,
) -> tuple[SignalSide, float | None, float]:
    tick_size = snapshot.tick_size if snapshot.tick_size is not None else 0.01
    if token_id == snapshot.token_id:
        return _cleanup_exit_plan_from_levels(
            side=SignalSide.SELL_YES,
            best_bid=snapshot.best_bid_yes,
            best_bid_size=snapshot.best_bid_yes_size,
            bid_levels=snapshot.yes_bid_levels,
            desired_shares=desired_shares,
            tick_size=tick_size,
        )
    return _cleanup_exit_plan_from_levels(
        side=SignalSide.SELL_NO,
        best_bid=snapshot.best_bid_no,
        best_bid_size=snapshot.best_bid_no_size,
        bid_levels=snapshot.no_bid_levels,
        desired_shares=desired_shares,
        tick_size=tick_size,
    )


def _cleanup_exit_plan_from_levels(
    *,
    side: SignalSide,
    best_bid: float | None,
    best_bid_size: float | None,
    bid_levels: Sequence[object],
    desired_shares: float,
    tick_size: float,
) -> tuple[SignalSide, float | None, float]:
    if desired_shares <= 0:
        return side, None, 0.0
    cumulative_depth = 0.0
    selected_price: float | None = None
    selected_size = 0.0
    for raw_level in bid_levels:
        price = getattr(raw_level, "price", None)
        size = getattr(raw_level, "size", None)
        if not isinstance(price, (int, float)) or not isinstance(size, (int, float)):
            continue
        if float(size) <= 0:
            continue
        cumulative_depth += float(size)
        selected_price = float(price)
        selected_size = min(desired_shares, cumulative_depth)
        if cumulative_depth + 1e-9 >= desired_shares:
            return side, _cleanup_exit_price_floor(selected_price, tick_size), desired_shares
    if selected_price is not None and selected_size > 0:
        return side, _cleanup_exit_price_floor(selected_price, tick_size), selected_size
    if best_bid is None:
        return side, None, 0.0
    if best_bid_size is not None and best_bid_size > 0:
        return side, _cleanup_exit_price_floor(float(best_bid), tick_size), min(desired_shares, float(best_bid_size))
    return side, _cleanup_exit_price_floor(float(best_bid), tick_size), desired_shares


def _cleanup_exit_price_floor(price: float, tick_size: float) -> float:
    safe_tick = tick_size if tick_size > 0 else 0.01
    return max(0.01, round(price - safe_tick, 6))


def _cleanup_position_candidates(
    *,
    execution_positions: Sequence[LivePosition],
    runtime_open_positions: Sequence[PositionState],
) -> tuple[LivePosition | PositionState, ...]:
    merged: dict[tuple[str, str], LivePosition | PositionState] = {}
    for position in execution_positions:
        market_id = getattr(position, "market_id", None)
        token_id = getattr(position, "token_id", None)
        if not isinstance(market_id, str) or not isinstance(token_id, str):
            continue
        merged[(market_id, token_id)] = position
    for runtime_position in runtime_open_positions:
        key = (runtime_position.market_id, runtime_position.token_id)
        merged.setdefault(key, runtime_position)
    return tuple(merged.values())


def _filter_cleanup_runtime_positions(
    positions: Sequence[PositionState],
) -> tuple[PositionState, ...]:
    return tuple(position for position in positions if not _is_runtime_position_dust(position))


def _is_runtime_position_dust(position: PositionState) -> bool:
    shares = position.shares
    if isinstance(shares, (int, float)) and 0 < float(shares) <= SYNC_SHADOW_DUST_SHARES:
        return True
    return 0 < float(position.notional) <= SYNC_SHADOW_DUST_NOTIONAL


async def _prune_runtime_dust_positions(
    *,
    risk_manager: BasicRiskManager,
    recorder: LiveRuntimeRecorder | None,
) -> None:
    positions = tuple(risk_manager.state.open_positions.values())
    dust_positions = tuple(position for position in positions if _is_runtime_position_dust(position))
    if not dust_positions:
        return
    await risk_manager.sync_open_positions(_filter_cleanup_runtime_positions(positions))
    if recorder is None:
        return
    for position in dust_positions:
        await recorder.record(
            event_type="cleanup.dust_position_ignored",
            payload={
                "market_id": position.market_id,
                "token_id": position.token_id,
                "shares": position.shares,
                "notional": position.notional,
            },
        )


async def _prune_runtime_dust_pending_orders(
    *,
    execution: PolymarketLiveExecutionAdapter,
    risk_manager: BasicRiskManager,
    recorder: LiveRuntimeRecorder | None,
) -> None:
    try:
        open_orders = await execution.fetch_open_orders()
    except Exception:
        open_orders = []
    open_order_ids = {
        str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
        for raw_order in open_orders
        if str(raw_order.get("id") or raw_order.get("orderID") or raw_order.get("orderId") or "").strip()
    }
    remaining_orders = []
    dust_orders = []
    for order in risk_manager.state.pending_orders.values():
        remaining_shares = max(order.requested_shares - order.matched_shares, 0.0)
        remaining_notional = max(order.requested_notional - order.matched_notional, 0.0)
        is_dust = (
            remaining_shares <= SYNC_SHADOW_DUST_SHARES
            or remaining_notional <= SYNC_SHADOW_DUST_NOTIONAL
        )
        if order.order_id in open_order_ids or not is_dust:
            remaining_orders.append(order)
            continue
        dust_orders.append((order, remaining_shares, remaining_notional))
        execution.tracker.mark_canceled(order.order_id, at=datetime.now(tz=UTC))
    if len(remaining_orders) != len(risk_manager.state.pending_orders):
        await risk_manager.sync_pending_orders(remaining_orders)
    if recorder is None:
        return
    for order, remaining_shares, remaining_notional in dust_orders:
        await recorder.record(
            event_type="cleanup.dust_order_ignored",
            payload={
                "order_id": order.order_id,
                "market_id": order.market_id,
                "token_id": order.token_id,
                "remaining_shares": remaining_shares,
                "remaining_notional": remaining_notional,
            },
        )


def _cleanup_position_shares(position: LivePosition | PositionState) -> float:
    shares = position.shares
    if isinstance(shares, (int, float)) and float(shares) > 0:
        return float(shares)
    notional = getattr(position, "notional", None)
    average_entry_price = position.average_entry_price
    if (
        isinstance(notional, (int, float))
        and isinstance(average_entry_price, (int, float))
        and float(notional) > 0
        and float(average_entry_price) > 0
    ):
        return float(notional) / float(average_entry_price)
    return 0.0


def _cleanup_safe_position_shares(shares: float) -> float:
    if shares <= 0:
        return 0.0
    buffered = shares - max(shares * 0.005, 0.05)
    if buffered <= 0:
        return 0.0
    return math.floor(buffered * 10_000) / 10_000


def _cleanup_size_from_balance_error(*, reason: str, requested_shares: float) -> float | None:
    match = _BALANCE_ERROR_PATTERN.search(reason)
    if match is None:
        return None
    balance_units = int(match.group(1))
    order_amount_units = int(match.group(2))
    if balance_units <= 0 or order_amount_units <= 0 or requested_shares <= 0:
        return None
    available_shares = requested_shares * (balance_units / order_amount_units)
    resized = _cleanup_safe_position_shares(available_shares)
    if resized <= SYNC_SHADOW_DUST_SHARES or resized >= requested_shares:
        return None
    return resized


def _filter_snapshots_by_crypto_barrier_distance(
    *,
    snapshots: Sequence[MarketSnapshot],
    underlying_states: Mapping[str, object],
    min_distance_ratio: float | None,
    max_distance_ratio: float | None,
) -> list[MarketSnapshot]:
    filtered: list[MarketSnapshot] = []
    for snapshot in snapshots:
        normalized = normalize_crypto_market(snapshot)
        if normalized is None:
            filtered.append(snapshot)
            continue
        raw_state = underlying_states.get(normalized.underlying)
        spot_price = getattr(raw_state, "spot_price", None)
        if not isinstance(spot_price, (int, float)) or float(spot_price) == 0.0:
            filtered.append(snapshot)
            continue
        spot_value = float(spot_price)
        distance_ratio = abs(normalized.barrier_price - spot_value) / max(spot_value, 1e-9)
        if min_distance_ratio is not None and distance_ratio < min_distance_ratio:
            continue
        if max_distance_ratio is not None and distance_ratio > max_distance_ratio:
            continue
        filtered.append(snapshot)
    return filtered


def _parse_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise TypeError(f"expected float-like value, got {type(value).__name__}")


def _parse_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value.strip())
    raise TypeError(f"expected int-like value, got {type(value).__name__}")
