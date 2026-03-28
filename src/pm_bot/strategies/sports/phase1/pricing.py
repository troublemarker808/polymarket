"""Pricing helpers for Sports Phase 1 pregame research."""

from __future__ import annotations

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.sports.phase1.models import (
    SportsDislocationEstimate,
    SportsFairValue,
    SportsPregameFeatures,
)


def estimate_pregame_fair_value(features: SportsPregameFeatures) -> SportsFairValue:
    anchor_probability = features.anchor_probability or features.observed_probability
    adjustment_bps = (
        features.injury_adjustment_bps
        + features.lineup_adjustment_bps
        + features.travel_adjustment_bps
        + features.rest_adjustment_bps
    )
    public_pull_bps = 0.0
    if features.public_probability is not None:
        public_pull_bps = (features.public_probability - anchor_probability) * 2500.0
    adjusted_probability = anchor_probability + ((adjustment_bps + public_pull_bps) / 10000.0)
    fair_probability = max(0.01, min(0.99, adjusted_probability))
    confidence = _pregame_confidence(features=features)
    return SportsFairValue(
        fair_probability=fair_probability,
        confidence=confidence,
        model_adjustment_bps=adjustment_bps + public_pull_bps,
        anchor_probability=anchor_probability,
        rationale_tags=("pregame_anchor", "feature_adjusted"),
    )


def estimate_line_dislocation(
    *,
    observed_probability: float,
    fair_value: SportsFairValue,
) -> SportsDislocationEstimate:
    raw_edge_bps = (fair_value.fair_probability - observed_probability) * 10000
    confidence_scale = max(fair_value.confidence, 0.1)
    context_adjusted_edge_bps = raw_edge_bps * confidence_scale
    return SportsDislocationEstimate(
        observed_probability=observed_probability,
        fair_probability=fair_value.fair_probability,
        raw_edge_bps=raw_edge_bps,
        context_adjusted_edge_bps=context_adjusted_edge_bps,
    )


def to_fair_value_estimate(
    *,
    features: SportsPregameFeatures,
    fair_value: SportsFairValue,
    dislocation: SportsDislocationEstimate,
) -> FairValueEstimate:
    return FairValueEstimate(
        market_id=features.event.normalized.market_id,
        category=Category.SPORTS,
        fair_probability=fair_value.fair_probability,
        confidence=fair_value.confidence,
        half_life_seconds=_pregame_half_life_seconds(features.minutes_to_start),
        observed_probability=features.observed_probability,
        model_id="sports.phase1.pregame",
        rationale_tags=fair_value.rationale_tags,
        supporting_values={
            "anchor_probability": fair_value.anchor_probability,
            "model_adjustment_bps": fair_value.model_adjustment_bps,
            "raw_edge_bps": dislocation.raw_edge_bps,
            "context_adjusted_edge_bps": dislocation.context_adjusted_edge_bps,
            "minutes_to_start": features.minutes_to_start,
        },
    )


def _pregame_confidence(*, features: SportsPregameFeatures) -> float:
    confidence = 0.58
    if features.anchor_probability is not None:
        confidence += 0.08
    if features.public_probability is not None:
        confidence += 0.04
    if features.minutes_to_start <= 360:
        confidence += 0.05
    if abs(
        features.injury_adjustment_bps
        + features.lineup_adjustment_bps
        + features.travel_adjustment_bps
        + features.rest_adjustment_bps
    ) >= 40:
        confidence += 0.04
    return max(0.5, min(0.82, confidence))


def _pregame_half_life_seconds(minutes_to_start: float) -> int:
    if minutes_to_start <= 120:
        return 3600
    if minutes_to_start <= 360:
        return 3 * 3600
    return 6 * 3600
