"""Board-specific replay wrapper for Weather Phase 1 research."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.research import run_phase1_replay
from pm_bot.research.engine import load_market_snapshots
from pm_bot.research.phase1_artifacts import write_phase1_artifacts
from pm_bot.strategies.common import implied_yes_probability
from pm_bot.strategies.weather.phase1.attribution import build_weather_attribution_rows
from pm_bot.strategies.weather.phase1.forecasts import ingest_forecast_runs
from pm_bot.strategies.weather.phase1.fusion import fuse_weather_fair_value, to_fair_value_estimate
from pm_bot.strategies.weather.phase1.normalization import normalize_weather_market
from pm_bot.strategies.weather.phase1.pricing import (
    build_forecast_distribution,
    build_weather_peer_probability_map,
    estimate_strip_consistency,
    estimate_threshold_probability,
)
from pm_bot.strategies.weather.phase1.reports import (
    generate_weather_market_selection_report,
    generate_weather_run_scorecard_report,
    generate_weather_settlement_audit_report,
)
from pm_bot.strategies.weather.phase1.final_report import generate_weather_final_scorecard
from pm_bot.strategies.weather.phase1.models import WeatherMarketDefinition
from pm_bot.strategies.weather.phase1.skill import apply_bias_corrections, load_model_skill_store


async def run_weather_phase1_replay(
    *,
    snapshot_path: str | Path,
    forecast_payloads: Sequence[dict[str, object]],
    skill_payloads: Sequence[dict[str, object]],
    config_dir: str | Path | None = None,
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> tuple[FairValueEstimate, ...]:
    fair_values = compute_weather_phase1_fair_values(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
    )
    result = await run_phase1_replay(
        board=Category.WEATHER,
        snapshot_path=snapshot_path,
        config_dir=config_dir,
        limit=limit,
        output_dir=output_dir,
        run_id=run_id,
        fair_values=fair_values,
        attribution_rows=(),
    )
    attribution_rows = build_weather_attribution_rows(
        fair_values=fair_values,
        event_path=result.events_path,
    )
    write_phase1_artifacts(
        summary=result.summary,
        fair_values=fair_values,
        attribution_rows=attribution_rows,
    )
    if output_dir is not None:
        generate_weather_market_selection_report(
            snapshot_path=snapshot_path,
            forecast_payloads=list(forecast_payloads),
            skill_payloads=list(skill_payloads),
            output_dir=output_dir,
        )
        generate_weather_settlement_audit_report(
            snapshot_path=snapshot_path,
            forecast_payloads=list(forecast_payloads),
            skill_payloads=list(skill_payloads),
            output_dir=output_dir,
        )
        generate_weather_run_scorecard_report(
            snapshot_path=snapshot_path,
            forecast_payloads=list(forecast_payloads),
            skill_payloads=list(skill_payloads),
            output_dir=output_dir,
        )
        generate_weather_final_scorecard(
            snapshot_path=snapshot_path,
            forecast_payloads=list(forecast_payloads),
            skill_payloads=list(skill_payloads),
            output_dir=output_dir,
        )
    return fair_values


def compute_weather_phase1_fair_values(
    *,
    snapshot_path: str | Path,
    forecast_payloads: Sequence[dict[str, object]],
    skill_payloads: Sequence[dict[str, object]],
) -> tuple[FairValueEstimate, ...]:
    snapshots = load_market_snapshots(snapshot_path)
    latest_by_market: dict[str, MarketSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.category != Category.WEATHER:
            continue
        latest_by_market[snapshot.market_id] = snapshot

    normalized_markets: list[tuple[MarketSnapshot, WeatherMarketDefinition]] = []
    for snapshot in latest_by_market.values():
        normalized = normalize_weather_market(snapshot)
        if normalized is not None:
            normalized_markets.append((snapshot, normalized))

    fair_values: list[FairValueEstimate] = []
    series_keys = sorted({market.series_key for _, market in normalized_markets})
    for series_key in series_keys:
        series_rows = [
            (snapshot, market)
            for snapshot, market in normalized_markets
            if market.series_key == series_key
        ]
        ordered_markets = tuple(
            market
            for _, market in sorted(
                series_rows,
                key=lambda item: item[1].threshold,
            )
        )
        peer_snapshot_probabilities = tuple(
            (
                market,
                observed_probability,
            )
            for snapshot, market in series_rows
            if (observed_probability := implied_yes_probability(snapshot)) is not None
        )
        peer_probability_map = build_weather_peer_probability_map(
            markets=ordered_markets,
            snapshots=peer_snapshot_probabilities,
        )

        for snapshot, market in series_rows:
            observed_probability = implied_yes_probability(snapshot)
            if observed_probability is None:
                continue
            forecast_runs = ingest_forecast_runs(
                market=market,
                run_payloads=forecast_payloads,
            )
            if not forecast_runs:
                continue
            skill_store = load_model_skill_store(
                market=market,
                skill_payloads=skill_payloads,
            )
            corrected = apply_bias_corrections(
                market=market,
                forecast_runs=forecast_runs,
                skill_store=skill_store,
            )
            distribution = build_forecast_distribution(
                market=market,
                corrected_forecasts=corrected,
            )
            if distribution is None:
                continue
            threshold_estimate = estimate_threshold_probability(
                market=market,
                distribution=distribution,
            )
            strip_estimate = estimate_strip_consistency(
                series_key=market.series_key,
                market=market,
                observed_probability=observed_probability,
                peer_probabilities=peer_probability_map,
                ordered_markets=ordered_markets,
            )
            fused = fuse_weather_fair_value(
                market=market,
                distribution=distribution,
                threshold_estimate=threshold_estimate,
                strip_estimate=strip_estimate,
                observed_probability=observed_probability,
            )
            fair_values.append(
                to_fair_value_estimate(
                    market=market,
                    fused=fused,
                    distribution=distribution,
                    observed_probability=observed_probability,
                )
            )
    return tuple(sorted(fair_values, key=lambda item: item.market_id))
