from pm_bot.config.loader import load_settings_from_directory
from pm_bot.registry import build_default_registry


def test_default_registry_builds_all_v1_strategies() -> None:
    settings = load_settings_from_directory("configs")
    registry = build_default_registry()

    strategies = registry.build_enabled(settings=settings)

    assert len(strategies) == 6
    assert {strategy.strategy_id for strategy in strategies} == {
        "sports.anchor",
        "sports.live",
        "crypto.surface",
        "crypto.maker",
        "weather.ensemble",
        "weather.threshold",
    }

