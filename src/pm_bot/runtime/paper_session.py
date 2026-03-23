"""Helpers for running a paper crypto session against live market data."""

from __future__ import annotations

from collections.abc import Sequence

from pm_bot.adapters.polymarket import (
    ClobPublicClient,
    ClobSnapshotEnricher,
    GammaMarketsClient,
    PolymarketLiveMarketDataAdapter,
)
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.execution.factory import build_execution_adapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.state import DashboardState
from pm_bot.storage.recorder import InMemoryRecorder
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore

CRYPTO_GAMMA_TAG_ID = 21


async def run_crypto_paper_session_once(
    *,
    config_dir: str = "configs",
    limit: int = 50,
    max_pages: int = 1,
    tag_id: int = CRYPTO_GAMMA_TAG_ID,
    state_path: str = "data/runtime/runtime_state.json",
) -> dict[str, object]:
    settings = load_settings_from_directory(config_dir)
    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    state_store = JsonRuntimeStateStore(state_path)
    risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state_store=state_store,
    )
    execution = build_execution_adapter(settings=settings)
    recorder = InMemoryRecorder()

    async with GammaMarketsClient() as gamma_client, ClobPublicClient() as clob_client:
        market_data = PolymarketLiveMarketDataAdapter(
            gamma_client=gamma_client,
            clob_enricher=ClobSnapshotEnricher(clob_client),
            max_pages=max_pages,
            tag_id=tag_id,
        )
        router = EventRouter(
            market_data=market_data,
            strategies=strategies,
            risk_manager=risk_manager,
            execution=execution,
            recorder=recorder,
            default_order_size=settings.trading.default_order_notional,
        )

        processed = 0
        async for snapshot in market_data.stream_snapshots():
            await router.run_once(snapshot=snapshot)
            processed += 1
            if processed >= limit:
                break

    dashboard = risk_manager.dashboard_state()
    return {
        "processed_snapshots": processed,
        "submitted_orders": len(getattr(execution, "submitted_orders", [])),
        "dashboard": dashboard,
        "events_recorded": len(recorder.events),
    }


def format_dashboard_summary(result: dict[str, object]) -> str:
    dashboard = result["dashboard"]
    if not isinstance(dashboard, DashboardState):
        raise TypeError("dashboard result must be a DashboardState")

    return "\n".join(
        [
            f"processed_snapshots={result['processed_snapshots']}",
            f"submitted_orders={result['submitted_orders']}",
            f"events_recorded={result['events_recorded']}",
            render_dashboard(dashboard),
        ]
    )
