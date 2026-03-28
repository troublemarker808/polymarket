"""Runtime context builder for continuous Crypto Phase 2 paper sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import SignalSide
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.runtime.underlying_state import FileBackedUnderlyingStateProvider
from pm_bot.storage.recorder import PaperRuntimeRecorder
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.replay import compute_crypto_phase1_fair_values_from_snapshots
from pm_bot.strategies.crypto.phase1.selection import (
    generate_crypto_market_selection_report_from_snapshots,
    recommended_skip_series_keys,
)
from pm_bot.strategies.crypto.phase2.execution import classify_crypto_signal
from pm_bot.strategies.crypto.phase2.management import build_position_intent, update_reentry_state
from pm_bot.strategies.crypto.phase2.models import CryptoExitDecision, CryptoPositionIntent, CryptoReentryState


WORKING_BARRIER_MODEL_CONFIG = CryptoBarrierModelConfig(steepness=1.65)
WORKING_FUSION_MODEL_CONFIG = CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65)


class CryptoPhase2PaperContextBuilder:
    def __init__(
        self,
        *,
        underlying_state_path: str | Path,
        apply_series_filter: bool = True,
    ) -> None:
        self.provider = FileBackedUnderlyingStateProvider(underlying_state_path)
        self.apply_series_filter = apply_series_filter
        self.position_intents_by_market_id: dict[str, CryptoPositionIntent] = {}
        self.reentry_state_by_market_id: dict[str, CryptoReentryState] = {}
        self._processed_event_count = 0

    def build_context(
        self,
        *,
        snapshot_cache,
        recorder: PaperRuntimeRecorder,
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
        blocked_series_keys: set[str] = set()
        if self.apply_series_filter:
            report = generate_crypto_market_selection_report_from_snapshots(
                snapshots=snapshots,
                snapshot_label="paper-runtime",
                underlying_states=underlying_states,
                barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
                fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
            )
            blocked_series_keys = set(recommended_skip_series_keys(report))

        self._processed_event_count = _update_runtime_context_from_events(
            recorder=recorder,
            fair_values_by_market_id=fair_values_by_market_id,
            position_intents_by_market_id=self.position_intents_by_market_id,
            reentry_state_by_market_id=self.reentry_state_by_market_id,
            start_index=self._processed_event_count,
        )
        return {
            "fair_values_by_market_id": fair_values_by_market_id,
            "position_intents_by_market_id": dict(self.position_intents_by_market_id),
            "reentry_state_by_market_id": dict(self.reentry_state_by_market_id),
            "blocked_series_keys": blocked_series_keys,
        }


def _update_runtime_context_from_events(
    *,
    recorder: PaperRuntimeRecorder,
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
            realized_pnl = float(payload.get("realized_pnl", 0.0))
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


def _parse_event_timestamp(raw_value: object):
    if isinstance(raw_value, str) and raw_value:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return datetime.now(tz=timezone.utc)


def _optional_float(raw_value: object) -> float | None:
    if raw_value in (None, ""):
        return None
    return float(raw_value)
