"""Strategy registry and builders."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pm_bot.core.interfaces import Strategy
from pm_bot.core.settings import BotSettings
from pm_bot.strategies.crypto.maker.strategy import CryptoMakerStrategy
from pm_bot.strategies.crypto.surface.strategy import CryptoSurfaceStrategy
from pm_bot.strategies.sports.anchor.strategy import SportsAnchorStrategy
from pm_bot.strategies.sports.live.strategy import SportsLiveStrategy
from pm_bot.strategies.weather.ensemble.strategy import WeatherEnsembleStrategy
from pm_bot.strategies.weather.threshold.strategy import WeatherThresholdStrategy

StrategyFactory = Callable[[Mapping[str, Any]], Strategy]


class StrategyRegistry:
    """Build enabled strategies from validated configuration."""

    def __init__(self) -> None:
        self._factories: dict[str, StrategyFactory] = {}

    def register(self, strategy_id: str, factory: StrategyFactory) -> None:
        self._factories[strategy_id] = factory

    def build_enabled(self, settings: BotSettings) -> list[Strategy]:
        built: list[Strategy] = []
        for category_config in settings.category_configs.values():
            for strategy_id in category_config.enabled_strategies:
                factory = self._factories.get(strategy_id)
                if factory is None:
                    raise KeyError(f"Strategy not registered: {strategy_id}")

                strategy_config = category_config.strategy.get(strategy_id.split(".")[-1], {})
                built.append(factory(strategy_config))

        return built


def build_default_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("sports.anchor", lambda config: SportsAnchorStrategy(config=config))
    registry.register("sports.live", lambda config: SportsLiveStrategy(config=config))
    registry.register("crypto.surface", lambda config: CryptoSurfaceStrategy(config=config))
    registry.register("crypto.maker", lambda config: CryptoMakerStrategy(config=config))
    registry.register("weather.ensemble", lambda config: WeatherEnsembleStrategy(config=config))
    registry.register("weather.threshold", lambda config: WeatherThresholdStrategy(config=config))
    return registry

