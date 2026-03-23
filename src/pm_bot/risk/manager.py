"""Config-driven basic risk manager."""

from __future__ import annotations

from datetime import datetime, timezone

from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import OrderIntent, RiskDecision, SignalSide, StrategySignal
from pm_bot.risk.guards import basic_signal_guard
from pm_bot.runtime.state import (
    ClosedTrade,
    DashboardState,
    HaltReason,
    PendingOrderState,
    PositionState,
    RuntimeState,
    RuntimeStatus,
)
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore


class BasicRiskManager:
    """Minimal risk manager that enforces core foundation rules."""

    # Halt state machine:
    #
    # RUNNING
    #   -> consecutive losses breach
    #   -> daily drawdown breach
    #   -> future data-source halt hooks
    #   => HALTED
    #
    # HALTED
    #   -> manual_resume()
    #   => RUNNING

    def __init__(
        self,
        settings: RiskSettings,
        trading_settings: TradingSettings | None = None,
        min_signal_edge_bps: float = 100.0,
        state: RuntimeState | None = None,
        state_store: JsonRuntimeStateStore | None = None,
    ) -> None:
        self.settings = settings
        self.trading_settings = trading_settings or TradingSettings()
        self.min_signal_edge_bps = min_signal_edge_bps
        starting_equity = self.trading_settings.starting_equity
        self.state_store = state_store
        loaded_state = None if state is not None or state_store is None else state_store.load()
        self.state = state or loaded_state or RuntimeState(
            starting_equity=starting_equity,
            day_starting_equity=starting_equity,
        )
        self._persist_state()

    async def review_signal(self, signal: StrategySignal) -> RiskDecision:
        halted = self._reject_if_halted()
        if halted is not None:
            return halted

        return basic_signal_guard(signal=signal, max_edge_floor_bps=self.min_signal_edge_bps)

    async def review_order(self, intent: OrderIntent) -> RiskDecision:
        halted = self._reject_if_halted()
        if halted is not None:
            return halted

        order_notional = self._order_notional(intent)
        is_exit = intent.side in {SignalSide.SELL_YES, SignalSide.SELL_NO}
        if intent.price is None:
            return RiskDecision(approved=False, reason="missing order price")
        if intent.size <= 0:
            return RiskDecision(approved=False, reason="non-positive order size")
        if order_notional <= 0:
            return RiskDecision(approved=False, reason="non-positive order notional")
        if any(order.market_id == intent.market_id for order in self.state.pending_orders.values()):
            return RiskDecision(approved=False, reason="market already has a pending order")

        if is_exit:
            current_position = self.state.open_positions.get(intent.market_id)
            if current_position is None:
                return RiskDecision(approved=False, reason="no open position to close")
            if current_position.token_id != intent.token_id:
                return RiskDecision(approved=False, reason="close order token does not match open position")
            if current_position.shares is not None and intent.size - current_position.shares > 1e-6:
                return RiskDecision(approved=False, reason="close order exceeds current position size")
            if self.state.orders_today >= self.trading_settings.daily_order_hard_limit:
                return RiskDecision(approved=False, reason="daily order hard limit reached")
            return RiskDecision(approved=True, reason="approved")

        if order_notional > self.trading_settings.default_order_notional:
            return RiskDecision(approved=False, reason="order exceeds per-trade notional cap")
        if self.state.orders_today >= self.trading_settings.daily_order_hard_limit:
            return RiskDecision(approved=False, reason="daily order hard limit reached")
        if self.state.active_market_count >= self.trading_settings.max_concurrent_positions:
            return RiskDecision(approved=False, reason="max concurrent positions reached")
        if intent.market_id in self.state.open_positions:
            return RiskDecision(approved=False, reason="market already has an open position")

        return RiskDecision(approved=True, reason="approved")

    async def record_order_submission(self, intent: OrderIntent, order_id: str) -> None:
        order_notional = self._order_notional(intent)
        self.state.orders_today += 1
        submitted_at = datetime.now(tz=timezone.utc)
        self.state.pending_orders[order_id] = PendingOrderState(
            order_id=order_id,
            market_id=intent.market_id,
            token_id=intent.token_id,
            category=intent.category,
            strategy_id=intent.strategy_id,
            side=intent.side.value,
            limit_price=float(intent.price or 0.0),
            requested_shares=float(intent.size),
            requested_notional=order_notional,
            matched_shares=0.0,
            matched_notional=0.0,
            fees_paid=0.0,
            status="pending",
            created_at=submitted_at,
            updated_at=submitted_at,
        )
        self.state.touch()
        self._persist_state()

    async def record_trade_close(self, trade: ClosedTrade) -> None:
        net_pnl = trade.net_pnl
        self.state.realized_pnl_today += net_pnl
        self.state.consecutive_losses = self.state.consecutive_losses + 1 if net_pnl < 0 else 0
        self.state.touch()

        if self.state.consecutive_losses >= self.settings.max_consecutive_losses:
            self._halt(
                reason=HaltReason.CONSECUTIVE_LOSSES,
                message="halted after consecutive realized losses",
            )
            return

        if self.state.daily_drawdown_pct >= self.settings.max_daily_drawdown_pct:
            self._halt(
                reason=HaltReason.DAILY_DRAWDOWN,
                message="halted after daily drawdown threshold breach",
            )
            return

        self._persist_state()

    async def update_unrealized_pnl(self, unrealized_pnl: float) -> None:
        self.state.unrealized_pnl = unrealized_pnl
        self.state.touch()
        if self.state.daily_drawdown_pct >= self.settings.max_daily_drawdown_pct:
            self._halt(
                reason=HaltReason.DAILY_DRAWDOWN,
                message="halted after daily drawdown threshold breach",
            )
            return

        self._persist_state()

    async def sync_open_positions(self, positions: tuple[PositionState, ...] | list[PositionState]) -> None:
        self.state.open_positions = {
            position.market_id: position
            for position in positions
        }
        total_unrealized = sum(position.unrealized_pnl for position in positions)
        await self.update_unrealized_pnl(total_unrealized)

    async def sync_pending_orders(self, orders: tuple[PendingOrderState, ...] | list[PendingOrderState]) -> None:
        self.state.pending_orders = {
            order.order_id: order
            for order in orders
        }
        self.state.touch()
        self._persist_state()

    async def manual_resume(self) -> RiskDecision:
        if not self.settings.manual_resume_required:
            return RiskDecision(approved=False, reason="manual resume is disabled")

        self.state.status = RuntimeStatus.RUNNING
        self.state.consecutive_losses = 0
        self.state.halt_reason = HaltReason.NONE
        self.state.halt_message = None
        self.state.last_alert = "manual resume completed"
        self.state.touch()
        self._persist_state()
        return RiskDecision(approved=True, reason="manual resume completed")

    def dashboard_state(self) -> DashboardState:
        return self.state.snapshot(soft_limit=self.trading_settings.daily_order_soft_limit)

    def halt_for_reason(self, reason: HaltReason, message: str) -> None:
        self._halt(reason=reason, message=message)

    def _reject_if_halted(self) -> RiskDecision | None:
        if self.state.status == RuntimeStatus.HALTED:
            return RiskDecision(approved=False, reason=self.state.halt_message or "system halted")
        return None

    def _halt(self, reason: HaltReason, message: str) -> None:
        self.state.status = RuntimeStatus.HALTED
        self.state.halt_reason = reason
        self.state.halt_message = message
        self.state.last_alert = message
        self.state.touch()
        self._persist_state()

    def _persist_state(self) -> None:
        if self.state_store is None:
            return
        self.state_store.save(self.state)

    @staticmethod
    def _order_notional(intent: OrderIntent) -> float:
        if intent.notional is not None:
            return intent.notional
        if intent.price is None:
            return 0.0
        return intent.price * intent.size
