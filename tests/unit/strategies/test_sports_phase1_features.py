import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.sports.phase1.features import build_pregame_features, estimate_pregame_adjustments
from pm_bot.strategies.sports.phase1.normalization import normalize_sports_market


FIXTURE_SNAPSHOTS = Path("tests/fixtures/sports_phase1/nba_pregame_snapshots.jsonl")
FIXTURE_CASES = Path("tests/fixtures/sports_phase1/nba_feature_cases.json")


def test_build_pregame_features_returns_minutes_and_adjustments() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    snapshot.metadata.update(
        {
            "public_yes_probability": "0.49",
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
    assert round(features.observed_probability, 3) == 0.48
    assert features.minutes_to_start == 300.0
    assert features.anchor_probability == 0.52
    assert features.public_probability == 0.49
    assert features.injury_adjustment_bps == 45.0
    assert features.rest_adjustment_bps == 20.0


def test_estimate_pregame_adjustments_sums_metadata_bps() -> None:
    snapshot = load_market_snapshots(FIXTURE_SNAPSHOTS)[0]
    payload = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))["pregame_moneyline"]
    snapshot.metadata.update({key: str(value) for key, value in payload.items() if key.endswith("_bps")})

    adjustment = estimate_pregame_adjustments(snapshot=snapshot)

    assert adjustment.injury_adjustment_bps == 45.0
    assert adjustment.lineup_adjustment_bps == 10.0
    assert adjustment.travel_adjustment_bps == -15.0
    assert adjustment.rest_adjustment_bps == 20.0
    assert adjustment.total_adjustment_bps == 60.0
