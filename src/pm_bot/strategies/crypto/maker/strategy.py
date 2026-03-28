"""Crypto maker-style quote strategy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PositionState
from pm_bot.strategies.common import (
    current_position,
    dashboard_state,
    has_pending_order,
    implied_yes_probability,
    parse_float,
    parse_datetime,
    parse_probability,
    recent_runtime_events,
)

_INSIDE_TICK = 0.01


@dataclass(slots=True)
class _EntryQuoteState:
    generated_at: datetime
    side: SignalSide
    edge_bps: float


@dataclass(slots=True)
class _RecentFailureState:
    occurred_at: datetime
    edge_bps: float | None
    event_type: str
    reason: str | None


class CryptoMakerConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_spread_bps = float(config.get("min_spread_bps", 100))
        self.inventory_skew_strength = float(config.get("inventory_skew_strength", 0.5))
        self.quote_ttl_seconds = int(config.get("quote_ttl_seconds", 10))
        self.global_cooldown_seconds = int(config.get("global_cooldown_seconds", 0))
        self.market_cooldown_seconds = int(config.get("market_cooldown_seconds", 20))
        self.failure_cooldown_seconds = int(config.get("failure_cooldown_seconds", 0))
        self.min_requote_edge_improvement_bps = float(
            config.get("min_requote_edge_improvement_bps", 50)
        )
        self.failure_reentry_edge_improvement_bps = float(
            config.get(
                "failure_reentry_edge_improvement_bps",
                self.min_requote_edge_improvement_bps,
            )
        )


class CryptoMakerStrategy:
    strategy_id = "crypto.maker"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = CryptoMakerConfig(config)
        self._last_entry_by_market: dict[str, _EntryQuoteState] = {}
        self._last_global_entry: tuple[str, datetime] | None = None

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

        fair_probability = parse_probability(
            snapshot.metadata,
            "reference_yes_probability",
            "external_yes_probability",
            "fair_yes_probability",
            "consensus_yes_probability",
        ) or implied_yes_probability(snapshot)
        if fair_probability is None:
            return []

        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=position,
            )
            return [exit_signal] if exit_signal is not None else []

        yes_spread_bps = _spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
        no_spread_bps = _spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
        if max(yes_spread_bps, no_spread_bps) < self.config.min_spread_bps:
            return []

        yes_candidate = self._entry_candidate(
            snapshot=snapshot,
            fair_probability=fair_probability,
            side=SignalSide.BUY_YES,
            best_bid=snapshot.best_bid_yes,
            best_ask=snapshot.best_ask_yes,
        )
        no_candidate = self._entry_candidate(
            snapshot=snapshot,
            fair_probability=1 - fair_probability,
            side=SignalSide.BUY_NO,
            best_bid=snapshot.best_bid_no,
            best_ask=snapshot.best_ask_no,
        )
        candidates = [candidate for candidate in (yes_candidate, no_candidate) if candidate is not None]
        if not candidates:
            return []

        best_signal = max(
            candidates,
            key=lambda signal: (
                signal.edge_bps,
                signal.side == SignalSide.BUY_YES,
            ),
        )
        if not self._should_emit_entry(signal=best_signal, context=context):
            return []
        self._remember_entry(signal=best_signal)
        return [best_signal]

    def _entry_candidate(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        side: SignalSide,
        best_bid: float | None,
        best_ask: float | None,
    ) -> StrategySignal | None:
        if best_ask is None:
            return None

        quote_price = _maker_buy_price(
            best_bid=best_bid,
            best_ask=best_ask,
            fair_probability=fair_probability,
            min_spread_bps=self.config.min_spread_bps,
        )
        edge_bps = (fair_probability - quote_price) * 10000
        if edge_bps < self.config.min_spread_bps:
            return None

        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.CRYPTO,
            market_id=snapshot.market_id,
            token_id=snapshot.token_id,
            fair_probability=fair_probability if side == SignalSide.BUY_YES else 1 - fair_probability,
            side=side,
            confidence=0.62,
            edge_bps=edge_bps,
            generated_at=snapshot.timestamp,
            target_price=quote_price,
            quote_ttl_seconds=self.config.quote_ttl_seconds,
            rationale_tags=("crypto_maker", "inside_spread"),
        )

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        position: PositionState,
    ) -> StrategySignal | None:
        no_token_id = snapshot.metadata.get("no_token_id")
        yes_spread_bps = _spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
        no_spread_bps = _spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
        spread_floor = self.config.min_spread_bps / 2

        if position.token_id == snapshot.token_id:
            if snapshot.best_bid_yes is None:
                return None
            exit_price = snapshot.best_bid_yes
            fair_exit_price = fair_probability
            side = SignalSide.SELL_YES
            spread_collapsed = yes_spread_bps <= (spread_floor + 1e-6)
        elif no_token_id and position.token_id == no_token_id:
            if snapshot.best_bid_no is None:
                return None
            exit_price = snapshot.best_bid_no
            fair_exit_price = 1 - fair_probability
            side = SignalSide.SELL_NO
            spread_collapsed = no_spread_bps <= (spread_floor + 1e-6)
        else:
            return None

        edge_remaining_bps = (fair_exit_price - exit_price) * 10000
        if edge_remaining_bps > 0 and not spread_collapsed:
            return None

        shares = position.shares or 0.0
        target_notional = shares * exit_price
        if target_notional <= 0:
            return None

        rationale = "spread_collapsed" if spread_collapsed else "fair_value_reached"
        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.CRYPTO,
            market_id=snapshot.market_id,
            token_id=position.token_id,
            fair_probability=fair_probability,
            side=side,
            confidence=0.6,
            edge_bps=max(0.0, edge_remaining_bps),
            generated_at=snapshot.timestamp,
            target_price=exit_price,
            target_size=target_notional,
            quote_ttl_seconds=self.config.quote_ttl_seconds,
            rationale_tags=("crypto_maker_exit", rationale),
        )

    def _should_emit_entry(
        self,
        *,
        signal: StrategySignal,
        context: Mapping[str, object],
    ) -> bool:
        if not self._passes_failure_cooldown(signal=signal, context=context):
            return False
        previous = self._last_entry_by_market.get(signal.market_id)
        if previous is None:
            return self._passes_global_cooldown(signal=signal)
        if signal.side != previous.side:
            return self._passes_global_cooldown(signal=signal)
        if signal.generated_at <= previous.generated_at:
            return False
        if self.config.market_cooldown_seconds > 0:
            elapsed_seconds = (signal.generated_at - previous.generated_at).total_seconds()
            if elapsed_seconds < self.config.market_cooldown_seconds:
                edge_improvement_bps = signal.edge_bps - previous.edge_bps
                if edge_improvement_bps < self.config.min_requote_edge_improvement_bps:
                    return False
        return self._passes_global_cooldown(signal=signal)

    def _remember_entry(self, *, signal: StrategySignal) -> None:
        self._last_entry_by_market[signal.market_id] = _EntryQuoteState(
            generated_at=signal.generated_at,
            side=signal.side,
            edge_bps=signal.edge_bps,
        )
        self._last_global_entry = (signal.market_id, signal.generated_at)

    def _passes_global_cooldown(self, *, signal: StrategySignal) -> bool:
        if self.config.global_cooldown_seconds <= 0:
            return True
        previous = self._last_global_entry
        if previous is None:
            return True
        previous_market_id, previous_generated_at = previous
        if previous_market_id == signal.market_id:
            return True
        elapsed_seconds = (signal.generated_at - previous_generated_at).total_seconds()
        return elapsed_seconds >= self.config.global_cooldown_seconds

    def _passes_failure_cooldown(
        self,
        *,
        signal: StrategySignal,
        context: Mapping[str, object],
    ) -> bool:
        if self.config.failure_cooldown_seconds <= 0:
            return True
        failure = self._recent_failure(signal=signal, context=context)
        if failure is None:
            return True
        elapsed_seconds = (signal.generated_at - failure.occurred_at).total_seconds()
        if elapsed_seconds >= self.config.failure_cooldown_seconds:
            return True
        if failure.edge_bps is None:
            return False
        edge_improvement_bps = signal.edge_bps - failure.edge_bps
        return edge_improvement_bps >= self.config.failure_reentry_edge_improvement_bps

    def _recent_failure(
        self,
        *,
        signal: StrategySignal,
        context: Mapping[str, object],
    ) -> _RecentFailureState | None:
        for event in reversed(recent_runtime_events(context)):
            event_type = str(event.get("event_type", "")).strip()
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                continue
            if str(payload.get("market_id", "")).strip() != signal.market_id:
                continue
            if str(payload.get("strategy_id", "")).strip() not in {"", self.strategy_id}:
                continue
            if not _is_failure_event(event_type=event_type, payload=payload):
                continue
            occurred_at = parse_datetime(payload, "updated_at", "created_at", "generated_at")
            if occurred_at is None or occurred_at > signal.generated_at:
                continue
            return _RecentFailureState(
                occurred_at=occurred_at,
                edge_bps=parse_float(payload, "signal_edge_bps", "edge_bps"),
                event_type=event_type,
                reason=str(payload.get("reason", "")).strip() or None,
            )
        return None


def _maker_buy_price(
    *,
    best_bid: float | None,
    best_ask: float | None,
    fair_probability: float,
    min_spread_bps: float,
) -> float:
    if best_ask is None:
        raise ValueError("best_ask is required for maker quotes")
    if best_bid is None:
        return min(best_ask, max(0.01, fair_probability - (min_spread_bps / 10000)))

    capture_buffer = min_spread_bps / 10000
    target_price = max(best_bid + _INSIDE_TICK, fair_probability - capture_buffer)
    return min(best_ask, max(0.01, target_price))


def _spread_bps(best_bid: float | None, best_ask: float | None) -> float:
    if best_bid is None or best_ask is None:
        return 0.0
    return max(0.0, (best_ask - best_bid) * 10000)


def _is_failure_event(*, event_type: str, payload: Mapping[str, Any]) -> bool:
    if event_type == "order.expired":
        return True
    if event_type == "order.canceled":
        return str(payload.get("reason", "")).strip() == "open_order_replaced"
    if event_type == "order.rejected":
        reason = str(payload.get("reason", "")).strip()
        return reason not in {
            "",
            "daily order hard limit reached",
            "daily order soft limit reached",
        }
    return False
