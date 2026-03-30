from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.sports.phase1.anchors import estimate_odds_anchor
from pm_bot.strategies.sports.phase1.features import build_pregame_features
from pm_bot.strategies.sports.phase1.normalization import normalize_sports_market
from pm_bot.strategies.sports.phase1.pricing import (
    estimate_line_dislocation,
    estimate_pregame_fair_value,
    to_fair_value_estimate,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/sports_phase1/nba_pregame_snapshots.jsonl")


def test_estimate_pregame_fair_value_uses_anchor_and_feature_adjustments() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    snapshot.metadata.update(
        {
            "sharp_yes_probability": "0.52",
            "public_yes_probability": "0.49",
            "injury_adjustment_bps": "45",
            "lineup_adjustment_bps": "10",
            "travel_adjustment_bps": "-15",
            "rest_adjustment_bps": "20",
        }
    )
    event = normalize_sports_market(snapshot)
    assert event is not None
    anchor = estimate_odds_anchor(snapshot)
    assert anchor is not None
    features = build_pregame_features(snapshot=snapshot, event=event, anchor_probability=anchor.anchor_probability)
    assert features is not None

    fair_value = estimate_pregame_fair_value(features)

    assert round(fair_value.anchor_probability, 3) == 0.52
    assert round(fair_value.fair_probability, 4) == 0.5185
    assert fair_value.confidence >= 0.7


def test_estimate_line_dislocation_and_export_fair_value_estimate() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    snapshot.metadata.update(
        {
            "sharp_yes_probability": "0.52",
            "injury_adjustment_bps": "45",
            "lineup_adjustment_bps": "10",
            "travel_adjustment_bps": "-15",
            "rest_adjustment_bps": "20",
        }
    )
    event = normalize_sports_market(snapshot)
    assert event is not None
    anchor = estimate_odds_anchor(snapshot)
    assert anchor is not None
    features = build_pregame_features(snapshot=snapshot, event=event, anchor_probability=anchor.anchor_probability)
    assert features is not None
    fair_value = estimate_pregame_fair_value(features)

    dislocation = estimate_line_dislocation(
        observed_probability=features.observed_probability,
        fair_value=fair_value,
    )
    estimate = to_fair_value_estimate(
        features=features,
        fair_value=fair_value,
        dislocation=dislocation,
    )

    assert round(dislocation.raw_edge_bps, 1) == 460.0
    assert dislocation.context_adjusted_edge_bps > 0
    assert estimate.category.value == "sports"
    assert estimate.model_id == "sports.phase1.pregame"
    assert estimate.supporting_values["raw_edge_bps"] == dislocation.raw_edge_bps
