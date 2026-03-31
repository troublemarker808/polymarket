"""Config-driven basic risk manager."""

from __future__ import annotations

from collections.abc import Sequence
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
        self._last_data_success_wall_clock_at: datetime | None = None
        starting_equity = self.trading_settings.starting_equity
        self.state_store = state_store
        loaded_state = None if state is not None or state_store is None else state_store.load()
        self.state = state or loaded_state or RuntimeState(
            starting_equity=starting_equity,
            day_starting_equity=starting_equity,
        )
        self.advance_trading_day()
        self._persist_state()

    async def review_signal(self, signal: StrategySignal) -> RiskDecision:
        self.advance_trading_day(signal.generated_at)
        self.enforce_data_freshness()
        halted = self._reject_if_halted()
        if halted is not None:
            return halted

        return basic_signal_guard(signal=signal, max_edge_floor_bps=self.min_signal_edge_bps)

    async def review_order(self, intent: OrderIntent) -> RiskDecision:
        self.advance_trading_day(intent.created_at)
        self.enforce_data_freshness()
        halted = self._reject_if_halted()
        if halted is not None:
            return halted

        order_notional = self._order_notional(intent)
        is_exit = intent.side in {SignalSide.SELL_YES, SignalSide.SELL_NO}
        if intent.price is None:
            return self._reject_order(intent=intent, reason="missing order price")
        if intent.size <= 0:
            return self._reject_order(intent=intent, reason="non-positive order size")
        if order_notional <= 0:
            return self._reject_order(intent=intent, reason="non-positive order notional")

        if is_exit:
            current_position = self.state.open_positions.get(intent.market_id)
            if current_position is None:
                return self._reject_order(intent=intent, reason="no open position to close")
            if current_position.token_id != intent.token_id:
                return self._reject_order(intent=intent, reason="close order token does not match open position")
            if current_position.shares is not None and intent.size - current_position.shares > 1e-6:
                return self._reject_order(intent=intent, reason="close order exceeds current position size")
            existing_exit_order = next(
                (
                    order
                    for order in self.state.pending_orders.values()
                    if order.market_id == intent.market_id
                    and order.token_id == intent.token_id
                    and order.side == intent.side.value
                ),
                None,
            )
            if existing_exit_order is not None:
                return RiskDecision(
                    approved=True,
                    reason="approved_exit_reprice",
                    replacement_order_id=existing_exit_order.order_id,
                )
            if self.state.orders_today >= self.trading_settings.daily_order_hard_limit:
                return self._reject_order(intent=intent, reason="daily order hard limit reached")
            return RiskDecision(approved=True, reason="approved")

        if any(order.market_id == intent.market_id for order in self.state.pending_orders.values()):
            return self._reject_order(intent=intent, reason="market already has a pending order")

        per_trade_notional_cap = self._per_trade_notional_cap()
        if order_notional - per_trade_notional_cap > _NOTIONAL_COMPARISON_EPSILON:
            return self._reject_order(intent=intent, reason="order exceeds per-trade notional cap")
        if self.state.orders_today >= self.trading_settings.daily_order_hard_limit:
            return self._reject_order(intent=intent, reason="daily order hard limit reached")
        if intent.market_id in self.state.open_positions:
            return self._reject_order(intent=intent, reason="market already has an open position")
        replacement_order_id: str | None = None
        if len(self.state.pending_orders) >= self.settings.max_open_orders:
            replacement = self._replacement_candidate(intent)
            if replacement is None:
                return self._reject_order(intent=intent, reason="max open orders reached")
            replacement_order_id = replacement.order_id
        if (
            self._projected_market_notional(
                intent=intent,
                order_notional=order_notional,
                replacement_order_id=replacement_order_id,
            )
            > self.trading_settings.max_notional_per_market
        ):
            return self._reject_order(intent=intent, reason="order exceeds per-market notional cap")
        if (
            self._projected_category_notional(
                intent=intent,
                order_notional=order_notional,
                replacement_order_id=replacement_order_id,
            )
            > self.trading_settings.max_notional_per_category
        ):
            return self._reject_order(intent=intent, reason="order exceeds per-category notional cap")
        if (
            self._projected_exposure_group_notional(
                intent=intent,
                order_notional=order_notional,
                replacement_order_id=replacement_order_id,
            )
            > self.trading_settings.max_notional_per_exposure_group
        ):
            return self._reject_order(intent=intent, reason="order exceeds exposure-group notional cap")
        if (
            self._projected_thesis_group_notional(
                intent=intent,
                order_notional=order_notional,
                replacement_order_id=replacement_order_id,
            )
            > self.trading_settings.max_notional_per_thesis_group
        ):
            return self._reject_order(intent=intent, reason="order exceeds thesis-group notional cap")
        if (
            self._projected_underlying_group_notional(
                intent=intent,
                order_notional=order_notional,
                replacement_order_id=replacement_order_id,
            )
            > self.trading_settings.max_notional_per_underlying_group
        ):
            return self._reject_order(intent=intent, reason="order exceeds underlying-group notional cap")
        if (
            self._projected_total_notional(
                order_notional=order_notional,
                replacement_order_id=replacement_order_id,
            )
            > self.trading_settings.max_total_gross_notional
        ):
            return self._reject_order(intent=intent, reason="order exceeds total gross notional cap")
        if self.state.active_market_count >= self.trading_settings.max_concurrent_positions:
            if replacement_order_id is None:
                return self._reject_order(intent=intent, reason="max concurrent positions reached")
            replacement = self.state.pending_orders.get(replacement_order_id)
            if replacement is None or replacement.market_id in self.state.open_positions:
                return self._reject_order(intent=intent, reason="max concurrent positions reached")

        return RiskDecision(
            approved=True,
            reason="approved_with_replacement" if replacement_order_id is not None else "approved",
            replacement_order_id=replacement_order_id,
        )

    async def record_order_submission(self, intent: OrderIntent, order_id: str) -> None:
        self.advance_trading_day(intent.created_at)
        order_notional = self._order_notional(intent)
        self.state.orders_today += 1
        submitted_at = intent.created_at.astimezone(timezone.utc)
        self.state.pending_orders[order_id] = PendingOrderState(
            order_id=order_id,
            intent_id=intent.intent_id,
            market_id=intent.market_id,
            token_id=intent.token_id,
            category=intent.category,
            strategy_id=intent.strategy_id,
            side=intent.side.value,
            limit_price=float(intent.price or 0.0),
            requested_shares=float(intent.size),
            requested_notional=order_notional,
            quote_ttl_seconds=intent.quote_ttl_seconds,
            matched_shares=0.0,
            matched_notional=0.0,
            fees_paid=0.0,
            status="pending",
            created_at=submitted_at,
            updated_at=submitted_at,
            signal_edge_bps=intent.signal_edge_bps,
            exposure_group_id=intent.exposure_group_id,
            thesis_group_id=intent.thesis_group_id,
            underlying_group_id=intent.underlying_group_id,
        )
        self.state.touch()
        self._persist_state()

    async def record_order_cancellation(self, order_id: str) -> None:
        removed = self.state.pending_orders.pop(order_id, None)
        if removed is None:
            return
        self.state.touch()
        self._persist_state()

    async def record_trade_close(self, trade: ClosedTrade) -> None:
        self.advance_trading_day(trade.closed_at)
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

    async def sync_open_positions(self, positions: Sequence[PositionState]) -> None:
        self.state.open_positions = {
            position.market_id: position
            for position in positions
        }
        total_unrealized = sum(position.unrealized_pnl for position in positions)
        await self.update_unrealized_pnl(total_unrealized)

    async def sync_pending_orders(self, orders: Sequence[PendingOrderState]) -> None:
        self.state.pending_orders = {
            order.order_id: order
            for order in orders
        }
        self.state.touch()
        self._persist_state()

    async def manual_resume(self) -> RiskDecision:
        self.advance_trading_day()
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

    def advance_trading_day(self, now: datetime | None = None) -> bool:
        candidate = (now or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
        current_day = self.state.day_started_at.astimezone(timezone.utc).date()
        if current_day >= candidate.date():
            return False

        self.state.day_starting_equity = self.state.total_equity
        self.state.day_open_unrealized_pnl = self.state.unrealized_pnl
        self.state.realized_pnl_today = 0.0
        self.state.orders_today = 0
        self.state.day_started_at = candidate
        self.state.touch()
        self._persist_state()
        return True

    def record_data_success(
        self,
        timestamp: datetime | None = None,
        *,
        received_at: datetime | None = None,
    ) -> None:
        self.advance_trading_day(timestamp)
        recorded_at = (timestamp or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
        self._last_data_success_wall_clock_at = (
            received_at or datetime.now(tz=timezone.utc)
        ).astimezone(timezone.utc)
        failure_count = self.state.consecutive_data_failures
        if self.state.last_data_success_at is None or recorded_at >= self.state.last_data_success_at:
            self.state.last_data_success_at = recorded_at
        self.state.consecutive_data_failures = 0
        self.state.last_data_error = None
        if failure_count > 0:
            self.state.last_alert = "market data recovered"
        self.state.touch()
        self._persist_state()

    def record_data_failure(self, *, reason: str, occurred_at: datetime | None = None) -> bool:
        self.advance_trading_day(occurred_at)
        self.state.consecutive_data_failures += 1
        self.state.last_data_error = reason
        if self.settings.halt_on_data_source_failure and self.state.status != RuntimeStatus.HALTED:
            return self._halt(
                reason=HaltReason.DATA_SOURCE_FAILURE,
                message=f"halted after data source failure: {reason}",
            )
        self.state.last_alert = reason
        self.state.touch()
        self._persist_state()
        return False

    def enforce_data_freshness(self, now: datetime | None = None) -> bool:
        if self.state.status == RuntimeStatus.HALTED:
            return False
        if self._last_data_success_wall_clock_at is None:
            return False

        checked_at = (now or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
        stale_seconds = (
            checked_at - self._last_data_success_wall_clock_at.astimezone(timezone.utc)
        ).total_seconds()
        if stale_seconds < self.settings.kill_switch_on_stale_data_seconds:
            return False
        return self._halt(
            reason=HaltReason.STALE_DATA,
            message=(
                "halted after market data went stale "
                f"for {self.settings.kill_switch_on_stale_data_seconds}s"
            ),
        )

    def halt_for_reason(self, reason: HaltReason, message: str) -> bool:
        return self._halt(reason=reason, message=message)

    def _reject_if_halted(self) -> RiskDecision | None:
        if self.state.status == RuntimeStatus.HALTED:
            return RiskDecision(approved=False, reason=self.state.halt_message or "system halted")
        return None

    def _reject_order(self, *, intent: OrderIntent, reason: str) -> RiskDecision:
        self.state.last_order_rejection_reason = reason
        self.state.last_order_rejection_market_id = intent.market_id
        self.state.last_order_rejection_exposure_group_id = intent.exposure_group_id
        self.state.last_order_rejection_thesis_group_id = intent.thesis_group_id
        self.state.last_order_rejection_underlying_group_id = intent.underlying_group_id
        self.state.touch()
        self._persist_state()
        return RiskDecision(approved=False, reason=reason)

    def _halt(self, reason: HaltReason, message: str) -> bool:
        if self.state.status == RuntimeStatus.HALTED:
            self.state.touch()
            self._persist_state()
            return False
        self.state.status = RuntimeStatus.HALTED
        self.state.halt_reason = reason
        self.state.halt_message = message
        self.state.last_alert = message
        self.state.touch()
        self._persist_state()
        return True

    def _persist_state(self) -> None:
        if self.state_store is None:
            return
        self.state_store.save(self.state)

    def _replacement_candidate(self, intent: OrderIntent) -> PendingOrderState | None:
        frontier = self._replacement_frontier(intent.created_at)
        new_edge = intent.signal_edge_bps if intent.signal_edge_bps is not None else 0.0
        improvement_floor = self.settings.open_order_replacement_min_edge_improvement_bps
        soft_limit_available = self.state.orders_today < self.trading_settings.daily_order_soft_limit
        candidates: list[tuple[int, float, datetime, PendingOrderState]] = []
        for order in self.state.pending_orders.values():
            existing_edge = order.signal_edge_bps if order.signal_edge_bps is not None else 0.0
            is_stale = self._pending_order_is_stale(order=order, frontier=frontier)
            edge_improved = (
                soft_limit_available
                and self._pending_order_is_mature_for_replacement(order=order, frontier=frontier)
                and new_edge >= (existing_edge + improvement_floor)
            )
            if not is_stale and not edge_improved:
                continue
            candidates.append((0 if is_stale else 1, existing_edge, order.created_at, order))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][3]

    def _projected_market_notional(
        self,
        *,
        intent: OrderIntent,
        order_notional: float,
        replacement_order_id: str | None,
    ) -> float:
        current_notional = sum(
            position.notional
            for position in self.state.open_positions.values()
            if position.category == intent.category and position.market_id == intent.market_id
        ) + sum(
            order.requested_notional
            for order in self.state.pending_orders.values()
            if order.category == intent.category and order.market_id == intent.market_id
        )
        replacement = self.state.pending_orders.get(replacement_order_id or "")
        if (
            replacement is not None
            and replacement.category == intent.category
            and replacement.market_id == intent.market_id
        ):
            current_notional -= replacement.requested_notional
        return max(0.0, current_notional) + order_notional

    def _projected_category_notional(
        self,
        *,
        intent: OrderIntent,
        order_notional: float,
        replacement_order_id: str | None,
    ) -> float:
        current_notional = sum(
            position.notional
            for position in self.state.open_positions.values()
            if position.category == intent.category
        ) + sum(
            order.requested_notional
            for order in self.state.pending_orders.values()
            if order.category == intent.category
        )
        replacement = self.state.pending_orders.get(replacement_order_id or "")
        if replacement is not None and replacement.category == intent.category:
            current_notional -= replacement.requested_notional
        return max(0.0, current_notional) + order_notional

    def _projected_exposure_group_notional(
        self,
        *,
        intent: OrderIntent,
        order_notional: float,
        replacement_order_id: str | None,
    ) -> float:
        exposure_group_id = self._exposure_group_id(intent.exposure_group_id, intent.market_id)
        current_notional = sum(
            position.notional
            for position in self.state.open_positions.values()
            if self._exposure_group_id(position.exposure_group_id, position.market_id) == exposure_group_id
        ) + sum(
            order.requested_notional
            for order in self.state.pending_orders.values()
            if self._exposure_group_id(order.exposure_group_id, order.market_id) == exposure_group_id
        )
        replacement = self.state.pending_orders.get(replacement_order_id or "")
        if (
            replacement is not None
            and self._exposure_group_id(replacement.exposure_group_id, replacement.market_id) == exposure_group_id
        ):
            current_notional -= replacement.requested_notional
        return max(0.0, current_notional) + order_notional

    def _projected_total_notional(
        self,
        *,
        order_notional: float,
        replacement_order_id: str | None,
    ) -> float:
        current_notional = sum(position.notional for position in self.state.open_positions.values()) + sum(
            order.requested_notional
            for order in self.state.pending_orders.values()
        )
        replacement = self.state.pending_orders.get(replacement_order_id or "")
        if replacement is not None:
            current_notional -= replacement.requested_notional
        return max(0.0, current_notional) + order_notional

    def _projected_thesis_group_notional(
        self,
        *,
        intent: OrderIntent,
        order_notional: float,
        replacement_order_id: str | None,
    ) -> float:
        thesis_group_id = self._normalized_optional_group_id(intent.thesis_group_id)
        if thesis_group_id is None:
            return order_notional
        current_notional = sum(
            position.notional
            for position in self.state.open_positions.values()
            if self._normalized_optional_group_id(position.thesis_group_id) == thesis_group_id
        ) + sum(
            order.requested_notional
            for order in self.state.pending_orders.values()
            if self._normalized_optional_group_id(order.thesis_group_id) == thesis_group_id
        )
        replacement = self.state.pending_orders.get(replacement_order_id or "")
        if (
            replacement is not None
            and self._normalized_optional_group_id(replacement.thesis_group_id) == thesis_group_id
        ):
            current_notional -= replacement.requested_notional
        return max(0.0, current_notional) + order_notional

    def _projected_underlying_group_notional(
        self,
        *,
        intent: OrderIntent,
        order_notional: float,
        replacement_order_id: str | None,
    ) -> float:
        underlying_group_id = self._normalized_optional_group_id(intent.underlying_group_id)
        if underlying_group_id is None:
            return order_notional
        current_notional = sum(
            position.notional
            for position in self.state.open_positions.values()
            if self._normalized_optional_group_id(position.underlying_group_id) == underlying_group_id
        ) + sum(
            order.requested_notional
            for order in self.state.pending_orders.values()
            if self._normalized_optional_group_id(order.underlying_group_id) == underlying_group_id
        )
        replacement = self.state.pending_orders.get(replacement_order_id or "")
        if (
            replacement is not None
            and self._normalized_optional_group_id(replacement.underlying_group_id) == underlying_group_id
        ):
            current_notional -= replacement.requested_notional
        return max(0.0, current_notional) + order_notional

    def _replacement_frontier(self, created_at: datetime) -> datetime:
        frontier = created_at.astimezone(timezone.utc)
        if self.state.last_data_success_at is not None and self.state.last_data_success_at > frontier:
            return self.state.last_data_success_at
        return frontier

    def _pending_order_is_stale(self, *, order: PendingOrderState, frontier: datetime) -> bool:
        effective_ttl = (
            order.quote_ttl_seconds
            if order.quote_ttl_seconds is not None
            else self.trading_settings.default_quote_ttl_seconds
        )
        return self._pending_order_age_seconds(order=order, frontier=frontier) >= effective_ttl

    def _pending_order_is_mature_for_replacement(
        self,
        *,
        order: PendingOrderState,
        frontier: datetime,
    ) -> bool:
        effective_ttl = (
            order.quote_ttl_seconds
            if order.quote_ttl_seconds is not None
            else self.trading_settings.default_quote_ttl_seconds
        )
        return self._pending_order_age_seconds(order=order, frontier=frontier) >= max(1.0, effective_ttl * 0.5)

    @staticmethod
    def _pending_order_age_seconds(*, order: PendingOrderState, frontier: datetime) -> float:
        return max(
            0.0,
            (frontier - order.created_at.astimezone(timezone.utc)).total_seconds(),
        )

    @staticmethod
    def _order_notional(intent: OrderIntent) -> float:
        if intent.notional is not None:
            return intent.notional
        if intent.price is None:
            return 0.0
        return intent.price * intent.size

    def _per_trade_notional_cap(self) -> float:
        configured_cap = self.trading_settings.max_order_notional
        if configured_cap is not None:
            return configured_cap
        return self.trading_settings.default_order_notional

    @staticmethod
    def _exposure_group_id(exposure_group_id: str | None, market_id: str) -> str:
        normalized = str(exposure_group_id or market_id).strip()
        return normalized or market_id

    @staticmethod
    def _normalized_optional_group_id(value: str | None) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None
_NOTIONAL_COMPARISON_EPSILON = 1e-6
