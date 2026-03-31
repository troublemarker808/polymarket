"""Board-specific replay wrapper for Crypto Phase 1 research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.research import run_phase1_replay
from pm_bot.research.engine import load_market_snapshots
from pm_bot.research.phase1_artifacts import write_phase1_artifacts
from pm_bot.strategies.crypto.phase1.attribution import build_crypto_attribution_rows
from pm_bot.strategies.crypto.phase1.baseline import resolve_crypto_calibration_model_configs
from pm_bot.strategies.crypto.phase1.edge import enrich_fair_value_with_net_edge, estimate_net_edge
from pm_bot.strategies.crypto.phase1.fusion import fuse_crypto_fair_value, to_fair_value_estimate
from pm_bot.strategies.crypto.phase1.inputs import build_pricing_inputs
from pm_bot.strategies.crypto.phase1.models import (
    CryptoBarrierModelConfig,
    CryptoFusionModelConfig,
    CryptoMarketDefinition,
    CryptoResidualModelConfig,
    CryptoUnderlyingState,
)
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.pricing import (
    build_peer_probability_map,
    estimate_barrier_probability,
    estimate_surface_consistency,
    observed_mid_probability,
)
from pm_bot.strategies.crypto.phase1.series import build_crypto_ladder_series


async def run_crypto_phase1_replay(
    *,
    snapshot_path: str | Path,
    underlying_states: Mapping[str, CryptoUnderlyingState],
    config_dir: str | Path | None = None,
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    slippage_bps: float = 5.0,
    adverse_selection_bps: float = 10.0,
) -> tuple[FairValueEstimate, ...]:
    fair_values = compute_crypto_phase1_fair_values(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        slippage_bps=slippage_bps,
        adverse_selection_bps=adverse_selection_bps,
    )
    result = await run_phase1_replay(
        board=Category.CRYPTO,
        snapshot_path=snapshot_path,
        config_dir=config_dir,
        limit=limit,
        output_dir=output_dir,
        run_id=run_id,
        fair_values=fair_values,
        attribution_rows=(),
    )
    attribution_rows = build_crypto_attribution_rows(
        fair_values=fair_values,
        event_path=result.events_path,
    )
    write_phase1_artifacts(
        summary=result.summary,
        fair_values=fair_values,
        attribution_rows=attribution_rows,
    )
    return fair_values


def compute_crypto_phase1_fair_values(
    *,
    snapshot_path: str | Path,
    underlying_states: Mapping[str, CryptoUnderlyingState],
    slippage_bps: float = 5.0,
    adverse_selection_bps: float = 10.0,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
    residual_model_config: CryptoResidualModelConfig | None = None,
) -> tuple[FairValueEstimate, ...]:
    _, resolved_barrier_model_config, resolved_fusion_model_config, resolved_residual_model_config = resolve_crypto_calibration_model_configs(
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
        residual_model_config=residual_model_config,
    )
    snapshots = load_market_snapshots(snapshot_path)
    return compute_crypto_phase1_fair_values_from_snapshots(
        snapshots=snapshots,
        underlying_states=underlying_states,
        slippage_bps=slippage_bps,
        adverse_selection_bps=adverse_selection_bps,
        barrier_model_config=resolved_barrier_model_config,
        fusion_model_config=resolved_fusion_model_config,
        residual_model_config=resolved_residual_model_config,
    )


def compute_crypto_phase1_fair_values_from_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    underlying_states: Mapping[str, CryptoUnderlyingState],
    slippage_bps: float = 5.0,
    adverse_selection_bps: float = 10.0,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
    residual_model_config: CryptoResidualModelConfig | None = None,
) -> tuple[FairValueEstimate, ...]:
    _, resolved_barrier_model_config, resolved_fusion_model_config, resolved_residual_model_config = resolve_crypto_calibration_model_configs(
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
        residual_model_config=residual_model_config,
    )
    latest_by_market: dict[str, MarketSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.category != Category.CRYPTO:
            continue
        latest_by_market[snapshot.market_id] = snapshot

    normalized_markets: list[tuple[MarketSnapshot, CryptoMarketDefinition]] = []
    for snapshot in latest_by_market.values():
        normalized = normalize_crypto_market(snapshot)
        if normalized is not None:
            normalized_markets.append((snapshot, normalized))

    series_by_scope = {
        series.series_key: series
        for series in build_crypto_ladder_series([snapshot for snapshot, _ in normalized_markets])
    }

    fair_values: list[FairValueEstimate] = []
    for scope_key, series in series_by_scope.items():
        peer_probability_map = build_peer_probability_map(
            series=series,
            snapshots=tuple(
                (
                    normalized,
                    observed_mid_probability(
                        snapshot.best_bid_yes,
                        snapshot.best_ask_yes,
                        snapshot.last_traded_price,
                    ) or 0.0,
                )
                for snapshot, normalized in normalized_markets
                if normalized.normalized.scope_key == scope_key
            ),
        )
        for snapshot, market in normalized_markets:
            if market.normalized.scope_key != scope_key:
                continue
            observed_probability = observed_mid_probability(
                snapshot.best_bid_yes,
                snapshot.best_ask_yes,
                snapshot.last_traded_price,
            )
            if observed_probability is None:
                continue
            underlying_state = underlying_states.get(market.underlying)
            if underlying_state is None:
                continue
            pricing_inputs = build_pricing_inputs(
                market=market,
                underlying_state=underlying_state,
                as_of=snapshot.timestamp,
            )
            barrier = estimate_barrier_probability(
                pricing_inputs,
                model_config=resolved_barrier_model_config,
            )
            surface = estimate_surface_consistency(
                series=series,
                market=market,
                observed_probability=observed_probability,
                peer_probabilities=peer_probability_map,
            )
            fused = fuse_crypto_fair_value(
                inputs=pricing_inputs,
                barrier_estimate=barrier,
                surface_estimate=surface,
                observed_probability=observed_probability,
                model_config=resolved_fusion_model_config,
                residual_model_config=resolved_residual_model_config,
            )
            fair_estimate = to_fair_value_estimate(
                inputs=pricing_inputs,
                fused=fused,
                observed_probability=observed_probability,
            )
            trade_side = _trade_side_from_probabilities(
                fair_probability=fair_estimate.fair_probability,
                observed_probability=observed_probability,
            )
            entry_cost_bps = _spread_cost_bps_for_side(snapshot=snapshot, side=trade_side)
            net_edge = estimate_net_edge(
                market_id=market.normalized.market_id,
                fair_probability=fair_estimate.fair_probability,
                observed_probability=observed_probability,
                entry_cost_bps=entry_cost_bps,
                exit_cost_bps=entry_cost_bps,
                slippage_bps=slippage_bps,
                adverse_selection_bps=adverse_selection_bps,
            )
            fair_estimate = FairValueEstimate(
                market_id=fair_estimate.market_id,
                category=fair_estimate.category,
                fair_probability=fair_estimate.fair_probability,
                confidence=fair_estimate.confidence,
                half_life_seconds=fair_estimate.half_life_seconds,
                observed_probability=fair_estimate.observed_probability,
                model_id=fair_estimate.model_id,
                rationale_tags=fair_estimate.rationale_tags,
                supporting_values={
                    **fair_estimate.supporting_values,
                    "trade_side": trade_side.value,
                    "runtime_spread_bps": entry_cost_bps * 2.0,
                },
            )
            fair_values.append(
                enrich_fair_value_with_net_edge(
                    estimate=fair_estimate,
                    net_edge=net_edge,
                )
            )
    return tuple(sorted(fair_values, key=lambda item: item.market_id))


def _spread_cost_bps(best_bid_yes: float | None, best_ask_yes: float | None) -> float:
    if best_bid_yes is None or best_ask_yes is None:
        return 0.0
    return max(best_ask_yes - best_bid_yes, 0.0) * 5000


def _trade_side_from_probabilities(*, fair_probability: float, observed_probability: float) -> SignalSide:
    if fair_probability >= observed_probability:
        return SignalSide.BUY_YES
    return SignalSide.BUY_NO


def _spread_cost_bps_for_side(*, snapshot: MarketSnapshot, side: SignalSide) -> float:
    if side == SignalSide.BUY_NO:
        return _spread_cost_bps(snapshot.best_bid_no, snapshot.best_ask_no)
    return _spread_cost_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
