from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import Category


def test_load_research_crypto_phase1_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/research-crypto-phase1-v1")

    assert settings.categories.enabled_categories() == (Category.CRYPTO,)
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.surface", "crypto.maker")


def test_load_research_sports_phase1_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/research-sports-phase1-v1")

    assert settings.categories.enabled_categories() == (Category.SPORTS,)
    assert settings.category_configs[Category.SPORTS].enabled_strategies == ("sports.anchor",)


def test_load_research_weather_phase1_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/research-weather-phase1-v1")

    assert settings.categories.enabled_categories() == (Category.WEATHER,)
    assert settings.category_configs[Category.WEATHER].enabled_strategies == (
        "weather.ensemble",
        "weather.threshold",
    )


def test_load_research_crypto_phase2_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/research-crypto-phase2-v1")

    assert settings.categories.enabled_categories() == (Category.CRYPTO,)
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.phase2",)


def test_load_paper_crypto_phase2_profile() -> None:
    settings = load_settings_from_directory("configs/profiles/paper-crypto-phase2-v1")

    assert settings.categories.enabled_categories() == (Category.CRYPTO,)
    assert settings.app.mode.value == "paper"
    assert settings.category_configs[Category.CRYPTO].enabled_strategies == ("crypto.phase2",)
