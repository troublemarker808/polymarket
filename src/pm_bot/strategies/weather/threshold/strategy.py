"""Weather threshold-strip strategy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PositionState
from pm_bot.strategies.common import (
    current_position,
    dashboard_state,
    has_pending_order,
    implied_yes_probability,
    parse_float,
)
from pm_bot.strategies.weather.config_registry import (
    WeatherResolvedConfig,
    build_weather_preset_rules,
    resolve_weather_config_for_snapshot,
)


class WeatherThresholdConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_strip_inconsistency_bps = float(config.get("min_strip_inconsistency_bps", 300))
        self.use_official_forecast_inside_hours = int(config.get("use_official_forecast_inside_hours", 48))
        self.preset_rules = build_weather_preset_rules(dict(config))

    def resolve(self, snapshot: MarketSnapshot) -> WeatherResolvedConfig:
        return resolve_weather_config_for_snapshot(
            base=WeatherResolvedConfig(
                preset_name="default",
                min_strip_inconsistency_bps=self.min_strip_inconsistency_bps,
                use_official_forecast_inside_hours=self.use_official_forecast_inside_hours,
            ),
            preset_rules=self.preset_rules,
            snapshot=snapshot,
            mode="threshold",
        )


class WeatherThresholdStrategy:
    strategy_id = "weather.threshold"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = WeatherThresholdConfig(config)

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

        peers = self._series_peers(snapshot=snapshot, context=context)
        ranked_peers = self._ranked_peers(peers)
        current_index = next(
            (index for index, peer in enumerate(ranked_peers) if peer.market_id == snapshot.market_id),
            None,
        )
        if current_index is None:
            return []

        direction = self._monotonic_direction(snapshot)
        if direction is None:
            return []

        current_probability = implied_yes_probability(snapshot)
        if current_probability is None:
            return []
        resolved = self.config.resolve(snapshot)

        lower_bound, upper_bound = monotonic_bounds(
            ranked_peers=ranked_peers,
            current_index=current_index,
            direction=direction,
        )
        fair_probability = project_fair_probability(
            current_probability=current_probability,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        forecast_probability = self._forecast_anchor(
            snapshot=snapshot,
            direction=direction,
            use_official_forecast_inside_hours=int(resolved.use_official_forecast_inside_hours or 0),
        )
        if fair_probability is None:
            fair_probability = forecast_probability
        elif forecast_probability is not None:
            if forecast_probability >= 0.5:
                fair_probability = max(fair_probability, forecast_probability)
            else:
                fair_probability = min(fair_probability, forecast_probability)

        if fair_probability is None:
            return []

        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=position,
                resolved=resolved,
            )
            return [exit_signal] if exit_signal is not None else []

        return self._entry_signals(
            snapshot=snapshot,
            fair_probability=fair_probability,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            forecast_probability=forecast_probability,
            resolved=resolved,
        )

    def _series_peers(
        self,
        *,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> list[MarketSnapshot]:
        raw_snapshots = context.get("snapshot_cache")
        if not isinstance(raw_snapshots, tuple):
            return [snapshot]

        series_key = (
            snapshot.metadata.get("event_slug")
            or snapshot.metadata.get("series_key")
            or snapshot.metadata.get("location_date_key")
        )
        if not series_key:
            return [snapshot]

        return [
            peer
            for peer in raw_snapshots
            if isinstance(peer, MarketSnapshot)
            and peer.category == Category.WEATHER
            and (
                peer.metadata.get("event_slug")
                or peer.metadata.get("series_key")
                or peer.metadata.get("location_date_key")
            ) == series_key
        ]

    def _ranked_peers(self, peers: Sequence[MarketSnapshot]) -> list[MarketSnapshot]:
        return sorted(
            peers,
            key=lambda peer: (
                parse_numeric_threshold(peer.metadata.get("group_item_threshold", "")) or 1_000_000.0,
                peer.market_id,
            ),
        )

    def _monotonic_direction(self, snapshot: MarketSnapshot) -> int | None:
        combined = " ".join(
            (
                snapshot.metadata.get("question", "").lower(),
                snapshot.slug.lower(),
                snapshot.metadata.get("event_title", "").lower(),
            )
        )
        if any(token in combined for token in ("above", "over", "hotter", "greater-than")):
            return -1
        if any(token in combined for token in ("below", "under", "colder", "less-than")):
            return 1
        return None

    def _forecast_anchor(
        self,
        *,
        snapshot: MarketSnapshot,
        direction: int,
        use_official_forecast_inside_hours: int,
    ) -> float | None:
        if snapshot.resolution_time is None:
            return None
        hours_to_resolution = (snapshot.resolution_time - snapshot.timestamp).total_seconds() / 3600
        if hours_to_resolution > use_official_forecast_inside_hours:
            return None

        official_forecast = parse_float(snapshot.metadata, "official_forecast_value", "forecast_value")
        threshold = parse_float(snapshot.metadata, "group_item_threshold", "threshold")
        if official_forecast is None or threshold is None:
            return None

        if direction < 0:
            return 0.6 if official_forecast >= threshold else 0.4
        return 0.6 if official_forecast <= threshold else 0.4

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        lower_bound: float | None,
        upper_bound: float | None,
        forecast_probability: float | None,
        resolved: WeatherResolvedConfig,
    ) -> list[StrategySignal]:
        confidence = 0.6
        if lower_bound is not None and upper_bound is not None:
            confidence = 0.74
        elif forecast_probability is not None:
            confidence = 0.68

        if snapshot.best_ask_yes is not None:
            buy_yes_edge_bps = (fair_probability - snapshot.best_ask_yes) * 10000
            if buy_yes_edge_bps >= float(resolved.min_strip_inconsistency_bps or 0.0):
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.WEATHER,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_YES,
                        confidence=confidence,
                        edge_bps=buy_yes_edge_bps,
                        generated_at=snapshot.timestamp,
                        rationale_tags=("weather_threshold", "strip_inconsistency"),
                        diagnostics={"weather_preset": resolved.preset_name},
                    )
                ]

        if snapshot.best_bid_yes is not None:
            buy_no_edge_bps = (snapshot.best_bid_yes - fair_probability) * 10000
            if buy_no_edge_bps >= float(resolved.min_strip_inconsistency_bps or 0.0):
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.WEATHER,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_NO,
                        confidence=confidence,
                        edge_bps=buy_no_edge_bps,
                        generated_at=snapshot.timestamp,
                        rationale_tags=("weather_threshold", "strip_inconsistency"),
                        diagnostics={"weather_preset": resolved.preset_name},
                    )
                ]

        return []

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        position: PositionState,
        resolved: WeatherResolvedConfig,
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
        if edge_remaining_bps > (float(resolved.min_strip_inconsistency_bps or 0.0) / 2):
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
            rationale_tags=("weather_threshold_exit", "edge_normalized"),
            diagnostics={"weather_preset": resolved.preset_name},
        )


def monotonic_bounds(
    *,
    ranked_peers: Sequence[MarketSnapshot],
    current_index: int,
    direction: int,
) -> tuple[float | None, float | None]:
    probabilities = [implied_yes_probability(peer) for peer in ranked_peers]
    current_probability = probabilities[current_index]
    if current_probability is None:
        return (None, None)

    previous = [prob for prob in probabilities[:current_index] if prob is not None]
    following = [prob for prob in probabilities[current_index + 1 :] if prob is not None]

    if direction > 0:
        lower_bound = previous[-1] if previous else None
        upper_bound = following[0] if following else None
    else:
        lower_bound = following[0] if following else None
        upper_bound = previous[-1] if previous else None

    return (lower_bound, upper_bound)


def project_fair_probability(
    *,
    current_probability: float,
    lower_bound: float | None,
    upper_bound: float | None,
) -> float | None:
    if lower_bound is not None and upper_bound is not None and lower_bound > upper_bound:
        return None
    if lower_bound is not None and current_probability < lower_bound:
        return lower_bound
    if upper_bound is not None and current_probability > upper_bound:
        return upper_bound
    return None


def parse_numeric_threshold(raw_value: str) -> float | None:
    try:
        return float(raw_value)
    except ValueError:
        return None
