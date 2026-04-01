"""Crypto Phase 2 position and execution management helpers."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Mapping

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, SignalSide
from pm_bot.runtime.state import ClosedTrade, PendingOrderState, PositionState
from pm_bot.strategies.common import parse_float
from pm_bot.strategies.crypto.phase2.models import (
    CryptoExecutionFeedback,
    CryptoExitDecision,
    CryptoMarketProbationState,
    CryptoPositionIntent,
    CryptoReentryState,
    CryptoRoutePolicyState,
    CryptoSignalClassification,
)


def build_position_intent(
    *,
    fair_value: FairValueEstimate,
    classification: CryptoSignalClassification,
    token_id: str,
    created_at: datetime,
    entry_fill_price: float | None = None,
    entry_mid_price: float | None = None,
    entry_fill_source: str | None = None,
) -> CryptoPositionIntent:
    observed_probability = fair_value.observed_probability or fair_value.fair_probability
    effective_horizon_days = parse_float(fair_value.supporting_values, "effective_horizon_days") or 0.0
    expected_holding_seconds = _expected_holding_seconds(
        fair_value=fair_value,
        classification=classification,
        effective_horizon_days=effective_horizon_days,
    )
    net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
    return CryptoPositionIntent(
        market_id=fair_value.market_id,
        token_id=token_id,
        signal_type=classification.signal_type,
        entry_side=classification.side,
        expected_exit_mode=classification.expected_exit_mode,
        expected_holding_seconds=expected_holding_seconds,
        effective_horizon_days=effective_horizon_days,
        entry_fair_probability=fair_value.fair_probability,
        entry_observed_probability=observed_probability,
        net_edge_bps=net_edge_bps,
        created_at=created_at,
        entry_fill_price=entry_fill_price,
        entry_mid_price=entry_mid_price,
        entry_fill_source=entry_fill_source,
        rationale_tags=classification.rationale_tags,
    )


def evaluate_exit(
    *,
    fair_value: FairValueEstimate,
    position: PositionState,
    intent: CryptoPositionIntent,
    best_bid_yes: float | None,
    best_bid_no: float | None,
    as_of: datetime,
    exit_edge_bps: float = 75.0,
    stop_loss_bps: float = 250.0,
    max_holding_multiplier: float = 2.0,
    execution_max_holding_seconds: float | None = None,
    min_holding_seconds_before_exit: float = 1.0,
    aging_exit_edge_bps: float = 150.0,
    stale_exit_edge_bps: float = 300.0,
    aging_start_fraction: float = 0.5,
    stale_start_fraction: float = 1.0,
    stop_loss_min_ticks: int = 2,
    tick_size: float | None = None,
    stop_loss_max_remaining_edge_bps: float = 150.0,
    adverse_fill_exit_bps: float = 75.0,
    adverse_fill_max_remaining_edge_bps: float = 150.0,
    time_stop_max_remaining_edge_bps: float | None = None,
    escalated_entry_tail_guard_enabled: bool = False,
    escalated_entry_adverse_fill_exit_bps: float | None = None,
    escalated_entry_adverse_fill_max_remaining_edge_bps: float | None = None,
    escalated_entry_max_holding_multiplier: float | None = None,
) -> CryptoExitDecision:
    if position.average_entry_price is None:
        return _hold_decision(fair_value.market_id, "missing_entry_price", 0.0)

    if intent.entry_side == SignalSide.BUY_YES:
        if best_bid_yes is None:
            return _hold_decision(fair_value.market_id, "missing_bid", 0.0)
        exit_side = SignalSide.SELL_YES
        fair_exit_price = fair_value.fair_probability
        exit_price = best_bid_yes
    else:
        if best_bid_no is None:
            return _hold_decision(fair_value.market_id, "missing_bid", 0.0)
        exit_side = SignalSide.SELL_NO
        fair_exit_price = 1.0 - fair_value.fair_probability
        exit_price = best_bid_no

    remaining_edge_bps = (fair_exit_price - exit_price) * 10000
    stop_loss_distance = position.average_entry_price * (stop_loss_bps / 10000)
    if tick_size is not None and tick_size > 0:
        stop_loss_distance = max(stop_loss_distance, tick_size * stop_loss_min_ticks)
    stop_loss_price = max(0.0, position.average_entry_price - stop_loss_distance)
    stop_loss_triggered = (
        exit_price <= stop_loss_price
        and remaining_edge_bps <= stop_loss_max_remaining_edge_bps
    )
    holding_seconds = max(0.0, (as_of - intent.created_at).total_seconds())
    if holding_seconds < min_holding_seconds_before_exit:
        return _hold_decision(fair_value.market_id, "fresh_fill_hold", remaining_edge_bps)
    expected_holding_seconds: float = max(float(intent.expected_holding_seconds), 1.0)
    if execution_max_holding_seconds is not None and (
        intent.effective_horizon_days < 7.0
        or intent.signal_type in {"repricing_edge", "liquidity_edge"}
    ):
        expected_holding_seconds = min(expected_holding_seconds, max(execution_max_holding_seconds, 1.0))
    holding_fraction = holding_seconds / expected_holding_seconds
    effective_max_holding_multiplier = max_holding_multiplier
    effective_adverse_fill_exit_bps = adverse_fill_exit_bps
    effective_adverse_fill_max_remaining_edge_bps = adverse_fill_max_remaining_edge_bps
    if (
        escalated_entry_tail_guard_enabled
        and intent.signal_type == "repricing_edge"
        and intent.entry_fill_source == "taker"
    ):
        if escalated_entry_adverse_fill_exit_bps is not None:
            effective_adverse_fill_exit_bps = min(
                adverse_fill_exit_bps,
                max(0.0, escalated_entry_adverse_fill_exit_bps),
            )
        if escalated_entry_adverse_fill_max_remaining_edge_bps is not None:
            effective_adverse_fill_max_remaining_edge_bps = max(
                adverse_fill_max_remaining_edge_bps,
                max(0.0, escalated_entry_adverse_fill_max_remaining_edge_bps),
            )
        if escalated_entry_max_holding_multiplier is not None:
            effective_max_holding_multiplier = min(
                max_holding_multiplier,
                max(0.1, escalated_entry_max_holding_multiplier),
            )

    time_stop_triggered = holding_seconds >= (expected_holding_seconds * effective_max_holding_multiplier)
    effective_exit_edge_bps = exit_edge_bps
    exit_reason = "fair_value_reached"
    if holding_fraction >= stale_start_fraction:
        effective_exit_edge_bps = max(exit_edge_bps, stale_exit_edge_bps)
        exit_reason = "stale_position_cleanup"
    elif holding_fraction >= aging_start_fraction:
        effective_exit_edge_bps = max(exit_edge_bps, aging_exit_edge_bps)
        exit_reason = "aging_exit"
    adverse_fill_triggered = False
    if (
        intent.entry_fill_source == "taker"
        and intent.signal_type in {"repricing_edge", "liquidity_edge"}
        and intent.entry_fill_price is not None
        and remaining_edge_bps <= effective_adverse_fill_max_remaining_edge_bps
    ):
        adverse_fill_price = intent.entry_fill_price * (1 - (effective_adverse_fill_exit_bps / 10000))
        adverse_fill_triggered = exit_price <= adverse_fill_price

    if adverse_fill_triggered:
        return CryptoExitDecision(
            market_id=fair_value.market_id,
            should_exit=True,
            exit_side=exit_side,
            reason="adverse_fill_reversal",
            target_price=exit_price,
            remaining_edge_bps=remaining_edge_bps,
            rationale_tags=("adverse_fill_reversal",),
        )
    if stop_loss_triggered:
        return CryptoExitDecision(
            market_id=fair_value.market_id,
            should_exit=True,
            exit_side=exit_side,
            reason="stop_loss",
            target_price=exit_price,
            remaining_edge_bps=remaining_edge_bps,
            rationale_tags=("stop_loss",),
        )
    if remaining_edge_bps <= effective_exit_edge_bps:
        return CryptoExitDecision(
            market_id=fair_value.market_id,
            should_exit=True,
            exit_side=exit_side,
            reason=exit_reason,
            target_price=exit_price,
            remaining_edge_bps=remaining_edge_bps,
            rationale_tags=(exit_reason,),
        )
    if time_stop_triggered and (
        time_stop_max_remaining_edge_bps is None
        or remaining_edge_bps <= time_stop_max_remaining_edge_bps
    ):
        return CryptoExitDecision(
            market_id=fair_value.market_id,
            should_exit=True,
            exit_side=exit_side,
            reason="time_stop",
            target_price=exit_price,
            remaining_edge_bps=remaining_edge_bps,
            rationale_tags=("time_stop",),
        )
    return _hold_decision(fair_value.market_id, "hold", remaining_edge_bps)


def _expected_holding_seconds(
    *,
    fair_value: FairValueEstimate,
    classification: CryptoSignalClassification,
    effective_horizon_days: float,
) -> int:
    base_holding_seconds = fair_value.half_life_seconds or 24 * 3600
    horizon_floor_seconds = 0
    if effective_horizon_days >= 180:
        horizon_floor_seconds = 7 * 24 * 3600 if classification.expected_exit_mode == "time_decay_or_resolution" else 12 * 3600
    elif effective_horizon_days >= 30:
        horizon_floor_seconds = 3 * 24 * 3600 if classification.expected_exit_mode == "time_decay_or_resolution" else 6 * 3600
    elif effective_horizon_days >= 7:
        horizon_floor_seconds = 24 * 3600 if classification.expected_exit_mode == "time_decay_or_resolution" else 2 * 3600
    return max(int(base_holding_seconds), horizon_floor_seconds)


def update_reentry_state(
    *,
    market_id: str,
    previous: CryptoReentryState | None,
    exit_decision: CryptoExitDecision,
    as_of: datetime,
    cooldown_seconds: int = 300,
    quarantine_after_stopouts: int = 3,
) -> CryptoReentryState:
    stop_out_count = previous.stop_out_count if previous is not None else 0
    if exit_decision.reason == "stop_loss":
        stop_out_count += 1
        quarantine_active = stop_out_count >= quarantine_after_stopouts
        blocked_until = as_of + timedelta(seconds=cooldown_seconds)
        reason = "quarantine" if quarantine_active else "cooldown"
        return CryptoReentryState(
            market_id=market_id,
            blocked_until=blocked_until,
            stop_out_count=stop_out_count,
            quarantine_active=quarantine_active,
            reason=reason,
        )
    if previous is None:
        return CryptoReentryState(
            market_id=market_id,
            blocked_until=None,
            stop_out_count=0,
            quarantine_active=False,
            reason="clear",
        )
    return CryptoReentryState(
        market_id=market_id,
        blocked_until=previous.blocked_until,
        stop_out_count=stop_out_count,
        quarantine_active=previous.quarantine_active,
        reason=previous.reason,
    )


def is_reentry_blocked(
    *,
    state: CryptoReentryState | None,
    as_of: datetime,
) -> bool:
    if state is None:
        return False
    if state.quarantine_active:
        return True
    if state.blocked_until is None:
        return False
    return as_of < state.blocked_until


def summarize_execution_feedback(
    *,
    pending_orders: Sequence[PendingOrderState],
    closed_trades: Sequence[ClosedTrade],
) -> CryptoExecutionFeedback:
    maker_orders = [order for order in pending_orders if order.quote_ttl_seconds not in (None, 30)]
    taker_orders = [order for order in pending_orders if order.quote_ttl_seconds == 30]
    maker_fill_rate = (
        sum(1 for order in maker_orders if order.matched_shares > 0) / len(maker_orders)
        if maker_orders
        else 0.0
    )
    repeated_expiration_rate = (
        sum(1 for order in maker_orders if order.status == "expired") / len(maker_orders)
        if maker_orders
        else 0.0
    )
    stop_out_trades = sum(1 for trade in closed_trades if trade.net_pnl < 0)
    repeated_stop_out_rate = (stop_out_trades / len(closed_trades)) if closed_trades else 0.0
    taker_shortfall_bps = (
        sum(abs(order.signal_edge_bps or 0.0) for order in taker_orders) / len(taker_orders) * 0.1
        if taker_orders
        else 0.0
    )

    if repeated_stop_out_rate >= 0.5:
        recommended_route_bias = "more_passive"
    elif repeated_expiration_rate >= 0.6 and maker_fill_rate < 0.2:
        recommended_route_bias = "more_aggressive"
    else:
        recommended_route_bias = "stable"

    return CryptoExecutionFeedback(
        maker_fill_rate=round(maker_fill_rate, 4),
        taker_shortfall_bps=round(taker_shortfall_bps, 4),
        repeated_expiration_rate=round(repeated_expiration_rate, 4),
        repeated_stop_out_rate=round(repeated_stop_out_rate, 4),
        recommended_route_bias=recommended_route_bias,
    )


def summarize_execution_feedback_from_events(
    *,
    recent_events: Sequence[Mapping[str, object]],
    pending_orders: Sequence[PendingOrderState],
) -> CryptoExecutionFeedback:
    closed_trades: list[ClosedTrade] = []
    for event in recent_events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if event_type != "trade.closed" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("strategy_id", "")).strip() == "recovered.live":
            continue
        closed_at = _parse_datetime(payload.get("closed_at"))
        if closed_at is None:
            continue
        closed_trades.append(
            ClosedTrade(
                market_id=str(payload.get("market_id", "")),
                token_id=str(payload.get("token_id", "")),
                category=Category.CRYPTO,
                strategy_id=str(payload.get("strategy_id", "")),
                realized_pnl=float(payload.get("realized_pnl", 0.0) or 0.0),
                fees_paid=float(payload.get("fees_paid", 0.0) or 0.0),
                closed_at=closed_at,
                intent_id=(str(payload.get("intent_id")) if payload.get("intent_id") not in (None, "") else None),
                exposure_group_id=(
                    str(payload.get("exposure_group_id"))
                    if payload.get("exposure_group_id") not in (None, "")
                    else None
                ),
                thesis_group_id=(
                    str(payload.get("thesis_group_id"))
                    if payload.get("thesis_group_id") not in (None, "")
                    else None
                ),
                underlying_group_id=(
                    str(payload.get("underlying_group_id"))
                    if payload.get("underlying_group_id") not in (None, "")
                    else None
                ),
            )
        )
    return summarize_execution_feedback(
        pending_orders=pending_orders,
        closed_trades=tuple(closed_trades),
    )


def summarize_market_probation_state_from_events(
    *,
    market_id: str,
    recent_events: Sequence[Mapping[str, object]],
    as_of: datetime,
    loss_streak_for_probation: int = 2,
    loss_streak_for_quarantine: int = 3,
    recovery_win_streak_required: int = 2,
    cooldown_seconds: float = 300.0,
) -> CryptoMarketProbationState:
    close_events: list[tuple[datetime, float]] = []
    for event in recent_events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if event_type != "trade.closed" or not isinstance(payload, Mapping):
            continue
        if str(payload.get("strategy_id", "")).strip() == "recovered.live":
            continue
        if str(payload.get("market_id", "")).strip() != market_id:
            continue
        closed_at = _parse_datetime(payload.get("closed_at"))
        if closed_at is None:
            continue
        net_pnl = float(payload.get("net_pnl", payload.get("realized_pnl", 0.0)) or 0.0)
        close_events.append((closed_at, net_pnl))
    close_events.sort(key=lambda item: item[0])
    recent_loss_streak = 0
    for _, pnl in reversed(close_events):
        if pnl < 0:
            recent_loss_streak += 1
            continue
        break
    recent_win_streak = 0
    for _, pnl in reversed(close_events):
        if pnl > 0:
            recent_win_streak += 1
            continue
        break
    last_loss_at = next((closed_at for closed_at, pnl in reversed(close_events) if pnl < 0), None)
    cooldown = timedelta(seconds=max(0.0, cooldown_seconds))
    blocked_until = None
    if last_loss_at is not None:
        blocked_until = last_loss_at + cooldown
    if recent_loss_streak >= max(1, loss_streak_for_quarantine):
        state = "quarantined"
    elif recent_loss_streak >= max(1, loss_streak_for_probation):
        state = "probation"
    elif (
        last_loss_at is not None
        and recent_win_streak >= max(1, recovery_win_streak_required)
        and as_of >= (blocked_until or as_of)
    ):
        state = "recovery"
        blocked_until = None
    else:
        state = "active"
        if state == "active":
            blocked_until = None
    return CryptoMarketProbationState(
        market_id=market_id,
        state=state,
        recent_loss_streak=recent_loss_streak,
        recent_win_streak=recent_win_streak,
        last_loss_at=last_loss_at,
        blocked_until=blocked_until if state in {"probation", "quarantined"} else None,
    )


def build_route_policy_key(*, underlying: str, event_family: str, signal_type: str) -> str:
    return f"{underlying}:{event_family}:{signal_type}"


def update_route_policy_state(
    *,
    route_key: str,
    previous: CryptoRoutePolicyState | None,
    feedback: CryptoExecutionFeedback,
    sample_count: int,
    as_of: datetime,
    min_samples: int = 3,
    cooldown_seconds: int = 120,
) -> CryptoRoutePolicyState:
    if previous is not None and as_of < previous.cooldown_until:
        return previous
    if sample_count < min_samples:
        return CryptoRoutePolicyState(
            route_key=route_key,
            sample_count=sample_count,
            route_bias="stable",
            aggressiveness_adjustment=0.0,
            taker_urgency_adjustment=0.0,
            taker_premium_adjustment_bps=0.0,
            updated_at=as_of,
            cooldown_until=as_of,
        )
    route_bias = feedback.recommended_route_bias
    if route_bias == "more_passive":
        return CryptoRoutePolicyState(
            route_key=route_key,
            sample_count=sample_count,
            route_bias=route_bias,
            aggressiveness_adjustment=-0.15,
            taker_urgency_adjustment=0.06,
            taker_premium_adjustment_bps=-80.0,
            updated_at=as_of,
            cooldown_until=as_of + timedelta(seconds=cooldown_seconds),
        )
    if route_bias == "more_aggressive":
        return CryptoRoutePolicyState(
            route_key=route_key,
            sample_count=sample_count,
            route_bias=route_bias,
            aggressiveness_adjustment=0.20,
            taker_urgency_adjustment=-0.06,
            taker_premium_adjustment_bps=80.0,
            updated_at=as_of,
            cooldown_until=as_of + timedelta(seconds=cooldown_seconds),
        )
    return CryptoRoutePolicyState(
        route_key=route_key,
        sample_count=sample_count,
        route_bias="stable",
        aggressiveness_adjustment=0.0,
        taker_urgency_adjustment=0.0,
        taker_premium_adjustment_bps=0.0,
        updated_at=as_of,
        cooldown_until=as_of + timedelta(seconds=cooldown_seconds),
    )


def _hold_decision(market_id: str, reason: str, remaining_edge_bps: float) -> CryptoExitDecision:
    return CryptoExitDecision(
        market_id=market_id,
        should_exit=False,
        exit_side=None,
        reason=reason,
        target_price=None,
        remaining_edge_bps=remaining_edge_bps,
        rationale_tags=(reason,),
    )


def _parse_datetime(raw_value: object) -> datetime | None:
    if not isinstance(raw_value, str) or not raw_value:
        return None
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    return parsed
