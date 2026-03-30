"""Protocols that isolate strategies from adapters, execution, and risk."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import datetime
from typing import Protocol

from pm_bot.core.types import MarketSnapshot, OrderIntent, RiskDecision, StrategySignal
from pm_bot.runtime.state import ClosedTrade, DashboardState, PendingOrderState, PositionState


class MarketDataAdapter(Protocol):
    """Normalized read-only interface for market and external feature inputs."""

    def stream_snapshots(self) -> AsyncIterator[MarketSnapshot]:
        ...


class Strategy(Protocol):
    """Pure strategy contract.

    Strategies consume normalized inputs and emit signals. They must not submit
    orders, call exchange clients directly, or depend on other categories.
    """

    strategy_id: str

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        ...


class RiskManager(Protocol):
    """Independent approval layer for strategy signals and order intents."""

    async def review_signal(self, signal: StrategySignal) -> RiskDecision:
        ...

    async def review_order(self, intent: OrderIntent) -> RiskDecision:
        ...

    async def record_order_submission(self, intent: OrderIntent, order_id: str) -> None:
        ...

    async def record_order_cancellation(self, order_id: str) -> None:
        ...

    async def record_trade_close(self, trade: ClosedTrade) -> None:
        ...

    async def update_unrealized_pnl(self, unrealized_pnl: float) -> None:
        ...

    async def sync_open_positions(self, positions: Sequence[PositionState]) -> None:
        ...

    async def sync_pending_orders(self, orders: Sequence[PendingOrderState]) -> None:
        ...

    async def manual_resume(self) -> RiskDecision:
        ...

    def dashboard_state(self) -> DashboardState:
        ...


class ExecutionAdapter(Protocol):
    """Boundary for order placement and order lifecycle management."""

    async def submit(self, intent: OrderIntent) -> str:
        ...

    async def cancel_order(self, order_id: str, *, now: datetime | None = None) -> object | None:
        ...

    async def cancel_stale(self) -> int:
        ...


class ResearchEngine(Protocol):
    """Boundary for replay and backtest workflows."""

    async def run(self) -> None:
        ...


class EventRecorder(Protocol):
    """Write normalized runtime events for replay and audit."""

    async def record(self, event_type: str, payload: Mapping[str, object]) -> None:
        ...
