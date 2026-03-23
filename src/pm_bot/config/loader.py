"""Load and validate layered configuration files."""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from pm_bot.core.settings import BotSettings, CategoryRuntimeConfig
from pm_bot.core.types import Category


def load_config_file(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)

    if config_path.suffix == ".toml":
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    elif config_path.suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "YAML config support requires PyYAML. Prefer .toml configs in this repository."
            ) from exc

        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    return data


def load_settings(
    base_config_path: str | Path,
    category_config_paths: list[str | Path],
) -> BotSettings:
    base_raw = load_config_file(base_config_path)
    settings = BotSettings.model_validate({**base_raw, "category_configs": {}})

    category_configs: dict[Category, CategoryRuntimeConfig] = {}
    for config_path in category_config_paths:
        category_raw = load_config_file(config_path)
        category_config = CategoryRuntimeConfig.model_validate(category_raw)
        category_configs[category_config.category] = category_config

    enabled = set(settings.categories.enabled_categories())
    missing = enabled.difference(category_configs)
    if missing:
        missing_names = ", ".join(sorted(category.value for category in missing))
        raise ValueError(f"Missing category configs for enabled categories: {missing_names}")

    settings.category_configs = category_configs
    return settings


def load_settings_from_directory(config_dir: str | Path) -> BotSettings:
    config_root = Path(config_dir)
    base_config_path = config_root / "base.example.toml"
    category_config_paths = sorted(config_root.glob("*.v1.example.toml"))
    return load_settings(base_config_path=base_config_path, category_config_paths=category_config_paths)
