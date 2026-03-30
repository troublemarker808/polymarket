"""Family-aware configuration overrides for crypto Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

from pm_bot.core.types import MarketSnapshot

if TYPE_CHECKING:
    from pm_bot.strategies.crypto.phase2.strategy import CryptoPhase2Config


@dataclass(slots=True, frozen=True)
class CryptoPhase2ResolvedConfig:
    preset_name: str
    min_confidence: float
    min_net_edge_bps: float
    max_spread_bps: float
    min_liquidity_score: float
    min_contract_price: float
    taker_urgency_threshold: float
    maker_min_edge_bps: float
    resolution_maker_min_edge_bps: float
    high_edge_taker_min_edge_bps: float
    high_edge_taker_max_spread_bps: float
    taker_max_entry_premium_bps: float
    taker_time_in_force: str
    maker_quote_ttl_seconds: int
    resolution_maker_quote_ttl_seconds: int
    maker_aggressiveness: float
    default_notional: float
    exit_edge_bps: float
    stop_loss_bps: float
    execution_max_holding_seconds: float | None
    min_holding_seconds_before_exit: float
    aging_exit_edge_bps: float
    stale_exit_edge_bps: float
    aging_start_fraction: float
    stale_start_fraction: float
    stop_loss_min_ticks: int
    stop_loss_max_remaining_edge_bps: float
    adverse_fill_exit_bps: float
    adverse_fill_max_remaining_edge_bps: float
    max_holding_multiplier: float
    exit_repost_cooldown_seconds: float
    entry_repost_cooldown_seconds: float
    entry_failure_cooldown_seconds: float
    exit_failure_cooldown_seconds: float
    time_stop_force_ioc_after_expiries: int
    thesis_entry_cooldown_seconds: float
    single_active_market_per_thesis: bool
    max_no_fill_entry_attempts_per_market: int


@dataclass(slots=True, frozen=True)
class CryptoPhase2PresetRule:
    name: str
    underlying: str | None
    event_family: str | None
    overrides: dict[str, object]


def build_phase2_preset_rules(config: dict[str, Any]) -> tuple[CryptoPhase2PresetRule, ...]:
    raw_registry = config.get("preset_registry", {})
    if not isinstance(raw_registry, dict):
        return ()
    rules: list[CryptoPhase2PresetRule] = []
    for name, payload in raw_registry.items():
        if not isinstance(name, str) or not isinstance(payload, dict):
            continue
        match = payload.get("match", {})
        overrides = payload.get("overrides", {})
        if not isinstance(match, dict) or not isinstance(overrides, dict):
            continue
        rules.append(
            CryptoPhase2PresetRule(
                name=name,
                underlying=(
                    str(match["underlying"]).upper()
                    if match.get("underlying") not in (None, "")
                    else None
                ),
                event_family=(
                    str(match["event_family"]).lower()
                    if match.get("event_family") not in (None, "")
                    else None
                ),
                overrides=dict(overrides),
            )
        )
    return tuple(rules)


def resolve_phase2_config_for_snapshot(
    *,
    base: "CryptoPhase2Config",
    snapshot: MarketSnapshot,
) -> CryptoPhase2ResolvedConfig:
    preset_name = "default"
    resolved = _base_resolved_config(base)
    underlying = _infer_underlying(snapshot)
    event_family = _infer_event_family(snapshot)
    for rule in base.preset_rules:
        if rule.underlying is not None and rule.underlying != underlying:
            continue
        if rule.event_family is not None and rule.event_family != event_family:
            continue
        preset_name = rule.name
        resolved = _apply_overrides(resolved, rule.overrides, preset_name)
        break
    return resolved


def _base_resolved_config(base: "CryptoPhase2Config") -> CryptoPhase2ResolvedConfig:
    return CryptoPhase2ResolvedConfig(
        preset_name="default",
        min_confidence=base.min_confidence,
        min_net_edge_bps=base.min_net_edge_bps,
        max_spread_bps=base.max_spread_bps,
        min_liquidity_score=base.min_liquidity_score,
        min_contract_price=base.min_contract_price,
        taker_urgency_threshold=base.taker_urgency_threshold,
        maker_min_edge_bps=base.maker_min_edge_bps,
        resolution_maker_min_edge_bps=base.resolution_maker_min_edge_bps,
        high_edge_taker_min_edge_bps=base.high_edge_taker_min_edge_bps,
        high_edge_taker_max_spread_bps=base.high_edge_taker_max_spread_bps,
        taker_max_entry_premium_bps=base.taker_max_entry_premium_bps,
        taker_time_in_force=base.taker_time_in_force,
        maker_quote_ttl_seconds=base.maker_quote_ttl_seconds,
        resolution_maker_quote_ttl_seconds=base.resolution_maker_quote_ttl_seconds,
        maker_aggressiveness=base.maker_aggressiveness,
        default_notional=base.default_notional,
        exit_edge_bps=base.exit_edge_bps,
        stop_loss_bps=base.stop_loss_bps,
        execution_max_holding_seconds=base.execution_max_holding_seconds,
        min_holding_seconds_before_exit=base.min_holding_seconds_before_exit,
        aging_exit_edge_bps=base.aging_exit_edge_bps,
        stale_exit_edge_bps=base.stale_exit_edge_bps,
        aging_start_fraction=base.aging_start_fraction,
        stale_start_fraction=base.stale_start_fraction,
        stop_loss_min_ticks=base.stop_loss_min_ticks,
        stop_loss_max_remaining_edge_bps=base.stop_loss_max_remaining_edge_bps,
        adverse_fill_exit_bps=base.adverse_fill_exit_bps,
        adverse_fill_max_remaining_edge_bps=base.adverse_fill_max_remaining_edge_bps,
        max_holding_multiplier=base.max_holding_multiplier,
        exit_repost_cooldown_seconds=base.exit_repost_cooldown_seconds,
        entry_repost_cooldown_seconds=base.entry_repost_cooldown_seconds,
        entry_failure_cooldown_seconds=base.entry_failure_cooldown_seconds,
        exit_failure_cooldown_seconds=base.exit_failure_cooldown_seconds,
        time_stop_force_ioc_after_expiries=base.time_stop_force_ioc_after_expiries,
        thesis_entry_cooldown_seconds=base.thesis_entry_cooldown_seconds,
        single_active_market_per_thesis=base.single_active_market_per_thesis,
        max_no_fill_entry_attempts_per_market=base.max_no_fill_entry_attempts_per_market,
    )


def _apply_overrides(
    resolved: CryptoPhase2ResolvedConfig,
    overrides: dict[str, object],
    preset_name: str,
) -> CryptoPhase2ResolvedConfig:
    allowed: dict[str, Any] = {"preset_name": preset_name}
    for field_name in resolved.__dataclass_fields__:
        if field_name == "preset_name":
            continue
        if field_name not in overrides:
            continue
        raw_value = overrides[field_name]
        if field_name in {
            "maker_quote_ttl_seconds",
            "resolution_maker_quote_ttl_seconds",
            "stop_loss_min_ticks",
            "time_stop_force_ioc_after_expiries",
            "max_no_fill_entry_attempts_per_market",
        }:
            allowed[field_name] = int(cast(Any, raw_value))
        elif field_name == "taker_time_in_force":
            allowed[field_name] = str(cast(Any, raw_value)).upper()
        elif field_name == "single_active_market_per_thesis":
            allowed[field_name] = bool(cast(Any, raw_value))
        elif field_name == "execution_max_holding_seconds":
            allowed[field_name] = None if raw_value in (None, "") else float(cast(Any, raw_value))
        else:
            allowed[field_name] = float(cast(Any, raw_value))
    return replace(resolved, **cast(Any, allowed))


def _infer_underlying(snapshot: MarketSnapshot) -> str | None:
    for key in ("underlying", "asset", "base_asset"):
        raw_value = snapshot.metadata.get(key)
        if isinstance(raw_value, str) and raw_value:
            return raw_value.upper()
    slug = snapshot.slug.upper()
    if "BTC" in slug:
        return "BTC"
    if "ETH" in slug:
        return "ETH"
    market_id = snapshot.market_id.upper()
    if "BTC" in market_id:
        return "BTC"
    if "ETH" in market_id:
        return "ETH"
    return None


def _infer_event_family(snapshot: MarketSnapshot) -> str | None:
    for key in ("event_family", "ladder_family"):
        raw_value = snapshot.metadata.get(key)
        if isinstance(raw_value, str) and raw_value:
            return raw_value.lower()
    slug = snapshot.slug.lower()
    if "reach" in slug:
        return "reach"
    if "dip" in slug:
        return "dip"
    market_id = snapshot.market_id.lower()
    if "reach" in market_id:
        return "reach"
    if "dip" in market_id:
        return "dip"
    return None
