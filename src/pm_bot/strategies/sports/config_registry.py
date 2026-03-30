"""League and market-family specific strategy presets for sports."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, cast

from pm_bot.core.types import MarketSnapshot


@dataclass(slots=True, frozen=True)
class SportsResolvedConfig:
    preset_name: str
    min_edge_bps: float
    max_time_to_start_minutes: int | None = None
    cancel_before_start_minutes: int | None = None
    stale_state_seconds: int | None = None
    allow_maker_quotes: bool | None = None


@dataclass(slots=True, frozen=True)
class SportsPresetRule:
    name: str
    league: str | None
    market_family: str | None
    mode: str | None
    overrides: dict[str, object]


def build_sports_preset_rules(config: dict[str, Any]) -> tuple[SportsPresetRule, ...]:
    raw_registry = config.get("preset_registry", {})
    if not isinstance(raw_registry, dict):
        return ()
    rules: list[SportsPresetRule] = []
    for name, payload in raw_registry.items():
        if not isinstance(name, str) or not isinstance(payload, dict):
            continue
        match = payload.get("match", {})
        overrides = payload.get("overrides", {})
        if not isinstance(match, dict) or not isinstance(overrides, dict):
            continue
        rules.append(
            SportsPresetRule(
                name=name,
                league=str(match.get("league", "")).strip().lower() or None,
                market_family=str(match.get("market_family", "")).strip().lower() or None,
                mode=str(match.get("mode", "")).strip().lower() or None,
                overrides=dict(overrides),
            )
        )
    return tuple(rules)


def resolve_sports_config_for_snapshot(
    *,
    base: SportsResolvedConfig,
    preset_rules: tuple[SportsPresetRule, ...],
    snapshot: MarketSnapshot,
    mode: str,
) -> SportsResolvedConfig:
    league = str(snapshot.metadata.get("league", snapshot.metadata.get("sport", ""))).strip().lower() or None
    market_family = str(snapshot.metadata.get("market_family", "")).strip().lower() or None
    resolved = base
    for rule in preset_rules:
        if rule.mode is not None and rule.mode != mode:
            continue
        if rule.league is not None and rule.league != league:
            continue
        if rule.market_family is not None and rule.market_family != market_family:
            continue
        resolved = _apply_overrides(resolved, rule.overrides, rule.name)
        break
    return resolved


def _apply_overrides(
    resolved: SportsResolvedConfig,
    overrides: dict[str, object],
    preset_name: str,
) -> SportsResolvedConfig:
    allowed: dict[str, Any] = {"preset_name": preset_name}
    for field_name in resolved.__dataclass_fields__:
        if field_name == "preset_name" or field_name not in overrides:
            continue
        raw_value = overrides[field_name]
        if field_name in {"max_time_to_start_minutes", "cancel_before_start_minutes", "stale_state_seconds"}:
            allowed[field_name] = None if raw_value in (None, "") else int(cast(Any, raw_value))
        elif field_name == "allow_maker_quotes":
            allowed[field_name] = bool(raw_value)
        else:
            allowed[field_name] = float(cast(Any, raw_value))
    return replace(resolved, **cast(Any, allowed))
