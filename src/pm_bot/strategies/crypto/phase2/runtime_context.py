"""Runtime context builder for continuous Crypto Phase 2 paper sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Sequence

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import PendingOrderState
from pm_bot.runtime.underlying_state import FileBackedUnderlyingStateProvider
from pm_bot.storage.recorder import ComparableRuntimeRecorder
from pm_bot.strategies.common import parse_float
from pm_bot.strategies.crypto.phase1.baseline import get_locked_crypto_calibration_baseline_preset
from pm_bot.strategies.crypto.phase1.replay import compute_crypto_phase1_fair_values_from_snapshots
from pm_bot.strategies.crypto.phase1.selection import (
    generate_crypto_market_selection_report_from_snapshots,
    load_runtime_blocked_market_ids,
    load_runtime_blocked_market_reasons,
    load_runtime_market_selection_actions,
    load_runtime_market_selection_reasons,
    load_runtime_blocked_series_keys,
    load_runtime_blocked_series_reasons,
    runtime_market_selection_actions,
    runtime_market_selection_reasons,
    recommended_runtime_blocked_market_ids,
    recommended_runtime_blocked_market_reasons,
    recommended_runtime_blocked_series_keys,
    recommended_runtime_blocked_series_reasons,
    runtime_scan_identify_diagnostics,
)
from pm_bot.strategies.crypto.phase2.execution import classify_crypto_signal
from pm_bot.strategies.crypto.phase2.management import (
    build_route_policy_key,
    build_position_intent,
    summarize_market_probation_state_from_events,
    summarize_execution_feedback_from_events,
    update_route_policy_state,
    update_reentry_state,
)
from pm_bot.strategies.crypto.phase2.models import (
    CryptoDynamicEligibilityGate,
    CryptoExecutionFeedback,
    CryptoExitDecision,
    CryptoMarketProbationState,
    CryptoPositionIntent,
    CryptoReentryState,
    CryptoRoutePolicyState,
)


_LOCKED_BASELINE = get_locked_crypto_calibration_baseline_preset()
WORKING_BARRIER_MODEL_CONFIG = _LOCKED_BASELINE.barrier_model_config
WORKING_FUSION_MODEL_CONFIG = _LOCKED_BASELINE.fusion_model_config
_DYNAMIC_GATE_MIN_SAMPLES = 3


class CryptoPhase2PaperContextBuilder:
    def __init__(
        self,
        *,
        underlying_state_path: str | Path,
        apply_series_filter: bool = True,
        selection_report_path: str | Path | None = None,
    ) -> None:
        self.provider = FileBackedUnderlyingStateProvider(underlying_state_path)
        self.apply_series_filter = apply_series_filter
        self.static_blocked_series_keys = (
            set(load_runtime_blocked_series_keys(selection_report_path))
            if selection_report_path is not None
            else set()
        )
        self.static_blocked_market_ids = (
            set(load_runtime_blocked_market_ids(selection_report_path))
            if selection_report_path is not None
            else set()
        )
        self.static_blocked_series_reasons = (
            load_runtime_blocked_series_reasons(selection_report_path)
            if selection_report_path is not None
            else {}
        )
        self.static_blocked_market_reasons = (
            load_runtime_blocked_market_reasons(selection_report_path)
            if selection_report_path is not None
            else {}
        )
        self.static_market_selection_actions = (
            load_runtime_market_selection_actions(selection_report_path)
            if selection_report_path is not None
            else {}
        )
        self.static_market_selection_reasons = (
            load_runtime_market_selection_reasons(selection_report_path)
            if selection_report_path is not None
            else {}
        )
        self.position_intents_by_market_id: dict[str, CryptoPositionIntent] = {}
        self.reentry_state_by_market_id: dict[str, CryptoReentryState] = {}
        self.route_policy_state_by_key: dict[str, CryptoRoutePolicyState] = {}
        self._processed_event_count = 0

    def build_context(
        self,
        *,
        snapshot_cache: Sequence[MarketSnapshot],
        recorder: ComparableRuntimeRecorder,
    ) -> dict[str, object]:
        snapshots = tuple(snapshot_cache)
        underlying_states = self.provider.current_states()
        fair_values = compute_crypto_phase1_fair_values_from_snapshots(
            snapshots=snapshots,
            underlying_states=underlying_states,
            barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
            fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
        )
        fair_values_by_market_id = {item.market_id: item for item in fair_values}
        blocked_series_keys: set[str] = set(self.static_blocked_series_keys)
        blocked_market_ids: set[str] = set(self.static_blocked_market_ids)
        blocked_series_reasons: dict[str, tuple[str, ...]] = dict(self.static_blocked_series_reasons)
        blocked_market_reasons: dict[str, tuple[str, ...]] = dict(self.static_blocked_market_reasons)
        market_selection_actions: dict[str, str] = dict(self.static_market_selection_actions)
        market_selection_reasons: dict[str, tuple[str, ...]] = dict(self.static_market_selection_reasons)
        scan_identify_diagnostics: dict[str, object] = {}
        if self.apply_series_filter:
            report = generate_crypto_market_selection_report_from_snapshots(
                snapshots=snapshots,
                snapshot_label="paper-runtime",
                underlying_states=underlying_states,
                events=recorder.events,
                barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
                fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
            )
            blocked_series_keys.update(recommended_runtime_blocked_series_keys(report))
            blocked_market_ids.update(recommended_runtime_blocked_market_ids(report))
            blocked_series_reasons.update(recommended_runtime_blocked_series_reasons(report))
            blocked_market_reasons.update(recommended_runtime_blocked_market_reasons(report))
            market_selection_actions.update(runtime_market_selection_actions(report))
            market_selection_reasons.update(runtime_market_selection_reasons(report))
            scan_identify_diagnostics = runtime_scan_identify_diagnostics(report)

        self._processed_event_count = _update_runtime_context_from_events(
            recorder=recorder,
            fair_values_by_market_id=fair_values_by_market_id,
            position_intents_by_market_id=self.position_intents_by_market_id,
            reentry_state_by_market_id=self.reentry_state_by_market_id,
            start_index=self._processed_event_count,
        )
        recent_events = tuple(
            event
            for event in recorder.events[-64:]
            if isinstance(event, dict)
        )
        market_family_by_market_id = _market_family_by_market_id(snapshots)
        pending_orders = _pending_orders_from_events(recent_events)
        execution_feedback = summarize_execution_feedback_from_events(
            recent_events=recent_events,
            pending_orders=pending_orders,
        )
        execution_feedback_by_family = _execution_feedback_by_family(
            recent_events=recent_events,
            pending_orders=pending_orders,
            market_family_by_market_id=market_family_by_market_id,
        )
        sample_counts_by_family = _sample_counts_by_family(
            recent_events=recent_events,
            market_family_by_market_id=market_family_by_market_id,
        )
        dynamic_eligibility_gates = _dynamic_gates_by_family(
            execution_feedback_by_family=execution_feedback_by_family,
            sample_counts_by_family=sample_counts_by_family,
        )
        signal_type_by_market_id = _signal_type_by_market_id(fair_values_by_market_id)
        execution_feedback_by_route_key = _execution_feedback_by_route_key(
            recent_events=recent_events,
            pending_orders=pending_orders,
            market_family_by_market_id=market_family_by_market_id,
            signal_type_by_market_id=signal_type_by_market_id,
        )
        sample_counts_by_route_key = _sample_counts_by_route_key(
            recent_events=recent_events,
            market_family_by_market_id=market_family_by_market_id,
            signal_type_by_market_id=signal_type_by_market_id,
        )
        now = snapshots[-1].timestamp if snapshots else datetime.now(tz=timezone.utc)
        for route_key, feedback in execution_feedback_by_route_key.items():
            self.route_policy_state_by_key[route_key] = update_route_policy_state(
                route_key=route_key,
                previous=self.route_policy_state_by_key.get(route_key),
                feedback=feedback,
                sample_count=sample_counts_by_route_key.get(route_key, 0),
                as_of=now,
            )
        market_probation_state_by_market_id = _market_probation_state_by_market_id(
            snapshots=snapshots,
            recent_events=recent_events,
            as_of=now,
        )
        return {
            "fair_values_by_market_id": fair_values_by_market_id,
            "position_intents_by_market_id": dict(self.position_intents_by_market_id),
            "reentry_state_by_market_id": dict(self.reentry_state_by_market_id),
            "blocked_series_keys": blocked_series_keys,
            "blocked_market_ids": blocked_market_ids,
            "blocked_series_reasons": blocked_series_reasons,
            "blocked_market_reasons": blocked_market_reasons,
            "market_selection_actions": market_selection_actions,
            "market_selection_reasons": market_selection_reasons,
            "scan_identify_diagnostics": scan_identify_diagnostics,
            "execution_feedback": execution_feedback,
            "execution_feedback_by_family": execution_feedback_by_family,
            "dynamic_eligibility_gates": dynamic_eligibility_gates,
            "route_policy_state_by_key": dict(self.route_policy_state_by_key),
            "market_probation_state_by_market_id": market_probation_state_by_market_id,
        }


def _update_runtime_context_from_events(
    *,
    recorder: ComparableRuntimeRecorder,
    fair_values_by_market_id: dict[str, FairValueEstimate],
    position_intents_by_market_id: dict[str, CryptoPositionIntent],
    reentry_state_by_market_id: dict[str, CryptoReentryState],
    start_index: int,
) -> int:
    for event in recorder.events[start_index:]:
        payload = event.get("payload", {})
        market_id = str(payload.get("market_id", ""))
        if not market_id:
            continue
        if _is_recovered_live_event(payload):
            continue
        fair_value = fair_values_by_market_id.get(market_id)
        if event.get("event_type") == "order.filled" and fair_value is not None and market_id not in position_intents_by_market_id:
            token_id = str(payload.get("token_id", ""))
            classification = classify_crypto_signal(fair_value=fair_value)
            position_intents_by_market_id[market_id] = build_position_intent(
                fair_value=fair_value,
                classification=classification,
                token_id=token_id,
                created_at=_parse_event_timestamp(payload.get("updated_at")),
                entry_fill_price=_optional_float(payload.get("average_fill_price")),
                entry_mid_price=_optional_float(payload.get("mid_price")),
                entry_fill_source=str(payload.get("fill_source", "")) or None,
            )
        elif event.get("event_type") == "trade.closed":
            position_intents_by_market_id.pop(market_id, None)
            realized_pnl = parse_float(payload, "realized_pnl") or 0.0
            if realized_pnl < 0:
                reentry_state_by_market_id[market_id] = update_reentry_state(
                    market_id=market_id,
                    previous=reentry_state_by_market_id.get(market_id),
                    exit_decision=CryptoExitDecision(
                        market_id=market_id,
                        should_exit=True,
                        exit_side=SignalSide.SELL_YES,
                        reason="stop_loss",
                        target_price=None,
                        remaining_edge_bps=0.0,
                        rationale_tags=("stop_loss",),
                    ),
                    as_of=_parse_event_timestamp(payload.get("closed_at")),
                )
    return len(recorder.events)


def _parse_event_timestamp(raw_value: object) -> datetime:
    if isinstance(raw_value, str) and raw_value:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return datetime.now(tz=timezone.utc)


def _optional_float(raw_value: object) -> float | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, (int, float, str, bytes, bytearray)):
        return float(raw_value)
    try:
        return float(str(raw_value))
    except (TypeError, ValueError):
        return None


def _is_recovered_live_event(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return str(payload.get("strategy_id", "")).strip() == "recovered.live"


def _pending_orders_from_events(
    recent_events: Sequence[dict[str, object]],
) -> tuple[PendingOrderState, ...]:
    orders_by_id: dict[str, PendingOrderState] = {}
    for event in recent_events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if event_type not in {"order.submitted", "order.expired", "order.canceled", "order.filled", "order.partially_filled"}:
            continue
        if not isinstance(payload, dict):
            continue
        order_id = str(payload.get("order_id", "")).strip()
        if not order_id:
            continue
        created_at = _parse_event_timestamp(payload.get("created_at"))
        updated_at = _parse_event_timestamp(payload.get("updated_at"))
        existing = orders_by_id.get(order_id)
        orders_by_id[order_id] = PendingOrderState(
            order_id=order_id,
            intent_id=(str(payload.get("intent_id")) if payload.get("intent_id") not in (None, "") else None),
            market_id=str(payload.get("market_id", "")),
            token_id=str(payload.get("token_id", "")),
            category=Category.CRYPTO,
            strategy_id=str(payload.get("strategy_id", "")),
            side=str(payload.get("side", "")),
            limit_price=float(payload.get("price", payload.get("limit_price", 0.0)) or 0.0),
            requested_shares=float(payload.get("size", payload.get("requested_shares", 0.0)) or 0.0),
            requested_notional=float(payload.get("notional", payload.get("requested_notional", 0.0)) or 0.0),
            matched_shares=float(payload.get("matched_shares", 0.0) or 0.0),
            matched_notional=float(payload.get("matched_notional", 0.0) or 0.0),
            fees_paid=float(payload.get("fees_paid_total", payload.get("fees_paid", 0.0)) or 0.0),
            status=(
                "expired"
                if event_type == "order.expired"
                else "canceled"
                if event_type == "order.canceled"
                else "filled"
                if event_type == "order.filled"
                else "partially_filled"
                if event_type == "order.partially_filled"
                else str(payload.get("status", "pending"))
            ),
            created_at=existing.created_at if existing is not None else created_at,
            updated_at=updated_at,
            quote_ttl_seconds=(
                int(payload["quote_ttl_seconds"])
                if payload.get("quote_ttl_seconds") not in (None, "")
                else None
            ),
            signal_edge_bps=_optional_float(payload.get("signal_edge_bps")),
        )
    return tuple(orders_by_id.values())


def _market_family_by_market_id(
    snapshots: Sequence[MarketSnapshot],
) -> dict[str, str]:
    families: dict[str, str] = {}
    for snapshot in snapshots:
        family_key = _market_family_key(snapshot)
        if family_key is None:
            continue
        families[snapshot.market_id] = family_key
    return families


def _execution_feedback_by_family(
    *,
    recent_events: Sequence[dict[str, object]],
    pending_orders: Sequence[PendingOrderState],
    market_family_by_market_id: dict[str, str],
) -> dict[str, CryptoExecutionFeedback]:
    events_by_family: dict[str, list[dict[str, object]]] = {}
    pending_by_family: dict[str, list[PendingOrderState]] = {}
    for event in recent_events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        market_id = str(payload.get("market_id", "")).strip()
        family_key = market_family_by_market_id.get(market_id)
        if not family_key:
            continue
        events_by_family.setdefault(family_key, []).append(event)
    for order in pending_orders:
        family_key = market_family_by_market_id.get(order.market_id)
        if not family_key:
            continue
        pending_by_family.setdefault(family_key, []).append(order)
    feedback_by_family: dict[str, CryptoExecutionFeedback] = {}
    for family_key in sorted(set(events_by_family) | set(pending_by_family)):
        feedback_by_family[family_key] = summarize_execution_feedback_from_events(
            recent_events=tuple(events_by_family.get(family_key, ())),
            pending_orders=tuple(pending_by_family.get(family_key, ())),
        )
    return feedback_by_family


def _dynamic_gates_by_family(
    *,
    execution_feedback_by_family: dict[str, CryptoExecutionFeedback],
    sample_counts_by_family: dict[str, int],
) -> dict[str, CryptoDynamicEligibilityGate]:
    gates: dict[str, CryptoDynamicEligibilityGate] = {}
    for family_key, feedback in execution_feedback_by_family.items():
        sample_count = max(0, sample_counts_by_family.get(family_key, 0))
        if sample_count < _DYNAMIC_GATE_MIN_SAMPLES:
            gates[family_key] = CryptoDynamicEligibilityGate(
                family_key=family_key,
                sample_count=sample_count,
                min_net_edge_bps=75.0,
                taker_max_entry_premium_bps=750.0,
                repricing_taker_max_entry_premium_bps=90.0,
                reason_tag="dynamic_insufficient_samples",
            )
            continue
        if feedback.recommended_route_bias == "more_passive":
            gates[family_key] = CryptoDynamicEligibilityGate(
                family_key=family_key,
                sample_count=sample_count,
                min_net_edge_bps=125.0,
                taker_max_entry_premium_bps=500.0,
                repricing_taker_max_entry_premium_bps=80.0,
                reason_tag="dynamic_more_passive",
            )
        elif feedback.recommended_route_bias == "more_aggressive":
            gates[family_key] = CryptoDynamicEligibilityGate(
                family_key=family_key,
                sample_count=sample_count,
                min_net_edge_bps=65.0,
                taker_max_entry_premium_bps=850.0,
                repricing_taker_max_entry_premium_bps=110.0,
                reason_tag="dynamic_more_aggressive",
            )
        else:
            gates[family_key] = CryptoDynamicEligibilityGate(
                family_key=family_key,
                sample_count=sample_count,
                min_net_edge_bps=75.0,
                taker_max_entry_premium_bps=750.0,
                repricing_taker_max_entry_premium_bps=90.0,
                reason_tag="dynamic_stable",
            )
    return gates


def _sample_counts_by_family(
    *,
    recent_events: Sequence[dict[str, object]],
    market_family_by_market_id: dict[str, str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    tracked_event_types = {"order.submitted", "order.filled", "order.expired", "order.rejected", "trade.closed"}
    for event in recent_events:
        event_type = str(event.get("event_type", "")).strip()
        if event_type not in tracked_event_types:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        market_id = str(payload.get("market_id", "")).strip()
        family_key = market_family_by_market_id.get(market_id)
        if not family_key:
            continue
        counts[family_key] = counts.get(family_key, 0) + 1
    return counts


def _signal_type_by_market_id(
    fair_values_by_market_id: dict[str, FairValueEstimate],
) -> dict[str, str]:
    signal_type: dict[str, str] = {}
    for market_id, fair_value in fair_values_by_market_id.items():
        signal_type[market_id] = classify_crypto_signal(fair_value=fair_value).signal_type
    return signal_type


def _execution_feedback_by_route_key(
    *,
    recent_events: Sequence[dict[str, object]],
    pending_orders: Sequence[PendingOrderState],
    market_family_by_market_id: dict[str, str],
    signal_type_by_market_id: dict[str, str],
) -> dict[str, CryptoExecutionFeedback]:
    events_by_key: dict[str, list[dict[str, object]]] = {}
    pending_by_key: dict[str, list[PendingOrderState]] = {}
    for event in recent_events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        market_id = str(payload.get("market_id", "")).strip()
        family_key = market_family_by_market_id.get(market_id)
        signal_type = signal_type_by_market_id.get(market_id)
        if not family_key or not signal_type:
            continue
        route_key = build_route_policy_key(
            underlying=family_key.split(":")[0],
            event_family=family_key.split(":")[1],
            signal_type=signal_type,
        )
        events_by_key.setdefault(route_key, []).append(event)
    for order in pending_orders:
        family_key = market_family_by_market_id.get(order.market_id)
        signal_type = signal_type_by_market_id.get(order.market_id)
        if not family_key or not signal_type:
            continue
        route_key = build_route_policy_key(
            underlying=family_key.split(":")[0],
            event_family=family_key.split(":")[1],
            signal_type=signal_type,
        )
        pending_by_key.setdefault(route_key, []).append(order)
    result: dict[str, CryptoExecutionFeedback] = {}
    for route_key in sorted(set(events_by_key) | set(pending_by_key)):
        result[route_key] = summarize_execution_feedback_from_events(
            recent_events=tuple(events_by_key.get(route_key, ())),
            pending_orders=tuple(pending_by_key.get(route_key, ())),
        )
    return result


def _sample_counts_by_route_key(
    *,
    recent_events: Sequence[dict[str, object]],
    market_family_by_market_id: dict[str, str],
    signal_type_by_market_id: dict[str, str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    tracked_event_types = {"order.submitted", "order.filled", "order.expired", "order.rejected", "trade.closed"}
    for event in recent_events:
        event_type = str(event.get("event_type", "")).strip()
        if event_type not in tracked_event_types:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        market_id = str(payload.get("market_id", "")).strip()
        family_key = market_family_by_market_id.get(market_id)
        signal_type = signal_type_by_market_id.get(market_id)
        if not family_key or not signal_type:
            continue
        route_key = build_route_policy_key(
            underlying=family_key.split(":")[0],
            event_family=family_key.split(":")[1],
            signal_type=signal_type,
        )
        counts[route_key] = counts.get(route_key, 0) + 1
    return counts


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


def _market_probation_state_by_market_id(
    *,
    snapshots: Sequence[MarketSnapshot],
    recent_events: Sequence[dict[str, object]],
    as_of: datetime,
) -> dict[str, CryptoMarketProbationState]:
    result: dict[str, CryptoMarketProbationState] = {}
    for snapshot in snapshots:
        result[snapshot.market_id] = summarize_market_probation_state_from_events(
            market_id=snapshot.market_id,
            recent_events=recent_events,
            as_of=as_of,
        )
    return result
