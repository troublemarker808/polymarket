"""Anchor and adjustment helpers for Sports Phase 1 research."""

from __future__ import annotations

from pm_bot.core.types import MarketSnapshot
from pm_bot.strategies.common import parse_float
from pm_bot.strategies.sports.phase1.models import SportsAnchorEstimate, SportsPregameFeatures


def estimate_odds_anchor(snapshot: MarketSnapshot) -> SportsAnchorEstimate | None:
    for key, source in (
        ("sharp_yes_probability", "sharp"),
        ("market_implied_yes_probability", "market_implied"),
        ("model_yes_probability", "model"),
    ):
        value = parse_float(snapshot.metadata, key)
        if value is None:
            continue
        probability = value / 100 if value > 1 else value
        return SportsAnchorEstimate(anchor_probability=probability, source=source)
    return None


def apply_anchor_adjustments(
    *,
    anchor_probability: float,
    features: SportsPregameFeatures,
) -> float:
    adjusted_probability = anchor_probability + (
        (
            features.injury_adjustment_bps
            + features.lineup_adjustment_bps
            + features.travel_adjustment_bps
            + features.rest_adjustment_bps
        )
        / 10000.0
    )
    return max(0.01, min(0.99, adjusted_probability))
