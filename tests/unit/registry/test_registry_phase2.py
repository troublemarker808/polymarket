from pm_bot.core.settings import BotSettings
from pm_bot.core.types import Category
from pm_bot.registry import build_default_registry


def test_default_registry_builds_crypto_phase2_strategy() -> None:
    registry = build_default_registry()
    settings = BotSettings.model_validate(
        {
            "app": {"environment": "test", "mode": "paper", "log_level": "INFO"},
            "categories": {"sports": False, "crypto": True, "weather": False},
            "trading": {"starting_equity": 1000.0},
            "risk": {"max_daily_drawdown_pct": 10.0, "max_consecutive_losses": 5, "max_open_orders": 5},
            "category_configs": {
                Category.CRYPTO: {
                    "category": "crypto",
                    "enabled_strategies": ["crypto.phase2"],
                    "strategy": {
                        "phase2": {
                            "min_confidence": 0.6,
                            "min_net_edge_bps": 75.0,
                        }
                    },
                }
            },
        }
    )

    strategies = registry.build_enabled(settings=settings)

    assert len(strategies) == 1
    assert strategies[0].strategy_id == "crypto.phase2"
