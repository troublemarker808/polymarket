from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import Category


def test_load_settings_from_directory_loads_all_enabled_categories() -> None:
    settings = load_settings_from_directory("configs")

    assert settings.app.mode.value == "paper"
    assert Category.SPORTS in settings.category_configs
    assert Category.CRYPTO in settings.category_configs
    assert Category.WEATHER in settings.category_configs
    assert settings.trading.starting_equity == 100.0
    assert settings.trading.default_order_notional == 5.0
    assert settings.trading.daily_order_hard_limit == 15
    assert settings.risk.max_daily_drawdown_pct == 5.0
    assert settings.risk.max_consecutive_losses == 5
