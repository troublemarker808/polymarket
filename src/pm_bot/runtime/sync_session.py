"""Synchronized live + shadow-paper runtime for normal strategy validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pm_bot.adapters.polymarket import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    GammaMarketsClient,
    MarketChannelClient,
    PolymarketLiveMarketDataAdapter,
    UserChannelClient,
)
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import Category, MarketSnapshot, RuntimeMode
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.paper_matching import PaperMatchEvent
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.execution_artifacts import tracked_order_payload
from pm_bot.runtime.live_session import supervise_live_session
from pm_bot.runtime.market_universe import build_snapshot_selector
from pm_bot.runtime.paper_sync import order_payload_from_match_event, sync_paper_execution_state
from pm_bot.storage.recorder import LiveRuntimeRecorder, PaperRuntimeRecorder
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore


CRYPTO_GAMMA_TAG_ID = 21


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

    async def mirror_submission(self, *, live_order_id: str, intent) -> str:
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

    def dashboard_state(self):
        return self.risk_manager.dashboard_state()

    def _snapshot_for_order(self, order) -> MarketSnapshot | None:
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

    async def submit(self, intent) -> str:
        live_order_id = await self.live_execution.submit(intent)
        await self.shadow_coordinator.mirror_submission(
            live_order_id=live_order_id,
            intent=intent,
        )
        return live_order_id

    async def cancel_order(self, order_id: str, *, now: datetime | None = None):
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

    async def cancel_stale_orders(self):
        canceled_orders = await self.live_execution.cancel_stale_orders()
        for order in canceled_orders:
            await self.shadow_coordinator.mirror_cancellation(
                live_order_id=order.order_id,
                now=order.updated_at,
                reason="stale_ttl_cancel",
            )
        return canceled_orders

    def __getattr__(self, name: str):
        return getattr(self.live_execution, name)


def format_sync_session_summary(result: SyncSessionResult) -> str:
    live = result.live_stats
    shadow = result.shadow_stats
    return "\n".join(
        [
            "[live]",
            *(f"{key}={value}" for key, value in live.items()),
            "",
            "[shadow]",
            *(f"{key}={value}" for key, value in shadow.items()),
        ]
    )


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
) -> SyncSessionResult:
    settings = load_settings_from_directory(config_dir)
    if settings.app.mode != RuntimeMode.LIVE:
        raise ValueError("Sync session runner requires app.mode=live")

    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    crypto_config = settings.category_configs.get(Category.CRYPTO)
    snapshot_selector = build_snapshot_selector(
        crypto_config.markets if crypto_config is not None else None
    )

    live_state_store = JsonRuntimeStateStore(live_state_path)
    live_risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state_store=live_state_store,
    )
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

    session_started_at = datetime.now(tz=UTC)
    await live_recorder.record(
        event_type="live.session_started",
        payload={
            "started_at": session_started_at.isoformat(),
            "mode": "sync_shadow",
            "recovery_scope": settings.polymarket.live_recovery_scope,
            "configured_signature_type": settings.polymarket.signature_type,
            "resolved_signature_type": live_execution.signature_type,
        },
    )
    await shadow_recorder.record(
        event_type="shadow.session_started",
        payload={
            "started_at": session_started_at.isoformat(),
            "mode": "sync_shadow",
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
        seed_snapshots = await market_data.bootstrap_snapshots()
        if seed_snapshots:
            latest_seed = max(snapshot.timestamp for snapshot in seed_snapshots)
            live_risk_manager.record_data_success(latest_seed)
            shadow_risk_manager.record_data_success(latest_seed)
        router = EventRouter(
            market_data=market_data,
            strategies=strategies,
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
            execution=sync_execution,
            risk_manager=live_risk_manager,
            recorder=live_recorder,
            initial_snapshots=seed_snapshots,
            max_market_snapshots=max_market_snapshots,
            max_user_events=max_user_events,
            summary_every_snapshots=summary_every_snapshots,
            recovery_scope=settings.polymarket.live_recovery_scope,
            session_started_at=session_started_at,
            shadow_coordinator=shadow_coordinator,
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
            "dashboard_status": shadow_risk_manager.dashboard_state().status.value,
        },
    )
