"""Execution adapter factory.

This keeps runtime wiring separate from adapter implementations so paper and live
execution can evolve without touching strategies or orchestrators.
"""

from __future__ import annotations

from collections.abc import Mapping
import os
from typing import Any

from pm_bot.core.settings import BotSettings
from pm_bot.core.types import RuntimeMode
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.polymarket_live import (
    PolymarketLiveExecutionAdapter,
    describe_live_execution_configuration,
)


def build_execution_adapter(
    settings: BotSettings,
    *,
    env: Mapping[str, str] | None = None,
    client_factory: Any = None,
) -> object:
    """Build the configured execution adapter."""

    if settings.app.mode != RuntimeMode.LIVE:
        return PaperExecutionAdapter(
            ttl_seconds=settings.trading.default_quote_ttl_seconds,
            place_latency_ms=settings.trading.paper_place_latency_ms,
            cancel_latency_ms=settings.trading.paper_cancel_latency_ms,
            fee_bps=settings.trading.paper_fee_bps,
            taker_slippage_bps=settings.trading.paper_taker_slippage_bps,
        )

    return PolymarketLiveExecutionAdapter.from_settings(
        settings=settings.polymarket,
        ttl_seconds=settings.trading.default_quote_ttl_seconds,
        env=env,
        client_factory=client_factory,
    )


def describe_execution_configuration(
    settings: BotSettings,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Summarize how execution will be wired for the current runtime mode."""

    live_summary = describe_live_execution_configuration(
        settings.polymarket,
        os.environ if env is None else env,
    )
    adapter_name = "paper"
    if settings.app.mode == RuntimeMode.LIVE:
        adapter_name = "polymarket_live" if settings.polymarket.allow_live_orders else "blocked"

    return {
        "mode": settings.app.mode.value,
        "adapter": adapter_name,
        **live_summary,
    }
