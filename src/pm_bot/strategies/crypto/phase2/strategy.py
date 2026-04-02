"""Crypto Phase 2 strategy wrapper around Phase 1 fair values and Phase 2 execution policy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.execution.exposure_keys import derive_exposure_keys
from pm_bot.runtime.state import DashboardState, PendingOrderState, PositionState
from datetime import datetime, timezone

from pm_bot.strategies.common import current_position, dashboard_state, parse_float, recent_runtime_events
from pm_bot.strategies.crypto.phase2.config_registry import (
    CryptoPhase2ResolvedConfig,
    build_phase2_preset_rules,
    resolve_phase2_config_for_snapshot,
)
from pm_bot.strategies.crypto.phase2.execution import (
    build_order_intent,
    classify_crypto_signal,
    counterfactual_entry_score,
    evaluate_trade_eligibility,
    route_execution,
    spread_cost_bps,
)
from pm_bot.strategies.crypto.phase2.management import (
    build_position_intent,
    evaluate_exit,
    is_reentry_blocked,
    summarize_close_out_quality_from_events,
    summarize_market_probation_state_from_events,
)
from pm_bot.strategies.crypto.phase2.models import (
    CryptoCounterfactualEntryResult,
    CryptoDynamicEligibilityGate,
    CryptoExecutionFeedback,
    CryptoMarketProbationState,
    CryptoPositionIntent,
    CryptoReentryState,
    CryptoRoutePolicyState,
)

_DEFAULT_SELECTIVE_REPRICING_TAKER_MAX_QUOTE_AGE_SECONDS = 600.0
_DEFAULT_REPRICING_FALLBACK_ESCALATION_TAKER_URGENCY_FLOOR = 0.55


class CryptoPhase2Config:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_confidence = float(config.get("min_confidence", 0.6))
        self.min_net_edge_bps = float(config.get("min_net_edge_bps", 75.0))
        self.max_spread_bps = float(config.get("max_spread_bps", 250.0))
        self.min_liquidity_score = float(config.get("min_liquidity_score", 0.0))
        self.min_contract_price = float(config.get("min_contract_price", 0.05))
        self.repricing_max_net_edge_bps = float(config.get("repricing_max_net_edge_bps", 5000.0))
        self.taker_urgency_threshold = float(config.get("taker_urgency_threshold", 0.72))
        self.repricing_fallback_escalation_taker_urgency_floor = float(
            config.get(
                "repricing_fallback_escalation_taker_urgency_floor",
                _DEFAULT_REPRICING_FALLBACK_ESCALATION_TAKER_URGENCY_FLOOR,
            )
        )
        self.maker_min_edge_bps = float(config.get("maker_min_edge_bps", 100.0))
        self.resolution_maker_min_edge_bps = float(config.get("resolution_maker_min_edge_bps", 150.0))
        self.high_edge_taker_min_edge_bps = float(config.get("high_edge_taker_min_edge_bps", 2000.0))
        self.high_edge_taker_max_spread_bps = float(config.get("high_edge_taker_max_spread_bps", 250.0))
        self.taker_max_entry_premium_bps = float(config.get("taker_max_entry_premium_bps", 750.0))
        self.repricing_taker_max_entry_premium_bps = float(
            config.get("repricing_taker_max_entry_premium_bps", self.taker_max_entry_premium_bps)
        )
        self.repricing_fallback_taker_after_no_fill_attempts = int(
            config.get("repricing_fallback_taker_after_no_fill_attempts", 0)
        )
        self.repricing_fallback_probe_taker_enabled = bool(
            config.get("repricing_fallback_probe_taker_enabled", False)
        )
        self.repricing_fallback_probe_after_no_fill_attempts = int(
            config.get("repricing_fallback_probe_after_no_fill_attempts", 3)
        )
        self.repricing_fallback_probe_taker_max_entry_premium_bps = float(
            config.get("repricing_fallback_probe_taker_max_entry_premium_bps", 140.0)
        )
        self.repricing_fallback_probe_min_net_edge_bps = float(
            config.get("repricing_fallback_probe_min_net_edge_bps", 250.0)
        )
        self.repricing_fallback_probe_notional_multiplier = float(
            config.get("repricing_fallback_probe_notional_multiplier", 0.25)
        )
        self.repricing_fallback_probe_allow_on_maker_fallback = bool(
            config.get("repricing_fallback_probe_allow_on_maker_fallback", False)
        )
        raw_repricing_fallback_taker_retry_max_entry_premium_bps = config.get(
            "repricing_fallback_taker_retry_max_entry_premium_bps"
        )
        self.repricing_fallback_taker_retry_max_entry_premium_bps = (
            None
            if raw_repricing_fallback_taker_retry_max_entry_premium_bps in (None, "")
            else float(raw_repricing_fallback_taker_retry_max_entry_premium_bps)
        )
        raw_repricing_fallback_taker_escalation_max_spread_bps = config.get(
            "repricing_fallback_taker_escalation_max_spread_bps"
        )
        self.repricing_fallback_taker_escalation_max_spread_bps = (
            None
            if raw_repricing_fallback_taker_escalation_max_spread_bps in (None, "")
            else float(raw_repricing_fallback_taker_escalation_max_spread_bps)
        )
        raw_repricing_fallback_taker_escalation_min_net_edge_bps = config.get(
            "repricing_fallback_taker_escalation_min_net_edge_bps"
        )
        self.repricing_fallback_taker_escalation_min_net_edge_bps = (
            None
            if raw_repricing_fallback_taker_escalation_min_net_edge_bps in (None, "")
            else float(raw_repricing_fallback_taker_escalation_min_net_edge_bps)
        )
        self.taker_slippage_guard_bps = float(config.get("taker_slippage_guard_bps", 0.0))
        self.taker_min_net_edge_after_premium_bps = float(
            config.get("taker_min_net_edge_after_premium_bps", 150.0)
        )
        self.taker_time_in_force = str(config.get("taker_time_in_force", "IOC")).upper()
        self.maker_quote_ttl_seconds = int(config.get("maker_quote_ttl_seconds", 60))
        self.resolution_maker_quote_ttl_seconds = int(config.get("resolution_maker_quote_ttl_seconds", 180))
        self.repricing_fallback_quote_ttl_seconds = int(
            config.get("repricing_fallback_quote_ttl_seconds", self.maker_quote_ttl_seconds)
        )
        self.maker_aggressiveness = float(config.get("maker_aggressiveness", 1.0))
        self.default_notional = float(config.get("default_notional", 5.0))
        self.exit_edge_bps = float(config.get("exit_edge_bps", 75.0))
        self.stop_loss_bps = float(config.get("stop_loss_bps", 250.0))
        self.execution_max_holding_seconds = (
            float(config["execution_max_holding_seconds"])
            if "execution_max_holding_seconds" in config
            else None
        )
        self.min_holding_seconds_before_exit = float(config.get("min_holding_seconds_before_exit", 1.0))
        self.aging_exit_edge_bps = float(config.get("aging_exit_edge_bps", 150.0))
        self.stale_exit_edge_bps = float(config.get("stale_exit_edge_bps", 300.0))
        self.aging_start_fraction = float(config.get("aging_start_fraction", 0.5))
        self.stale_start_fraction = float(config.get("stale_start_fraction", 1.0))
        self.stop_loss_min_ticks = int(config.get("stop_loss_min_ticks", 2))
        self.stop_loss_max_remaining_edge_bps = float(config.get("stop_loss_max_remaining_edge_bps", 150.0))
        self.adverse_fill_exit_bps = float(config.get("adverse_fill_exit_bps", 75.0))
        self.adverse_fill_max_remaining_edge_bps = float(
            config.get("adverse_fill_max_remaining_edge_bps", 150.0)
        )
        self.adverse_fill_force_ioc = bool(config.get("adverse_fill_force_ioc", False))
        raw_time_stop_max_remaining_edge_bps = config.get("time_stop_max_remaining_edge_bps")
        self.time_stop_max_remaining_edge_bps = (
            None
            if raw_time_stop_max_remaining_edge_bps in (None, "")
            else float(raw_time_stop_max_remaining_edge_bps)
        )
        self.max_holding_multiplier = float(config.get("max_holding_multiplier", 2.0))
        self.exit_repost_cooldown_seconds = float(config.get("exit_repost_cooldown_seconds", 30.0))
        self.exit_scaleout_enabled = bool(config.get("exit_scaleout_enabled", False))
        self.time_stop_scaleout_fraction = float(config.get("time_stop_scaleout_fraction", 1.0))
        self.adverse_fill_scaleout_fraction = float(config.get("adverse_fill_scaleout_fraction", 1.0))
        self.exit_scaleout_min_notional = float(config.get("exit_scaleout_min_notional", 0.0))
        self.time_stop_passive_quote_ttl_seconds = int(
            config.get("time_stop_passive_quote_ttl_seconds", 5)
        )
        self.entry_repost_cooldown_seconds = float(config.get("entry_repost_cooldown_seconds", 120.0))
        self.repricing_fallback_entry_repost_cooldown_seconds = float(
            config.get("repricing_fallback_entry_repost_cooldown_seconds", self.entry_repost_cooldown_seconds)
        )
        self.entry_failure_cooldown_seconds = float(
            config.get("entry_failure_cooldown_seconds", self.entry_repost_cooldown_seconds)
        )
        self.entry_market_cooldown_seconds = float(
            config.get("entry_market_cooldown_seconds", self.entry_failure_cooldown_seconds)
        )
        self.repricing_fallback_entry_market_cooldown_seconds = float(
            config.get("repricing_fallback_entry_market_cooldown_seconds", self.entry_market_cooldown_seconds)
        )
        self.entry_no_fill_cooldown_seconds = float(
            config.get("entry_no_fill_cooldown_seconds", 60.0)
        )
        self.entry_family_cooldown_seconds = float(config.get("entry_family_cooldown_seconds", 0.0))
        raw_entry_family_cooldown_seconds_reach = config.get("entry_family_cooldown_seconds_reach")
        self.entry_family_cooldown_seconds_reach = (
            None
            if raw_entry_family_cooldown_seconds_reach in (None, "")
            else float(raw_entry_family_cooldown_seconds_reach)
        )
        raw_entry_family_cooldown_seconds_dip = config.get("entry_family_cooldown_seconds_dip")
        self.entry_family_cooldown_seconds_dip = (
            None
            if raw_entry_family_cooldown_seconds_dip in (None, "")
            else float(raw_entry_family_cooldown_seconds_dip)
        )
        self.exit_failure_cooldown_seconds = float(
            config.get("exit_failure_cooldown_seconds", self.exit_repost_cooldown_seconds)
        )
        self.loss_reentry_cooldown_seconds = float(config.get("loss_reentry_cooldown_seconds", 300.0))
        self.max_loss_trades_per_market = int(config.get("max_loss_trades_per_market", 0))
        self.max_loss_trades_per_exposure_group = int(
            config.get("max_loss_trades_per_exposure_group", 0)
        )
        self.market_probation_enabled = bool(config.get("market_probation_enabled", False))
        self.market_probation_loss_streak_for_probation = int(
            config.get("market_probation_loss_streak_for_probation", 2)
        )
        self.market_probation_loss_streak_for_quarantine = int(
            config.get("market_probation_loss_streak_for_quarantine", 3)
        )
        self.market_probation_recovery_win_streak_required = int(
            config.get("market_probation_recovery_win_streak_required", 2)
        )
        self.market_probation_cooldown_seconds = float(
            config.get("market_probation_cooldown_seconds", self.loss_reentry_cooldown_seconds)
        )
        self.time_stop_force_ioc_after_expiries = int(config.get("time_stop_force_ioc_after_expiries", 2))
        self.time_stop_force_ioc_for_repricing_taker = bool(
            config.get("time_stop_force_ioc_for_repricing_taker", True)
        )
        self.time_stop_force_ioc_suspension_on_passive_feedback_enabled = bool(
            config.get("time_stop_force_ioc_suspension_on_passive_feedback_enabled", True)
        )
        self.time_stop_force_ioc_suspension_min_taker_shortfall_bps = float(
            config.get("time_stop_force_ioc_suspension_min_taker_shortfall_bps", 0.0)
        )
        raw_time_stop_force_ioc_min_adverse_move_bps = config.get("time_stop_force_ioc_min_adverse_move_bps")
        self.time_stop_force_ioc_min_adverse_move_bps = (
            None
            if raw_time_stop_force_ioc_min_adverse_move_bps in (None, "")
            else float(raw_time_stop_force_ioc_min_adverse_move_bps)
        )
        raw_time_stop_force_ioc_max_spread_bps = config.get("time_stop_force_ioc_max_spread_bps")
        self.time_stop_force_ioc_max_spread_bps = (
            None
            if raw_time_stop_force_ioc_max_spread_bps in (None, "")
            else float(raw_time_stop_force_ioc_max_spread_bps)
        )
        raw_time_stop_force_ioc_max_remaining_edge_bps = config.get("time_stop_force_ioc_max_remaining_edge_bps")
        self.time_stop_force_ioc_max_remaining_edge_bps = (
            None
            if raw_time_stop_force_ioc_max_remaining_edge_bps in (None, "")
            else float(raw_time_stop_force_ioc_max_remaining_edge_bps)
        )
        raw_time_stop_force_ioc_skip_below_remaining_edge_bps = config.get(
            "time_stop_force_ioc_skip_below_remaining_edge_bps"
        )
        self.time_stop_force_ioc_skip_below_remaining_edge_bps = (
            None
            if raw_time_stop_force_ioc_skip_below_remaining_edge_bps in (None, "")
            else float(raw_time_stop_force_ioc_skip_below_remaining_edge_bps)
        )
        self.escalated_entry_exit_containment_enabled = bool(
            config.get("escalated_entry_exit_containment_enabled", False)
        )
        raw_escalated_entry_adverse_fill_exit_bps = config.get("escalated_entry_adverse_fill_exit_bps")
        self.escalated_entry_adverse_fill_exit_bps = (
            None
            if raw_escalated_entry_adverse_fill_exit_bps in (None, "")
            else float(raw_escalated_entry_adverse_fill_exit_bps)
        )
        raw_escalated_entry_adverse_fill_max_remaining_edge_bps = config.get(
            "escalated_entry_adverse_fill_max_remaining_edge_bps"
        )
        self.escalated_entry_adverse_fill_max_remaining_edge_bps = (
            None
            if raw_escalated_entry_adverse_fill_max_remaining_edge_bps in (None, "")
            else float(raw_escalated_entry_adverse_fill_max_remaining_edge_bps)
        )
        raw_escalated_entry_max_holding_multiplier = config.get("escalated_entry_max_holding_multiplier")
        self.escalated_entry_max_holding_multiplier = (
            None
            if raw_escalated_entry_max_holding_multiplier in (None, "")
            else float(raw_escalated_entry_max_holding_multiplier)
        )
        self.escalated_entry_exit_containment_enabled_reach = (
            None
            if config.get("escalated_entry_exit_containment_enabled_reach") in (None, "")
            else bool(config.get("escalated_entry_exit_containment_enabled_reach"))
        )
        self.escalated_entry_exit_containment_enabled_dip = (
            None
            if config.get("escalated_entry_exit_containment_enabled_dip") in (None, "")
            else bool(config.get("escalated_entry_exit_containment_enabled_dip"))
        )
        raw_escalated_entry_adverse_fill_exit_bps_reach = config.get(
            "escalated_entry_adverse_fill_exit_bps_reach"
        )
        self.escalated_entry_adverse_fill_exit_bps_reach = (
            None
            if raw_escalated_entry_adverse_fill_exit_bps_reach in (None, "")
            else float(raw_escalated_entry_adverse_fill_exit_bps_reach)
        )
        raw_escalated_entry_adverse_fill_exit_bps_dip = config.get(
            "escalated_entry_adverse_fill_exit_bps_dip"
        )
        self.escalated_entry_adverse_fill_exit_bps_dip = (
            None
            if raw_escalated_entry_adverse_fill_exit_bps_dip in (None, "")
            else float(raw_escalated_entry_adverse_fill_exit_bps_dip)
        )
        raw_escalated_entry_adverse_fill_max_remaining_edge_bps_reach = config.get(
            "escalated_entry_adverse_fill_max_remaining_edge_bps_reach"
        )
        self.escalated_entry_adverse_fill_max_remaining_edge_bps_reach = (
            None
            if raw_escalated_entry_adverse_fill_max_remaining_edge_bps_reach in (None, "")
            else float(raw_escalated_entry_adverse_fill_max_remaining_edge_bps_reach)
        )
        raw_escalated_entry_adverse_fill_max_remaining_edge_bps_dip = config.get(
            "escalated_entry_adverse_fill_max_remaining_edge_bps_dip"
        )
        self.escalated_entry_adverse_fill_max_remaining_edge_bps_dip = (
            None
            if raw_escalated_entry_adverse_fill_max_remaining_edge_bps_dip in (None, "")
            else float(raw_escalated_entry_adverse_fill_max_remaining_edge_bps_dip)
        )
        raw_escalated_entry_max_holding_multiplier_reach = config.get(
            "escalated_entry_max_holding_multiplier_reach"
        )
        self.escalated_entry_max_holding_multiplier_reach = (
            None
            if raw_escalated_entry_max_holding_multiplier_reach in (None, "")
            else float(raw_escalated_entry_max_holding_multiplier_reach)
        )
        raw_escalated_entry_max_holding_multiplier_dip = config.get(
            "escalated_entry_max_holding_multiplier_dip"
        )
        self.escalated_entry_max_holding_multiplier_dip = (
            None
            if raw_escalated_entry_max_holding_multiplier_dip in (None, "")
            else float(raw_escalated_entry_max_holding_multiplier_dip)
        )
        self.thesis_entry_cooldown_seconds = float(
            config.get("thesis_entry_cooldown_seconds", self.entry_failure_cooldown_seconds)
        )
        self.single_active_market_per_thesis = bool(config.get("single_active_market_per_thesis", True))
        self.max_no_fill_entry_attempts_per_market = int(
            config.get("max_no_fill_entry_attempts_per_market", 2)
        )
        self.enforce_exposure_group_conflict_guard = bool(
            config.get("enforce_exposure_group_conflict_guard", True)
        )
        self.skip_selective_wide_spread_markets = bool(
            config.get("skip_selective_wide_spread_markets", False)
        )
        self.selective_repricing_taker_max_quote_age_seconds = float(
            config.get(
                "selective_repricing_taker_max_quote_age_seconds",
                _DEFAULT_SELECTIVE_REPRICING_TAKER_MAX_QUOTE_AGE_SECONDS,
            )
        )
        self.dynamic_gates_enabled = bool(config.get("dynamic_gates_enabled", True))
        self.dynamic_gate_min_samples = int(config.get("dynamic_gate_min_samples", 3))
        self.dynamic_min_net_edge_floor_bps = float(config.get("dynamic_min_net_edge_floor_bps", 50.0))
        self.dynamic_min_net_edge_ceiling_bps = float(config.get("dynamic_min_net_edge_ceiling_bps", 300.0))
        self.dynamic_taker_max_entry_premium_floor_bps = float(
            config.get("dynamic_taker_max_entry_premium_floor_bps", 60.0)
        )
        self.dynamic_taker_max_entry_premium_ceiling_bps = float(
            config.get("dynamic_taker_max_entry_premium_ceiling_bps", 1200.0)
        )
        self.dynamic_repricing_taker_max_entry_premium_floor_bps = float(
            config.get("dynamic_repricing_taker_max_entry_premium_floor_bps", 50.0)
        )
        self.dynamic_repricing_taker_max_entry_premium_ceiling_bps = float(
            config.get("dynamic_repricing_taker_max_entry_premium_ceiling_bps", 300.0)
        )
        self.entry_execution_drag_bps = float(config.get("entry_execution_drag_bps", 0.0))
        self.entry_execution_spread_weight = float(config.get("entry_execution_spread_weight", 0.0))
        self.entry_execution_feedback_weight = float(config.get("entry_execution_feedback_weight", 0.0))
        self.entry_execution_drag_cap_bps = float(config.get("entry_execution_drag_cap_bps", 1000.0))
        self.route_adaptation_enabled = bool(config.get("route_adaptation_enabled", True))
        self.route_adaptation_min_samples = int(config.get("route_adaptation_min_samples", 3))
        self.route_adaptation_cooldown_seconds = float(config.get("route_adaptation_cooldown_seconds", 120.0))
        self.selective_market_allow_taker = bool(config.get("selective_market_allow_taker", False))
        self.selective_market_allow_taker_when_aggressive = bool(
            config.get("selective_market_allow_taker_when_aggressive", False)
        )
        raw_selective_market_allow_taker_reach = config.get("selective_market_allow_taker_reach")
        self.selective_market_allow_taker_reach = (
            None
            if raw_selective_market_allow_taker_reach in (None, "")
            else bool(raw_selective_market_allow_taker_reach)
        )
        raw_selective_market_allow_taker_dip = config.get("selective_market_allow_taker_dip")
        self.selective_market_allow_taker_dip = (
            None
            if raw_selective_market_allow_taker_dip in (None, "")
            else bool(raw_selective_market_allow_taker_dip)
        )
        raw_selective_market_allow_taker_when_aggressive_reach = config.get(
            "selective_market_allow_taker_when_aggressive_reach"
        )
        self.selective_market_allow_taker_when_aggressive_reach = (
            None
            if raw_selective_market_allow_taker_when_aggressive_reach in (None, "")
            else bool(raw_selective_market_allow_taker_when_aggressive_reach)
        )
        raw_selective_market_allow_taker_when_aggressive_dip = config.get(
            "selective_market_allow_taker_when_aggressive_dip"
        )
        self.selective_market_allow_taker_when_aggressive_dip = (
            None
            if raw_selective_market_allow_taker_when_aggressive_dip in (None, "")
            else bool(raw_selective_market_allow_taker_when_aggressive_dip)
        )
        self.quality_sizing_enabled = bool(config.get("quality_sizing_enabled", True))
        self.quality_sizing_min_multiplier = float(config.get("quality_sizing_min_multiplier", 0.75))
        self.quality_sizing_max_multiplier = float(config.get("quality_sizing_max_multiplier", 1.15))
        self.quality_sizing_edge_reference_bps = float(config.get("quality_sizing_edge_reference_bps", 700.0))
        self.quality_sizing_confidence_weight = float(config.get("quality_sizing_confidence_weight", 0.45))
        self.quality_sizing_edge_weight = float(config.get("quality_sizing_edge_weight", 0.35))
        self.quality_sizing_route_feedback_weight = float(
            config.get("quality_sizing_route_feedback_weight", 0.20)
        )
        self.counterfactual_entry_gate_enabled = bool(config.get("counterfactual_entry_gate_enabled", False))
        self.counterfactual_entry_top_k = int(config.get("counterfactual_entry_top_k", 1))
        self.counterfactual_entry_min_score_margin_bps = float(
            config.get("counterfactual_entry_min_score_margin_bps", 25.0)
        )
        self.counterfactual_entry_min_candidates = int(config.get("counterfactual_entry_min_candidates", 2))
        self.counterfactual_entry_max_snapshot_age_seconds = float(
            config.get("counterfactual_entry_max_snapshot_age_seconds", 120.0)
        )
        self.counterfactual_entry_net_edge_weight = float(
            config.get("counterfactual_entry_net_edge_weight", 1.0)
        )
        self.counterfactual_entry_confidence_weight = float(
            config.get("counterfactual_entry_confidence_weight", 0.5)
        )
        self.counterfactual_entry_urgency_weight = float(
            config.get("counterfactual_entry_urgency_weight", 0.25)
        )
        self.counterfactual_entry_spread_weight = float(
            config.get("counterfactual_entry_spread_weight", 1.0)
        )
        self.family_trade_budget_enabled = bool(config.get("family_trade_budget_enabled", False))
        self.family_trade_budget_min_samples = int(config.get("family_trade_budget_min_samples", 3))
        self.family_trade_budget_low_quality_share = float(
            config.get("family_trade_budget_low_quality_share", 0.25)
        )
        self.family_trade_budget_stable_share = float(config.get("family_trade_budget_stable_share", 0.5))
        self.family_trade_budget_high_quality_share = float(
            config.get("family_trade_budget_high_quality_share", 0.75)
        )
        self.family_trade_budget_lookback_events = int(config.get("family_trade_budget_lookback_events", 64))
        self.fragile_closer_notional_haircut_enabled = bool(
            config.get("fragile_closer_notional_haircut_enabled", False)
        )
        self.fragile_closer_notional_haircut_min_multiplier = float(
            config.get("fragile_closer_notional_haircut_min_multiplier", 0.55)
        )
        self.fragile_closer_notional_haircut_max_multiplier = float(
            config.get("fragile_closer_notional_haircut_max_multiplier", 1.0)
        )
        self.fragile_closer_notional_haircut_expired_ratio_threshold = float(
            config.get("fragile_closer_notional_haircut_expired_ratio_threshold", 0.40)
        )
        self.fragile_closer_notional_haircut_min_samples = int(
            config.get("fragile_closer_notional_haircut_min_samples", 4)
        )
        self.fragile_closer_notional_haircut_lookback_events = int(
            config.get("fragile_closer_notional_haircut_lookback_events", 128)
        )
        self.close_out_quality_guard_enabled = bool(config.get("close_out_quality_guard_enabled", False))
        self.close_out_quality_guard_lookback_events = int(config.get("close_out_quality_guard_lookback_events", 128))
        self.close_out_quality_guard_min_closed_samples = int(
            config.get("close_out_quality_guard_min_closed_samples", 3)
        )
        self.close_out_quality_guard_max_stop_out_share = float(
            config.get("close_out_quality_guard_max_stop_out_share", 0.50)
        )
        self.close_out_quality_guard_min_realized_pnl_bps = float(
            config.get("close_out_quality_guard_min_realized_pnl_bps", 0.0)
        )
        self.close_out_quality_guard_notional_min_multiplier = float(
            config.get("close_out_quality_guard_notional_min_multiplier", 0.60)
        )
        self.close_out_quality_guard_notional_max_multiplier = float(
            config.get("close_out_quality_guard_notional_max_multiplier", 1.0)
        )
        self.close_out_quality_guard_entry_cooldown_seconds = float(
            config.get("close_out_quality_guard_entry_cooldown_seconds", 0.0)
        )
        self.family_pnl_notional_haircut_enabled = bool(
            config.get("family_pnl_notional_haircut_enabled", False)
        )
        self.family_pnl_notional_haircut_min_multiplier = float(
            config.get("family_pnl_notional_haircut_min_multiplier", 0.6)
        )
        self.family_pnl_notional_haircut_max_multiplier = float(
            config.get("family_pnl_notional_haircut_max_multiplier", 1.0)
        )
        self.family_pnl_notional_haircut_min_closed_samples = int(
            config.get("family_pnl_notional_haircut_min_closed_samples", 2)
        )
        self.family_pnl_notional_haircut_lookback_events = int(
            config.get("family_pnl_notional_haircut_lookback_events", 128)
        )
        self.family_pnl_notional_haircut_full_haircut_pnl_per_notional = float(
            config.get("family_pnl_notional_haircut_full_haircut_pnl_per_notional", -0.02)
        )
        self.decision_trace_version = str(config.get("decision_trace_version", "v1"))
        self.preset_rules = build_phase2_preset_rules(dict(config))


class CryptoPhase2Strategy:
    strategy_id = "crypto.phase2"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = CryptoPhase2Config(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.CRYPTO:
            _record_runtime_skip(context=context, snapshot=snapshot, reason="non_crypto_snapshot")
            return []

        dashboard = dashboard_state(context)
        position = current_position(snapshot=snapshot, dashboard=dashboard)
        fair_value = _fair_value_for_market(snapshot=snapshot, context=context)
        if fair_value is None and position is not None:
            fair_value = _fallback_exit_fair_value(snapshot=snapshot, position=position)
        if fair_value is None:
            _record_runtime_skip(context=context, snapshot=snapshot, reason="missing_fair_value")
            return []
        if position is not None:
            return self._exit_signals(
                snapshot=snapshot,
                fair_value=fair_value,
                position=position,
                context=context,
            )
        if _market_pending_orders_block_entry(snapshot=snapshot, dashboard=dashboard, context=context):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="pending_order_exists")
            return []

        resolved_config = resolve_phase2_config_for_snapshot(base=self.config, snapshot=snapshot)
        reentry_state = _reentry_state_for_market(snapshot=snapshot, context=context)
        if is_reentry_blocked(state=reentry_state, as_of=snapshot.timestamp):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="reentry_blocked")
            return []
        if _recent_negative_trade_closed(
            snapshot=snapshot,
            context=context,
            cooldown_seconds=resolved_config.loss_reentry_cooldown_seconds,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="loss_reentry_cooldown_active")
            return []
        if _market_loss_quarantined(
            snapshot=snapshot,
            context=context,
            max_loss_trades=resolved_config.max_loss_trades_per_market,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="market_loss_quarantined")
            return []
        probation_state = _market_probation_state_for_snapshot(
            snapshot=snapshot,
            context=context,
            config=resolved_config,
        )
        if probation_state is not None and probation_state.state in {"probation", "quarantined"}:
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason=(
                    "market_probation_active"
                    if probation_state.state == "probation"
                    else "market_probation_quarantined"
                ),
                extra={
                    "probation_state": probation_state.state,
                    "probation_recent_loss_streak": probation_state.recent_loss_streak,
                    "probation_recent_win_streak": probation_state.recent_win_streak,
                    "probation_blocked_until": (
                        probation_state.blocked_until.isoformat()
                        if probation_state.blocked_until is not None
                        else None
                    ),
                },
            )
            return []
        if _exposure_group_recent_negative_trade_closed(
            snapshot=snapshot,
            context=context,
            cooldown_seconds=resolved_config.loss_reentry_cooldown_seconds,
        ):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="exposure_group_loss_reentry_cooldown_active",
            )
            return []
        if _exposure_group_loss_quarantined(
            snapshot=snapshot,
            context=context,
            max_loss_trades=resolved_config.max_loss_trades_per_exposure_group,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="exposure_group_loss_quarantined")
            return []

        if _market_is_blocked(snapshot=snapshot, context=context):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="market_blocked",
                extra={
                    "selection_action": _selection_action_for_market(snapshot=snapshot, context=context),
                    "selection_reasons": list(_selection_reasons_for_market(snapshot=snapshot, context=context)),
                },
            )
            return []

        if _series_is_blocked(snapshot=snapshot, context=context):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="series_blocked")
            return []

        return self._entry_signals(
            snapshot=snapshot,
            fair_value=fair_value,
            context=context,
            resolved_config=resolved_config,
        )

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        context: Mapping[str, object],
        resolved_config: CryptoPhase2ResolvedConfig,
    ) -> Sequence[StrategySignal]:
        classification = classify_crypto_signal(fair_value=fair_value)
        execution_feedback = _execution_feedback(context)
        dynamic_gate = _dynamic_eligibility_gate_for_snapshot(snapshot=snapshot, context=context)
        dynamic_min_net_edge_bps = _effective_dynamic_min_net_edge_bps(
            base_min_net_edge_bps=resolved_config.min_net_edge_bps,
            gate=dynamic_gate,
            config=resolved_config,
        )
        dynamic_min_net_edge_reason = _min_net_edge_reason_for_dynamic_gate(
            base_min_net_edge_bps=resolved_config.min_net_edge_bps,
            effective_min_net_edge_bps=dynamic_min_net_edge_bps,
        )
        entry_execution_drag_bps = _entry_execution_drag_bps(
            snapshot=snapshot,
            classification=classification,
            feedback=execution_feedback,
            config=resolved_config,
        )
        effective_min_net_edge_bps = dynamic_min_net_edge_bps + entry_execution_drag_bps
        effective_min_net_edge_reason = _min_net_edge_reason_for_dynamic_gate_and_drag(
            base_min_net_edge_bps=resolved_config.min_net_edge_bps,
            dynamic_min_net_edge_bps=dynamic_min_net_edge_bps,
            effective_min_net_edge_bps=effective_min_net_edge_bps,
            dynamic_reason=dynamic_min_net_edge_reason,
        )
        dynamic_taker_max_entry_premium_bps = _effective_dynamic_taker_max_entry_premium_bps(
            base_taker_max_entry_premium_bps=resolved_config.taker_max_entry_premium_bps,
            gate=dynamic_gate,
            config=resolved_config,
        )
        dynamic_repricing_taker_max_entry_premium_bps = _effective_dynamic_repricing_taker_max_entry_premium_bps(
            base_repricing_taker_max_entry_premium_bps=resolved_config.repricing_taker_max_entry_premium_bps,
            gate=dynamic_gate,
            config=resolved_config,
        )
        market_repricing_no_fill_attempts = _repricing_maker_fallback_no_fill_attempts(
            snapshot=snapshot,
            context=context,
            side=classification.side,
        )
        family_repricing_no_fill_attempts = _repricing_family_maker_no_fill_attempts(
            snapshot=snapshot,
            context=context,
        )
        repricing_fallback_no_fill_attempts = max(
            market_repricing_no_fill_attempts,
            family_repricing_no_fill_attempts,
        )
        repricing_fallback_taker_escalated = False
        repricing_fallback_taker_escalation_block_reason: str | None = None
        repricing_fallback_probe_taker_eligible = False
        repricing_fallback_probe_taker_active = False
        repricing_fallback_probe_taker_block_reason: str | None = None
        repricing_fallback_probe_bootstrap_eligible = False
        repricing_fallback_probe_notional_multiplier = 1.0
        repricing_fallback_probe_notional_floor_applied = False
        repricing_route_stage = "not_applicable"
        repricing_route_stage_source = "not_applicable"
        repricing_route_cooldown_active = False
        repricing_route_cooldown_until_iso: str | None = None
        selection_action = _selection_action_for_market(snapshot=snapshot, context=context)
        selection_reasons = _selection_reasons_for_market(snapshot=snapshot, context=context)
        signal_net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
        if classification.signal_type == "repricing_edge":
            base_repricing_route_stage = _repricing_route_stage_from_no_fill_progression(
                no_fill_attempts=repricing_fallback_no_fill_attempts,
                probe_enabled=resolved_config.repricing_fallback_probe_taker_enabled,
                probe_after_no_fill_attempts=resolved_config.repricing_fallback_probe_after_no_fill_attempts,
                taker_after_no_fill_attempts=resolved_config.repricing_fallback_taker_after_no_fill_attempts,
            )
            (
                repricing_route_stage,
                repricing_route_stage_source,
                repricing_route_cooldown_active,
                repricing_route_cooldown_until,
            ) = _resolve_repricing_route_stage(
                snapshot=snapshot,
                signal_type=classification.signal_type,
                context=context,
                as_of=snapshot.timestamp,
                base_stage=base_repricing_route_stage,
            )
            if repricing_route_cooldown_until is not None:
                repricing_route_cooldown_until_iso = repricing_route_cooldown_until.isoformat()
        if (
            classification.signal_type == "repricing_edge"
            and signal_net_edge_bps > resolved_config.repricing_max_net_edge_bps
        ):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="repricing_extreme_mispricing_filtered",
                extra={
                    "phase2_preset": resolved_config.preset_name,
                    "signal_net_edge_bps": signal_net_edge_bps,
                    "repricing_max_net_edge_bps": resolved_config.repricing_max_net_edge_bps,
                    "selection_action": selection_action,
                    "selection_reasons": list(selection_reasons),
                },
            )
            return []
        if (
            resolved_config.skip_selective_wide_spread_markets
            and selection_action == "selective_market"
            and _has_wide_spread_selection_reason(selection_reasons)
        ):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="selection_wide_spread_selective_blocked",
                extra={
                    "phase2_preset": resolved_config.preset_name,
                    "selection_action": selection_action,
                    "selection_reasons": list(selection_reasons),
                },
            )
            return []
        eligibility = evaluate_trade_eligibility(
            fair_value=fair_value,
            snapshot=snapshot,
            classification=classification,
            min_confidence=resolved_config.min_confidence,
            min_net_edge_bps=effective_min_net_edge_bps,
            max_spread_bps=resolved_config.max_spread_bps,
            min_liquidity_score=resolved_config.min_liquidity_score,
            min_contract_price=resolved_config.min_contract_price,
            min_net_edge_reason=effective_min_net_edge_reason,
        )
        if classification.signal_type == "repricing_edge" and repricing_route_stage == "escalation":
            escalation_allowed = True
            max_spread_bps = resolved_config.repricing_fallback_taker_escalation_max_spread_bps
            if max_spread_bps is not None and eligibility.market_spread_bps > max_spread_bps:
                escalation_allowed = False
                repricing_fallback_taker_escalation_block_reason = "repricing_fallback_escalation_spread_too_wide"
            min_net_edge_bps = resolved_config.repricing_fallback_taker_escalation_min_net_edge_bps
            if escalation_allowed and min_net_edge_bps is not None and signal_net_edge_bps < min_net_edge_bps:
                escalation_allowed = False
                repricing_fallback_taker_escalation_block_reason = "repricing_fallback_escalation_net_edge_too_low"
            if escalation_allowed:
                retry_taker_cap = resolved_config.repricing_fallback_taker_retry_max_entry_premium_bps
                if retry_taker_cap is None:
                    retry_taker_cap = dynamic_taker_max_entry_premium_bps
                dynamic_repricing_taker_max_entry_premium_bps = max(
                    dynamic_repricing_taker_max_entry_premium_bps,
                    retry_taker_cap,
                )
                repricing_fallback_taker_escalated = True
        elif (
            classification.signal_type == "repricing_edge"
            and resolved_config.repricing_fallback_taker_after_no_fill_attempts > 0
            and repricing_fallback_no_fill_attempts >= resolved_config.repricing_fallback_taker_after_no_fill_attempts
        ):
            if repricing_route_stage == "cooldown":
                repricing_fallback_taker_escalation_block_reason = "repricing_route_stage_cooldown_active"
            else:
                repricing_fallback_taker_escalation_block_reason = "repricing_route_stage_not_escalation"
        effective_taker_urgency_threshold = _feedback_taker_urgency_threshold(
            base_threshold=resolved_config.taker_urgency_threshold,
            feedback=execution_feedback,
        )
        if repricing_fallback_taker_escalated:
            effective_taker_urgency_threshold = min(
                effective_taker_urgency_threshold,
                resolved_config.repricing_fallback_escalation_taker_urgency_floor,
            )
        route_policy_bias = _route_policy_bias_for_snapshot(
            snapshot=snapshot,
            signal_type=classification.signal_type,
            context=context,
        )
        decision = route_execution(
            fair_value=fair_value,
            snapshot=snapshot,
            classification=classification,
            eligibility=eligibility,
            allow_taker_routes=_allow_taker_routes_for_selection(
                snapshot=snapshot,
                selection_action=selection_action,
                route_policy_bias=route_policy_bias,
                feedback=execution_feedback,
                config=resolved_config,
            ),
            taker_urgency_threshold=effective_taker_urgency_threshold,
            maker_min_edge_bps=resolved_config.maker_min_edge_bps,
            resolution_maker_min_edge_bps=resolved_config.resolution_maker_min_edge_bps,
            high_edge_taker_min_edge_bps=resolved_config.high_edge_taker_min_edge_bps,
            high_edge_taker_max_spread_bps=resolved_config.high_edge_taker_max_spread_bps,
            taker_max_entry_premium_bps=dynamic_taker_max_entry_premium_bps,
            repricing_taker_max_entry_premium_bps=dynamic_repricing_taker_max_entry_premium_bps,
            taker_slippage_guard_bps=resolved_config.taker_slippage_guard_bps,
            taker_min_net_edge_after_premium_bps=resolved_config.taker_min_net_edge_after_premium_bps,
            maker_quote_ttl_seconds=_feedback_maker_quote_ttl_seconds(
                base_ttl=resolved_config.maker_quote_ttl_seconds,
                feedback=execution_feedback,
            ),
            resolution_maker_quote_ttl_seconds=_feedback_resolution_maker_quote_ttl_seconds(
                base_ttl=resolved_config.resolution_maker_quote_ttl_seconds,
                feedback=execution_feedback,
            ),
            repricing_fallback_quote_ttl_seconds=_feedback_maker_quote_ttl_seconds(
                base_ttl=resolved_config.repricing_fallback_quote_ttl_seconds,
                feedback=execution_feedback,
            ),
            maker_aggressiveness=_feedback_maker_aggressiveness(
                base_aggressiveness=resolved_config.maker_aggressiveness,
                feedback=execution_feedback,
            ),
            route_policy_bias=route_policy_bias,
        )
        probe_stage_eligible = repricing_route_stage in {"probe", "escalation"}
        probe_bootstrap_eligible = (
            resolved_config.repricing_fallback_probe_allow_on_maker_fallback
            and selection_action == "selective_market"
            and not _has_wide_spread_selection_reason(selection_reasons)
            and classification.signal_type == "repricing_edge"
            and repricing_route_stage == "maker"
            and decision.route == "maker"
        )
        repricing_fallback_probe_bootstrap_eligible = probe_bootstrap_eligible
        if (
            classification.signal_type == "repricing_edge"
            and resolved_config.repricing_fallback_probe_taker_enabled
            and (probe_stage_eligible or probe_bootstrap_eligible)
        ):
            repricing_fallback_probe_taker_eligible = True
            if signal_net_edge_bps < resolved_config.repricing_fallback_probe_min_net_edge_bps:
                repricing_fallback_probe_taker_block_reason = "repricing_fallback_probe_net_edge_too_low"
            elif decision.route != "maker":
                repricing_fallback_probe_taker_block_reason = "repricing_fallback_probe_route_not_maker"
            elif (
                not probe_stage_eligible
                and "maker_fallback" not in decision.rationale_tags
                and not probe_bootstrap_eligible
            ):
                repricing_fallback_probe_taker_block_reason = "repricing_fallback_probe_not_maker_fallback"
            else:
                probe_decision = route_execution(
                    fair_value=fair_value,
                    snapshot=snapshot,
                    classification=classification,
                    eligibility=eligibility,
                    # Probe lane is already guarded by strict stage/premium/net-edge conditions.
                    # Bypass selective-market generic taker block so constrained probe IOC can execute.
                    allow_taker_routes=True,
                    taker_urgency_threshold=0.0,
                    maker_min_edge_bps=resolved_config.maker_min_edge_bps,
                    resolution_maker_min_edge_bps=resolved_config.resolution_maker_min_edge_bps,
                    high_edge_taker_min_edge_bps=resolved_config.high_edge_taker_min_edge_bps,
                    high_edge_taker_max_spread_bps=resolved_config.high_edge_taker_max_spread_bps,
                    taker_max_entry_premium_bps=dynamic_taker_max_entry_premium_bps,
                    repricing_taker_max_entry_premium_bps=resolved_config.repricing_fallback_probe_taker_max_entry_premium_bps,
                    taker_slippage_guard_bps=resolved_config.taker_slippage_guard_bps,
                    taker_min_net_edge_after_premium_bps=max(
                        resolved_config.taker_min_net_edge_after_premium_bps,
                        resolved_config.repricing_fallback_probe_min_net_edge_bps,
                    ),
                    maker_quote_ttl_seconds=_feedback_maker_quote_ttl_seconds(
                        base_ttl=resolved_config.maker_quote_ttl_seconds,
                        feedback=execution_feedback,
                    ),
                    resolution_maker_quote_ttl_seconds=_feedback_resolution_maker_quote_ttl_seconds(
                        base_ttl=resolved_config.resolution_maker_quote_ttl_seconds,
                        feedback=execution_feedback,
                    ),
                    repricing_fallback_quote_ttl_seconds=_feedback_maker_quote_ttl_seconds(
                        base_ttl=resolved_config.repricing_fallback_quote_ttl_seconds,
                        feedback=execution_feedback,
                    ),
                    maker_aggressiveness=_feedback_maker_aggressiveness(
                        base_aggressiveness=resolved_config.maker_aggressiveness,
                        feedback=execution_feedback,
                    ),
                    route_policy_bias=route_policy_bias,
                    taker_cross_ticks=(1 if selection_action == "selective_market" else 0),
                )
                if probe_decision.route == "taker":
                    decision = probe_decision
                    repricing_fallback_probe_taker_active = True
                    repricing_fallback_probe_notional_multiplier = max(
                        0.0,
                        min(1.0, resolved_config.repricing_fallback_probe_notional_multiplier),
                    )
                else:
                    repricing_fallback_probe_taker_block_reason = "repricing_fallback_probe_route_not_taker"
        elif (
            classification.signal_type == "repricing_edge"
            and resolved_config.repricing_fallback_probe_taker_enabled
            and repricing_fallback_no_fill_attempts >= resolved_config.repricing_fallback_probe_after_no_fill_attempts
        ):
            if repricing_route_stage == "cooldown":
                repricing_fallback_probe_taker_block_reason = "repricing_route_stage_cooldown_active"
            else:
                repricing_fallback_probe_taker_block_reason = "repricing_route_stage_not_probe_or_escalation"
        quote_age_seconds = _snapshot_quote_age_seconds(snapshot)
        if _should_block_selective_repricing_taker_due_quote_age(
            decision=decision,
            classification=classification,
            selection_action=selection_action,
            quote_age_seconds=quote_age_seconds,
            max_quote_age_seconds=resolved_config.selective_repricing_taker_max_quote_age_seconds,
        ):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="selective_repricing_taker_stale_quote_blocked",
                extra={
                    "phase2_preset": resolved_config.preset_name,
                    "selection_action": selection_action,
                    "selection_reasons": list(selection_reasons),
                    "quote_age_seconds": quote_age_seconds,
                    "quote_age_threshold_seconds": resolved_config.selective_repricing_taker_max_quote_age_seconds,
                    "decision_route": decision.route,
                    "decision_rationale_tags": list(decision.rationale_tags),
                },
            )
            return []
        counterfactual_result = None
        if decision.route != "skip" and decision.target_price is not None:
            counterfactual_result = self._evaluate_counterfactual_entry_gate(
                snapshot=snapshot,
                fair_value=fair_value,
                classification=classification,
                execution_feedback=execution_feedback,
                context=context,
            )
            if counterfactual_result is not None and counterfactual_result.blocked:
                _record_runtime_skip(
                    context=context,
                    snapshot=snapshot,
                    reason=counterfactual_result.reason,
                    extra={
                        "phase2_preset": resolved_config.preset_name,
                        "counterfactual_current_score": counterfactual_result.current_score,
                        "counterfactual_best_market_id": counterfactual_result.best_market_id,
                        "counterfactual_best_score": counterfactual_result.best_score,
                        "counterfactual_current_rank": counterfactual_result.current_rank,
                        "counterfactual_candidate_count": counterfactual_result.candidate_count,
                        "counterfactual_top_candidates": list(counterfactual_result.top_candidates),
                    },
                )
                return []
        if decision.route == "skip" or decision.target_price is None:
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="entry_not_actionable",
                extra={
                    "eligibility_reason": eligibility.reason,
                    "decision_route": decision.route,
                    "decision_rationale_tags": list(decision.rationale_tags),
                    "phase2_preset": resolved_config.preset_name,
                    "signal_type": classification.signal_type,
                    "selection_action": selection_action,
                    "selection_reasons": list(selection_reasons),
                    "dynamic_gate_reason": (dynamic_gate.reason_tag if dynamic_gate is not None else "dynamic_disabled"),
                    "entry_execution_drag_bps": entry_execution_drag_bps,
                    "effective_min_net_edge_bps": effective_min_net_edge_bps,
                    "repricing_fallback_no_fill_attempts": repricing_fallback_no_fill_attempts,
                    "repricing_fallback_taker_escalated": repricing_fallback_taker_escalated,
                    "repricing_fallback_taker_escalation_block_reason": repricing_fallback_taker_escalation_block_reason,
                    "repricing_fallback_probe_taker_eligible": repricing_fallback_probe_taker_eligible,
                    "repricing_fallback_probe_taker_active": repricing_fallback_probe_taker_active,
                    "repricing_fallback_probe_taker_block_reason": repricing_fallback_probe_taker_block_reason,
                    "repricing_fallback_probe_bootstrap_eligible": repricing_fallback_probe_bootstrap_eligible,
                    "repricing_route_stage": repricing_route_stage,
                    "repricing_route_stage_source": repricing_route_stage_source,
                    "repricing_route_cooldown_active": repricing_route_cooldown_active,
                    "repricing_route_cooldown_until": repricing_route_cooldown_until_iso,
                    "repricing_market_no_fill_attempts": market_repricing_no_fill_attempts,
                    "repricing_family_no_fill_attempts": family_repricing_no_fill_attempts,
                },
            )
            return []

        quality_notional, quality_score, quality_multiplier, quality_status = _quality_weighted_default_notional(
            base_notional=resolved_config.default_notional,
            confidence=fair_value.confidence,
            net_edge_bps=eligibility.net_edge_bps,
            feedback=execution_feedback,
            config=resolved_config,
        )
        fragile_closer_state = _fragile_closer_notional_state_for_snapshot(
            snapshot=snapshot,
            context=context,
            config=resolved_config,
        )
        family_pnl_state = _family_pnl_notional_state_for_snapshot(
            snapshot=snapshot,
            context=context,
            config=resolved_config,
        )
        close_out_quality_guard_state = _close_out_quality_guard_state_for_snapshot(
            snapshot=snapshot,
            context=context,
            config=resolved_config,
        )
        if bool(close_out_quality_guard_state["blocked"]):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="close_out_quality_guard_blocked",
                extra={
                    "close_out_guard_status": close_out_quality_guard_state["status"],
                    "close_out_guard_stop_out_share": close_out_quality_guard_state["stop_out_share"],
                    "close_out_guard_realized_pnl_bps": close_out_quality_guard_state["average_realized_pnl_bps"],
                    "close_out_guard_closed_samples": close_out_quality_guard_state["closed_samples"],
                    "close_out_guard_cooldown_seconds": close_out_quality_guard_state["cooldown_seconds"],
                },
            )
            return []
        sized_notional = round(
            quality_notional
            * float(fragile_closer_state["multiplier"])
            * float(family_pnl_state["multiplier"]),
            4,
        )
        sized_notional = round(
            sized_notional * float(close_out_quality_guard_state["multiplier"]),
            4,
        )
        sized_notional = round(sized_notional * repricing_fallback_probe_notional_multiplier, 4)
        if (
            repricing_fallback_probe_taker_active
            and decision.target_price is not None
            and decision.target_price > 0
            and snapshot.min_order_size is not None
            and snapshot.min_order_size > 0
        ):
            min_probe_notional = float(snapshot.min_order_size) * float(decision.target_price)
            if sized_notional + 1e-9 < min_probe_notional:
                sized_notional = round(min_probe_notional, 4)
                repricing_fallback_probe_notional_floor_applied = True

        intent = build_order_intent(
            fair_value=fair_value,
            snapshot=snapshot,
            decision=decision,
            default_notional=sized_notional,
            taker_time_in_force=resolved_config.taker_time_in_force,
            strategy_id=self.strategy_id,
        )
        target_size = intent.notional if intent is not None else sized_notional
        refreshable_pending_order_exists = _has_refreshable_repricing_fallback_pending_order(
            snapshot=snapshot,
            dashboard=dashboard_state(context),
            context=context,
        )
        entry_repost_cooldown_seconds = (
            resolved_config.repricing_fallback_entry_repost_cooldown_seconds
            if _is_repricing_maker_fallback(decision)
            else resolved_config.entry_repost_cooldown_seconds
        )
        if _recently_reposted_order(
            snapshot=snapshot,
            context=context,
            target_price=decision.target_price,
            side=decision.side,
            cooldown_seconds=entry_repost_cooldown_seconds,
            allowed_event_types={"order.expired", "order.canceled"},
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="entry_repost_cooldown_active")
            return []
        if _recent_failed_entry_attempt(
            snapshot=snapshot,
            context=context,
            side=decision.side,
            cooldown_seconds=resolved_config.entry_failure_cooldown_seconds,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="entry_failure_cooldown_active")
            return []
        if (
            not refreshable_pending_order_exists
            and _recent_entry_activity_for_market(
                snapshot=snapshot,
                context=context,
                side=decision.side,
                cooldown_seconds=(
                    resolved_config.repricing_fallback_entry_market_cooldown_seconds
                    if _is_repricing_maker_fallback(decision)
                    else resolved_config.entry_market_cooldown_seconds
                ),
            )
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="entry_market_activity_lock_active")
            return []
        recent_no_fill_attempts = _market_recent_no_fill_attempts(
            snapshot=snapshot,
            context=context,
            side=decision.side,
        )
        if (
            not refreshable_pending_order_exists
            and _recent_no_fill_entry_activity_for_market(
                snapshot=snapshot,
                context=context,
                side=decision.side,
                cooldown_seconds=resolved_config.entry_no_fill_cooldown_seconds,
            )
        ):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="entry_no_fill_cooldown_active",
                extra={
                    "no_fill_attempts": recent_no_fill_attempts,
                    "no_fill_cooldown_seconds": resolved_config.entry_no_fill_cooldown_seconds,
                },
            )
            return []
        family_entry_cooldown_seconds = _family_entry_cooldown_seconds(
            snapshot=snapshot,
            config=resolved_config,
        )
        if (
            not refreshable_pending_order_exists
            and _recent_entry_activity_for_family(
                snapshot=snapshot,
                context=context,
                side=decision.side,
                cooldown_seconds=family_entry_cooldown_seconds,
            )
        ):
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="entry_family_activity_lock_active",
                extra={
                    "family_key": _market_family_key(snapshot),
                    "family_cooldown_seconds": family_entry_cooldown_seconds,
                },
            )
            return []
        if _market_no_fill_quarantined(
            snapshot=snapshot,
            context=context,
            side=decision.side,
            max_attempts=resolved_config.max_no_fill_entry_attempts_per_market,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="entry_market_no_fill_quarantined")
            return []
        if resolved_config.enforce_exposure_group_conflict_guard and _exposure_group_conflict_active(
            snapshot=snapshot,
            context=context,
            side=decision.side,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="exposure_group_conflict_active")
            return []
        if _thesis_entry_locked(
            snapshot=snapshot,
            context=context,
            side=decision.side,
            cooldown_seconds=resolved_config.thesis_entry_cooldown_seconds,
            single_active_market_per_thesis=resolved_config.single_active_market_per_thesis,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="entry_thesis_lock_active")
            return []
        family_budget_state = _family_trade_budget_state_for_snapshot(
            snapshot=snapshot,
            context=context,
            config=resolved_config,
        )
        if family_budget_state["blocked"]:
            _record_runtime_skip(
                context=context,
                snapshot=snapshot,
                reason="family_trade_budget_exhausted",
                extra={
                    "family_key": family_budget_state["family_key"],
                    "family_budget_cap_share": family_budget_state["cap_share"],
                    "family_projected_share": family_budget_state["projected_share"],
                    "family_sample_count": family_budget_state["sample_count"],
                    "family_entry_count": family_budget_state["family_entry_count"],
                    "family_total_entry_count": family_budget_state["total_entry_count"],
                },
            )
            return []
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=(intent.token_id if intent is not None else snapshot.token_id),
                fair_probability=fair_value.fair_probability,
                side=decision.side,
                confidence=fair_value.confidence,
                edge_bps=parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0,
                generated_at=snapshot.timestamp,
                target_price=decision.target_price,
                target_size=target_size,
                time_in_force=("IOC" if decision.route == "taker" else "GTC"),
                quote_ttl_seconds=decision.quote_ttl_seconds,
                rationale_tags=decision.rationale_tags,
                diagnostics={
                    "observed_probability": fair_value.observed_probability,
                    "gross_edge_bps": parse_float(fair_value.supporting_values, "gross_edge_bps") or 0.0,
                    "net_edge_bps": parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0,
                    "signal_type": classification.signal_type,
                    "execution_route": decision.route,
                    "decision_trace_version": resolved_config.decision_trace_version,
                    "entry_decision_reason_code": (
                        decision.rationale_tags[0] if decision.rationale_tags else "unknown"
                    ),
                    "entry_decision_rationale_tags": list(decision.rationale_tags),
                    "entry_eligibility_reason": eligibility.reason,
                    "entry_route_policy_bias": route_policy_bias,
                    "execution_feedback_bias": execution_feedback.recommended_route_bias if execution_feedback is not None else "none",
                    "execution_feedback_notional": sized_notional,
                    "execution_feedback_notional_pre_haircut": quality_notional,
                    "quality_sizing_score": quality_score,
                    "quality_sizing_multiplier": quality_multiplier,
                    "quality_sizing_status": quality_status,
                    "fragile_closer_notional_status": fragile_closer_state["status"],
                    "fragile_closer_notional_multiplier": fragile_closer_state["multiplier"],
                    "fragile_closer_notional_expired_ratio": fragile_closer_state["expired_ratio"],
                    "fragile_closer_notional_sample_count": fragile_closer_state["sample_count"],
                    "fragile_closer_notional_expired_count": fragile_closer_state["expired_count"],
                    "fragile_closer_notional_closed_count": fragile_closer_state["closed_count"],
                    "fragile_closer_notional_threshold": fragile_closer_state["threshold"],
                    "family_pnl_notional_status": family_pnl_state["status"],
                    "family_pnl_notional_multiplier": family_pnl_state["multiplier"],
                    "family_pnl_notional_closed_samples": family_pnl_state["closed_samples"],
                    "family_pnl_notional_submitted_notional": family_pnl_state["submitted_notional"],
                    "family_pnl_notional_closed_net_pnl": family_pnl_state["closed_net_pnl"],
                    "family_pnl_notional_ratio": family_pnl_state["pnl_per_notional"],
                    "close_out_quality_guard_status": close_out_quality_guard_state["status"],
                    "close_out_quality_guard_multiplier": close_out_quality_guard_state["multiplier"],
                    "close_out_quality_guard_blocked": close_out_quality_guard_state["blocked"],
                    "close_out_quality_guard_closed_samples": close_out_quality_guard_state["closed_samples"],
                    "close_out_quality_guard_stop_out_share": close_out_quality_guard_state["stop_out_share"],
                    "close_out_quality_guard_realized_pnl_bps": close_out_quality_guard_state["average_realized_pnl_bps"],
                    "close_out_quality_guard_dominant_reason": close_out_quality_guard_state["dominant_close_reason"],
                    "phase2_preset": resolved_config.preset_name,
                    "selection_action": selection_action,
                    "selection_reasons": list(selection_reasons),
                    "dynamic_min_net_edge_bps": dynamic_min_net_edge_bps,
                    "entry_execution_drag_bps": entry_execution_drag_bps,
                    "effective_min_net_edge_bps": effective_min_net_edge_bps,
                    "dynamic_taker_max_entry_premium_bps": dynamic_taker_max_entry_premium_bps,
                    "dynamic_repricing_taker_max_entry_premium_bps": dynamic_repricing_taker_max_entry_premium_bps,
                    "effective_taker_urgency_threshold": effective_taker_urgency_threshold,
                    "dynamic_gate_reason": (dynamic_gate.reason_tag if dynamic_gate is not None else "dynamic_disabled"),
                    "repricing_fallback_no_fill_attempts": repricing_fallback_no_fill_attempts,
                    "repricing_fallback_taker_escalated": repricing_fallback_taker_escalated,
                    "repricing_fallback_taker_escalation_block_reason": repricing_fallback_taker_escalation_block_reason,
                    "repricing_fallback_probe_taker_eligible": repricing_fallback_probe_taker_eligible,
                    "repricing_fallback_probe_taker_active": repricing_fallback_probe_taker_active,
                    "repricing_fallback_probe_taker_block_reason": repricing_fallback_probe_taker_block_reason,
                    "repricing_fallback_probe_bootstrap_eligible": repricing_fallback_probe_bootstrap_eligible,
                    "repricing_fallback_probe_notional_multiplier": repricing_fallback_probe_notional_multiplier,
                    "repricing_fallback_probe_notional_floor_applied": repricing_fallback_probe_notional_floor_applied,
                    "repricing_route_stage": repricing_route_stage,
                    "repricing_route_stage_source": repricing_route_stage_source,
                    "repricing_route_cooldown_active": repricing_route_cooldown_active,
                    "repricing_route_cooldown_until": repricing_route_cooldown_until_iso,
                    "repricing_market_no_fill_attempts": market_repricing_no_fill_attempts,
                    "repricing_family_no_fill_attempts": family_repricing_no_fill_attempts,
                    "recent_no_fill_attempts": recent_no_fill_attempts,
                    "counterfactual_blocked": (
                        counterfactual_result.blocked if counterfactual_result is not None else False
                    ),
                    "counterfactual_current_score": (
                        counterfactual_result.current_score if counterfactual_result is not None else None
                    ),
                    "counterfactual_best_market_id": (
                        counterfactual_result.best_market_id if counterfactual_result is not None else None
                    ),
                    "counterfactual_best_score": (
                        counterfactual_result.best_score if counterfactual_result is not None else None
                    ),
                    "counterfactual_current_rank": (
                        counterfactual_result.current_rank if counterfactual_result is not None else None
                    ),
                    "counterfactual_candidate_count": (
                        counterfactual_result.candidate_count if counterfactual_result is not None else 0
                    ),
                    "family_budget_blocked": family_budget_state["blocked"],
                    "family_budget_cap_share": family_budget_state["cap_share"],
                    "family_budget_projected_share": family_budget_state["projected_share"],
                    "family_budget_sample_count": family_budget_state["sample_count"],
                    "market_family_key": _market_family_key(snapshot),
                },
            )
        ]

    def _evaluate_counterfactual_entry_gate(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        classification: Any,
        execution_feedback: CryptoExecutionFeedback | None,
        context: Mapping[str, object],
    ) -> CryptoCounterfactualEntryResult | None:
        base_config = resolve_phase2_config_for_snapshot(base=self.config, snapshot=snapshot)
        if not base_config.counterfactual_entry_gate_enabled:
            return None
        fair_values = context.get("fair_values_by_market_id")
        if not isinstance(fair_values, Mapping):
            return None
        snapshots_by_market_id = context.get("snapshots_by_market_id")
        market_snapshot_map = snapshots_by_market_id if isinstance(snapshots_by_market_id, Mapping) else {}
        current_underlying_group = _snapshot_underlying_group(snapshot)
        candidates: list[dict[str, float | str]] = []
        for market_id, candidate_fair_value in fair_values.items():
            if not isinstance(market_id, str) or not isinstance(candidate_fair_value, FairValueEstimate):
                continue
            candidate_snapshot_raw = market_snapshot_map.get(market_id)
            candidate_snapshot = (
                snapshot
                if market_id == snapshot.market_id
                else (candidate_snapshot_raw if isinstance(candidate_snapshot_raw, MarketSnapshot) else None)
            )
            if candidate_snapshot is None:
                continue
            if candidate_snapshot.category != Category.CRYPTO:
                continue
            if _market_is_blocked(snapshot=candidate_snapshot, context=context) or _series_is_blocked(
                snapshot=candidate_snapshot, context=context
            ):
                continue
            candidate_underlying_group = _snapshot_underlying_group(candidate_snapshot)
            if (
                current_underlying_group is not None
                and candidate_underlying_group is not None
                and candidate_underlying_group != current_underlying_group
            ):
                continue
            max_age_seconds = max(0.0, base_config.counterfactual_entry_max_snapshot_age_seconds)
            if max_age_seconds > 0:
                age_seconds = abs((snapshot.timestamp - candidate_snapshot.timestamp).total_seconds())
                if age_seconds > max_age_seconds:
                    continue
            candidate_classification = classify_crypto_signal(fair_value=candidate_fair_value)
            if candidate_classification.signal_type == "no_trade":
                continue
            candidate_config = resolve_phase2_config_for_snapshot(base=self.config, snapshot=candidate_snapshot)
            candidate_dynamic_gate = _dynamic_eligibility_gate_for_snapshot(
                snapshot=candidate_snapshot,
                context=context,
            )
            candidate_dynamic_min_net_edge_bps = _effective_dynamic_min_net_edge_bps(
                base_min_net_edge_bps=candidate_config.min_net_edge_bps,
                gate=candidate_dynamic_gate,
                config=candidate_config,
            )
            candidate_entry_drag = _entry_execution_drag_bps(
                snapshot=candidate_snapshot,
                classification=candidate_classification,
                feedback=execution_feedback,
                config=candidate_config,
            )
            candidate_effective_min_net_edge_bps = candidate_dynamic_min_net_edge_bps + candidate_entry_drag
            candidate_eligibility = evaluate_trade_eligibility(
                fair_value=candidate_fair_value,
                snapshot=candidate_snapshot,
                classification=candidate_classification,
                min_confidence=candidate_config.min_confidence,
                min_net_edge_bps=candidate_effective_min_net_edge_bps,
                max_spread_bps=candidate_config.max_spread_bps,
                min_liquidity_score=candidate_config.min_liquidity_score,
                min_contract_price=candidate_config.min_contract_price,
                min_net_edge_reason="counterfactual_min_net_edge",
            )
            if not candidate_eligibility.eligible:
                continue
            candidate_spread_bps = spread_cost_bps(snapshot=candidate_snapshot, side=candidate_classification.side)
            score = counterfactual_entry_score(
                net_edge_bps=candidate_eligibility.net_edge_bps,
                confidence=candidate_fair_value.confidence,
                urgency_score=candidate_classification.urgency_score,
                spread_bps=candidate_spread_bps,
                net_edge_weight=candidate_config.counterfactual_entry_net_edge_weight,
                confidence_weight=candidate_config.counterfactual_entry_confidence_weight,
                urgency_weight=candidate_config.counterfactual_entry_urgency_weight,
                spread_weight=candidate_config.counterfactual_entry_spread_weight,
            )
            candidates.append(
                {
                    "market_id": candidate_snapshot.market_id,
                    "score": score,
                    "signal_type": candidate_classification.signal_type,
                }
            )
        candidates.sort(
            key=lambda item: (-float(item["score"]), str(item["market_id"])),
        )
        current_index = next(
            (
                idx
                for idx, item in enumerate(candidates)
                if str(item["market_id"]) == snapshot.market_id
            ),
            -1,
        )
        current_score = 0.0
        if current_index >= 0:
            current_score = float(candidates[current_index]["score"])
        else:
            current_score = counterfactual_entry_score(
                net_edge_bps=parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0,
                confidence=fair_value.confidence,
                urgency_score=classification.urgency_score,
                spread_bps=spread_cost_bps(snapshot=snapshot, side=classification.side),
                net_edge_weight=base_config.counterfactual_entry_net_edge_weight,
                confidence_weight=base_config.counterfactual_entry_confidence_weight,
                urgency_weight=base_config.counterfactual_entry_urgency_weight,
                spread_weight=base_config.counterfactual_entry_spread_weight,
            )
        best_market_id = str(candidates[0]["market_id"]) if candidates else None
        best_score = float(candidates[0]["score"]) if candidates else current_score
        min_candidates = max(1, base_config.counterfactual_entry_min_candidates)
        if len(candidates) < min_candidates:
            return CryptoCounterfactualEntryResult(
                blocked=False,
                reason="counterfactual_insufficient_candidates",
                current_market_id=snapshot.market_id,
                current_score=round(current_score, 4),
                best_market_id=best_market_id,
                best_score=round(best_score, 4),
                current_rank=max(1, current_index + 1) if current_index >= 0 else len(candidates) + 1,
                candidate_count=len(candidates),
                top_candidates=tuple(candidates[:3]),
            )
        top_k = max(1, base_config.counterfactual_entry_top_k)
        if current_index >= 0 and current_index < top_k:
            return CryptoCounterfactualEntryResult(
                blocked=False,
                reason="counterfactual_current_in_top_k",
                current_market_id=snapshot.market_id,
                current_score=round(current_score, 4),
                best_market_id=best_market_id,
                best_score=round(best_score, 4),
                current_rank=current_index + 1,
                candidate_count=len(candidates),
                top_candidates=tuple(candidates[:3]),
            )
        score_margin = best_score - current_score
        reason = (
            "counterfactual_replaced"
            if score_margin >= max(0.0, base_config.counterfactual_entry_min_score_margin_bps)
            else "counterfactual_margin_too_low"
        )
        return CryptoCounterfactualEntryResult(
            blocked=True,
            reason=reason,
            current_market_id=snapshot.market_id,
            current_score=round(current_score, 4),
            best_market_id=best_market_id,
            best_score=round(best_score, 4),
            current_rank=max(1, current_index + 1) if current_index >= 0 else len(candidates) + 1,
            candidate_count=len(candidates),
            top_candidates=tuple(candidates[:3]),
        )

    def _exit_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        position: PositionState,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        intent = _position_intent_for_market(snapshot=snapshot, context=context)
        execution_feedback = _execution_feedback(context)
        if intent is None:
            # Fallback: if runtime context missed the entry intent, reconstruct from live position data
            # so exit logic keeps running and positions can still close safely.
            classification = classify_crypto_signal(fair_value=fair_value)
            no_token_id = str(snapshot.metadata.get("no_token_id", "")).strip()
            inferred_entry_side = (
                SignalSide.BUY_NO
                if no_token_id and position.token_id == no_token_id
                else SignalSide.BUY_YES
            )
            if classification.side != inferred_entry_side:
                classification = type(classification)(
                    market_id=classification.market_id,
                    signal_type=classification.signal_type,
                    side=inferred_entry_side,
                    urgency_score=classification.urgency_score,
                    expected_exit_mode=classification.expected_exit_mode,
                    rationale_tags=classification.rationale_tags,
                )
            intent = build_position_intent(
                fair_value=fair_value,
                classification=classification,
                token_id=position.token_id,
                created_at=position.opened_at,
                entry_fill_price=position.average_entry_price,
                entry_mid_price=position.mark_price,
                entry_fill_source=None,
            )
        resolved_config = resolve_phase2_config_for_snapshot(base=self.config, snapshot=snapshot)
        escalated_entry_lineage = _has_repricing_fallback_taker_escalation_lineage(
            snapshot=snapshot,
            position=position,
            context=context,
        )
        if (
            not escalated_entry_lineage
            and intent.signal_type == "repricing_edge"
            and intent.entry_fill_source == "taker"
        ):
            escalated_entry_lineage = True
        (
            family_escalated_entry_exit_containment_enabled,
            family_escalated_entry_adverse_fill_exit_bps,
            family_escalated_entry_adverse_fill_max_remaining_edge_bps,
            family_escalated_entry_max_holding_multiplier,
        ) = _family_specific_escalated_entry_exit_policy(
            snapshot=snapshot,
            config=resolved_config,
        )
        escalated_entry_tail_guard_active = (
            family_escalated_entry_exit_containment_enabled
            and escalated_entry_lineage
        )

        exit_decision = evaluate_exit(
            fair_value=fair_value,
            position=position,
            intent=intent,
            best_bid_yes=snapshot.best_bid_yes,
            best_bid_no=snapshot.best_bid_no,
            as_of=snapshot.timestamp,
            exit_edge_bps=resolved_config.exit_edge_bps,
            stop_loss_bps=resolved_config.stop_loss_bps,
            max_holding_multiplier=resolved_config.max_holding_multiplier,
            execution_max_holding_seconds=resolved_config.execution_max_holding_seconds,
            min_holding_seconds_before_exit=resolved_config.min_holding_seconds_before_exit,
            aging_exit_edge_bps=resolved_config.aging_exit_edge_bps,
            stale_exit_edge_bps=resolved_config.stale_exit_edge_bps,
            aging_start_fraction=resolved_config.aging_start_fraction,
            stale_start_fraction=resolved_config.stale_start_fraction,
            stop_loss_min_ticks=resolved_config.stop_loss_min_ticks,
            tick_size=snapshot.tick_size,
            stop_loss_max_remaining_edge_bps=resolved_config.stop_loss_max_remaining_edge_bps,
            adverse_fill_exit_bps=resolved_config.adverse_fill_exit_bps,
            adverse_fill_max_remaining_edge_bps=resolved_config.adverse_fill_max_remaining_edge_bps,
            time_stop_max_remaining_edge_bps=resolved_config.time_stop_max_remaining_edge_bps,
            escalated_entry_tail_guard_enabled=escalated_entry_tail_guard_active,
            escalated_entry_adverse_fill_exit_bps=family_escalated_entry_adverse_fill_exit_bps,
            escalated_entry_adverse_fill_max_remaining_edge_bps=(
                family_escalated_entry_adverse_fill_max_remaining_edge_bps
            ),
            escalated_entry_max_holding_multiplier=family_escalated_entry_max_holding_multiplier,
        )
        if not exit_decision.should_exit or exit_decision.exit_side is None or exit_decision.target_price is None:
            return []

        exit_price = exit_decision.target_price
        time_in_force = "IOC"
        quote_ttl_seconds = None
        exit_retry_count = _exit_retry_count(
            snapshot=snapshot,
            position=position,
            context=context,
        )
        if exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop", "adverse_fill_reversal"}:
            force_ioc_suspended_by_feedback = _should_prefer_passive_time_stop_exit_due_feedback(
                exit_reason=exit_decision.reason,
                feedback=execution_feedback,
                suspension_enabled=resolved_config.time_stop_force_ioc_suspension_on_passive_feedback_enabled,
                min_taker_shortfall_bps=resolved_config.time_stop_force_ioc_suspension_min_taker_shortfall_bps,
            )
            if (
                (
                    not force_ioc_suspended_by_feedback
                    and _should_force_immediate_time_stop_exit(
                    intent=intent,
                    exit_reason=exit_decision.reason,
                    force_ioc_for_repricing_taker=resolved_config.time_stop_force_ioc_for_repricing_taker,
                    exit_price=exit_decision.target_price,
                    remaining_edge_bps=exit_decision.remaining_edge_bps,
                    min_adverse_move_bps=resolved_config.time_stop_force_ioc_min_adverse_move_bps,
                    exit_spread_bps=_snapshot_exit_spread_bps(
                        snapshot=snapshot,
                        exit_side=exit_decision.exit_side,
                    ),
                    max_spread_bps_for_force_ioc=resolved_config.time_stop_force_ioc_max_spread_bps,
                    max_remaining_edge_bps_for_force_ioc=resolved_config.time_stop_force_ioc_max_remaining_edge_bps,
                    skip_below_remaining_edge_bps_for_force_ioc=(
                        resolved_config.time_stop_force_ioc_skip_below_remaining_edge_bps
                    ),
                    )
                )
                or (
                    exit_decision.reason == "time_stop"
                    and exit_retry_count >= resolved_config.time_stop_force_ioc_after_expiries
                    and not force_ioc_suspended_by_feedback
                )
                or (
                    exit_decision.reason == "adverse_fill_reversal"
                    and (
                        resolved_config.adverse_fill_force_ioc
                        or exit_retry_count >= max(1, resolved_config.time_stop_force_ioc_after_expiries)
                    )
                )
            ):
                exit_price = exit_decision.target_price
                time_in_force = "IOC"
                quote_ttl_seconds = None
            else:
                exit_price, quote_ttl_seconds = _passive_exit_price(
                    snapshot=snapshot,
                    position=position,
                    exit_side=exit_decision.exit_side,
                    exit_reason=exit_decision.reason,
                    fallback_price=exit_decision.target_price,
                    retry_count=exit_retry_count,
                    time_stop_quote_ttl_seconds=resolved_config.time_stop_passive_quote_ttl_seconds,
                )
                time_in_force = "GTC"

        target_notional = (position.shares or 0.0) * exit_price
        target_notional = _scaled_exit_notional(
            full_notional=target_notional,
            reason=exit_decision.reason,
            retry_count=exit_retry_count,
            config=resolved_config,
        )
        if target_notional <= 0:
            return []

        existing_exit_order = _pending_exit_order(
            snapshot=snapshot,
            position=position,
            context=context,
        )
        if (
            existing_exit_order is not None
            and exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop", "adverse_fill_reversal"}
        ):
            return []
        if (
            existing_exit_order is None
            and exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop", "adverse_fill_reversal"}
            and _recent_active_exit_submission(
                snapshot=snapshot,
                context=context,
                cooldown_seconds=max(
                    resolved_config.exit_repost_cooldown_seconds,
                    float(quote_ttl_seconds or 0),
                ),
            )
        ):
            return []
        if (
            existing_exit_order is not None
            and abs(existing_exit_order.limit_price - exit_price) < 1e-9
            and existing_exit_order.time_in_force == time_in_force
            and existing_exit_order.quote_ttl_seconds == quote_ttl_seconds
        ):
            return []
        if (
            exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop", "adverse_fill_reversal"}
            and _recently_reposted_exit(
                snapshot=snapshot,
                position=position,
                context=context,
                target_price=exit_price,
                cooldown_seconds=resolved_config.exit_repost_cooldown_seconds,
            )
        ):
            return []
        if _recent_failed_exit_attempt(
            snapshot=snapshot,
            position=position,
            context=context,
            cooldown_seconds=resolved_config.exit_failure_cooldown_seconds,
        ):
            return []

        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=position.token_id,
                fair_probability=fair_value.fair_probability,
                side=exit_decision.exit_side,
                confidence=fair_value.confidence,
                edge_bps=max(0.0, exit_decision.remaining_edge_bps),
                generated_at=snapshot.timestamp,
                target_price=exit_price,
                target_size=target_notional,
                time_in_force=time_in_force,
                quote_ttl_seconds=quote_ttl_seconds,
                rationale_tags=exit_decision.rationale_tags,
                diagnostics={
                    "observed_probability": fair_value.observed_probability,
                    "gross_edge_bps": parse_float(fair_value.supporting_values, "gross_edge_bps") or 0.0,
                    "net_edge_bps": parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0,
                    "remaining_edge_bps": exit_decision.remaining_edge_bps,
                    "phase2_preset": resolved_config.preset_name,
                    "signal_type": "exit",
                    "execution_route": ("taker" if time_in_force == "IOC" else "maker"),
                    "escalated_entry_lineage": escalated_entry_lineage,
                    "escalated_entry_tail_guard_active": escalated_entry_tail_guard_active,
                    "escalated_entry_tail_guard_family_enabled": family_escalated_entry_exit_containment_enabled,
                    "escalated_entry_tail_guard_family_adverse_fill_exit_bps": (
                        family_escalated_entry_adverse_fill_exit_bps
                    ),
                    "escalated_entry_tail_guard_family_max_remaining_edge_bps": (
                        family_escalated_entry_adverse_fill_max_remaining_edge_bps
                    ),
                    "escalated_entry_tail_guard_family_max_holding_multiplier": (
                        family_escalated_entry_max_holding_multiplier
                    ),
                    "time_stop_force_ioc_suspended_by_feedback": (
                        force_ioc_suspended_by_feedback
                        if exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop", "adverse_fill_reversal"}
                        else False
                    ),
                },
            )
        ]


def _fair_value_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> FairValueEstimate | None:
    fair_values = context.get("fair_values_by_market_id")
    if isinstance(fair_values, Mapping):
        fair_value = fair_values.get(snapshot.market_id)
        if isinstance(fair_value, FairValueEstimate):
            return fair_value
    return None


def _fallback_exit_fair_value(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
) -> FairValueEstimate:
    observed_probability = _observed_probability_for_token(
        snapshot=snapshot,
        token_id=position.token_id,
    )
    return FairValueEstimate(
        market_id=snapshot.market_id,
        category=snapshot.category,
        fair_probability=observed_probability,
        confidence=0.0,
        half_life_seconds=60,
        observed_probability=observed_probability,
        model_id="crypto.phase2.fallback_exit_no_fair",
        rationale_tags=("fallback_exit_no_fair_value",),
        supporting_values={
            "gross_edge_bps": 0.0,
            "net_edge_bps": 0.0,
            "fallback_exit_no_fair_value": True,
        },
    )


def _observed_probability_for_token(
    *,
    snapshot: MarketSnapshot,
    token_id: str,
) -> float:
    no_token_id = str(snapshot.metadata.get("no_token_id", "")).strip()
    is_no_token = bool(no_token_id and token_id == no_token_id)
    best_bid = snapshot.best_bid_no if is_no_token else snapshot.best_bid_yes
    best_ask = snapshot.best_ask_no if is_no_token else snapshot.best_ask_yes
    if best_bid is not None and best_ask is not None:
        return max(0.01, min(0.99, (best_bid + best_ask) / 2.0))
    if best_bid is not None:
        return max(0.01, min(0.99, best_bid))
    if best_ask is not None:
        return max(0.01, min(0.99, best_ask))
    return 0.5


def _position_intent_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> CryptoPositionIntent | None:
    intents = context.get("position_intents_by_market_id")
    if isinstance(intents, Mapping):
        intent = intents.get(snapshot.market_id)
        if isinstance(intent, CryptoPositionIntent):
            return intent
    return None


def _reentry_state_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> CryptoReentryState | None:
    states = context.get("reentry_state_by_market_id")
    if isinstance(states, Mapping):
        state = states.get(snapshot.market_id)
        if isinstance(state, CryptoReentryState):
            return state
    return None


def _series_is_blocked(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> bool:
    blocked = context.get("blocked_series_keys")
    if not isinstance(blocked, (set, frozenset, tuple, list)):
        return False
    series_key = snapshot.metadata.get("event_slug")
    if not series_key:
        return False
    return str(series_key) in blocked


def _market_is_blocked(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> bool:
    blocked = context.get("blocked_market_ids")
    if not isinstance(blocked, (set, frozenset, tuple, list)):
        return False
    return snapshot.market_id in blocked


def _selection_action_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> str | None:
    actions = context.get("market_selection_actions")
    if isinstance(actions, Mapping):
        action = actions.get(snapshot.market_id)
        if isinstance(action, str):
            return action
    return None


def _selection_reasons_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> tuple[str, ...]:
    reasons = context.get("market_selection_reasons")
    if isinstance(reasons, Mapping):
        raw_value = reasons.get(snapshot.market_id)
        if isinstance(raw_value, tuple):
            return tuple(str(reason) for reason in raw_value)
        if isinstance(raw_value, list):
            return tuple(str(reason) for reason in raw_value)
    return ()


def _has_wide_spread_selection_reason(reasons: Sequence[str]) -> bool:
    return any(reason in {"wide_spread", "wide_runtime_spread"} for reason in reasons)


def _recent_negative_trade_closed(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "trade.closed" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _is_stop_out_trade_payload(payload):
            return False
        event_time = _event_timestamp(payload)
        if event_time is None:
            return False
        return (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds
    return False


def _market_loss_quarantined(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    max_loss_trades: int,
) -> bool:
    if max_loss_trades <= 0:
        return False
    loss_trades = 0
    for event in recent_runtime_events(context):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "trade.closed" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if _is_stop_out_trade_payload(payload):
            loss_trades += 1
            if loss_trades >= max_loss_trades:
                return True
    return False


def _exposure_group_recent_negative_trade_closed(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    exposure_group_id = _snapshot_exposure_group_id(snapshot)
    if exposure_group_id is None:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "trade.closed" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("exposure_group_id", "")).strip() != exposure_group_id:
            continue
        if not _is_stop_out_trade_payload(payload):
            return False
        event_time = _event_timestamp(payload)
        if event_time is None:
            return False
        return (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds
    return False


def _exposure_group_loss_quarantined(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    max_loss_trades: int,
) -> bool:
    if max_loss_trades <= 0:
        return False
    exposure_group_id = _snapshot_exposure_group_id(snapshot)
    if exposure_group_id is None:
        return False
    loss_trades = 0
    for event in recent_runtime_events(context):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "trade.closed" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("exposure_group_id", "")).strip() != exposure_group_id:
            continue
        if _is_stop_out_trade_payload(payload):
            loss_trades += 1
            if loss_trades >= max_loss_trades:
                return True
    return False


def _is_stop_out_trade_payload(payload: Mapping[str, object]) -> bool:
    close_reason = str(payload.get("close_reason", payload.get("reason", ""))).strip().lower()
    if close_reason:
        return close_reason in {"stop_loss", "adverse_fill_reversal"}
    realized_pnl = parse_float(payload, "realized_pnl")
    net_pnl = parse_float(payload, "net_pnl")
    effective_pnl = net_pnl if net_pnl is not None else (realized_pnl or 0.0)
    return effective_pnl < 0


def _should_force_immediate_time_stop_exit(
    *,
    intent: CryptoPositionIntent,
    exit_reason: str,
    force_ioc_for_repricing_taker: bool,
    exit_price: float,
    remaining_edge_bps: float,
    min_adverse_move_bps: float | None,
    exit_spread_bps: float | None,
    max_spread_bps_for_force_ioc: float | None,
    max_remaining_edge_bps_for_force_ioc: float | None,
    skip_below_remaining_edge_bps_for_force_ioc: float | None,
) -> bool:
    if (
        not force_ioc_for_repricing_taker
        or exit_reason != "time_stop"
        or intent.signal_type != "repricing_edge"
        or intent.entry_fill_source != "taker"
    ):
        return False
    if min_adverse_move_bps is None:
        return True
    entry_fill_price = intent.entry_fill_price
    if entry_fill_price is None or entry_fill_price <= 0:
        return True
    adverse_move_bps = max(0.0, (entry_fill_price - exit_price) / entry_fill_price * 10000.0)
    if adverse_move_bps < max(0.0, min_adverse_move_bps):
        return False
    if (
        max_spread_bps_for_force_ioc is not None
        and exit_spread_bps is not None
        and exit_spread_bps > max(0.0, max_spread_bps_for_force_ioc)
    ):
        return False
    if (
        max_remaining_edge_bps_for_force_ioc is not None
        and remaining_edge_bps > max(0.0, max_remaining_edge_bps_for_force_ioc)
    ):
        return False
    if (
        skip_below_remaining_edge_bps_for_force_ioc is not None
        and remaining_edge_bps <= max(0.0, skip_below_remaining_edge_bps_for_force_ioc)
    ):
        return False
    return True


def _should_prefer_passive_time_stop_exit_due_feedback(
    *,
    exit_reason: str,
    feedback: CryptoExecutionFeedback | None,
    suspension_enabled: bool,
    min_taker_shortfall_bps: float,
) -> bool:
    if not suspension_enabled or exit_reason != "time_stop" or feedback is None:
        return False
    if feedback.recommended_route_bias != "more_passive":
        return False
    return feedback.taker_shortfall_bps >= max(0.0, min_taker_shortfall_bps)


def _snapshot_exit_spread_bps(
    *,
    snapshot: MarketSnapshot,
    exit_side: SignalSide,
) -> float | None:
    if exit_side == SignalSide.SELL_YES:
        bid = snapshot.best_bid_yes
        ask = snapshot.best_ask_yes
    else:
        bid = snapshot.best_bid_no
        ask = snapshot.best_ask_no
    if bid is None or ask is None:
        return None
    midpoint = _midpoint(bid, ask)
    if midpoint is None or midpoint <= 0:
        return None
    return max(0.0, (ask - bid) / midpoint * 10000.0)


def _record_runtime_skip(
    *,
    context: Mapping[str, object],
    snapshot: MarketSnapshot,
    reason: str,
    extra: Mapping[str, object] | None = None,
) -> None:
    runtime_events = context.get("_strategy_runtime_events")
    if not isinstance(runtime_events, list):
        return
    payload: dict[str, object] = {
        "strategy_id": CryptoPhase2Strategy.strategy_id,
        "market_id": snapshot.market_id,
        "slug": snapshot.slug,
        "reason": reason,
        "updated_at": snapshot.timestamp.isoformat(),
    }
    if extra is not None:
        payload.update(dict(extra))
    runtime_events.append({"event_type": "strategy.skipped", "payload": payload})


def _execution_feedback(context: Mapping[str, object]) -> CryptoExecutionFeedback | None:
    feedback = context.get("execution_feedback")
    if isinstance(feedback, CryptoExecutionFeedback):
        return feedback
    return None


def _dynamic_eligibility_gate_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> CryptoDynamicEligibilityGate | None:
    payload = context.get("dynamic_eligibility_gates")
    if not isinstance(payload, Mapping):
        return None
    family_key = _market_family_key(snapshot)
    if family_key is None:
        return None
    gate = payload.get(family_key)
    if isinstance(gate, CryptoDynamicEligibilityGate):
        return gate
    return None


def _market_probation_state_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    config: CryptoPhase2Config,
) -> CryptoMarketProbationState | None:
    if not config.market_probation_enabled:
        return None
    payload = context.get("market_probation_state_by_market_id")
    if isinstance(payload, Mapping):
        state = payload.get(snapshot.market_id)
        if isinstance(state, CryptoMarketProbationState):
            return state
    return summarize_market_probation_state_from_events(
        market_id=snapshot.market_id,
        recent_events=recent_runtime_events(context),
        as_of=snapshot.timestamp,
        loss_streak_for_probation=max(1, config.market_probation_loss_streak_for_probation),
        loss_streak_for_quarantine=max(1, config.market_probation_loss_streak_for_quarantine),
        recovery_win_streak_required=max(1, config.market_probation_recovery_win_streak_required),
        cooldown_seconds=max(0.0, config.market_probation_cooldown_seconds),
    )


def _family_trade_budget_state_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    config: CryptoPhase2ResolvedConfig,
) -> dict[str, object]:
    result: dict[str, object] = {
        "blocked": False,
        "family_key": None,
        "cap_share": 1.0,
        "projected_share": 0.0,
        "sample_count": 0,
        "family_entry_count": 0,
        "total_entry_count": 0,
    }
    if not config.family_trade_budget_enabled:
        return result
    family_key = _market_family_key(snapshot)
    if family_key is None:
        return result
    result["family_key"] = family_key
    sample_count = 0
    dynamic_gates = context.get("dynamic_eligibility_gates")
    if isinstance(dynamic_gates, Mapping):
        gate = dynamic_gates.get(family_key)
        if isinstance(gate, CryptoDynamicEligibilityGate):
            sample_count = gate.sample_count
    result["sample_count"] = sample_count
    if sample_count < max(1, config.family_trade_budget_min_samples):
        return result
    feedback_by_family = context.get("execution_feedback_by_family")
    route_bias = "stable"
    if isinstance(feedback_by_family, Mapping):
        family_feedback = feedback_by_family.get(family_key)
        if isinstance(family_feedback, CryptoExecutionFeedback):
            route_bias = family_feedback.recommended_route_bias
    if route_bias == "more_passive":
        cap_share = _clamp(config.family_trade_budget_low_quality_share, floor=0.0, ceiling=1.0)
    elif route_bias == "more_aggressive":
        cap_share = _clamp(config.family_trade_budget_high_quality_share, floor=0.0, ceiling=1.0)
    else:
        cap_share = _clamp(config.family_trade_budget_stable_share, floor=0.0, ceiling=1.0)
    result["cap_share"] = cap_share
    lookback = max(1, config.family_trade_budget_lookback_events)
    recent_events = recent_runtime_events(context)
    window = recent_events[-lookback:] if len(recent_events) > lookback else recent_events
    snapshots_by_market_id = context.get("snapshots_by_market_id")
    market_snapshots = snapshots_by_market_id if isinstance(snapshots_by_market_id, Mapping) else {}
    family_entry_count = 0
    total_entry_count = 0
    for event in window:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "order.submitted" or not isinstance(payload, Mapping):
            continue
        market_id = str(payload.get("market_id", "")).strip()
        if not market_id:
            continue
        total_entry_count += 1
        if market_id == snapshot.market_id:
            entry_family = family_key
        else:
            candidate_snapshot = market_snapshots.get(market_id)
            if not isinstance(candidate_snapshot, MarketSnapshot):
                continue
            entry_family = _market_family_key(candidate_snapshot)
        if entry_family == family_key:
            family_entry_count += 1
    projected_share = (family_entry_count + 1) / (total_entry_count + 1)
    result["projected_share"] = round(projected_share, 4)
    result["family_entry_count"] = family_entry_count
    result["total_entry_count"] = total_entry_count
    result["blocked"] = projected_share > cap_share
    return result


def _fragile_closer_notional_state_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    config: CryptoPhase2ResolvedConfig,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "fragile_closer_disabled",
        "multiplier": 1.0,
        "threshold": 0.0,
        "sample_count": 0,
        "expired_count": 0,
        "closed_count": 0,
        "expired_ratio": 0.0,
    }
    if not config.fragile_closer_notional_haircut_enabled:
        return result
    result["status"] = "fragile_closer_insufficient_samples"
    threshold = _clamp(config.fragile_closer_notional_haircut_expired_ratio_threshold, floor=0.0, ceiling=1.0)
    result["threshold"] = round(threshold, 4)
    lookback = max(1, config.fragile_closer_notional_haircut_lookback_events)
    recent_events = recent_runtime_events(context)
    window = recent_events[-lookback:] if len(recent_events) > lookback else recent_events
    expired_count = 0
    closed_count = 0
    for event in window:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")).strip() != snapshot.market_id:
            continue
        if event_type == "order.expired":
            expired_count += 1
            continue
        if event_type == "order.canceled":
            cancel_reason = str(payload.get("reason", "")).strip().lower()
            if cancel_reason in {"stale_ttl_cancel", "exchange_canceled"}:
                expired_count += 1
            continue
        if event_type in {"trade.closed", "position.closed"}:
            closed_count += 1
    sample_count = expired_count + closed_count
    result["sample_count"] = sample_count
    result["expired_count"] = expired_count
    result["closed_count"] = closed_count
    if sample_count < max(1, config.fragile_closer_notional_haircut_min_samples):
        return result
    expired_ratio = expired_count / sample_count
    result["expired_ratio"] = round(expired_ratio, 4)
    min_multiplier = _clamp(config.fragile_closer_notional_haircut_min_multiplier, floor=0.0, ceiling=1.0)
    max_multiplier = _clamp(
        config.fragile_closer_notional_haircut_max_multiplier,
        floor=min_multiplier,
        ceiling=1.0,
    )
    if expired_ratio <= threshold:
        result["status"] = "fragile_closer_healthy"
        result["multiplier"] = round(max_multiplier, 4)
        return result
    normalized_gap = (expired_ratio - threshold) / max(1e-9, 1.0 - threshold)
    raw_multiplier = max_multiplier - (max_multiplier - min_multiplier) * normalized_gap
    result["multiplier"] = round(_clamp(raw_multiplier, floor=min_multiplier, ceiling=max_multiplier), 4)
    result["status"] = "fragile_closer_haircut_applied"
    return result


def _family_pnl_notional_state_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    config: CryptoPhase2ResolvedConfig,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "family_pnl_haircut_disabled",
        "multiplier": 1.0,
        "closed_samples": 0,
        "submitted_notional": 0.0,
        "closed_net_pnl": 0.0,
        "pnl_per_notional": 0.0,
    }
    if not config.family_pnl_notional_haircut_enabled:
        return result
    family_key = _market_family_key(snapshot)
    if family_key is None:
        result["status"] = "family_pnl_haircut_no_family"
        return result
    result["status"] = "family_pnl_haircut_insufficient_samples"
    lookback = max(1, config.family_pnl_notional_haircut_lookback_events)
    recent_events = recent_runtime_events(context)
    window = recent_events[-lookback:] if len(recent_events) > lookback else recent_events
    submitted_notional = 0.0
    closed_net_pnl = 0.0
    closed_samples = 0
    for event in window:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if _payload_market_family_key(payload) != family_key:
            continue
        if event_type == "order.submitted":
            try:
                submitted_notional += max(0.0, float(payload.get("notional", 0.0) or 0.0))
            except (TypeError, ValueError):
                continue
            continue
        if event_type == "trade.closed":
            try:
                closed_net_pnl += float(payload.get("net_pnl", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            closed_samples += 1
    result["closed_samples"] = closed_samples
    result["submitted_notional"] = round(submitted_notional, 6)
    result["closed_net_pnl"] = round(closed_net_pnl, 6)
    if closed_samples < max(1, config.family_pnl_notional_haircut_min_closed_samples) or submitted_notional <= 0:
        return result
    pnl_per_notional = closed_net_pnl / submitted_notional
    result["pnl_per_notional"] = round(pnl_per_notional, 6)
    min_multiplier = _clamp(config.family_pnl_notional_haircut_min_multiplier, floor=0.0, ceiling=1.0)
    max_multiplier = _clamp(
        config.family_pnl_notional_haircut_max_multiplier,
        floor=min_multiplier,
        ceiling=1.0,
    )
    full_haircut_ratio = min(
        -1e-6,
        float(config.family_pnl_notional_haircut_full_haircut_pnl_per_notional),
    )
    if pnl_per_notional > 0:
        result["status"] = "family_pnl_haircut_healthy"
        result["multiplier"] = round(max_multiplier, 4)
        return result
    severity = min(1.0, max(0.0, abs(pnl_per_notional) / abs(full_haircut_ratio)))
    raw_multiplier = max_multiplier - (max_multiplier - min_multiplier) * severity
    result["multiplier"] = round(_clamp(raw_multiplier, floor=min_multiplier, ceiling=max_multiplier), 4)
    result["status"] = "family_pnl_haircut_applied"
    return result


def _close_out_quality_guard_state_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    config: CryptoPhase2ResolvedConfig,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "close_out_quality_guard_disabled",
        "multiplier": 1.0,
        "blocked": False,
        "closed_samples": 0,
        "stop_out_share": 0.0,
        "average_realized_pnl_bps": 0.0,
        "dominant_close_reason": "none",
        "cooldown_seconds": 0.0,
    }
    if not config.close_out_quality_guard_enabled:
        return result

    recent_events = recent_runtime_events(context)
    lookback = max(1, config.close_out_quality_guard_lookback_events)
    window = recent_events[-lookback:] if len(recent_events) > lookback else recent_events
    summary = summarize_close_out_quality_from_events(
        recent_events=window,
        market_id=snapshot.market_id,
    )
    closed_samples = int(summary["closed_count"])
    stop_out_share = float(summary["stop_out_share"])
    average_realized_pnl_bps = float(summary["average_realized_pnl_bps"])
    dominant_close_reason = str(summary["dominant_close_reason"])
    result["closed_samples"] = closed_samples
    result["stop_out_share"] = round(stop_out_share, 4)
    result["average_realized_pnl_bps"] = round(average_realized_pnl_bps, 4)
    result["dominant_close_reason"] = dominant_close_reason
    result["status"] = "close_out_quality_guard_insufficient_samples"

    min_closed_samples = max(1, config.close_out_quality_guard_min_closed_samples)
    if closed_samples < min_closed_samples:
        return result

    max_stop_out_share = _clamp(config.close_out_quality_guard_max_stop_out_share, floor=0.0, ceiling=1.0)
    min_realized_pnl_bps = float(config.close_out_quality_guard_min_realized_pnl_bps)
    stop_out_excess = max(0.0, stop_out_share - max_stop_out_share)
    stop_out_severity = stop_out_excess / max(1e-9, 1.0 - max_stop_out_share)
    pnl_shortfall = max(0.0, min_realized_pnl_bps - average_realized_pnl_bps)
    pnl_severity = pnl_shortfall / max(1.0, abs(min_realized_pnl_bps) + 100.0)
    severity = max(0.0, min(1.0, max(stop_out_severity, pnl_severity)))

    if severity <= 0:
        result["status"] = "close_out_quality_guard_healthy"
        return result

    min_multiplier = _clamp(config.close_out_quality_guard_notional_min_multiplier, floor=0.0, ceiling=1.0)
    max_multiplier = _clamp(
        config.close_out_quality_guard_notional_max_multiplier,
        floor=min_multiplier,
        ceiling=1.0,
    )
    raw_multiplier = max_multiplier - (max_multiplier - min_multiplier) * severity
    result["multiplier"] = round(_clamp(raw_multiplier, floor=min_multiplier, ceiling=max_multiplier), 4)
    result["status"] = "close_out_quality_guard_notional_haircut_applied"

    latest_closed_at = summary.get("latest_closed_at")
    cooldown_seconds = max(0.0, float(config.close_out_quality_guard_entry_cooldown_seconds))
    result["cooldown_seconds"] = cooldown_seconds
    if (
        cooldown_seconds > 0
        and isinstance(latest_closed_at, datetime)
        and (snapshot.timestamp - latest_closed_at).total_seconds() < cooldown_seconds
    ):
        result["blocked"] = True
        result["status"] = "close_out_quality_guard_cooldown_active"
    return result


def _effective_dynamic_min_net_edge_bps(
    *,
    base_min_net_edge_bps: float,
    gate: CryptoDynamicEligibilityGate | None,
    config: CryptoPhase2Config,
) -> float:
    if not config.dynamic_gates_enabled or gate is None or gate.sample_count < config.dynamic_gate_min_samples:
        return base_min_net_edge_bps
    clipped = _clamp(
        gate.min_net_edge_bps,
        floor=config.dynamic_min_net_edge_floor_bps,
        ceiling=config.dynamic_min_net_edge_ceiling_bps,
    )
    return clipped


def _effective_dynamic_taker_max_entry_premium_bps(
    *,
    base_taker_max_entry_premium_bps: float,
    gate: CryptoDynamicEligibilityGate | None,
    config: CryptoPhase2Config,
) -> float:
    if not config.dynamic_gates_enabled or gate is None or gate.sample_count < config.dynamic_gate_min_samples:
        return base_taker_max_entry_premium_bps
    clipped = _clamp(
        gate.taker_max_entry_premium_bps,
        floor=config.dynamic_taker_max_entry_premium_floor_bps,
        ceiling=config.dynamic_taker_max_entry_premium_ceiling_bps,
    )
    return clipped


def _effective_dynamic_repricing_taker_max_entry_premium_bps(
    *,
    base_repricing_taker_max_entry_premium_bps: float,
    gate: CryptoDynamicEligibilityGate | None,
    config: CryptoPhase2Config,
) -> float:
    if not config.dynamic_gates_enabled or gate is None or gate.sample_count < config.dynamic_gate_min_samples:
        return base_repricing_taker_max_entry_premium_bps
    clipped = _clamp(
        gate.repricing_taker_max_entry_premium_bps,
        floor=config.dynamic_repricing_taker_max_entry_premium_floor_bps,
        ceiling=config.dynamic_repricing_taker_max_entry_premium_ceiling_bps,
    )
    return clipped


def _min_net_edge_reason_for_dynamic_gate(
    *,
    base_min_net_edge_bps: float,
    effective_min_net_edge_bps: float,
) -> str:
    if effective_min_net_edge_bps > base_min_net_edge_bps:
        return "cost_regime_min_net_edge"
    return "insufficient_net_edge"


def _min_net_edge_reason_for_dynamic_gate_and_drag(
    *,
    base_min_net_edge_bps: float,
    dynamic_min_net_edge_bps: float,
    effective_min_net_edge_bps: float,
    dynamic_reason: str,
) -> str:
    if effective_min_net_edge_bps > dynamic_min_net_edge_bps:
        return "execution_drag_min_net_edge"
    return _min_net_edge_reason_for_dynamic_gate(
        base_min_net_edge_bps=base_min_net_edge_bps,
        effective_min_net_edge_bps=dynamic_min_net_edge_bps,
    ) if dynamic_reason == "insufficient_net_edge" else dynamic_reason


def _entry_execution_drag_bps(
    *,
    snapshot: MarketSnapshot,
    classification: CryptoSignalClassification,
    feedback: CryptoExecutionFeedback | None,
    config: CryptoPhase2ResolvedConfig,
) -> float:
    spread_component = max(0.0, config.entry_execution_spread_weight) * spread_cost_bps(
        snapshot=snapshot,
        side=classification.side,
    )
    feedback_shortfall = feedback.taker_shortfall_bps if feedback is not None else 0.0
    feedback_component = max(0.0, config.entry_execution_feedback_weight) * max(0.0, feedback_shortfall)
    explicit_component = max(0.0, config.entry_execution_drag_bps)
    drag = explicit_component + spread_component + feedback_component
    cap = max(0.0, config.entry_execution_drag_cap_bps)
    return _clamp(drag, floor=0.0, ceiling=cap)


def _scaled_exit_notional(
    *,
    full_notional: float,
    reason: str,
    retry_count: int,
    config: CryptoPhase2ResolvedConfig,
) -> float:
    if full_notional <= 0:
        return 0.0
    if not config.exit_scaleout_enabled or retry_count > 0:
        return full_notional
    fraction = 1.0
    if reason == "time_stop":
        fraction = config.time_stop_scaleout_fraction
    elif reason == "adverse_fill_reversal":
        fraction = config.adverse_fill_scaleout_fraction
    fraction = _clamp(fraction, floor=0.05, ceiling=1.0)
    if fraction >= 0.999:
        return full_notional
    scaled = full_notional * fraction
    min_notional = max(0.0, config.exit_scaleout_min_notional)
    if min_notional > 0.0:
        scaled = max(scaled, min_notional)
    return min(full_notional, scaled)


def _quality_weighted_default_notional(
    *,
    base_notional: float,
    confidence: float,
    net_edge_bps: float,
    feedback: CryptoExecutionFeedback | None,
    config: CryptoPhase2Config,
) -> tuple[float, float | None, float, str]:
    if not config.quality_sizing_enabled:
        return base_notional, None, 1.0, "quality_sizing_disabled"
    if feedback is None:
        return base_notional, None, 1.0, "quality_components_missing"
    confidence_component = _clamp(confidence, floor=0.0, ceiling=1.0)
    edge_reference = max(1.0, config.quality_sizing_edge_reference_bps)
    edge_component = _clamp(net_edge_bps / edge_reference, floor=0.0, ceiling=1.0)
    route_feedback_component = _route_feedback_quality_component(feedback=feedback)
    total_weight = (
        config.quality_sizing_confidence_weight
        + config.quality_sizing_edge_weight
        + config.quality_sizing_route_feedback_weight
    )
    if total_weight <= 0:
        return base_notional, None, 1.0, "invalid_quality_weights"
    min_multiplier = min(config.quality_sizing_min_multiplier, config.quality_sizing_max_multiplier)
    max_multiplier = max(config.quality_sizing_min_multiplier, config.quality_sizing_max_multiplier)
    quality_score = (
        confidence_component * config.quality_sizing_confidence_weight
        + edge_component * config.quality_sizing_edge_weight
        + route_feedback_component * config.quality_sizing_route_feedback_weight
    ) / total_weight
    multiplier_span = max_multiplier - min_multiplier
    multiplier = min_multiplier + (quality_score * multiplier_span)
    if feedback.recommended_route_bias == "more_passive":
        multiplier = min(multiplier, 1.0)
    elif feedback.recommended_route_bias == "more_aggressive":
        multiplier = max(multiplier, 1.0)
    multiplier = _clamp(
        multiplier,
        floor=min_multiplier,
        ceiling=max_multiplier,
    )
    notional = round(base_notional * multiplier, 4)
    return notional, round(quality_score, 4), round(multiplier, 4), "quality_sizing_applied"


def _route_feedback_quality_component(*, feedback: CryptoExecutionFeedback) -> float:
    maker_fill_component = _clamp(feedback.maker_fill_rate, floor=0.0, ceiling=1.0)
    expiration_penalty = _clamp(feedback.repeated_expiration_rate, floor=0.0, ceiling=1.0)
    stop_out_penalty = _clamp(feedback.repeated_stop_out_rate, floor=0.0, ceiling=1.0)
    shortfall_penalty = _clamp(feedback.taker_shortfall_bps / 200.0, floor=0.0, ceiling=1.0)
    quality = (
        0.55 * maker_fill_component
        + 0.20 * (1.0 - expiration_penalty)
        + 0.20 * (1.0 - stop_out_penalty)
        + 0.05 * (1.0 - shortfall_penalty)
    )
    return _clamp(quality, floor=0.0, ceiling=1.0)


def _feedback_maker_aggressiveness(
    *,
    base_aggressiveness: float,
    feedback: CryptoExecutionFeedback | None,
) -> float:
    if feedback is None:
        return base_aggressiveness
    if feedback.recommended_route_bias == "more_passive":
        return max(0.5, round(base_aggressiveness * 0.85, 4))
    if feedback.recommended_route_bias == "more_aggressive":
        return min(2.0, round(base_aggressiveness * 1.25, 4))
    return base_aggressiveness


def _feedback_taker_urgency_threshold(
    *,
    base_threshold: float,
    feedback: CryptoExecutionFeedback | None,
) -> float:
    if feedback is None:
        return base_threshold
    if feedback.recommended_route_bias == "more_passive":
        return min(0.95, round(base_threshold + 0.08, 4))
    if feedback.recommended_route_bias == "more_aggressive":
        return max(0.55, round(base_threshold - 0.08, 4))
    return base_threshold


def _feedback_maker_quote_ttl_seconds(
    *,
    base_ttl: int,
    feedback: CryptoExecutionFeedback | None,
) -> int:
    if feedback is None:
        return base_ttl
    if feedback.recommended_route_bias == "more_passive":
        return int(round(base_ttl * 1.25))
    if feedback.recommended_route_bias == "more_aggressive":
        return max(15, int(round(base_ttl * 0.75)))
    return base_ttl


def _feedback_resolution_maker_quote_ttl_seconds(
    *,
    base_ttl: int,
    feedback: CryptoExecutionFeedback | None,
) -> int:
    if feedback is None:
        return base_ttl
    if feedback.recommended_route_bias == "more_passive":
        return int(round(base_ttl * 1.2))
    if feedback.recommended_route_bias == "more_aggressive":
        return max(30, int(round(base_ttl * 0.8)))
    return base_ttl


def _clamp(value: float, *, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))


def _market_family_key(snapshot: MarketSnapshot) -> str | None:
    text = " ".join(
        (
            str(snapshot.metadata.get("question", "")),
            snapshot.slug,
            str(snapshot.metadata.get("event_title", "")),
        )
    ).lower()
    if "bitcoin" in text or "btc" in text:
        underlying = "BTC"
    elif "ethereum" in text or "eth" in text:
        underlying = "ETH"
    else:
        return None
    if any(token in text for token in ("dip", "drop", "fall", "below", "under")):
        event_family = "dip"
    elif any(token in text for token in ("reach", "hit", "above", "over")):
        event_family = "reach"
    else:
        return None
    return f"{underlying}:{event_family}"


def _route_policy_bias_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    signal_type: str,
    context: Mapping[str, object],
) -> str:
    state = _route_policy_state_for_snapshot(
        snapshot=snapshot,
        signal_type=signal_type,
        context=context,
    )
    if isinstance(state, CryptoRoutePolicyState):
        return state.route_bias
    return "stable"


def _route_policy_state_for_snapshot(
    *,
    snapshot: MarketSnapshot,
    signal_type: str,
    context: Mapping[str, object],
) -> CryptoRoutePolicyState | None:
    payload = context.get("route_policy_state_by_key")
    if not isinstance(payload, Mapping):
        return None
    family_key = _market_family_key(snapshot)
    if family_key is None:
        return None
    route_key = f"{family_key}:{signal_type}"
    state = payload.get(route_key)
    if isinstance(state, CryptoRoutePolicyState):
        return state
    return None


def _repricing_route_stage_from_no_fill_progression(
    *,
    no_fill_attempts: int,
    probe_enabled: bool,
    probe_after_no_fill_attempts: int,
    taker_after_no_fill_attempts: int,
) -> str:
    if taker_after_no_fill_attempts > 0 and no_fill_attempts >= taker_after_no_fill_attempts:
        return "escalation"
    if probe_enabled and probe_after_no_fill_attempts > 0 and no_fill_attempts >= probe_after_no_fill_attempts:
        return "probe"
    return "maker"


def _resolve_repricing_route_stage(
    *,
    snapshot: MarketSnapshot,
    signal_type: str,
    context: Mapping[str, object],
    as_of: datetime,
    base_stage: str,
) -> tuple[str, str, bool, datetime | None]:
    state = _route_policy_state_for_snapshot(
        snapshot=snapshot,
        signal_type=signal_type,
        context=context,
    )
    if (
        state is not None
        and state.repricing_route_stage == "cooldown"
        and as_of < state.repricing_route_cooldown_until
    ):
        return ("cooldown", "policy_cooldown", True, state.repricing_route_cooldown_until)
    return (base_stage, "no_fill_progression", False, None)


def _allow_taker_routes_for_selection(
    *,
    snapshot: MarketSnapshot,
    selection_action: str,
    route_policy_bias: str,
    feedback: CryptoExecutionFeedback | None,
    config: CryptoPhase2Config,
) -> bool:
    if selection_action != "selective_market":
        return True
    aggressive_route = (
        route_policy_bias == "more_aggressive"
        or (feedback is not None and feedback.recommended_route_bias == "more_aggressive")
    )
    family_allow, family_allow_when_aggressive = _family_specific_selective_taker_policy(
        snapshot=snapshot,
        config=config,
    )
    if family_allow is not None or family_allow_when_aggressive is not None:
        if family_allow is True:
            return True
        if family_allow is False:
            return bool(family_allow_when_aggressive) and aggressive_route
        if family_allow_when_aggressive is False:
            return False
        return bool(family_allow_when_aggressive) and aggressive_route
    if config.selective_market_allow_taker:
        return True
    if not config.selective_market_allow_taker_when_aggressive:
        return False
    return aggressive_route


def _family_specific_selective_taker_policy(
    *,
    snapshot: MarketSnapshot,
    config: CryptoPhase2Config,
) -> tuple[bool | None, bool | None]:
    family_key = _market_family_key(snapshot)
    if family_key is None:
        return (None, None)
    _, _, event_family = family_key.partition(":")
    if event_family == "reach":
        return (
            config.selective_market_allow_taker_reach,
            config.selective_market_allow_taker_when_aggressive_reach,
        )
    if event_family == "dip":
        return (
            config.selective_market_allow_taker_dip,
            config.selective_market_allow_taker_when_aggressive_dip,
        )
    return (None, None)


def _family_specific_escalated_entry_exit_policy(
    *,
    snapshot: MarketSnapshot,
    config: CryptoPhase2Config,
) -> tuple[bool, float | None, float | None, float | None]:
    family_key = _market_family_key(snapshot)
    if family_key is None:
        return (
            config.escalated_entry_exit_containment_enabled,
            config.escalated_entry_adverse_fill_exit_bps,
            config.escalated_entry_adverse_fill_max_remaining_edge_bps,
            config.escalated_entry_max_holding_multiplier,
        )
    _, _, event_family = family_key.partition(":")
    if event_family == "reach":
        enabled = (
            config.escalated_entry_exit_containment_enabled
            if config.escalated_entry_exit_containment_enabled_reach is None
            else config.escalated_entry_exit_containment_enabled_reach
        )
        return (
            enabled,
            (
                config.escalated_entry_adverse_fill_exit_bps
                if config.escalated_entry_adverse_fill_exit_bps_reach is None
                else config.escalated_entry_adverse_fill_exit_bps_reach
            ),
            (
                config.escalated_entry_adverse_fill_max_remaining_edge_bps
                if config.escalated_entry_adverse_fill_max_remaining_edge_bps_reach is None
                else config.escalated_entry_adverse_fill_max_remaining_edge_bps_reach
            ),
            (
                config.escalated_entry_max_holding_multiplier
                if config.escalated_entry_max_holding_multiplier_reach is None
                else config.escalated_entry_max_holding_multiplier_reach
            ),
        )
    if event_family == "dip":
        enabled = (
            config.escalated_entry_exit_containment_enabled
            if config.escalated_entry_exit_containment_enabled_dip is None
            else config.escalated_entry_exit_containment_enabled_dip
        )
        return (
            enabled,
            (
                config.escalated_entry_adverse_fill_exit_bps
                if config.escalated_entry_adverse_fill_exit_bps_dip is None
                else config.escalated_entry_adverse_fill_exit_bps_dip
            ),
            (
                config.escalated_entry_adverse_fill_max_remaining_edge_bps
                if config.escalated_entry_adverse_fill_max_remaining_edge_bps_dip is None
                else config.escalated_entry_adverse_fill_max_remaining_edge_bps_dip
            ),
            (
                config.escalated_entry_max_holding_multiplier
                if config.escalated_entry_max_holding_multiplier_dip is None
                else config.escalated_entry_max_holding_multiplier_dip
            ),
        )
    return (
        config.escalated_entry_exit_containment_enabled,
        config.escalated_entry_adverse_fill_exit_bps,
        config.escalated_entry_adverse_fill_max_remaining_edge_bps,
        config.escalated_entry_max_holding_multiplier,
    )


def _family_entry_cooldown_seconds(
    *,
    snapshot: MarketSnapshot,
    config: CryptoPhase2Config,
) -> float:
    family_key = _market_family_key(snapshot)
    if family_key is None:
        return max(0.0, float(config.entry_family_cooldown_seconds))
    _, _, event_family = family_key.partition(":")
    if event_family == "reach" and config.entry_family_cooldown_seconds_reach is not None:
        return max(0.0, float(config.entry_family_cooldown_seconds_reach))
    if event_family == "dip" and config.entry_family_cooldown_seconds_dip is not None:
        return max(0.0, float(config.entry_family_cooldown_seconds_dip))
    return max(0.0, float(config.entry_family_cooldown_seconds))


def _is_repricing_maker_fallback(decision: Any) -> bool:
    return (
        getattr(decision, "route", None) == "maker"
        and tuple(getattr(decision, "rationale_tags", ())) in {
            ("repricing_taker_too_expensive", "maker_fallback"),
            ("repricing_taker_edge_buffer_too_thin", "maker_fallback"),
        }
    )


def _market_pending_orders_block_entry(
    *,
    snapshot: MarketSnapshot,
    dashboard: DashboardState | None,
    context: Mapping[str, object],
) -> bool:
    if dashboard is None:
        return False
    market_orders = tuple(
        order
        for order in dashboard.pending_orders
        if order.market_id == snapshot.market_id
    )
    if not market_orders:
        return False
    return any(
        not _pending_order_is_refreshable_repricing_fallback(
            order=order,
            snapshot=snapshot,
            context=context,
        )
        for order in market_orders
    )


def _has_refreshable_repricing_fallback_pending_order(
    *,
    snapshot: MarketSnapshot,
    dashboard: DashboardState | None,
    context: Mapping[str, object],
) -> bool:
    if dashboard is None:
        return False
    return any(
        _pending_order_is_refreshable_repricing_fallback(
            order=order,
            snapshot=snapshot,
            context=context,
        )
        for order in dashboard.pending_orders
        if order.market_id == snapshot.market_id
    )


def _pending_order_is_refreshable_repricing_fallback(
    *,
    order: PendingOrderState,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> bool:
    if order.market_id != snapshot.market_id:
        return False
    if order.strategy_id != CryptoPhase2Strategy.strategy_id:
        return False
    if str(order.time_in_force or "").upper() != "GTC":
        return False
    if order.matched_shares > 0:
        return False
    if not _pending_order_submission_has_rationale(
        order_id=order.order_id,
        context=context,
        rationale_tags={
            ("repricing_taker_too_expensive", "maker_fallback"),
            ("repricing_taker_edge_buffer_too_thin", "maker_fallback"),
            ("repricing_edge", "maker"),
        },
    ):
        return False
    effective_ttl = order.quote_ttl_seconds if order.quote_ttl_seconds is not None else 0
    maturity_seconds = max(1.0, float(effective_ttl) * 0.5)
    age_seconds = max(
        0.0,
        (snapshot.timestamp - order.created_at.astimezone(timezone.utc)).total_seconds(),
    )
    return age_seconds >= maturity_seconds


def _pending_order_submission_has_rationale(
    *,
    order_id: str,
    context: Mapping[str, object],
    rationale_tags: set[tuple[str, str]],
) -> bool:
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "order.submitted" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("order_id", "")).strip() != order_id:
            continue
        raw_tags = payload.get("rationale_tags")
        if not isinstance(raw_tags, Sequence) or isinstance(raw_tags, (str, bytes, bytearray)):
            return False
        normalized = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
        return _rationale_tags_match(normalized=normalized, expected=rationale_tags)
    return False


def _rationale_tags_match(
    *,
    normalized: tuple[str, ...],
    expected: set[tuple[str, str]],
) -> bool:
    if normalized in expected:
        return True
    return len(normalized) >= 2 and normalized[:2] in expected


def _pending_exit_order(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
) -> PendingOrderState | None:
    dashboard = dashboard_state(context)
    if dashboard is None:
        return None
    return next(
        (
            order
            for order in dashboard.pending_orders
            if order.market_id == snapshot.market_id
            and order.token_id == position.token_id
            and order.side == (
                SignalSide.SELL_YES.value
                if position.token_id == snapshot.token_id
                else SignalSide.SELL_NO.value
            )
        ),
        None,
    )


def _recently_reposted_exit(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
    target_price: float,
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _matches_exit_side(payload):
            continue
        raw_price = payload.get("price", payload.get("limit_price"))
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        if abs(price - target_price) >= 1e-9:
            continue
        if event_type not in {"order.expired", "order.canceled", "order.submitted"}:
            continue
        event_time = _event_timestamp(payload)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _exit_retry_count(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
) -> int:
    retries = 0
    seen_order_ids: set[str] = set()
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _matches_exit_side(payload):
            continue
        if event_type == "trade.closed":
            break
        if event_type == "order.expired":
            retries += 1
            continue
        if event_type == "order.canceled":
            cancel_reason = str(payload.get("reason", "")).strip().lower()
            if cancel_reason not in {"stale_ttl_cancel", "exchange_canceled"}:
                continue
            order_id = str(payload.get("order_id", "")).strip()
            if order_id and order_id in seen_order_ids:
                continue
            if order_id:
                seen_order_ids.add(order_id)
            retries += 1
            continue
        if event_type == "order.filled":
            break
    return retries


def _recently_reposted_order(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    target_price: float,
    side: SignalSide,
    cooldown_seconds: float,
    allowed_event_types: set[str],
) -> bool:
    if cooldown_seconds <= 0:
        return False
    target_side = side.value
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if event_type not in allowed_event_types:
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        raw_price = payload.get("price", payload.get("limit_price"))
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue
        if abs(price - target_price) >= 1e-9:
            continue
        event_time = _event_timestamp(payload)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _recent_failed_entry_attempt(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    target_side = side.value
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        if event_type == "order.filled":
            return False
        if event_type != "order.rejected":
            continue
        event_time = _event_timestamp(payload)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _recent_entry_activity_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    target_side = side.value
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        if event_type in {"trade.closed", "position.closed"}:
            return False
        if event_type not in {"signal.generated", "order.submitted", "order.filled", "order.rejected"}:
            continue
        event_time = _event_timestamp(payload) or _event_timestamp(event)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _recent_entry_activity_for_family(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    target_family_key = _market_family_key(snapshot)
    if target_family_key is None:
        return False
    target_side = side.value
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        payload_family_key = _payload_market_family_key(payload)
        if payload_family_key != target_family_key:
            continue
        if event_type in {"trade.closed", "position.closed"}:
            return False
        if event_type not in {"signal.generated", "order.submitted", "order.filled", "order.rejected"}:
            continue
        event_time = _event_timestamp(payload) or _event_timestamp(event)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _payload_market_family_key(payload: Mapping[str, object]) -> str | None:
    payload_market_family_key = str(payload.get("market_family_key", "")).strip()
    if payload_market_family_key:
        return payload_market_family_key
    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, Mapping):
        diagnostics_market_family_key = str(diagnostics.get("market_family_key", "")).strip()
        if diagnostics_market_family_key:
            return diagnostics_market_family_key
    event_family: str | None = None
    if isinstance(diagnostics, Mapping):
        phase2_preset = str(diagnostics.get("phase2_preset", "")).lower()
        if "_reach_" in phase2_preset or phase2_preset.endswith("_reach"):
            event_family = "reach"
        elif "_dip_" in phase2_preset or phase2_preset.endswith("_dip"):
            event_family = "dip"
    market_id = str(payload.get("market_id", "")).lower()
    if event_family is None:
        if "reach" in market_id:
            event_family = "reach"
        elif "dip" in market_id:
            event_family = "dip"
    if event_family is None:
        return None
    underlying_group_id = str(payload.get("underlying_group_id", "")).strip()
    if ":" in underlying_group_id:
        _, _, raw_underlying = underlying_group_id.partition(":")
        underlying = raw_underlying.upper() if raw_underlying else ""
    else:
        underlying = underlying_group_id.upper()
    if not underlying:
        if "btc" in market_id:
            underlying = "BTC"
        elif "eth" in market_id:
            underlying = "ETH"
    if not underlying:
        return None
    return f"{underlying}:{event_family}"


def _thesis_entry_locked(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
    cooldown_seconds: float,
    single_active_market_per_thesis: bool,
) -> bool:
    thesis_group_id = _snapshot_thesis_group_id(snapshot, side=side)
    if thesis_group_id is None:
        return False
    dashboard = dashboard_state(context)
    if dashboard is not None and single_active_market_per_thesis:
        for position in dashboard.open_positions:
            if position.market_id == snapshot.market_id:
                continue
            if str(position.thesis_group_id or "").strip() == thesis_group_id:
                return True
        for order in dashboard.pending_orders:
            if order.market_id == snapshot.market_id:
                continue
            if not _pending_order_still_locks_thesis(order=order, as_of=snapshot.timestamp):
                continue
            if str(order.thesis_group_id or "").strip() == thesis_group_id:
                return True
    if cooldown_seconds <= 0:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        event_thesis_group_id = str(payload.get("thesis_group_id", "")).strip()
        if event_thesis_group_id != thesis_group_id:
            continue
        if str(payload.get("market_id", "")) == snapshot.market_id:
            continue
        if event_type in {"trade.closed", "position.closed"}:
            return False
        if event_type != "order.filled":
            continue
        event_time = _event_timestamp(payload) or _event_timestamp(event)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _pending_order_still_locks_thesis(
    *,
    order: PendingOrderState,
    as_of: datetime,
) -> bool:
    status = str(order.status or "").strip().lower()
    if status and status not in {"pending", "partially_filled", "open", "live"}:
        return False
    if order.matched_shares > 0:
        return True
    if order.quote_ttl_seconds is None or order.quote_ttl_seconds <= 0:
        return True
    age_seconds = max(0.0, (as_of - order.updated_at).total_seconds())
    return age_seconds <= (float(order.quote_ttl_seconds) + 2.0)


def _market_no_fill_quarantined(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
    max_attempts: int,
) -> bool:
    if max_attempts <= 0:
        return False
    no_fill_attempts = _market_recent_no_fill_attempts(
        snapshot=snapshot,
        context=context,
        side=side,
    )
    return no_fill_attempts >= max_attempts


def _market_recent_no_fill_attempts(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
) -> int:
    target_side = side.value
    no_fill_attempts = 0
    seen_order_ids: set[str] = set()
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        if event_type in {"order.filled", "trade.closed", "position.closed"}:
            break
        order_id = str(payload.get("order_id", "")).strip()
        if event_type in {"order.submitted", "order.expired"}:
            if order_id and order_id in seen_order_ids:
                continue
            if order_id:
                seen_order_ids.add(order_id)
            no_fill_attempts += 1
            continue
        if event_type != "order.canceled":
            continue
        cancel_reason = str(payload.get("reason", "")).strip().lower()
        if cancel_reason not in {"stale_ttl_cancel", "exchange_canceled"}:
            continue
        if order_id and order_id in seen_order_ids:
            continue
        if order_id:
            seen_order_ids.add(order_id)
        no_fill_attempts += 1
    return no_fill_attempts


def _recent_no_fill_entry_activity_for_market(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    target_side = side.value
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        if event_type in {"order.filled", "trade.closed", "position.closed"}:
            return False
        if event_type == "order.expired":
            event_time = _event_timestamp(payload) or _event_timestamp(event)
            if event_time is None:
                continue
            if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
                return True
            return False
        if event_type != "order.canceled":
            continue
        cancel_reason = str(payload.get("reason", "")).strip().lower()
        if cancel_reason not in {"stale_ttl_cancel", "exchange_canceled"}:
            continue
        event_time = _event_timestamp(payload) or _event_timestamp(event)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _repricing_maker_fallback_no_fill_attempts(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
) -> int:
    target_side = side.value
    attempts = 0
    seen_order_ids: set[str] = set()
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if str(payload.get("side", "")).lower() != target_side:
            continue
        if event_type in {"order.filled", "trade.closed", "position.closed"}:
            break
        if event_type != "order.submitted":
            continue
        raw_tags = payload.get("rationale_tags")
        if not isinstance(raw_tags, Sequence) or isinstance(raw_tags, (str, bytes, bytearray)):
            continue
        normalized_tags = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
        if not _rationale_tags_match(
            normalized=normalized_tags,
            expected={
                ("repricing_taker_too_expensive", "maker_fallback"),
                ("repricing_taker_edge_buffer_too_thin", "maker_fallback"),
                ("repricing_edge", "maker"),
            },
        ):
            continue
        order_id = str(payload.get("order_id", "")).strip()
        if order_id and order_id in seen_order_ids:
            continue
        if order_id:
            seen_order_ids.add(order_id)
        attempts += 1
    return attempts


def _repricing_family_maker_no_fill_attempts(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
) -> int:
    target_family_key = _market_family_key(snapshot)
    if target_family_key is None:
        return 0
    attempts = 0
    seen_order_ids: set[str] = set()
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        payload_family_key = _payload_market_family_key(payload)
        if payload_family_key != target_family_key:
            continue
        if event_type in {"order.filled", "trade.closed", "position.closed"}:
            break
        if event_type != "order.submitted":
            continue
        raw_tags = payload.get("rationale_tags")
        if not isinstance(raw_tags, Sequence) or isinstance(raw_tags, (str, bytes, bytearray)):
            continue
        normalized_tags = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
        if not _rationale_tags_match(
            normalized=normalized_tags,
            expected={
                ("repricing_taker_too_expensive", "maker_fallback"),
                ("repricing_taker_edge_buffer_too_thin", "maker_fallback"),
                ("repricing_edge", "maker"),
            },
        ):
            continue
        order_id = str(payload.get("order_id", "")).strip()
        if order_id and order_id in seen_order_ids:
            continue
        if order_id:
            seen_order_ids.add(order_id)
        attempts += 1
    return attempts


def _has_repricing_fallback_taker_escalation_lineage(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
) -> bool:
    submitted_escalated_by_order_id: dict[str, bool] = {}
    for event in recent_runtime_events(context):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type != "order.submitted" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        payload_token_id = str(payload.get("token_id", "")).strip()
        if payload_token_id and payload_token_id != position.token_id:
            continue
        order_id = str(payload.get("order_id", "")).strip()
        if not order_id:
            continue
        diagnostics = payload.get("diagnostics")
        if not isinstance(diagnostics, Mapping):
            continue
        if bool(diagnostics.get("repricing_fallback_taker_escalated", False)) or bool(
            diagnostics.get("repricing_fallback_probe_taker_active", False)
        ):
            submitted_escalated_by_order_id[order_id] = True

    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        payload_token_id = str(payload.get("token_id", "")).strip()
        if payload_token_id and payload_token_id != position.token_id:
            continue
        if event_type in {"trade.closed", "position.closed"}:
            return False
        if event_type != "order.filled":
            continue
        if str(payload.get("trade_side", "")).upper() != "BUY":
            continue
        if str(payload.get("fill_source", "")).strip().lower() != "taker":
            continue
        token_id = str(payload.get("token_id", "")).strip()
        if token_id and token_id != position.token_id:
            continue
        order_id = str(payload.get("order_id", "")).strip()
        if not order_id:
            return False
        if submitted_escalated_by_order_id.get(order_id, False):
            return True
        signal_type = str(payload.get("signal_type", "")).strip().lower()
        execution_route = str(payload.get("execution_route", "")).strip().lower()
        return signal_type == "repricing_edge" and execution_route == "taker"
    return False


def _exposure_group_conflict_active(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    side: SignalSide,
) -> bool:
    exposure_group_id = _snapshot_exposure_group_id(snapshot)
    thesis_group_id = _snapshot_thesis_group_id(snapshot, side=side)
    if exposure_group_id is None or thesis_group_id is None:
        return False
    dashboard = dashboard_state(context)
    if dashboard is not None:
        for position in dashboard.open_positions:
            if position.market_id == snapshot.market_id:
                continue
            if str(position.exposure_group_id or "").strip() != exposure_group_id:
                continue
            active_thesis = str(position.thesis_group_id or "").strip()
            if active_thesis and active_thesis != thesis_group_id:
                return True
        for order in dashboard.pending_orders:
            if order.market_id == snapshot.market_id:
                continue
            if str(order.exposure_group_id or "").strip() != exposure_group_id:
                continue
            active_thesis = str(order.thesis_group_id or "").strip()
            if active_thesis and active_thesis != thesis_group_id:
                return True
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if event_type not in {"order.submitted", "order.filled"}:
            continue
        if str(payload.get("market_id", "")) == snapshot.market_id:
            continue
        if str(payload.get("exposure_group_id", "")).strip() != exposure_group_id:
            continue
        active_thesis = str(payload.get("thesis_group_id", "")).strip()
        if active_thesis and active_thesis != thesis_group_id:
            return True
    return False


def _recent_failed_exit_attempt(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    context: Mapping[str, object],
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _matches_exit_side(payload):
            continue
        if event_type == "order.filled":
            return False
        if event_type != "order.rejected":
            continue
        event_time = _event_timestamp(payload)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _recent_active_exit_submission(
    *,
    snapshot: MarketSnapshot,
    context: Mapping[str, object],
    cooldown_seconds: float,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    for event in reversed(recent_runtime_events(context)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, Mapping):
            continue
        if str(payload.get("market_id", "")) != snapshot.market_id:
            continue
        if not _matches_exit_side(payload):
            continue
        if event_type in {
            "trade.closed",
            "position.closed",
            "order.filled",
            "order.canceled",
            "order.expired",
            "order.rejected",
        }:
            return False
        if event_type != "order.submitted":
            continue
        event_time = _event_timestamp(payload) or _event_timestamp(event)
        if event_time is None:
            continue
        if (snapshot.timestamp - event_time).total_seconds() < cooldown_seconds:
            return True
        return False
    return False


def _event_timestamp(payload: Mapping[str, object]) -> datetime | None:
    for key in ("updated_at", "created_at", "closed_at", "generated_at"):
        raw_value = payload.get(key)
        if not isinstance(raw_value, str) or not raw_value:
            continue
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _snapshot_quote_age_seconds(snapshot: MarketSnapshot) -> float | None:
    for key in ("clob_timestamp", "updated_at"):
        raw_value = snapshot.metadata.get(key, "")
        if not isinstance(raw_value, str) or not raw_value:
            continue
        try:
            observed_at = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        return max(0.0, (snapshot.timestamp - observed_at).total_seconds())
    return None


def _should_block_selective_repricing_taker_due_quote_age(
    *,
    decision: Any,
    classification: Any,
    selection_action: str,
    quote_age_seconds: float | None,
    max_quote_age_seconds: float,
) -> bool:
    if selection_action != "selective_market":
        return False
    if quote_age_seconds is None or quote_age_seconds <= max_quote_age_seconds:
        return False
    if str(getattr(classification, "signal_type", "")) != "repricing_edge":
        return False
    return str(getattr(decision, "route", "")) == "taker"


def _snapshot_thesis_group_id(
    snapshot: MarketSnapshot,
    *,
    side: SignalSide | None = None,
) -> str | None:
    for key in ("thesis_group_id", "thesis_group", "event_group"):
        raw_value = snapshot.metadata.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
    return derive_exposure_keys(snapshot, side=side).thesis_group_id


def _snapshot_exposure_group_id(snapshot: MarketSnapshot) -> str | None:
    for key in ("exposure_group_id", "exposure_group", "series_group"):
        raw_value = snapshot.metadata.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
    return derive_exposure_keys(snapshot).exposure_group_id


def _snapshot_underlying_group(snapshot: MarketSnapshot) -> str | None:
    for key in ("underlying_group_id", "underlying", "asset", "base_asset"):
        raw_value = snapshot.metadata.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip().lower()
    derived = derive_exposure_keys(snapshot).underlying_group_id
    if derived:
        return str(derived).strip().lower()
    return None


def _matches_exit_side(payload: Mapping[str, object]) -> bool:
    side = str(payload.get("side", "")).lower()
    trade_side = str(payload.get("trade_side", "")).lower()
    return side in {SignalSide.SELL_YES.value, SignalSide.SELL_NO.value} or trade_side == "sell"


def _passive_exit_price(
    *,
    snapshot: MarketSnapshot,
    position: PositionState,
    exit_side: SignalSide,
    exit_reason: str,
    fallback_price: float,
    retry_count: int = 0,
    time_stop_quote_ttl_seconds: int = 5,
) -> tuple[float, int]:
    tick_size = snapshot.tick_size or 0.01
    entry_price = position.average_entry_price or fallback_price
    if exit_side == SignalSide.SELL_YES:
        best_ask = snapshot.best_ask_yes
        best_bid = snapshot.best_bid_yes
        midpoint = _midpoint(snapshot.best_bid_yes, snapshot.best_ask_yes)
    else:
        best_ask = snapshot.best_ask_no
        best_bid = snapshot.best_bid_no
        midpoint = _midpoint(snapshot.best_bid_no, snapshot.best_ask_no)
    fallback_floor = fallback_price + tick_size
    if exit_reason == "aging_exit":
        candidates = [entry_price, fallback_floor]
        if midpoint is not None:
            candidates.append(midpoint)
        passive_price = max(candidates)
        if best_ask is not None:
            passive_price = min(passive_price, best_ask)
        passive_price -= retry_count * tick_size
        passive_price = max(passive_price, max(fallback_floor, best_bid + tick_size if best_bid is not None else 0.01))
        return round(min(passive_price, 0.99), 4), 30
    if exit_reason == "stale_position_cleanup":
        candidates = [fallback_floor]
        if midpoint is not None:
            candidates.append(midpoint)
        elif best_bid is not None:
            candidates.append(best_bid + tick_size)
        passive_price = max(candidates)
        if best_ask is not None:
            passive_price = min(passive_price, best_ask)
        passive_price -= retry_count * tick_size
        passive_price = max(passive_price, best_bid + tick_size if best_bid is not None else 0.01)
        return round(min(passive_price, 0.99), 4), 15

    candidates = [fallback_floor]
    if best_bid is not None:
        candidates.append(best_bid + tick_size)
    if midpoint is not None:
        candidates.append(min(midpoint, entry_price))
    passive_price = max(candidates)
    if best_ask is not None:
        passive_price = min(passive_price, best_ask)
    passive_price -= retry_count * tick_size
    passive_price = max(passive_price, best_bid if best_bid is not None else 0.01)
    return round(min(passive_price, 0.99), 4), max(1, int(time_stop_quote_ttl_seconds))


def _midpoint(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2
