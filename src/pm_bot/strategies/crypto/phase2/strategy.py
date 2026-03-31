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
    build_phase2_preset_rules,
    resolve_phase2_config_for_snapshot,
)
from pm_bot.strategies.crypto.phase2.execution import (
    build_order_intent,
    classify_crypto_signal,
    evaluate_trade_eligibility,
    route_execution,
)
from pm_bot.strategies.crypto.phase2.management import evaluate_exit, is_reentry_blocked
from pm_bot.strategies.crypto.phase2.models import (
    CryptoExecutionFeedback,
    CryptoPositionIntent,
    CryptoReentryState,
)


class CryptoPhase2Config:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_confidence = float(config.get("min_confidence", 0.6))
        self.min_net_edge_bps = float(config.get("min_net_edge_bps", 75.0))
        self.max_spread_bps = float(config.get("max_spread_bps", 250.0))
        self.min_liquidity_score = float(config.get("min_liquidity_score", 0.0))
        self.min_contract_price = float(config.get("min_contract_price", 0.05))
        self.taker_urgency_threshold = float(config.get("taker_urgency_threshold", 0.72))
        self.maker_min_edge_bps = float(config.get("maker_min_edge_bps", 100.0))
        self.resolution_maker_min_edge_bps = float(config.get("resolution_maker_min_edge_bps", 150.0))
        self.high_edge_taker_min_edge_bps = float(config.get("high_edge_taker_min_edge_bps", 2000.0))
        self.high_edge_taker_max_spread_bps = float(config.get("high_edge_taker_max_spread_bps", 250.0))
        self.taker_max_entry_premium_bps = float(config.get("taker_max_entry_premium_bps", 750.0))
        self.repricing_taker_max_entry_premium_bps = float(
            config.get("repricing_taker_max_entry_premium_bps", self.taker_max_entry_premium_bps)
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
        raw_time_stop_max_remaining_edge_bps = config.get("time_stop_max_remaining_edge_bps")
        self.time_stop_max_remaining_edge_bps = (
            None
            if raw_time_stop_max_remaining_edge_bps in (None, "")
            else float(raw_time_stop_max_remaining_edge_bps)
        )
        self.max_holding_multiplier = float(config.get("max_holding_multiplier", 2.0))
        self.exit_repost_cooldown_seconds = float(config.get("exit_repost_cooldown_seconds", 30.0))
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
        self.exit_failure_cooldown_seconds = float(
            config.get("exit_failure_cooldown_seconds", self.exit_repost_cooldown_seconds)
        )
        self.loss_reentry_cooldown_seconds = float(config.get("loss_reentry_cooldown_seconds", 300.0))
        self.max_loss_trades_per_market = int(config.get("max_loss_trades_per_market", 0))
        self.max_loss_trades_per_exposure_group = int(
            config.get("max_loss_trades_per_exposure_group", 0)
        )
        self.time_stop_force_ioc_after_expiries = int(config.get("time_stop_force_ioc_after_expiries", 2))
        self.thesis_entry_cooldown_seconds = float(
            config.get("thesis_entry_cooldown_seconds", self.entry_failure_cooldown_seconds)
        )
        self.single_active_market_per_thesis = bool(config.get("single_active_market_per_thesis", True))
        self.max_no_fill_entry_attempts_per_market = int(
            config.get("max_no_fill_entry_attempts_per_market", 2)
        )
        self.skip_selective_wide_spread_markets = bool(
            config.get("skip_selective_wide_spread_markets", False)
        )
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

        fair_value = _fair_value_for_market(snapshot=snapshot, context=context)
        if fair_value is None:
            _record_runtime_skip(context=context, snapshot=snapshot, reason="missing_fair_value")
            return []

        dashboard = dashboard_state(context)
        position = current_position(snapshot=snapshot, dashboard=dashboard)
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

        reentry_state = _reentry_state_for_market(snapshot=snapshot, context=context)
        if is_reentry_blocked(state=reentry_state, as_of=snapshot.timestamp):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="reentry_blocked")
            return []
        if _recent_negative_trade_closed(
            snapshot=snapshot,
            context=context,
            cooldown_seconds=self.config.loss_reentry_cooldown_seconds,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="loss_reentry_cooldown_active")
            return []
        if _market_loss_quarantined(
            snapshot=snapshot,
            context=context,
            max_loss_trades=self.config.max_loss_trades_per_market,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="market_loss_quarantined")
            return []
        if _exposure_group_recent_negative_trade_closed(
            snapshot=snapshot,
            context=context,
            cooldown_seconds=self.config.loss_reentry_cooldown_seconds,
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
            max_loss_trades=self.config.max_loss_trades_per_exposure_group,
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
        )

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        classification = classify_crypto_signal(fair_value=fair_value)
        execution_feedback = _execution_feedback(context)
        resolved_config = resolve_phase2_config_for_snapshot(base=self.config, snapshot=snapshot)
        feedback_notional = _feedback_default_notional(
            base_notional=resolved_config.default_notional,
            feedback=execution_feedback,
        )
        selection_action = _selection_action_for_market(snapshot=snapshot, context=context)
        selection_reasons = _selection_reasons_for_market(snapshot=snapshot, context=context)
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
            min_net_edge_bps=resolved_config.min_net_edge_bps,
            max_spread_bps=resolved_config.max_spread_bps,
            min_liquidity_score=resolved_config.min_liquidity_score,
            min_contract_price=resolved_config.min_contract_price,
        )
        decision = route_execution(
            fair_value=fair_value,
            snapshot=snapshot,
            classification=classification,
            eligibility=eligibility,
            allow_taker_routes=selection_action != "selective_market",
            taker_urgency_threshold=_feedback_taker_urgency_threshold(
                base_threshold=resolved_config.taker_urgency_threshold,
                feedback=execution_feedback,
            ),
            maker_min_edge_bps=resolved_config.maker_min_edge_bps,
            resolution_maker_min_edge_bps=resolved_config.resolution_maker_min_edge_bps,
            high_edge_taker_min_edge_bps=resolved_config.high_edge_taker_min_edge_bps,
            high_edge_taker_max_spread_bps=resolved_config.high_edge_taker_max_spread_bps,
            taker_max_entry_premium_bps=resolved_config.taker_max_entry_premium_bps,
            repricing_taker_max_entry_premium_bps=resolved_config.repricing_taker_max_entry_premium_bps,
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
        )
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
                },
            )
            return []

        intent = build_order_intent(
            fair_value=fair_value,
            snapshot=snapshot,
            decision=decision,
            default_notional=feedback_notional,
            taker_time_in_force=resolved_config.taker_time_in_force,
            strategy_id=self.strategy_id,
        )
        target_size = intent.notional if intent is not None else feedback_notional
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
        if _market_no_fill_quarantined(
            snapshot=snapshot,
            context=context,
            side=decision.side,
            max_attempts=resolved_config.max_no_fill_entry_attempts_per_market,
        ):
            _record_runtime_skip(context=context, snapshot=snapshot, reason="entry_market_no_fill_quarantined")
            return []
        if _exposure_group_conflict_active(
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
                    "execution_feedback_bias": execution_feedback.recommended_route_bias if execution_feedback is not None else "none",
                    "execution_feedback_notional": feedback_notional,
                    "phase2_preset": resolved_config.preset_name,
                    "selection_action": selection_action,
                    "selection_reasons": list(selection_reasons),
                },
            )
        ]

    def _exit_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_value: FairValueEstimate,
        position: PositionState,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        intent = _position_intent_for_market(snapshot=snapshot, context=context)
        if intent is None:
            return []
        resolved_config = resolve_phase2_config_for_snapshot(base=self.config, snapshot=snapshot)

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
        if exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop"}:
            if (
                _should_force_immediate_time_stop_exit(
                    intent=intent,
                    exit_reason=exit_decision.reason,
                )
                or (
                    exit_decision.reason == "time_stop"
                    and exit_retry_count >= resolved_config.time_stop_force_ioc_after_expiries
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
                )
                time_in_force = "GTC"

        target_notional = (position.shares or 0.0) * exit_price
        if target_notional <= 0:
            return []

        existing_exit_order = _pending_exit_order(
            snapshot=snapshot,
            position=position,
            context=context,
        )
        if (
            existing_exit_order is not None
            and exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop"}
        ):
            return []
        if (
            existing_exit_order is None
            and exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop"}
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
            exit_decision.reason in {"aging_exit", "stale_position_cleanup", "time_stop"}
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
        realized_pnl = parse_float(payload, "realized_pnl")
        net_pnl = parse_float(payload, "net_pnl")
        effective_pnl = net_pnl if net_pnl is not None else (realized_pnl or 0.0)
        if effective_pnl >= 0:
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
        realized_pnl = parse_float(payload, "realized_pnl")
        net_pnl = parse_float(payload, "net_pnl")
        effective_pnl = net_pnl if net_pnl is not None else (realized_pnl or 0.0)
        if effective_pnl < 0:
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
        realized_pnl = parse_float(payload, "realized_pnl")
        net_pnl = parse_float(payload, "net_pnl")
        effective_pnl = net_pnl if net_pnl is not None else (realized_pnl or 0.0)
        if effective_pnl >= 0:
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
        realized_pnl = parse_float(payload, "realized_pnl")
        net_pnl = parse_float(payload, "net_pnl")
        effective_pnl = net_pnl if net_pnl is not None else (realized_pnl or 0.0)
        if effective_pnl < 0:
            loss_trades += 1
            if loss_trades >= max_loss_trades:
                return True
    return False


def _should_force_immediate_time_stop_exit(
    *,
    intent: CryptoPositionIntent,
    exit_reason: str,
) -> bool:
    return (
        exit_reason == "time_stop"
        and intent.signal_type == "repricing_edge"
        and intent.entry_fill_source == "taker"
    )


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


def _feedback_default_notional(
    *,
    base_notional: float,
    feedback: CryptoExecutionFeedback | None,
) -> float:
    if feedback is None:
        return base_notional
    if feedback.recommended_route_bias == "more_passive":
        return round(base_notional * 0.75, 4)
    if feedback.recommended_route_bias == "more_aggressive":
        return round(base_notional * 1.15, 4)
    return base_notional


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
        return normalized in rationale_tags
    return False


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
        if event_type == "order.submitted":
            if order_id and order_id in seen_order_ids:
                continue
            if order_id:
                seen_order_ids.add(order_id)
            no_fill_attempts += 1
            if no_fill_attempts >= max_attempts:
                return True
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
        if no_fill_attempts >= max_attempts:
            return True
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
    return round(min(passive_price, 0.99), 4), 5


def _midpoint(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2
