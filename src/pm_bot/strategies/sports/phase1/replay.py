"""Board-specific replay wrapper for Sports Phase 1 research."""

from __future__ import annotations

from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.research import run_phase1_replay
from pm_bot.research.engine import load_market_snapshots
from pm_bot.research.phase1_artifacts import write_phase1_artifacts
from pm_bot.strategies.sports.phase1.anchors import estimate_odds_anchor
from pm_bot.strategies.sports.phase1.attribution import build_sports_attribution_rows
from pm_bot.strategies.sports.phase1.features import build_pregame_features
from pm_bot.strategies.sports.phase1.normalization import normalize_sports_market
from pm_bot.strategies.sports.phase1.pricing import (
    estimate_line_dislocation,
    estimate_pregame_fair_value,
    to_fair_value_estimate,
)


async def run_sports_phase1_replay(
    *,
    snapshot_path: str | Path,
    config_dir: str | Path | None = None,
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> tuple[FairValueEstimate, ...]:
    fair_values = compute_sports_phase1_fair_values(snapshot_path=snapshot_path)
    result = await run_phase1_replay(
        board=Category.SPORTS,
        snapshot_path=snapshot_path,
        config_dir=config_dir,
        limit=limit,
        output_dir=output_dir,
        run_id=run_id,
        fair_values=fair_values,
        attribution_rows=(),
    )
    attribution_rows = build_sports_attribution_rows(
        fair_values=fair_values,
        event_path=result.events_path,
    )
    write_phase1_artifacts(
        summary=result.summary,
        fair_values=fair_values,
        attribution_rows=attribution_rows,
    )
    return fair_values


def compute_sports_phase1_fair_values(
    *,
    snapshot_path: str | Path,
) -> tuple[FairValueEstimate, ...]:
    snapshots = load_market_snapshots(snapshot_path)
    latest_by_market: dict[str, object] = {}
    for snapshot in snapshots:
        if snapshot.category != Category.SPORTS:
            continue
        latest_by_market[snapshot.market_id] = snapshot

    fair_values: list[FairValueEstimate] = []
    for snapshot in latest_by_market.values():
        event = normalize_sports_market(snapshot)
        if event is None:
            continue
        anchor = estimate_odds_anchor(snapshot)
        features = build_pregame_features(
            snapshot=snapshot,
            event=event,
            anchor_probability=(anchor.anchor_probability if anchor is not None else None),
        )
        if features is None:
            continue
        fair_value = estimate_pregame_fair_value(features)
        dislocation = estimate_line_dislocation(
            observed_probability=features.observed_probability,
            fair_value=fair_value,
        )
        fair_values.append(
            to_fair_value_estimate(
                features=features,
                fair_value=fair_value,
                dislocation=dislocation,
            )
        )
    return tuple(sorted(fair_values, key=lambda item: item.market_id))
