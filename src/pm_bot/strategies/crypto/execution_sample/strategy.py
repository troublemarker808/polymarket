"""Execution-sample strategy for paper-only fill collection on active crypto markets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PositionState
from pm_bot.strategies.common import (
    clamp_probability,
    current_position,
    dashboard_state,
    has_pending_order,
    parse_datetime,
    recent_runtime_events,
)


class CryptoExecutionSampleConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_spread_bps = float(config.get("min_spread_bps", 100))
        self.min_recent_updates = int(config.get("min_recent_updates", 3))
        self.recent_update_window_seconds = int(config.get("recent_update_window_seconds", 90))
        self.hold_seconds = int(config.get("hold_seconds", 20))
        self.market_cooldown_seconds = int(config.get("market_cooldown_seconds", 20))
        self.entry_cross_bps = float(config.get("entry_cross_bps", 25))
        self.exit_cross_bps = float(config.get("exit_cross_bps", 25))
        self.min_price = float(config.get("min_price", 0.15))
        self.max_price = float(config.get("max_price", 0.85))
        self.quote_ttl_seconds = int(config.get("quote_ttl_seconds", 30))


class CryptoExecutionSampleStrategy:
    strategy_id = "crypto.execution_sample"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = CryptoExecutionSampleConfig(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.CRYPTO:
            return []

        dashboard = dashboard_state(context)
        if has_pending_order(snapshot=snapshot, dashboard=dashboard):
            return []

        recent_updates = _recent_market_updates(
            snapshot=snapshot,
            context=context,
            window_seconds=self.config.recent_update_window_seconds,
        )
        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                position=position,
                recent_updates=recent_updates,
            )
            return [exit_signal] if exit_signal is not None else []

        if recent_updates < self.config.min_recent_updates:
            return []
        if _market_in_cooldown(
            strategy_id=self.strategy_id,
            snapshot=snapshot,
            context=context,
            cooldown_seconds=self.config.market_cooldown_seconds,
        ):
            return []

        candidate = _best_entry_candidate(
            snapshot=snapshot,
            min_spread_bps=self.config.min_spread_bps,
            min_price=self.config.min_price,
            max_price=self.config.max_price,
            entry_cross_bps=self.config.entry_cross_bps,
        )
        if candidate is None:
            return []

        side, fair_probability, quote_price, spread_bps = candidate
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=snapshot.token_id,
                fair_probability=fair_probability,
                side=side,
                confidence=min(0.95, 0.55 + (recent_updates * 0.05)),
                edge_bps=max(spread_bps, self.config.min_spread_bps),
                generated_at=snapshot.timestamp,
                target_price=quote_price,
                quote_ttl_seconds=self.config.quote_ttl_seconds,
                rationale_tags=("crypto_execution_sample", "active_market"),
            )
        ]

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        position: PositionState,
        recent_updates: int,
    ) -> StrategySignal | None:
        if recent_updates < 1:
            return None
        held_seconds = (snapshot.timestamp - position.opened_at).total_seconds()
        if held_seconds < self.config.hold_seconds:
            return None

        no_token_id = snapshot.metadata.get("no_token_id")
        if position.token_id == snapshot.token_id:
            best_bid = snapshot.best_bid_yes
            spread_bps = _spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
            if best_bid is None:
                return None
            target_price = _cross_sell_price(best_bid=best_bid, cross_bps=self.config.exit_cross_bps)
            fair_probability = snapshot.best_bid_yes if snapshot.best_bid_yes is not None else 0.5
            side = SignalSide.SELL_YES
        elif no_token_id and position.token_id == no_token_id:
            best_bid = snapshot.best_bid_no
            spread_bps = _spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
            if best_bid is None:
                return None
            target_price = _cross_sell_price(best_bid=best_bid, cross_bps=self.config.exit_cross_bps)
            fair_probability = snapshot.best_bid_no if snapshot.best_bid_no is not None else 0.5
            side = SignalSide.SELL_NO
        else:
            return None

        shares = position.shares or 0.0
        target_notional = shares * target_price
        if target_notional <= 0:
            return None

        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.CRYPTO,
            market_id=snapshot.market_id,
            token_id=position.token_id,
            fair_probability=fair_probability,
            side=side,
            confidence=min(0.95, 0.5 + (recent_updates * 0.04)),
            edge_bps=max(spread_bps, self.config.min_spread_bps),
            generated_at=snapshot.timestamp,
            target_price=target_price,
            target_size=target_notional,
            quote_ttl_seconds=self.config.quote_ttl_seconds,
            rationale_tags=("crypto_execution_sample_exit", "hold_window_complete"),
        )


def _best_entry_candidate(
    *,
    snapshot: MarketSnapshot,
    min_spread_bps: float,
    min_price: float,
    max_price: float,
    entry_cross_bps: float,
) -> tuple[SignalSide, float, float, float] | None:
    candidates: list[tuple[float, float, SignalSide, float, float]] = []

    yes_spread_bps = _spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
    if (
        snapshot.best_ask_yes is not None
        and min_price <= snapshot.best_ask_yes <= max_price
        and yes_spread_bps >= min_spread_bps
    ):
        candidates.append(
            (
                abs(snapshot.best_ask_yes - 0.5),
                -yes_spread_bps,
                SignalSide.BUY_YES,
                snapshot.best_ask_yes,
                yes_spread_bps,
            )
        )

    no_spread_bps = _spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
    if (
        snapshot.best_ask_no is not None
        and min_price <= snapshot.best_ask_no <= max_price
        and no_spread_bps >= min_spread_bps
    ):
        candidates.append(
            (
                abs(snapshot.best_ask_no - 0.5),
                -no_spread_bps,
                SignalSide.BUY_NO,
                snapshot.best_ask_no,
                no_spread_bps,
            )
        )

    if not candidates:
        return None

    _, _, side, ask_price, spread_bps = min(candidates)
    quote_price = _cross_buy_price(best_ask=ask_price, cross_bps=entry_cross_bps)
    fair_probability = ask_price if side == SignalSide.BUY_YES else 1.0 - ask_price
    return (side, clamp_probability(fair_probability), quote_price, spread_bps)


def _recent_market_updates(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    window_seconds: int,
) -> int:
    count = 0
    for event in recent_runtime_events(context):
        if event.get("event_type") != "market.snapshot_processed":
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        updated_at = parse_datetime(payload, "updated_at")
        if updated_at is None:
            continue
        if (snapshot.timestamp - updated_at).total_seconds() > window_seconds:
            continue
        count += 1
    return count


def _market_in_cooldown(
    *,
    strategy_id: str,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    cooldown_seconds: int,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    latest = _latest_market_event(
        strategy_id=strategy_id,
        market_id=snapshot.market_id,
        context=context,
    )
    if latest is None:
        return False
    return (snapshot.timestamp - latest).total_seconds() < cooldown_seconds


def _latest_market_event(
    *,
    strategy_id: str,
    market_id: str,
    context: Mapping[str, object],
) -> datetime | None:
    latest: datetime | None = None
    for event in recent_runtime_events(context):
        event_type = str(event.get("event_type", "")).strip()
        if event_type not in {"order.submitted", "order.filled", "order.expired", "order.canceled"}:
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if str(payload.get("strategy_id", "")) != strategy_id:
            continue
        if str(payload.get("market_id", "")) != market_id:
            continue
        occurred_at = parse_datetime(payload, "updated_at", "created_at")
        if occurred_at is None:
            continue
        if latest is None or occurred_at > latest:
            latest = occurred_at
    return latest


def _spread_bps(best_bid: float | None, best_ask: float | None) -> float:
    if best_bid is None or best_ask is None:
        return 0.0
    return max(0.0, (best_ask - best_bid) * 10000)


def _cross_buy_price(*, best_ask: float, cross_bps: float) -> float:
    return round(clamp_probability(best_ask * (1 + (cross_bps / 10000))), 6)


def _cross_sell_price(*, best_bid: float, cross_bps: float) -> float:
    return round(clamp_probability(best_bid * (1 - (cross_bps / 10000))), 6)
