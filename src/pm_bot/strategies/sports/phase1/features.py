"""Pregame feature helpers for Sports Phase 1 research."""

from __future__ import annotations

from datetime import timezone

from pm_bot.core.types import MarketSnapshot
from pm_bot.strategies.common import implied_yes_probability, parse_float
from pm_bot.strategies.sports.phase1.models import (
    SportsAdjustmentEstimate,
    SportsEventDefinition,
    SportsPregameFeatures,
)


def build_pregame_features(
    *,
    snapshot: MarketSnapshot,
    event: SportsEventDefinition,
    anchor_probability: float | None = None,
) -> SportsPregameFeatures | None:
    observed_probability = implied_yes_probability(snapshot)
    if observed_probability is None:
        return None

    start_time = event.start_time.astimezone(timezone.utc)
    minutes_to_start = (start_time - snapshot.timestamp).total_seconds() / 60
    if minutes_to_start <= 0:
        return None

    adjustment = estimate_pregame_adjustments(snapshot=snapshot)
    public_probability = _parse_optional_probability(
        snapshot,
        "consensus_yes_probability",
        "public_yes_probability",
        "crowd_yes_probability",
    )

    feature_values: dict[str, float | str] = {
        "league": event.league,
        "minutes_to_start": minutes_to_start,
    }
    if public_probability is not None:
        feature_values["public_probability"] = public_probability
    if anchor_probability is not None:
        feature_values["anchor_probability"] = anchor_probability

    return SportsPregameFeatures(
        event=event,
        observed_probability=observed_probability,
        start_time=start_time,
        minutes_to_start=minutes_to_start,
        anchor_probability=anchor_probability,
        public_probability=public_probability,
        injury_adjustment_bps=adjustment.injury_adjustment_bps,
        lineup_adjustment_bps=adjustment.lineup_adjustment_bps,
        travel_adjustment_bps=adjustment.travel_adjustment_bps,
        rest_adjustment_bps=adjustment.rest_adjustment_bps,
        feature_values=feature_values,
    )


def estimate_pregame_adjustments(*, snapshot: MarketSnapshot) -> SportsAdjustmentEstimate:
    injury_adjustment_bps = parse_float(snapshot.metadata, "injury_adjustment_bps") or 0.0
    lineup_adjustment_bps = parse_float(snapshot.metadata, "lineup_adjustment_bps") or 0.0
    travel_adjustment_bps = parse_float(snapshot.metadata, "travel_adjustment_bps") or 0.0
    rest_adjustment_bps = parse_float(snapshot.metadata, "rest_adjustment_bps") or 0.0
    total_adjustment_bps = (
        injury_adjustment_bps
        + lineup_adjustment_bps
        + travel_adjustment_bps
        + rest_adjustment_bps
    )
    return SportsAdjustmentEstimate(
        total_adjustment_bps=total_adjustment_bps,
        injury_adjustment_bps=injury_adjustment_bps,
        lineup_adjustment_bps=lineup_adjustment_bps,
        travel_adjustment_bps=travel_adjustment_bps,
        rest_adjustment_bps=rest_adjustment_bps,
    )


def _parse_optional_probability(snapshot: MarketSnapshot, *keys: str) -> float | None:
    for key in keys:
        raw = parse_float(snapshot.metadata, key)
        if raw is None:
            continue
        return raw / 100 if raw > 1 else raw
    return None
