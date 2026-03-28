"""Weather ensemble strategy using model-consensus pricing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PositionState
from pm_bot.strategies.common import (
    clamp_probability,
    current_position,
    dashboard_state,
    has_pending_order,
    parse_float_list,
    parse_probability,
    parse_string_list,
)


class WeatherEnsembleConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_edge_bps = float(config.get("min_edge_bps", 400))
        self.model_runs_utc = tuple(str(value) for value in config.get("model_runs_utc", ()))


class WeatherEnsembleStrategy:
    strategy_id = "weather.ensemble"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = WeatherEnsembleConfig(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.WEATHER:
            return []

        dashboard = dashboard_state(context)
        if has_pending_order(snapshot=snapshot, dashboard=dashboard):
            return []

        fair_probability, model_count = _ensemble_probability(snapshot.metadata)
        if fair_probability is None:
            return []

        allowed_runs = self.config.model_runs_utc
        if allowed_runs:
            reported_runs = parse_string_list(snapshot.metadata, "model_runs_utc", "forecast_run_utc")
            if reported_runs and not set(reported_runs).intersection(allowed_runs):
                return []

        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=position,
            )
            return [exit_signal] if exit_signal is not None else []

        return self._entry_signals(
            snapshot=snapshot,
            fair_probability=fair_probability,
            model_count=model_count,
        )

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        model_count: int,
    ) -> list[StrategySignal]:
        confidence = 0.58 + min(model_count, 5) * 0.04
        if snapshot.best_ask_yes is not None:
            buy_yes_edge_bps = (fair_probability - snapshot.best_ask_yes) * 10000
            if buy_yes_edge_bps >= self.config.min_edge_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.WEATHER,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_YES,
                        confidence=min(confidence, 0.8),
                        edge_bps=buy_yes_edge_bps,
                        generated_at=snapshot.timestamp,
                        rationale_tags=("weather_ensemble", f"models_{model_count}"),
                    )
                ]

        if snapshot.best_bid_yes is not None:
            buy_no_edge_bps = (snapshot.best_bid_yes - fair_probability) * 10000
            if buy_no_edge_bps >= self.config.min_edge_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.WEATHER,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_NO,
                        confidence=min(confidence, 0.8),
                        edge_bps=buy_no_edge_bps,
                        generated_at=snapshot.timestamp,
                        rationale_tags=("weather_ensemble", f"models_{model_count}"),
                    )
                ]

        return []

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        position: PositionState,
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
        if edge_remaining_bps > (self.config.min_edge_bps / 2):
            return None

        shares = position.shares or 0.0
        target_notional = shares * exit_price
        if target_notional <= 0:
            return None

        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.WEATHER,
            market_id=snapshot.market_id,
            token_id=position.token_id,
            fair_probability=fair_probability,
            side=side,
            confidence=0.65,
            edge_bps=max(0.0, edge_remaining_bps),
            generated_at=snapshot.timestamp,
            target_price=exit_price,
            target_size=target_notional,
            rationale_tags=("weather_ensemble_exit", "edge_normalized"),
        )


def _ensemble_probability(metadata: Mapping[str, Any]) -> tuple[float | None, int]:
    probabilities = parse_float_list(
        metadata,
        "ensemble_probabilities",
        "model_yes_probabilities",
        "forecast_probabilities",
    )
    if probabilities:
        normalized = tuple(
            clamp_probability(value / 100 if value > 1 else value)
            for value in probabilities
        )
        return (sum(normalized) / len(normalized), len(normalized))

    direct_probability = parse_probability(
        metadata,
        "ensemble_yes_probability",
        "consensus_yes_probability",
        "fair_yes_probability",
    )
    if direct_probability is None:
        return (None, 0)
    return (direct_probability, 1)
