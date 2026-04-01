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
    repricing_max_net_edge_bps: float
    taker_urgency_threshold: float
    maker_min_edge_bps: float
    resolution_maker_min_edge_bps: float
    high_edge_taker_min_edge_bps: float
    high_edge_taker_max_spread_bps: float
    taker_max_entry_premium_bps: float
    repricing_taker_max_entry_premium_bps: float
    repricing_fallback_taker_after_no_fill_attempts: int
    repricing_fallback_taker_retry_max_entry_premium_bps: float | None
    taker_slippage_guard_bps: float
    taker_min_net_edge_after_premium_bps: float
    taker_time_in_force: str
    maker_quote_ttl_seconds: int
    resolution_maker_quote_ttl_seconds: int
    repricing_fallback_quote_ttl_seconds: int
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
    adverse_fill_force_ioc: bool
    time_stop_max_remaining_edge_bps: float | None
    max_holding_multiplier: float
    exit_repost_cooldown_seconds: float
    exit_scaleout_enabled: bool
    time_stop_scaleout_fraction: float
    adverse_fill_scaleout_fraction: float
    exit_scaleout_min_notional: float
    entry_repost_cooldown_seconds: float
    repricing_fallback_entry_repost_cooldown_seconds: float
    entry_failure_cooldown_seconds: float
    entry_market_cooldown_seconds: float
    repricing_fallback_entry_market_cooldown_seconds: float
    exit_failure_cooldown_seconds: float
    loss_reentry_cooldown_seconds: float
    max_loss_trades_per_market: int
    max_loss_trades_per_exposure_group: int
    time_stop_force_ioc_after_expiries: int
    time_stop_force_ioc_for_repricing_taker: bool
    thesis_entry_cooldown_seconds: float
    single_active_market_per_thesis: bool
    max_no_fill_entry_attempts_per_market: int
    skip_selective_wide_spread_markets: bool
    dynamic_gates_enabled: bool
    dynamic_gate_min_samples: int
    dynamic_min_net_edge_floor_bps: float
    dynamic_min_net_edge_ceiling_bps: float
    dynamic_taker_max_entry_premium_floor_bps: float
    dynamic_taker_max_entry_premium_ceiling_bps: float
    dynamic_repricing_taker_max_entry_premium_floor_bps: float
    dynamic_repricing_taker_max_entry_premium_ceiling_bps: float
    entry_execution_drag_bps: float
    entry_execution_spread_weight: float
    entry_execution_feedback_weight: float
    entry_execution_drag_cap_bps: float
    route_adaptation_enabled: bool
    route_adaptation_min_samples: int
    route_adaptation_cooldown_seconds: float
    selective_market_allow_taker: bool
    selective_market_allow_taker_when_aggressive: bool
    quality_sizing_enabled: bool
    quality_sizing_min_multiplier: float
    quality_sizing_max_multiplier: float
    quality_sizing_edge_reference_bps: float
    quality_sizing_confidence_weight: float
    quality_sizing_edge_weight: float
    quality_sizing_route_feedback_weight: float


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
        repricing_max_net_edge_bps=base.repricing_max_net_edge_bps,
        taker_urgency_threshold=base.taker_urgency_threshold,
        maker_min_edge_bps=base.maker_min_edge_bps,
        resolution_maker_min_edge_bps=base.resolution_maker_min_edge_bps,
        high_edge_taker_min_edge_bps=base.high_edge_taker_min_edge_bps,
        high_edge_taker_max_spread_bps=base.high_edge_taker_max_spread_bps,
        taker_max_entry_premium_bps=base.taker_max_entry_premium_bps,
        repricing_taker_max_entry_premium_bps=base.repricing_taker_max_entry_premium_bps,
        repricing_fallback_taker_after_no_fill_attempts=base.repricing_fallback_taker_after_no_fill_attempts,
        repricing_fallback_taker_retry_max_entry_premium_bps=base.repricing_fallback_taker_retry_max_entry_premium_bps,
        taker_slippage_guard_bps=base.taker_slippage_guard_bps,
        taker_min_net_edge_after_premium_bps=base.taker_min_net_edge_after_premium_bps,
        taker_time_in_force=base.taker_time_in_force,
        maker_quote_ttl_seconds=base.maker_quote_ttl_seconds,
        resolution_maker_quote_ttl_seconds=base.resolution_maker_quote_ttl_seconds,
        repricing_fallback_quote_ttl_seconds=base.repricing_fallback_quote_ttl_seconds,
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
        adverse_fill_force_ioc=base.adverse_fill_force_ioc,
        time_stop_max_remaining_edge_bps=base.time_stop_max_remaining_edge_bps,
        max_holding_multiplier=base.max_holding_multiplier,
        exit_repost_cooldown_seconds=base.exit_repost_cooldown_seconds,
        exit_scaleout_enabled=base.exit_scaleout_enabled,
        time_stop_scaleout_fraction=base.time_stop_scaleout_fraction,
        adverse_fill_scaleout_fraction=base.adverse_fill_scaleout_fraction,
        exit_scaleout_min_notional=base.exit_scaleout_min_notional,
        entry_repost_cooldown_seconds=base.entry_repost_cooldown_seconds,
        repricing_fallback_entry_repost_cooldown_seconds=base.repricing_fallback_entry_repost_cooldown_seconds,
        entry_failure_cooldown_seconds=base.entry_failure_cooldown_seconds,
        entry_market_cooldown_seconds=base.entry_market_cooldown_seconds,
        repricing_fallback_entry_market_cooldown_seconds=base.repricing_fallback_entry_market_cooldown_seconds,
        exit_failure_cooldown_seconds=base.exit_failure_cooldown_seconds,
        loss_reentry_cooldown_seconds=base.loss_reentry_cooldown_seconds,
        max_loss_trades_per_market=base.max_loss_trades_per_market,
        max_loss_trades_per_exposure_group=base.max_loss_trades_per_exposure_group,
        time_stop_force_ioc_after_expiries=base.time_stop_force_ioc_after_expiries,
        time_stop_force_ioc_for_repricing_taker=base.time_stop_force_ioc_for_repricing_taker,
        thesis_entry_cooldown_seconds=base.thesis_entry_cooldown_seconds,
        single_active_market_per_thesis=base.single_active_market_per_thesis,
        max_no_fill_entry_attempts_per_market=base.max_no_fill_entry_attempts_per_market,
        skip_selective_wide_spread_markets=base.skip_selective_wide_spread_markets,
        dynamic_gates_enabled=base.dynamic_gates_enabled,
        dynamic_gate_min_samples=base.dynamic_gate_min_samples,
        dynamic_min_net_edge_floor_bps=base.dynamic_min_net_edge_floor_bps,
        dynamic_min_net_edge_ceiling_bps=base.dynamic_min_net_edge_ceiling_bps,
        dynamic_taker_max_entry_premium_floor_bps=base.dynamic_taker_max_entry_premium_floor_bps,
        dynamic_taker_max_entry_premium_ceiling_bps=base.dynamic_taker_max_entry_premium_ceiling_bps,
        dynamic_repricing_taker_max_entry_premium_floor_bps=base.dynamic_repricing_taker_max_entry_premium_floor_bps,
        dynamic_repricing_taker_max_entry_premium_ceiling_bps=base.dynamic_repricing_taker_max_entry_premium_ceiling_bps,
        entry_execution_drag_bps=base.entry_execution_drag_bps,
        entry_execution_spread_weight=base.entry_execution_spread_weight,
        entry_execution_feedback_weight=base.entry_execution_feedback_weight,
        entry_execution_drag_cap_bps=base.entry_execution_drag_cap_bps,
        route_adaptation_enabled=base.route_adaptation_enabled,
        route_adaptation_min_samples=base.route_adaptation_min_samples,
        route_adaptation_cooldown_seconds=base.route_adaptation_cooldown_seconds,
        selective_market_allow_taker=base.selective_market_allow_taker,
        selective_market_allow_taker_when_aggressive=base.selective_market_allow_taker_when_aggressive,
        quality_sizing_enabled=base.quality_sizing_enabled,
        quality_sizing_min_multiplier=base.quality_sizing_min_multiplier,
        quality_sizing_max_multiplier=base.quality_sizing_max_multiplier,
        quality_sizing_edge_reference_bps=base.quality_sizing_edge_reference_bps,
        quality_sizing_confidence_weight=base.quality_sizing_confidence_weight,
        quality_sizing_edge_weight=base.quality_sizing_edge_weight,
        quality_sizing_route_feedback_weight=base.quality_sizing_route_feedback_weight,
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
            "repricing_fallback_quote_ttl_seconds",
            "stop_loss_min_ticks",
            "time_stop_force_ioc_after_expiries",
            "max_no_fill_entry_attempts_per_market",
            "max_loss_trades_per_market",
            "max_loss_trades_per_exposure_group",
            "dynamic_gate_min_samples",
            "route_adaptation_min_samples",
            "repricing_fallback_taker_after_no_fill_attempts",
        }:
            allowed[field_name] = int(cast(Any, raw_value))
        elif field_name == "taker_time_in_force":
            allowed[field_name] = str(cast(Any, raw_value)).upper()
        elif field_name in {
            "single_active_market_per_thesis",
            "skip_selective_wide_spread_markets",
            "dynamic_gates_enabled",
            "route_adaptation_enabled",
            "selective_market_allow_taker",
            "selective_market_allow_taker_when_aggressive",
            "quality_sizing_enabled",
            "adverse_fill_force_ioc",
            "exit_scaleout_enabled",
            "time_stop_force_ioc_for_repricing_taker",
        }:
            allowed[field_name] = bool(cast(Any, raw_value))
        elif field_name in {
            "execution_max_holding_seconds",
            "time_stop_max_remaining_edge_bps",
            "repricing_fallback_taker_retry_max_entry_premium_bps",
        }:
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
