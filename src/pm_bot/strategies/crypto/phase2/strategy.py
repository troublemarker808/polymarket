"""Crypto Phase 2 strategy wrapper around Phase 1 fair values and Phase 2 execution policy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PendingOrderState, PositionState
from datetime import datetime, timezone

from pm_bot.strategies.common import current_position, dashboard_state, has_pending_order, recent_runtime_events
from pm_bot.strategies.crypto.phase2.execution import (
    build_order_intent,
    classify_crypto_signal,
    evaluate_trade_eligibility,
    route_execution,
)
from pm_bot.strategies.crypto.phase2.management import evaluate_exit, is_reentry_blocked
from pm_bot.strategies.crypto.phase2.models import CryptoPositionIntent, CryptoReentryState


class CryptoPhase2Config:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_confidence = float(config.get("min_confidence", 0.6))
        self.min_net_edge_bps = float(config.get("min_net_edge_bps", 75.0))
        self.max_spread_bps = float(config.get("max_spread_bps", 250.0))
        self.min_liquidity_score = float(config.get("min_liquidity_score", 0.0))
        self.min_contract_price = float(config.get("min_contract_price", 0.05))
        self.taker_urgency_threshold = float(config.get("taker_urgency_threshold", 0.72))
        self.maker_min_edge_bps = float(config.get("maker_min_edge_bps", 100.0))
        self.resolution_maker_min_edge_bps = float(config.get("resolution_maker_min_edge_bps", 150.0))
        self.high_edge_taker_min_edge_bps = float(config.get("high_edge_taker_min_edge_bps", 2000.0))
        self.high_edge_taker_max_spread_bps = float(config.get("high_edge_taker_max_spread_bps", 250.0))
        self.taker_max_entry_premium_bps = float(config.get("taker_max_entry_premium_bps", 750.0))
        self.maker_quote_ttl_seconds = int(config.get("maker_quote_ttl_seconds", 60))
        self.resolution_maker_quote_ttl_seconds = int(config.get("resolution_maker_quote_ttl_seconds", 180))
        self.maker_aggressiveness = float(config.get("maker_aggressiveness", 1.0))
        self.default_notional = float(config.get("default_notional", 5.0))
        self.exit_edge_bps = float(config.get("exit_edge_bps", 75.0))
        self.stop_loss_bps = float(config.get("stop_loss_bps", 250.0))
        self.execution_max_holding_seconds = (
            float(config["execution_max_holding_seconds"])
            if "execution_max_holding_seconds" in config
            else None
        )
        self.min_holding_seconds_before_exit = float(config.get("min_holding_seconds_before_exit", 1.0))
        self.aging_exit_edge_bps = float(config.get("aging_exit_edge_bps", 150.0))
        self.stale_exit_edge_bps = float(config.get("stale_exit_edge_bps", 300.0))
        self.aging_start_fraction = float(config.get("aging_start_fraction", 0.5))
        self.stale_start_fraction = float(config.get("stale_start_fraction", 1.0))
        self.stop_loss_min_ticks = int(config.get("stop_loss_min_ticks", 2))
        self.stop_loss_max_remaining_edge_bps = float(config.get("stop_loss_max_remaining_edge_bps", 150.0))
        self.adverse_fill_exit_bps = float(config.get("adverse_fill_exit_bps", 75.0))
        self.adverse_fill_max_remaining_edge_bps = float(
            config.get("adverse_fill_max_remaining_edge_bps", 150.0)
        )
        self.max_holding_multiplier = float(config.get("max_holding_multiplier", 2.0))
        self.exit_repost_cooldown_seconds = float(config.get("exit_repost_cooldown_seconds", 30.0))
        self.entry_repost_cooldown_seconds = float(config.get("entry_repost_cooldown_seconds", 120.0))
        self.time_stop_force_ioc_after_expiries = int(config.get("time_stop_force_ioc_after_expiries", 2))


class CryptoPhase2Strategy:
    strategy_id = "crypto.phase2"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = CryptoPhase2Config(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.CRYPTO:
            return []

        fair_value = _fair_value_for_market(snapshot=snapshot, context=context)
        if fair_value is None:
            return []

        dashboard = dashboard_state(context)
        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            return self._exit_signals(
                snapshot=snapshot,
                fair_value=fair_value,
                position=position,
                context=context,
            )
        if has_pending_order(snapshot=snapshot, dashboard=dashboard):
            return []

        reentry_state = _reentry_state_for_market(snapshot=snapshot, context=context)
        if is_reentry_blocked(state=reentry_state, as_of=snapshot.timestamp):
            return []

        if _series_is_blocked(snapshot=snapshot, context=context):
            return []

        return self._entry_signals(
            snapshot=snapshot,
            fair_value=fair_value,
            context=context,
        )

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        classification = classify_crypto_signal(fair_value=fair_value)
        eligibility = evaluate_trade_eligibility(
            fair_value=fair_value,
            snapshot=snapshot,
            classification=classification,
            min_confidence=self.config.min_confidence,
            min_net_edge_bps=self.config.min_net_edge_bps,
            max_spread_bps=self.config.max_spread_bps,
            min_liquidity_score=self.config.min_liquidity_score,
            min_contract_price=self.config.min_contract_price,
        )
        decision = route_execution(
            fair_value=fair_value,
            snapshot=snapshot,
            classification=classification,
            eligibility=eligibility,
            taker_urgency_threshold=self.config.taker_urgency_threshold,
            maker_min_edge_bps=self.config.maker_min_edge_bps,
            resolution_maker_min_edge_bps=self.config.resolution_maker_min_edge_bps,
            high_edge_taker_min_edge_bps=self.config.high_edge_taker_min_edge_bps,
            high_edge_taker_max_spread_bps=self.config.high_edge_taker_max_spread_bps,
            taker_max_entry_premium_bps=self.config.taker_max_entry_premium_bps,
            maker_quote_ttl_seconds=self.config.maker_quote_ttl_seconds,
            resolution_maker_quote_ttl_seconds=self.config.resolution_maker_quote_ttl_seconds,
            maker_aggressiveness=self.config.maker_aggressiveness,
        )
        if decision.route == "skip" or decision.target_price is None:
            return []

        intent = build_order_intent(
            fair_value=fair_value,
            snapshot=snapshot,
            decision=decision,
            default_notional=self.config.default_notional,
            strategy_id=self.strategy_id,
        )
        target_size = intent.notional if intent is not None else self.config.default_notional
        if _recently_reposted_order(
            snapshot=snapshot,
            context=context,
            target_price=decision.target_price,
            side=decision.side,
            cooldown_seconds=self.config.entry_repost_cooldown_seconds,
            allowed_event_types={"order.expired", "order.canceled"},
        ):
            return []
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=(intent.token_id if intent is not None else snapshot.token_id),
                fair_probability=fair_value.fair_probability,
                side=decision.side,
                confidence=fair_value.confidence,
                edge_bps=float(fair_value.supporting_values.get("net_edge_bps", 0.0)),
                generated_at=snapshot.timestamp,
                target_price=decision.target_price,
                target_size=target_size,
                time_in_force=("IOC" if decision.route == "taker" else "GTC"),
                quote_ttl_seconds=decision.quote_ttl_seconds,
                rationale_tags=decision.rationale_tags,
                diagnostics={
                    "observed_probability": fair_value.observed_probability,
                    "gross_edge_bps": float(fair_value.supporting_values.get("gross_edge_bps", 0.0)),
                    "net_edge_bps": float(fair_value.supporting_values.get("net_edge_bps", 0.0)),
                    "signal_type": classification.signal_type,
                    "execution_route": decision.route,
                },
            )
        ]

    def _exit_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        position: PositionState,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        intent = _position_intent_for_market(snapshot=snapshot, context=context)
        if intent is None:
            return []

        exit_decision = evaluate_exit(
            fair_value=fair_value,
            position=position,
            intent=intent,
            best_bid_yes=snapshot.best_bid_yes,
            best_bid_no=snapshot.best_bid_no,
            as_of=snapshot.timestamp,
            exit_edge_bps=self.config.exit_edge_bps,
            stop_loss_bps=self.config.stop_loss_bps,
            max_holding_multiplier=self.config.max_holding_multiplier,
            execution_max_holding_seconds=self.config.execution_max_holding_seconds,
            min_holding_seconds_before_exit=self.config.min_holding_seconds_before_exit,
            aging_exit_edge_bps=self.config.aging_exit_edge_bps,
            stale_exit_edge_bps=self.config.stale_exit_edge_bps,
            aging_start_fraction=self.config.aging_start_fraction,
            stale_start_fraction=self.config.stale_start_fraction,
            stop_loss_min_ticks=self.config.stop_loss_min_ticks,
            tick_size=snapshot.tick_size,
            stop_loss_max_remaining_edge_bps=self.config.stop_loss_max_remaining_edge_bps,
            adverse_fill_exit_bps=self.config.adverse_fill_exit_bps,
            adverse_fill_max_remaining_edge_bps=self.config.adverse_fill_max_remaining_edge_bps,
        )
        if not exit_decision.should_exit or exit_decision.exit_side is None or exit_decision.target_price is None:
            return []

        exit_price = exit_decision.target_price
        time_in_force = "IOC"
        quote_ttl_seconds = None
        exit_retry_count = _exit_retry_count(
            snapshot=snapshot,
            position=position,
            context=context,
        )
        if exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop"}:
            if (
                exit_decision.reason == "time_stop"
                and exit_retry_count >= self.config.time_stop_force_ioc_after_expiries
            ):
                exit_price = exit_decision.target_price
                time_in_force = "IOC"
                quote_ttl_seconds = None
            else:
                exit_price, quote_ttl_seconds = _passive_exit_price(
                    snapshot=snapshot,
                    position=position,
                    exit_side=exit_decision.exit_side,
                    exit_reason=exit_decision.reason,
                    fallback_price=exit_decision.target_price,
                    retry_count=exit_retry_count,
                )
                time_in_force = "GTC"

        target_notional = (position.shares or 0.0) * exit_price
        if target_notional <= 0:
            return []

        existing_exit_order = _pending_exit_order(
            snapshot=snapshot,
            position=position,
            context=context,
        )
        if (
            existing_exit_order is not None
            and abs(existing_exit_order.limit_price - exit_price) < 1e-9
            and existing_exit_order.time_in_force == time_in_force
            and existing_exit_order.quote_ttl_seconds == quote_ttl_seconds
        ):
            return []
        if (
            exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop"}
            and _recently_reposted_exit(
                snapshot=snapshot,
                position=position,
                context=context,
                target_price=exit_price,
                cooldown_seconds=self.config.exit_repost_cooldown_seconds,
            )
        ):
            return []

        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=position.token_id,
                fair_probability=fair_value.fair_probability,
                side=exit_decision.exit_side,
                confidence=fair_value.confidence,
                edge_bps=max(0.0, exit_decision.remaining_edge_bps),
                generated_at=snapshot.timestamp,
                target_price=exit_price,
                target_size=target_notional,
                time_in_force=time_in_force,
                quote_ttl_seconds=quote_ttl_seconds,
                rationale_tags=exit_decision.rationale_tags,
                diagnostics={
                    "observed_probability": fair_value.observed_probability,
                    "gross_edge_bps": float(fair_value.supporting_values.get("gross_edge_bps", 0.0)),
                    "net_edge_bps": float(fair_value.supporting_values.get("net_edge_bps", 0.0)),
                    "remaining_edge_bps": exit_decision.remaining_edge_bps,
                    "signal_type": "exit",
                    "execution_route": ("taker" if time_in_force == "IOC" else "maker"),
                },
            )
        ]


def _fair_value_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> FairValueEstimate | None:
    fair_values = context.get("fair_values_by_market_id")
    if isinstance(fair_values, Mapping):
        fair_value = fair_values.get(snapshot.market_id)
        if isinstance(fair_value, FairValueEstimate):
            return fair_value
    return None


def _position_intent_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> CryptoPositionIntent | None:
    intents = context.get("position_intents_by_market_id")
    if isinstance(intents, Mapping):
        intent = intents.get(snapshot.market_id)
        if isinstance(intent, CryptoPositionIntent):
            return intent
    return None


def _reentry_state_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> CryptoReentryState | None:
    states = context.get("reentry_state_by_market_id")
    if isinstance(states, Mapping):
        state = states.get(snapshot.market_id)
        if isinstance(state, CryptoReentryState):
            return state
    return None


def _series_is_blocked(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> bool:
    blocked = context.get("blocked_series_keys")
    if not isinstance(blocked, (set, frozenset, tuple, list)):
        return False
    series_key = snapshot.metadata.get("event_slug")
    if not series_key:
        return False
    return str(series_key) in blocked


def _pending_exit_order(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
) -> PendingOrderState | None:
    dashboard = dashboard_state(context)
    if dashboard is None:
        return None
    return next(
        (
            order
            for order in dashboard.pending_orders
            if order.market_id == snapshot.market_id
            and order.token_id == position.token_id
            and order.side == (
                SignalSide.SELL_YES.value
                if position.token_id == snapshot.token_id
                else SignalSide.SELL_NO.value
            )
        ),
        None,
    )


def _recently_reposted_exit(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
    target_price: float,
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _matches_exit_side(payload):
            continue
        raw_price = payload.get("price", payload.get("limit_price"))
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        if abs(price - target_price) >= 1e-9:
            continue
        if event_type not in {"order.expired", "order.canceled", "order.submitted"}:
            continue
        event_time = _event_timestamp(payload)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _exit_retry_count(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
) -> int:
    retries = 0
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _matches_exit_side(payload):
            continue
        if event_type == "trade.closed":
            break
        if event_type == "order.expired":
            retries += 1
            continue
        if event_type == "order.filled":
            break
    return retries


def _recently_reposted_order(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    target_price: float,
    side: SignalSide,
    cooldown_seconds: float,
    allowed_event_types: set[str],
) -> bool:
    if cooldown_seconds <= 0:
        return False
    target_side = side.value
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if event_type not in allowed_event_types:
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        raw_price = payload.get("price", payload.get("limit_price"))
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        if abs(price - target_price) >= 1e-9:
            continue
        event_time = _event_timestamp(payload)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _event_timestamp(payload: Mapping[str, object]) -> datetime | None:
    for key in ("updated_at", "created_at", "closed_at", "generated_at"):
        raw_value = payload.get(key)
        if not isinstance(raw_value, str) or not raw_value:
            continue
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _matches_exit_side(payload: Mapping[str, object]) -> bool:
    side = str(payload.get("side", "")).lower()
    trade_side = str(payload.get("trade_side", "")).lower()
    return side in {SignalSide.SELL_YES.value, SignalSide.SELL_NO.value} or trade_side == "sell"


def _passive_exit_price(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    exit_side: SignalSide,
    exit_reason: str,
    fallback_price: float,
    retry_count: int = 0,
) -> tuple[float, int]:
    tick_size = snapshot.tick_size or 0.01
    entry_price = position.average_entry_price or fallback_price
    if exit_side == SignalSide.SELL_YES:
        best_ask = snapshot.best_ask_yes
        best_bid = snapshot.best_bid_yes
        midpoint = _midpoint(snapshot.best_bid_yes, snapshot.best_ask_yes)
    else:
        best_ask = snapshot.best_ask_no
        best_bid = snapshot.best_bid_no
        midpoint = _midpoint(snapshot.best_bid_no, snapshot.best_ask_no)
    fallback_floor = fallback_price + tick_size
    if exit_reason == "aging_exit":
        candidates = [entry_price, fallback_floor]
        if midpoint is not None:
            candidates.append(midpoint)
        passive_price = max(candidates)
        if best_ask is not None:
            passive_price = min(passive_price, best_ask)
        passive_price -= retry_count * tick_size
        passive_price = max(passive_price, max(fallback_floor, best_bid + tick_size if best_bid is not None else 0.01))
        return round(min(passive_price, 0.99), 4), 30
    if exit_reason == "stale_position_cleanup":
        candidates = [fallback_floor]
        if midpoint is not None:
            candidates.append(midpoint)
        elif best_bid is not None:
            candidates.append(best_bid + tick_size)
        passive_price = max(candidates)
        if best_ask is not None:
            passive_price = min(passive_price, best_ask)
        passive_price -= retry_count * tick_size
        passive_price = max(passive_price, best_bid + tick_size if best_bid is not None else 0.01)
        return round(min(passive_price, 0.99), 4), 15

    candidates = [fallback_floor]
    if best_bid is not None:
        candidates.append(best_bid + tick_size)
    if midpoint is not None:
        candidates.append(min(midpoint, entry_price))
    passive_price = max(candidates)
    if best_ask is not None:
        passive_price = min(passive_price, best_ask)
    passive_price -= retry_count * tick_size
    passive_price = max(passive_price, best_bid if best_bid is not None else 0.01)
    return round(min(passive_price, 0.99), 4), 5


def _midpoint(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2
