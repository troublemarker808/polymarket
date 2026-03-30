"""Replay wrapper for Crypto Phase 2 strategy research."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Sequence

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.settings import BotSettings
from pm_bot.core.research_types import FairValueEstimate, Phase1RunSummary
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.strategies.common import parse_float
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.research.engine import ResearchRecorder, ResearchRunResult, load_market_snapshots
from pm_bot.research.phase1_artifacts import build_phase1_output_dir, write_phase1_artifacts
from pm_bot.research.phase1_runner import (
    Phase1ReplayResult,
    _reset_replay_output_files,
    _resolve_replay_summary_status,
)
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.state import RuntimeState
from pm_bot.runtime.paper_sync import sync_paper_execution_state
from pm_bot.strategies.crypto.phase1.attribution import build_crypto_attribution_rows
from pm_bot.strategies.crypto.phase1.baseline import resolve_crypto_calibration_model_configs
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig, CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.replay import (
    compute_crypto_phase1_fair_values,
    compute_crypto_phase1_fair_values_from_snapshots,
)
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
    update_reentry_state,
)
from pm_bot.strategies.crypto.phase2.models import CryptoPositionIntent, CryptoReentryState, CryptoExitDecision
from pm_bot.strategies.crypto.phase2.strategy import CryptoPhase2Strategy


async def run_crypto_phase2_replay(
    *,
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    config_dir: str | Path = "configs/profiles/research-crypto-phase2-v1",
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    slippage_bps: float = 5.0,
    adverse_selection_bps: float = 10.0,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
    apply_series_filter: bool = True,
    selection_report_path: str | Path | None = None,
    strategy_overrides: dict[str, object] | None = None,
) -> tuple[FairValueEstimate, ...]:
    settings = load_settings_from_directory(config_dir)
    snapshots = load_market_snapshots(snapshot_path)
    if limit is not None:
        snapshots = snapshots[: max(limit, 0)]
    return await run_crypto_phase2_replay_snapshots(
        snapshots=snapshots,
        underlying_states=underlying_states,
        settings=settings,
        config_dir=str(config_dir),
        output_dir=output_dir,
        run_id=run_id,
        slippage_bps=slippage_bps,
        adverse_selection_bps=adverse_selection_bps,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
        apply_series_filter=apply_series_filter,
        selection_report_path=selection_report_path,
        strategy_overrides=strategy_overrides,
        snapshot_path=snapshot_path,
    )


async def run_crypto_phase2_replay_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    underlying_states: dict[str, CryptoUnderlyingState],
    settings: BotSettings,
    config_dir: str,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    slippage_bps: float = 5.0,
    adverse_selection_bps: float = 10.0,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
    apply_series_filter: bool = True,
    selection_report_path: str | Path | None = None,
    snapshot_path: str | Path = "in-memory",
    strategy_overrides: dict[str, object] | None = None,
) -> tuple[FairValueEstimate, ...]:
    _, resolved_barrier_model_config, resolved_fusion_model_config = resolve_crypto_calibration_model_configs(
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )
    fair_values = compute_crypto_phase1_fair_values_from_snapshots(
        snapshots=snapshots,
        underlying_states=underlying_states,
        slippage_bps=slippage_bps,
        adverse_selection_bps=adverse_selection_bps,
        barrier_model_config=resolved_barrier_model_config,
        fusion_model_config=resolved_fusion_model_config,
    )
    result = await _run_crypto_phase2_loop_with_settings(
        snapshots=snapshots,
        fair_values=fair_values,
        underlying_states=underlying_states,
        settings=settings,
        config_dir=config_dir,
        snapshot_path=snapshot_path,
        output_dir=output_dir,
        run_id=run_id,
        barrier_model_config=resolved_barrier_model_config,
        fusion_model_config=resolved_fusion_model_config,
        apply_series_filter=apply_series_filter,
        selection_report_path=selection_report_path,
        strategy_overrides=strategy_overrides,
    )
    attribution_rows = build_crypto_attribution_rows(
        fair_values=fair_values,
        event_path=result.events_path,
        strategy_id="crypto.phase2",
    )
    write_phase1_artifacts(
        summary=result.summary,
        fair_values=fair_values,
        attribution_rows=attribution_rows,
    )
    return fair_values


def compute_crypto_phase2_fair_values(
    *,
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    slippage_bps: float = 5.0,
    adverse_selection_bps: float = 10.0,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
) -> tuple[FairValueEstimate, ...]:
    return compute_crypto_phase1_fair_values(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        slippage_bps=slippage_bps,
        adverse_selection_bps=adverse_selection_bps,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )


async def _run_crypto_phase2_loop(
    *,
    snapshot_path: str | Path,
    fair_values: tuple[FairValueEstimate, ...],
    underlying_states: dict[str, CryptoUnderlyingState],
    config_dir: str | Path,
    limit: int | None,
    output_dir: str | Path | None,
    run_id: str | None,
    barrier_model_config: CryptoBarrierModelConfig,
    fusion_model_config: CryptoFusionModelConfig,
    apply_series_filter: bool,
    selection_report_path: str | Path | None,
    strategy_overrides: dict[str, object] | None,
) -> Phase1ReplayResult:
    snapshots = load_market_snapshots(snapshot_path)
    if limit is not None:
        snapshots = snapshots[: max(limit, 0)]
    settings = load_settings_from_directory(config_dir)
    return await _run_crypto_phase2_loop_with_settings(
        snapshots=snapshots,
        fair_values=fair_values,
        underlying_states=underlying_states,
        settings=settings,
        config_dir=str(config_dir),
        snapshot_path=snapshot_path,
        output_dir=output_dir,
        run_id=run_id,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
        apply_series_filter=apply_series_filter,
        selection_report_path=selection_report_path,
        strategy_overrides=strategy_overrides,
    )


async def _run_crypto_phase2_loop_with_settings(
    *,
    snapshots: Sequence[MarketSnapshot],
    fair_values: tuple[FairValueEstimate, ...],
    underlying_states: dict[str, CryptoUnderlyingState],
    settings: BotSettings,
    config_dir: str,
    snapshot_path: str | Path,
    output_dir: str | Path | None,
    run_id: str | None,
    barrier_model_config: CryptoBarrierModelConfig,
    fusion_model_config: CryptoFusionModelConfig,
    apply_series_filter: bool,
    selection_report_path: str | Path | None,
    strategy_overrides: dict[str, object] | None,
) -> Phase1ReplayResult:
    started_at = snapshots[0].timestamp if snapshots else datetime.now(tz=timezone.utc)

    resolved_run_id = run_id or "crypto-phase2-replay"
    resolved_output_dir = Path(output_dir) if output_dir is not None else build_phase1_output_dir(
        "crypto",
        resolved_run_id,
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    events_path = resolved_output_dir / "events.jsonl"
    engine_metrics_path = resolved_output_dir / "engine.metrics.json"
    _reset_replay_output_files(events_path=events_path, engine_metrics_path=engine_metrics_path)

    strategy_config = dict(settings.category_configs[Category.CRYPTO].strategy.get("phase2", {}))
    if strategy_overrides:
        strategy_config.update(strategy_overrides)
    strategy = CryptoPhase2Strategy(strategy_config)
    static_blocked_series_keys = (
        set(load_runtime_blocked_series_keys(selection_report_path))
        if selection_report_path is not None
        else set()
    )
    static_blocked_market_ids = (
        set(load_runtime_blocked_market_ids(selection_report_path))
        if selection_report_path is not None
        else set()
    )
    static_blocked_series_reasons = (
        load_runtime_blocked_series_reasons(selection_report_path)
        if selection_report_path is not None
        else {}
    )
    static_blocked_market_reasons = (
        load_runtime_blocked_market_reasons(selection_report_path)
        if selection_report_path is not None
        else {}
    )
    static_market_selection_actions = (
        load_runtime_market_selection_actions(selection_report_path)
        if selection_report_path is not None
        else {}
    )
    static_market_selection_reasons = (
        load_runtime_market_selection_reasons(selection_report_path)
        if selection_report_path is not None
        else {}
    )
    blocked_series_keys: set[str] = set(static_blocked_series_keys)
    blocked_market_ids: set[str] = set(static_blocked_market_ids)
    blocked_series_reasons: dict[str, tuple[str, ...]] = dict(static_blocked_series_reasons)
    blocked_market_reasons: dict[str, tuple[str, ...]] = dict(static_blocked_market_reasons)
    market_selection_actions: dict[str, str] = dict(static_market_selection_actions)
    market_selection_reasons: dict[str, tuple[str, ...]] = dict(static_market_selection_reasons)
    risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state=RuntimeState(
            starting_equity=settings.trading.starting_equity,
            day_starting_equity=settings.trading.starting_equity,
            day_started_at=started_at,
            updated_at=started_at,
        ),
    )
    execution = PaperExecutionAdapter(
        ttl_seconds=settings.trading.default_quote_ttl_seconds,
        place_latency_ms=settings.trading.paper_place_latency_ms,
        cancel_latency_ms=settings.trading.paper_cancel_latency_ms,
        fee_bps=settings.trading.paper_fee_bps,
        taker_slippage_bps=settings.trading.paper_taker_slippage_bps,
    )
    recorder = ResearchRecorder(path=events_path, metrics_path=engine_metrics_path)
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter(snapshots),
        strategies=[strategy],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=settings.trading.default_order_notional,
    )

    fair_values_by_market_id = {item.market_id: item for item in fair_values}
    position_intents_by_market_id: dict[str, CryptoPositionIntent] = {}
    reentry_state_by_market_id: dict[str, CryptoReentryState] = {}
    processed_event_count = 0
    processed = 0

    for snapshot in snapshots:
        risk_manager.record_data_success(snapshot.timestamp)
        recorder.note_snapshot(snapshot.timestamp)
        fair_values_by_market_id = _refresh_fair_values_by_market_id(
            snapshots=tuple(router.snapshot_cache.values()) + (snapshot,),
            underlying_states=underlying_states,
            barrier_model_config=barrier_model_config,
            fusion_model_config=fusion_model_config,
        )
        if apply_series_filter:
            (
                runtime_blocked_series_keys,
                runtime_blocked_market_ids,
                runtime_blocked_series_reasons,
                runtime_blocked_market_reasons,
                runtime_selection_actions,
                runtime_selection_reasons,
            ) = _runtime_blocked_selection(
                snapshots=tuple(router.snapshot_cache.values()) + (snapshot,),
                snapshot_path=snapshot_path,
                underlying_states=underlying_states,
                recorder=recorder,
                barrier_model_config=barrier_model_config,
                fusion_model_config=fusion_model_config,
            )
            blocked_series_keys = static_blocked_series_keys.union(runtime_blocked_series_keys)
            blocked_market_ids = static_blocked_market_ids.union(runtime_blocked_market_ids)
            blocked_series_reasons = dict(static_blocked_series_reasons)
            blocked_series_reasons.update(runtime_blocked_series_reasons)
            blocked_market_reasons = dict(static_blocked_market_reasons)
            blocked_market_reasons.update(runtime_blocked_market_reasons)
            market_selection_actions = dict(static_market_selection_actions)
            market_selection_actions.update(runtime_selection_actions)
            market_selection_reasons = dict(static_market_selection_reasons)
            market_selection_reasons.update(runtime_selection_reasons)
        await sync_paper_execution_state(
            risk_manager=risk_manager,
            execution=execution,
            snapshot=snapshot,
            ttl_seconds=settings.trading.default_quote_ttl_seconds,
            recorder=recorder,
        )
        processed_event_count = _update_runtime_context_from_events(
            recorder=recorder,
            fair_values_by_market_id=fair_values_by_market_id,
            position_intents_by_market_id=position_intents_by_market_id,
            reentry_state_by_market_id=reentry_state_by_market_id,
            start_index=processed_event_count,
        )
        await router.run_once(
            snapshot=snapshot,
            context={
                "fair_values_by_market_id": fair_values_by_market_id,
                "position_intents_by_market_id": position_intents_by_market_id,
                "reentry_state_by_market_id": reentry_state_by_market_id,
                "blocked_series_keys": blocked_series_keys,
                "blocked_market_ids": blocked_market_ids,
                "blocked_series_reasons": blocked_series_reasons,
                "blocked_market_reasons": blocked_market_reasons,
                "market_selection_actions": market_selection_actions,
                "market_selection_reasons": market_selection_reasons,
            },
        )
        await sync_paper_execution_state(
            risk_manager=risk_manager,
            execution=execution,
            snapshot=snapshot,
            ttl_seconds=settings.trading.default_quote_ttl_seconds,
            recorder=recorder,
        )
        processed_event_count = _update_runtime_context_from_events(
            recorder=recorder,
            fair_values_by_market_id=fair_values_by_market_id,
            position_intents_by_market_id=position_intents_by_market_id,
            reentry_state_by_market_id=reentry_state_by_market_id,
            start_index=processed_event_count,
        )
        processed += 1

    replay_result = ResearchRunResult(
        mode="replay",
        processed_snapshots=processed,
        signals_generated=sum(1 for event in recorder.events if event["event_type"] == "signal.generated"),
        signals_rejected=sum(1 for event in recorder.events if event["event_type"] == "signal.rejected"),
        orders_rejected=sum(1 for event in recorder.events if event["event_type"] == "order.rejected"),
        submitted_orders=len(execution.submitted_orders),
        events_recorded=len(recorder.events),
        generated_by_strategy={"crypto.phase2": sum(1 for event in recorder.events if event["event_type"] == "signal.generated")},
        submitted_by_strategy={"crypto.phase2": sum(1 for event in recorder.events if event["event_type"] == "order.submitted")},
        dashboard=risk_manager.dashboard_state(),
    )
    summary = Phase1RunSummary(
        generated_at=snapshots[-1].timestamp if snapshots else datetime.now(tz=timezone.utc),
        board=Category.CRYPTO,
        mode="replay",
        run_id=resolved_run_id,
        config_dir=str(config_dir),
        snapshot_path=str(Path(snapshot_path)),
        output_dir=str(resolved_output_dir),
        processed_snapshots=replay_result.processed_snapshots,
        signals_generated=replay_result.signals_generated,
        signals_rejected=replay_result.signals_rejected,
        orders_rejected=replay_result.orders_rejected,
        submitted_orders=replay_result.submitted_orders,
        events_recorded=replay_result.events_recorded,
        generated_by_strategy=replay_result.generated_by_strategy,
        submitted_by_strategy=replay_result.submitted_by_strategy,
        total_equity=replay_result.dashboard.total_equity,
        today_pnl=replay_result.dashboard.today_pnl,
        status=_resolve_replay_summary_status(
            mode="replay",
            dashboard_status=replay_result.dashboard.status,
            halt_reason=replay_result.dashboard.halt_reason,
        ),
        halt_reason=replay_result.dashboard.halt_reason.value,
    )
    artifacts = write_phase1_artifacts(summary=summary, fair_values=fair_values, attribution_rows=())
    return Phase1ReplayResult(
        board=Category.CRYPTO,
        run_id=resolved_run_id,
        config_dir=str(config_dir),
        snapshot_path=str(Path(snapshot_path)),
        output_dir=resolved_output_dir,
        events_path=events_path,
        engine_metrics_path=engine_metrics_path,
        summary=summary,
        artifacts=artifacts,
        replay=replay_result,
    )


def _refresh_fair_values_by_market_id(
    *,
    snapshots: Sequence[MarketSnapshot],
    underlying_states: dict[str, CryptoUnderlyingState],
    barrier_model_config: CryptoBarrierModelConfig,
    fusion_model_config: CryptoFusionModelConfig,
) -> dict[str, FairValueEstimate]:
    fair_values = compute_crypto_phase1_fair_values_from_snapshots(
        snapshots=snapshots,
        underlying_states=underlying_states,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )
    return {item.market_id: item for item in fair_values}


def _runtime_blocked_selection(
    *,
    snapshots: Sequence[MarketSnapshot],
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    recorder: ResearchRecorder,
    barrier_model_config: CryptoBarrierModelConfig,
    fusion_model_config: CryptoFusionModelConfig,
) -> tuple[
    set[str],
    set[str],
    dict[str, tuple[str, ...]],
    dict[str, tuple[str, ...]],
    dict[str, str],
    dict[str, tuple[str, ...]],
]:
    selection_report = generate_crypto_market_selection_report_from_snapshots(
        snapshots=snapshots,
        snapshot_label=str(snapshot_path),
        underlying_states=underlying_states,
        events=recorder.events,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )
    return (
        set(recommended_runtime_blocked_series_keys(selection_report)),
        set(recommended_runtime_blocked_market_ids(selection_report)),
        recommended_runtime_blocked_series_reasons(selection_report),
        recommended_runtime_blocked_market_reasons(selection_report),
        runtime_market_selection_actions(selection_report),
        runtime_market_selection_reasons(selection_report),
    )


def _update_runtime_context_from_events(
    *,
    recorder: ResearchRecorder,
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
