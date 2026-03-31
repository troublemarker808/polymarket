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
)
from pm_bot.strategies.crypto.phase2.execution import classify_crypto_signal
from pm_bot.strategies.crypto.phase2.management import (
    build_position_intent,
    summarize_execution_feedback_from_events,
    update_reentry_state,
)
from pm_bot.strategies.crypto.phase2.models import CryptoExitDecision, CryptoPositionIntent, CryptoReentryState


_LOCKED_BASELINE = get_locked_crypto_calibration_baseline_preset()
WORKING_BARRIER_MODEL_CONFIG = _LOCKED_BASELINE.barrier_model_config
WORKING_FUSION_MODEL_CONFIG = _LOCKED_BASELINE.fusion_model_config


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
            "execution_feedback": summarize_execution_feedback_from_events(
                recent_events=recent_events,
                pending_orders=_pending_orders_from_events(recent_events),
            ),
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
