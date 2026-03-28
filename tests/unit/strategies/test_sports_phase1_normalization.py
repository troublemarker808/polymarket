from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.sports.phase1 import build_sports_event_schedule, classify_sports_market, normalize_sports_market


FIXTURE_PATH = Path("tests/fixtures/sports_phase1/nba_pregame_snapshots.jsonl")


def test_normalize_sports_market_parses_supported_nba_pregame_moneyline() -> None:
    snapshot = load_market_snapshots(FIXTURE_PATH)[0]

    normalized = normalize_sports_market(snapshot)

    assert normalized is not None
    assert normalized.league == "nba"
    assert normalized.market_family == "pregame_moneyline"
    assert normalized.away_team == "Los Angeles Lakers"
    assert normalized.home_team == "Boston Celtics"
    assert normalized.event_key == "nba:2026-03-23:los-angeles-lakers-at-boston-celtics"
    assert normalized.normalized.scope_key == normalized.event_key


def test_classify_sports_market_rejects_live_and_non_nba_markets() -> None:
    snapshots = load_market_snapshots(FIXTURE_PATH)

    assert classify_sports_market(snapshots[2]) is None
    assert classify_sports_market(snapshots[3]) is None


def test_build_sports_event_schedule_groups_same_nba_game() -> None:
    snapshots = load_market_snapshots(FIXTURE_PATH)

    groups = build_sports_event_schedule(snapshots)

    assert len(groups) == 1
    group = groups[0]
    assert group.event_key == "nba:2026-03-23:los-angeles-lakers-at-boston-celtics"
    assert group.league == "nba"
    assert group.market_family == "pregame_moneyline"
    assert tuple(item.normalized.market_id for item in group.markets) == ("nba-1", "nba-2")
