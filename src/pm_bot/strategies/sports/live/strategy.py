"""Sports in-play strategy driven by fresh live state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PositionState
from pm_bot.strategies.common import (
    current_position,
    dashboard_state,
    has_pending_order,
    parse_datetime,
    parse_probability,
)

_INSIDE_TICK = 0.01


class SportsLiveConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_edge_bps = float(config.get("min_edge_bps", 500))
        self.stale_state_seconds = int(config.get("stale_state_seconds", 5))
        self.allow_maker_quotes = bool(config.get("allow_maker_quotes", False))


class SportsLiveStrategy:
    strategy_id = "sports.live"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = SportsLiveConfig(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.SPORTS:
            return []

        dashboard = dashboard_state(context)
        if has_pending_order(snapshot=snapshot, dashboard=dashboard):
            return []

        fair_probability = parse_probability(
            snapshot.metadata,
            "live_yes_probability",
            "live_model_yes_probability",
            "consensus_yes_probability",
        )
        if fair_probability is None:
            return []

        state_updated_at = parse_datetime(
            snapshot.metadata,
            "live_state_updated_at",
            "scoreboard_updated_at",
            "updated_at",
        ) or snapshot.timestamp
        if (snapshot.timestamp - state_updated_at).total_seconds() > self.config.stale_state_seconds:
            return []

        market_state = (
            snapshot.metadata.get("market_status")
            or snapshot.metadata.get("game_status")
            or snapshot.metadata.get("state")
            or ""
        ).lower()
        is_terminal = any(token in market_state for token in ("final", "closed", "settled"))

        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=position,
                force_exit=is_terminal,
            )
            return [exit_signal] if exit_signal is not None else []

        if is_terminal:
            return []

        return self._entry_signals(snapshot=snapshot, fair_probability=fair_probability)

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
    ) -> list[StrategySignal]:
        buy_yes_price = snapshot.best_ask_yes
        if self.config.allow_maker_quotes:
            buy_yes_price = _maker_buy_price(
                best_bid=snapshot.best_bid_yes,
                best_ask=snapshot.best_ask_yes,
                fair_probability=fair_probability,
                min_edge_bps=self.config.min_edge_bps,
            )
        if buy_yes_price is not None:
            buy_yes_edge_bps = (fair_probability - buy_yes_price) * 10000
            if buy_yes_edge_bps >= self.config.min_edge_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.SPORTS,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_YES,
                        confidence=0.75,
                        edge_bps=buy_yes_edge_bps,
                        generated_at=datetime.now(tz=timezone.utc),
                        target_price=buy_yes_price,
                        rationale_tags=("sports_live", "fresh_state"),
                    )
                ]

        buy_no_price = snapshot.best_ask_no
        if self.config.allow_maker_quotes:
            buy_no_price = _maker_buy_price(
                best_bid=snapshot.best_bid_no,
                best_ask=snapshot.best_ask_no,
                fair_probability=1 - fair_probability,
                min_edge_bps=self.config.min_edge_bps,
            )
        if buy_no_price is not None:
            buy_no_edge_bps = ((1 - fair_probability) - buy_no_price) * 10000
            if buy_no_edge_bps >= self.config.min_edge_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.SPORTS,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_NO,
                        confidence=0.75,
                        edge_bps=buy_no_edge_bps,
                        generated_at=datetime.now(tz=timezone.utc),
                        target_price=buy_no_price,
                        rationale_tags=("sports_live", "fresh_state"),
                    )
                ]

        return []

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        position: PositionState,
        force_exit: bool,
    ) -> StrategySignal | None:
        no_token_id = snapshot.metadata.get("no_token_id")
        if position.token_id == snapshot.token_id:
            if snapshot.best_bid_yes is None:
                return None
            exit_price = snapshot.best_bid_yes
            fair_exit_price = fair_probability
            side = SignalSide.SELL_YES
        elif no_token_id and position.token_id == no_token_id:
            if snapshot.best_bid_no is None:
                return None
            exit_price = snapshot.best_bid_no
            fair_exit_price = 1 - fair_probability
            side = SignalSide.SELL_NO
        else:
            return None

        edge_remaining_bps = (fair_exit_price - exit_price) * 10000
        if not force_exit and edge_remaining_bps > (self.config.min_edge_bps / 3):
            return None

        shares = position.shares or 0.0
        target_notional = shares * exit_price
        if target_notional <= 0:
            return None

        rationale = "market_closed" if force_exit else "live_edge_normalized"
        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.SPORTS,
            market_id=snapshot.market_id,
            token_id=position.token_id,
            fair_probability=fair_probability,
            side=side,
            confidence=0.7,
            edge_bps=max(0.0, edge_remaining_bps),
            generated_at=datetime.now(tz=timezone.utc),
            target_price=exit_price,
            target_size=target_notional,
            rationale_tags=("sports_live_exit", rationale),
        )


def _maker_buy_price(
    *,
    best_bid: float | None,
    best_ask: float | None,
    fair_probability: float,
    min_edge_bps: float,
) -> float | None:
    if best_ask is None:
        return None
    if best_bid is None:
        return min(best_ask, max(0.01, fair_probability - (min_edge_bps / 10000)))

    capture_buffer = min_edge_bps / 10000
    target_price = max(best_bid + _INSIDE_TICK, fair_probability - capture_buffer)
    return min(best_ask, max(0.01, target_price))
