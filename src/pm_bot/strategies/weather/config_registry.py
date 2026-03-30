"""Event-family and settlement specific strategy presets for weather."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, cast

from pm_bot.core.types import MarketSnapshot


@dataclass(slots=True, frozen=True)
class WeatherResolvedConfig:
    preset_name: str
    min_edge_bps: float | None = None
    min_strip_inconsistency_bps: float | None = None
    use_official_forecast_inside_hours: int | None = None
    model_runs_utc: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class WeatherPresetRule:
    name: str
    event_family: str | None
    settlement_source: str | None
    mode: str | None
    overrides: dict[str, object]


def build_weather_preset_rules(config: dict[str, Any]) -> tuple[WeatherPresetRule, ...]:
    raw_registry = config.get("preset_registry", {})
    if not isinstance(raw_registry, dict):
        return ()
    rules: list[WeatherPresetRule] = []
    for name, payload in raw_registry.items():
        if not isinstance(name, str) or not isinstance(payload, dict):
            continue
        match = payload.get("match", {})
        overrides = payload.get("overrides", {})
        if not isinstance(match, dict) or not isinstance(overrides, dict):
            continue
        rules.append(
            WeatherPresetRule(
                name=name,
                event_family=str(match.get("event_family", "")).strip().lower() or None,
                settlement_source=str(match.get("settlement_source", "")).strip().lower() or None,
                mode=str(match.get("mode", "")).strip().lower() or None,
                overrides=dict(overrides),
            )
        )
    return tuple(rules)


def resolve_weather_config_for_snapshot(
    *,
    base: WeatherResolvedConfig,
    preset_rules: tuple[WeatherPresetRule, ...],
    snapshot: MarketSnapshot,
    mode: str,
) -> WeatherResolvedConfig:
    event_family = str(snapshot.metadata.get("event_family", "")).strip().lower() or None
    settlement_source = str(snapshot.metadata.get("settlement_source", "")).strip().lower() or None
    resolved = base
    for rule in preset_rules:
        if rule.mode is not None and rule.mode != mode:
            continue
        if rule.event_family is not None and rule.event_family != event_family:
            continue
        if rule.settlement_source is not None and rule.settlement_source != settlement_source:
            continue
        resolved = _apply_overrides(resolved, rule.overrides, rule.name)
        break
    return resolved


def _apply_overrides(
    resolved: WeatherResolvedConfig,
    overrides: dict[str, object],
    preset_name: str,
) -> WeatherResolvedConfig:
    allowed: dict[str, Any] = {"preset_name": preset_name}
    for field_name in resolved.__dataclass_fields__:
        if field_name == "preset_name" or field_name not in overrides:
            continue
        raw_value = overrides[field_name]
        if field_name == "model_runs_utc":
            if isinstance(raw_value, (list, tuple)):
                allowed[field_name] = tuple(str(item) for item in raw_value)
        elif field_name == "use_official_forecast_inside_hours":
            allowed[field_name] = None if raw_value in (None, "") else int(cast(Any, raw_value))
        else:
            allowed[field_name] = None if raw_value in (None, "") else float(cast(Any, raw_value))
    return replace(resolved, **cast(Any, allowed))
