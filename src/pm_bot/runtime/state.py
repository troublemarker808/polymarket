"""Runtime state used by risk controls and the operator dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pm_bot.core.types import Category


class RuntimeStatus(str, Enum):
    RUNNING = "running"
    HALTED = "halted"


class HaltReason(str, Enum):
    NONE = "none"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_DRAWDOWN = "daily_drawdown"
    STALE_DATA = "stale_data"
    DATA_SOURCE_FAILURE = "data_source_failure"
    MANUAL_REVIEW = "manual_review"


@dataclass(slots=True)
class PositionState:
    market_id: str
    token_id: str
    category: Category
    strategy_id: str
    notional: float
    opened_at: datetime
    shares: float | None = None
    average_entry_price: float | None = None
    mark_price: float | None = None
    unrealized_pnl: float = 0.0
    exposure_group_id: str | None = None
    thesis_group_id: str | None = None
    underlying_group_id: str | None = None


@dataclass(slots=True)
class PendingOrderState:
    order_id: str
    market_id: str
    token_id: str
    category: Category
    strategy_id: str
    side: str
    limit_price: float
    requested_shares: float
    requested_notional: float
    matched_shares: float
    matched_notional: float
    fees_paid: float
    status: str
    created_at: datetime
    updated_at: datetime
    intent_id: str | None = None
    time_in_force: str = "GTC"
    quote_ttl_seconds: int | None = None
    signal_edge_bps: float | None = None
    exposure_group_id: str | None = None
    thesis_group_id: str | None = None
    underlying_group_id: str | None = None


@dataclass(slots=True)
class ClosedTrade:
    market_id: str
    token_id: str
    category: Category
    strategy_id: str
    realized_pnl: float
    fees_paid: float
    closed_at: datetime
    intent_id: str | None = None
    exposure_group_id: str | None = None
    thesis_group_id: str | None = None
    underlying_group_id: str | None = None

    @property
    def net_pnl(self) -> float:
        return self.realized_pnl - self.fees_paid


@dataclass(slots=True)
class DashboardState:
    total_equity: float
    today_pnl: float
    open_positions: tuple[PositionState, ...]
    pending_orders: tuple[PendingOrderState, ...]
    status: RuntimeStatus
    halt_reason: HaltReason
    halt_message: str | None
    last_alert: str | None
    daily_order_count: int
    daily_order_soft_limit_reached: bool
    last_data_success_at: datetime | None = None
    last_data_error: str | None = None
    consecutive_data_failures: int = 0
    last_order_rejection_reason: str | None = None
    last_order_rejection_market_id: str | None = None
    last_order_rejection_exposure_group_id: str | None = None
    last_order_rejection_thesis_group_id: str | None = None
    last_order_rejection_underlying_group_id: str | None = None
    issue_codes: tuple[str, ...] = ()


@dataclass(slots=True)
class RuntimeState:
    starting_equity: float
    day_starting_equity: float
    day_open_unrealized_pnl: float = 0.0
    realized_pnl_today: float = 0.0
    unrealized_pnl: float = 0.0
    consecutive_losses: int = 0
    orders_today: int = 0
    open_positions: dict[str, PositionState] = field(default_factory=dict)
    pending_orders: dict[str, PendingOrderState] = field(default_factory=dict)
    processed_trade_ids: tuple[str, ...] = ()
    status: RuntimeStatus = RuntimeStatus.RUNNING
    halt_reason: HaltReason = HaltReason.NONE
    halt_message: str | None = None
    last_alert: str | None = None
    last_data_success_at: datetime | None = None
    last_data_error: str | None = None
    consecutive_data_failures: int = 0
    last_order_rejection_reason: str | None = None
    last_order_rejection_market_id: str | None = None
    last_order_rejection_exposure_group_id: str | None = None
    last_order_rejection_thesis_group_id: str | None = None
    last_order_rejection_underlying_group_id: str | None = None
    day_started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def total_equity(self) -> float:
        return (
            self.day_starting_equity
            + self.realized_pnl_today
            + (self.unrealized_pnl - self.day_open_unrealized_pnl)
        )

    @property
    def today_pnl(self) -> float:
        return self.realized_pnl_today + (self.unrealized_pnl - self.day_open_unrealized_pnl)

    @property
    def open_position_count(self) -> int:
        return len(self.open_positions)

    @property
    def pending_order_count(self) -> int:
        return len(self.pending_orders)

    @property
    def active_market_count(self) -> int:
        return len(
            set(self.open_positions).union(
                pending.market_id for pending in self.pending_orders.values()
            )
        )

    @property
    def daily_drawdown_pct(self) -> float:
        if self.day_starting_equity <= 0:
            return 0.0

        drawdown = max(0.0, self.day_starting_equity - self.total_equity)
        return (drawdown / self.day_starting_equity) * 100

    def touch(self) -> None:
        self.updated_at = datetime.now(tz=timezone.utc)

    def snapshot(self, soft_limit: int) -> DashboardState:
        issue_codes: list[str] = []
        if self.consecutive_data_failures > 0:
            issue_codes.append("data_source_failure")
        if self.halt_reason == HaltReason.STALE_DATA:
            issue_codes.append("stale_data")
        if self.halt_reason == HaltReason.DATA_SOURCE_FAILURE:
            issue_codes.append("runtime_halted_data_source")
        return DashboardState(
            total_equity=self.total_equity,
            today_pnl=self.today_pnl,
            open_positions=tuple(self.open_positions.values()),
            pending_orders=tuple(self.pending_orders.values()),
            status=self.status,
            halt_reason=self.halt_reason,
            halt_message=self.halt_message,
            last_alert=self.last_alert,
            daily_order_count=self.orders_today,
            daily_order_soft_limit_reached=self.orders_today >= soft_limit,
            last_data_success_at=self.last_data_success_at,
            last_data_error=self.last_data_error,
            consecutive_data_failures=self.consecutive_data_failures,
            last_order_rejection_reason=self.last_order_rejection_reason,
            last_order_rejection_market_id=self.last_order_rejection_market_id,
            last_order_rejection_exposure_group_id=self.last_order_rejection_exposure_group_id,
            last_order_rejection_thesis_group_id=self.last_order_rejection_thesis_group_id,
            last_order_rejection_underlying_group_id=self.last_order_rejection_underlying_group_id,
            issue_codes=tuple(issue_codes),
        )


def runtime_state_to_dict(state: RuntimeState) -> dict[str, Any]:
    return {
        "starting_equity": state.starting_equity,
        "day_starting_equity": state.day_starting_equity,
        "day_open_unrealized_pnl": state.day_open_unrealized_pnl,
        "realized_pnl_today": state.realized_pnl_today,
        "unrealized_pnl": state.unrealized_pnl,
        "consecutive_losses": state.consecutive_losses,
        "orders_today": state.orders_today,
        "open_positions": {
            market_id: position_state_to_dict(position)
            for market_id, position in state.open_positions.items()
        },
        "pending_orders": {
            order_id: pending_order_state_to_dict(order)
            for order_id, order in state.pending_orders.items()
        },
        "processed_trade_ids": list(state.processed_trade_ids),
        "status": state.status.value,
        "halt_reason": state.halt_reason.value,
        "halt_message": state.halt_message,
        "last_alert": state.last_alert,
        "last_data_success_at": (
            state.last_data_success_at.isoformat() if state.last_data_success_at is not None else None
        ),
        "last_data_error": state.last_data_error,
        "consecutive_data_failures": state.consecutive_data_failures,
        "last_order_rejection_reason": state.last_order_rejection_reason,
        "last_order_rejection_market_id": state.last_order_rejection_market_id,
        "last_order_rejection_exposure_group_id": state.last_order_rejection_exposure_group_id,
        "last_order_rejection_thesis_group_id": state.last_order_rejection_thesis_group_id,
        "last_order_rejection_underlying_group_id": state.last_order_rejection_underlying_group_id,
        "day_started_at": state.day_started_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
    }


def runtime_state_from_dict(payload: dict[str, Any]) -> RuntimeState:
    return RuntimeState(
        starting_equity=float(payload["starting_equity"]),
        day_starting_equity=float(payload["day_starting_equity"]),
        day_open_unrealized_pnl=float(payload.get("day_open_unrealized_pnl", 0.0)),
        realized_pnl_today=float(payload.get("realized_pnl_today", 0.0)),
        unrealized_pnl=float(payload.get("unrealized_pnl", 0.0)),
        consecutive_losses=int(payload.get("consecutive_losses", 0)),
        orders_today=int(payload.get("orders_today", 0)),
        open_positions={
            market_id: position_state_from_dict(position_payload)
            for market_id, position_payload in dict(payload.get("open_positions", {})).items()
        },
        pending_orders={
            order_id: pending_order_state_from_dict(order_payload)
            for order_id, order_payload in dict(payload.get("pending_orders", {})).items()
        },
        processed_trade_ids=tuple(
            str(trade_id)
            for trade_id in list(payload.get("processed_trade_ids", ()))
            if str(trade_id).strip()
        ),
        status=RuntimeStatus(str(payload.get("status", RuntimeStatus.RUNNING.value))),
        halt_reason=HaltReason(str(payload.get("halt_reason", HaltReason.NONE.value))),
        halt_message=payload.get("halt_message"),
        last_alert=payload.get("last_alert"),
        last_data_success_at=_parse_datetime(payload.get("last_data_success_at")),
        last_data_error=payload.get("last_data_error"),
        consecutive_data_failures=int(payload.get("consecutive_data_failures", 0)),
        last_order_rejection_reason=payload.get("last_order_rejection_reason"),
        last_order_rejection_market_id=payload.get("last_order_rejection_market_id"),
        last_order_rejection_exposure_group_id=payload.get("last_order_rejection_exposure_group_id"),
        last_order_rejection_thesis_group_id=payload.get("last_order_rejection_thesis_group_id"),
        last_order_rejection_underlying_group_id=payload.get("last_order_rejection_underlying_group_id"),
        day_started_at=(
            _parse_datetime(payload.get("day_started_at"))
            or _parse_datetime(payload.get("updated_at"))
            or datetime.now(tz=timezone.utc)
        ),
        updated_at=_parse_datetime(payload.get("updated_at")) or datetime.now(tz=timezone.utc),
    )


def position_state_to_dict(position: PositionState) -> dict[str, Any]:
    return {
        "market_id": position.market_id,
        "token_id": position.token_id,
        "category": position.category.value,
        "strategy_id": position.strategy_id,
        "notional": position.notional,
        "shares": position.shares,
        "average_entry_price": position.average_entry_price,
        "mark_price": position.mark_price,
        "unrealized_pnl": position.unrealized_pnl,
        "exposure_group_id": position.exposure_group_id,
        "thesis_group_id": position.thesis_group_id,
        "underlying_group_id": position.underlying_group_id,
        "opened_at": position.opened_at.isoformat(),
    }


def pending_order_state_to_dict(order: PendingOrderState) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "intent_id": order.intent_id,
        "time_in_force": order.time_in_force,
        "market_id": order.market_id,
        "token_id": order.token_id,
        "category": order.category.value,
        "strategy_id": order.strategy_id,
        "side": order.side,
        "limit_price": order.limit_price,
        "requested_shares": order.requested_shares,
        "requested_notional": order.requested_notional,
        "quote_ttl_seconds": order.quote_ttl_seconds,
        "signal_edge_bps": order.signal_edge_bps,
        "exposure_group_id": order.exposure_group_id,
        "thesis_group_id": order.thesis_group_id,
        "underlying_group_id": order.underlying_group_id,
        "matched_shares": order.matched_shares,
        "matched_notional": order.matched_notional,
        "fees_paid": order.fees_paid,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }


def position_state_from_dict(payload: dict[str, Any]) -> PositionState:
    return PositionState(
        market_id=str(payload["market_id"]),
        token_id=str(payload["token_id"]),
        category=Category(str(payload["category"])),
        strategy_id=str(payload["strategy_id"]),
        notional=float(payload["notional"]),
        opened_at=_parse_datetime(payload.get("opened_at")) or datetime.now(tz=timezone.utc),
        shares=_parse_optional_float(payload.get("shares")),
        average_entry_price=_parse_optional_float(payload.get("average_entry_price")),
        mark_price=_parse_optional_float(payload.get("mark_price")),
        unrealized_pnl=float(payload.get("unrealized_pnl", 0.0)),
        exposure_group_id=(
            str(payload["exposure_group_id"])
            if payload.get("exposure_group_id") not in (None, "")
            else None
        ),
        thesis_group_id=(
            str(payload["thesis_group_id"])
            if payload.get("thesis_group_id") not in (None, "")
            else None
        ),
        underlying_group_id=(
            str(payload["underlying_group_id"])
            if payload.get("underlying_group_id") not in (None, "")
            else None
        ),
    )


def pending_order_state_from_dict(payload: dict[str, Any]) -> PendingOrderState:
    return PendingOrderState(
        order_id=str(payload["order_id"]),
        intent_id=(str(payload["intent_id"]) if payload.get("intent_id") not in (None, "") else None),
        time_in_force=str(payload.get("time_in_force", "GTC")),
        market_id=str(payload["market_id"]),
        token_id=str(payload["token_id"]),
        category=Category(str(payload["category"])),
        strategy_id=str(payload["strategy_id"]),
        side=str(payload.get("side", "")),
        limit_price=float(payload["limit_price"]),
        requested_shares=float(payload["requested_shares"]),
        requested_notional=float(payload["requested_notional"]),
        quote_ttl_seconds=(
            int(payload["quote_ttl_seconds"])
            if payload.get("quote_ttl_seconds") not in (None, "")
            else None
        ),
        signal_edge_bps=_parse_optional_float(payload.get("signal_edge_bps")),
        exposure_group_id=(
            str(payload["exposure_group_id"])
            if payload.get("exposure_group_id") not in (None, "")
            else None
        ),
        thesis_group_id=(
            str(payload["thesis_group_id"])
            if payload.get("thesis_group_id") not in (None, "")
            else None
        ),
        underlying_group_id=(
            str(payload["underlying_group_id"])
            if payload.get("underlying_group_id") not in (None, "")
            else None
        ),
        matched_shares=float(payload.get("matched_shares", 0.0)),
        matched_notional=float(payload.get("matched_notional", 0.0)),
        fees_paid=float(payload.get("fees_paid", 0.0)),
        status=str(payload.get("status", "")),
        created_at=_parse_datetime(payload.get("created_at")) or datetime.now(tz=timezone.utc),
        updated_at=_parse_datetime(payload.get("updated_at")) or datetime.now(tz=timezone.utc),
    )


def dashboard_state_to_lines(dashboard: DashboardState) -> list[str]:
    lines = [
        f"total_equity={dashboard.total_equity:.2f}",
        f"today_pnl={dashboard.today_pnl:.2f}",
        f"status={dashboard.status.value}",
        f"halt_reason={dashboard.halt_reason.value}",
        f"halt_message={dashboard.halt_message or ''}",
        f"last_alert={dashboard.last_alert or ''}",
        f"last_data_success_at={dashboard.last_data_success_at.isoformat() if dashboard.last_data_success_at is not None else ''}",
        f"last_data_error={dashboard.last_data_error or ''}",
        f"consecutive_data_failures={dashboard.consecutive_data_failures}",
        f"last_order_rejection_reason={dashboard.last_order_rejection_reason or ''}",
        f"last_order_rejection_market_id={dashboard.last_order_rejection_market_id or ''}",
        f"last_order_rejection_exposure_group_id={dashboard.last_order_rejection_exposure_group_id or ''}",
        f"last_order_rejection_thesis_group_id={dashboard.last_order_rejection_thesis_group_id or ''}",
        f"last_order_rejection_underlying_group_id={dashboard.last_order_rejection_underlying_group_id or ''}",
        f"issue_codes={','.join(dashboard.issue_codes)}",
        f"open_positions={len(dashboard.open_positions)}",
        f"pending_orders={len(dashboard.pending_orders)}",
        f"daily_order_count={dashboard.daily_order_count}",
        f"daily_order_soft_limit_reached={str(dashboard.daily_order_soft_limit_reached).lower()}",
    ]
    for position in dashboard.open_positions:
        lines.append(
            "position="
            + f"{position.market_id}:{position.category.value}:notional={position.notional:.2f}:"
            + f"shares={_format_optional_float(position.shares)}:"
            + f"avg={_format_optional_float(position.average_entry_price)}:"
            + f"mark={_format_optional_float(position.mark_price)}:"
            + f"unrealized={position.unrealized_pnl:.2f}"
        )
    for order in dashboard.pending_orders:
        ttl_segment = (
            f":ttl={order.quote_ttl_seconds}"
            if order.quote_ttl_seconds is not None
            else ""
        )
        tif_segment = (
            f":tif={order.time_in_force}"
            if order.time_in_force
            else ""
        )
        lines.append(
            "pending_order="
            + f"{order.order_id}:{order.market_id}:{order.category.value}:{order.side}:status={order.status}:"
            + f"limit={order.limit_price:.6f}:"
            + f"req_shares={order.requested_shares:.6f}:"
            + f"matched_shares={order.matched_shares:.6f}"
            + tif_segment
            + ttl_segment
            + f":notional={order.requested_notional:.2f}"
        )
    return lines


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"
