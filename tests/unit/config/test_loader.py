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


def test_load_settings_from_directory_prefers_local_base_override(tmp_path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "base.example.toml").write_text(
        "\n".join(
            [
                "[app]",
                'environment = "dev"',
                'mode = "paper"',
                "",
                "[categories]",
                "sports = true",
                "crypto = false",
                "weather = false",
                "",
                "[trading]",
                "starting_equity = 100.0",
                "",
                "[risk]",
                "max_daily_drawdown_pct = 5.0",
                "max_consecutive_losses = 5",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "base.local.toml").write_text(
        "\n".join(
            [
                "[app]",
                'environment = "dev"',
                'mode = "live"',
                "",
                "[categories]",
                "sports = true",
                "crypto = false",
                "weather = false",
                "",
                "[trading]",
                "starting_equity = 100.0",
                "",
                "[risk]",
                "max_daily_drawdown_pct = 5.0",
                "max_consecutive_losses = 5",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "sports.v1.example.toml").write_text(
        "\n".join(
            [
                'category = "sports"',
                'enabled_strategies = ["sports.anchor"]',
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings_from_directory(config_dir)

    assert settings.app.mode.value == "live"


def test_load_settings_from_small_live_baseline_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/small-live-baseline-v1")

    assert settings.app.mode.value == "live"
    assert settings.polymarket.allow_live_orders is True
    assert settings.polymarket.derive_api_creds_if_missing is True
    assert settings.polymarket.live_recovery_scope == "session"
    assert settings.trading.default_order_notional == 1.1
    assert settings.trading.max_notional_per_market == 1.1
    assert settings.trading.max_concurrent_positions == 3
    assert settings.trading.daily_order_hard_limit == 120
    assert settings.risk.max_daily_drawdown_pct == 40.0
    assert settings.risk.max_consecutive_losses == 40
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.execution_sample",)


def test_load_settings_from_paper_sample_acquisition_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/paper-sample-acquisition-v1")

    assert settings.app.mode.value == "paper"
    assert settings.polymarket.allow_live_orders is False
    assert settings.trading.default_order_notional == 1.1
    assert settings.trading.default_quote_ttl_seconds == 20
    assert settings.trading.paper_taker_slippage_bps == 20.0
    assert settings.trading.max_notional_per_market == 1.1
    assert settings.trading.max_notional_per_category == 3.3
    assert settings.trading.max_concurrent_positions == 3
    assert settings.risk.max_open_orders == 5
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.execution_sample",)


def test_load_settings_from_sync_normal_shadow_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/sync-normal-shadow-v1")

    assert settings.app.mode.value == "live"
    assert settings.polymarket.allow_live_orders is True
    assert settings.polymarket.live_recovery_scope == "session"
    assert settings.trading.default_order_notional == 1.1
    assert settings.trading.paper_taker_slippage_bps == 20.0
    assert settings.trading.max_concurrent_positions == 3
    assert settings.risk.max_consecutive_losses == 40
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.surface",)


def test_load_settings_from_paper_normal_observation_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/paper-normal-observation-v1")

    assert settings.app.mode.value == "paper"
    assert settings.trading.starting_equity == 1000.0
    assert settings.trading.daily_order_soft_limit == 200
    assert settings.trading.daily_order_hard_limit == 1000
    assert settings.risk.max_daily_drawdown_pct == 40.0
    assert settings.risk.max_consecutive_losses == 40
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.surface", "crypto.maker")
