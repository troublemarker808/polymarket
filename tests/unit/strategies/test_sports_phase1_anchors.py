import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.sports.phase1.anchors import apply_anchor_adjustments, estimate_odds_anchor
from pm_bot.strategies.sports.phase1.features import build_pregame_features
from pm_bot.strategies.sports.phase1.normalization import normalize_sports_market


FIXTURE_SNAPSHOTS = Path("tests/fixtures/sports_phase1/nba_pregame_snapshots.jsonl")
FIXTURE_CASES = Path("tests/fixtures/sports_phase1/nba_feature_cases.json")


def test_estimate_odds_anchor_prefers_sharp_probability() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    payload = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))["pregame_moneyline"]
    snapshot.metadata["sharp_yes_probability"] = str(payload["sharp_yes_probability"])
    snapshot.metadata["model_yes_probability"] = "0.54"

    anchor = estimate_odds_anchor(snapshot)

    assert anchor is not None
    assert anchor.source == "sharp"
    assert anchor.anchor_probability == 0.52


def test_apply_anchor_adjustments_moves_anchor_by_feature_bps() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    snapshot.metadata.update(
        {
            "injury_adjustment_bps": "45",
            "lineup_adjustment_bps": "10",
            "travel_adjustment_bps": "-15",
            "rest_adjustment_bps": "20",
        }
    )
    event = normalize_sports_market(snapshot)
    assert event is not None
    features = build_pregame_features(snapshot=snapshot, event=event, anchor_probability=0.52)
    assert features is not None

    adjusted = apply_anchor_adjustments(anchor_probability=0.52, features=features)

    assert round(adjusted, 4) == 0.526
