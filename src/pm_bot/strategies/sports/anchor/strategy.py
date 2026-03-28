"""Sports pregame fair-value anchor strategy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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


class SportsAnchorConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_edge_bps = float(config.get("min_edge_bps", 300))
        self.max_time_to_start_minutes = int(config.get("max_time_to_start_minutes", 1440))
        self.cancel_before_start_minutes = int(config.get("cancel_before_start_minutes", 5))


class SportsAnchorStrategy:
    strategy_id = "sports.anchor"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = SportsAnchorConfig(config)

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
            "model_yes_probability",
            "consensus_yes_probability",
            "fair_yes_probability",
            "pregame_yes_probability",
        )
        if fair_probability is None:
            return []

        start_time = parse_datetime(
            snapshot.metadata,
            "start_time",
            "starts_at",
            "event_start",
            "scheduled_start",
        ) or snapshot.resolution_time
        if start_time is None:
            return []

        minutes_to_start = (start_time - snapshot.timestamp).total_seconds() / 60
        if minutes_to_start <= 0:
            return []

        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=position,
                force_exit=minutes_to_start <= self.config.cancel_before_start_minutes,
            )
            return [exit_signal] if exit_signal is not None else []

        if minutes_to_start > self.config.max_time_to_start_minutes:
            return []

        return self._entry_signals(
            snapshot=snapshot,
            fair_probability=fair_probability,
            minutes_to_start=minutes_to_start,
        )

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        minutes_to_start: float,
    ) -> list[StrategySignal]:
        confidence = _confidence(minutes_to_start=minutes_to_start)
        if snapshot.best_ask_yes is not None:
            buy_yes_edge_bps = (fair_probability - snapshot.best_ask_yes) * 10000
            if buy_yes_edge_bps >= self.config.min_edge_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.SPORTS,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_YES,
                        confidence=confidence,
                        edge_bps=buy_yes_edge_bps,
                        generated_at=snapshot.timestamp,
                        rationale_tags=("sports_anchor", "pregame_model"),
                    )
                ]

        if snapshot.best_bid_yes is not None:
            buy_no_edge_bps = (snapshot.best_bid_yes - fair_probability) * 10000
            if buy_no_edge_bps >= self.config.min_edge_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.SPORTS,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_NO,
                        confidence=confidence,
                        edge_bps=buy_no_edge_bps,
                        generated_at=snapshot.timestamp,
                        rationale_tags=("sports_anchor", "pregame_model"),
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
        if not force_exit and edge_remaining_bps > (self.config.min_edge_bps / 2):
            return None

        shares = position.shares or 0.0
        target_notional = shares * exit_price
        if target_notional <= 0:
            return None

        rationale = "pregame_closeout" if force_exit else "edge_normalized"
        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.SPORTS,
            market_id=snapshot.market_id,
            token_id=position.token_id,
            fair_probability=fair_probability,
            side=side,
            confidence=0.65,
            edge_bps=max(0.0, edge_remaining_bps),
            generated_at=snapshot.timestamp,
            target_price=exit_price,
            target_size=target_notional,
            rationale_tags=("sports_anchor_exit", rationale),
        )


def _confidence(*, minutes_to_start: float) -> float:
    if minutes_to_start <= 60:
        return 0.75
    if minutes_to_start <= 360:
        return 0.68
    return 0.6
