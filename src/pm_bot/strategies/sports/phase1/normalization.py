"""Normalization helpers for supported sports Phase 1 market families."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone
import re

from pm_bot.core.research_types import NormalizedMarketDefinition
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.strategies.sports.phase1.models import SportsEventDefinition, SportsEventGroup

_VERSUS_PATTERN = re.compile(r"^\s*(.+?)\s+vs\.?\s+(.+?)\s*$", re.IGNORECASE)


def classify_sports_market(snapshot: MarketSnapshot) -> str | None:
    normalized = normalize_sports_market(snapshot)
    if normalized is None:
        return None
    return normalized.market_family


def normalize_sports_market(snapshot: MarketSnapshot) -> SportsEventDefinition | None:
    if snapshot.category != Category.SPORTS:
        return None

    metadata = snapshot.metadata
    league = str(metadata.get("league", metadata.get("sport", ""))).strip().lower()
    if league != "nba":
        return None

    if _is_live_market(metadata):
        return None

    market_family = str(metadata.get("market_family", "moneyline")).strip().lower()
    if market_family not in {"moneyline", ""}:
        return None

    event_title = str(metadata.get("event_title", "")).strip()
    teams = _parse_teams(event_title)
    if teams is None:
        return None
    away_team, home_team = teams

    start_time = _parse_datetime(
        metadata.get("start_time")
        or metadata.get("starts_at")
        or metadata.get("event_start")
        or metadata.get("scheduled_start")
        or snapshot.resolution_time
    )
    if start_time is None:
        return None

    event_key = f"nba:{start_time.date().isoformat()}:{_slugify(away_team)}-at-{_slugify(home_team)}"
    normalized = NormalizedMarketDefinition(
        market_id=snapshot.market_id,
        category=Category.SPORTS,
        market_family="pregame_moneyline",
        scope_key=event_key,
        instrument_key=f"{event_key}:moneyline",
        resolution_time=snapshot.resolution_time,
        attributes={
            "league": "nba",
            "market_family": "pregame_moneyline",
            "home_team": home_team,
            "away_team": away_team,
            "event_key": event_key,
        },
    )
    return SportsEventDefinition(
        normalized=normalized,
        league="nba",
        market_family="pregame_moneyline",
        home_team=home_team,
        away_team=away_team,
        start_time=start_time,
        event_key=event_key,
    )


def build_sports_event_schedule(snapshots: Sequence[MarketSnapshot]) -> tuple[SportsEventGroup, ...]:
    grouped: dict[str, list[SportsEventDefinition]] = defaultdict(list)
    for snapshot in snapshots:
        normalized = normalize_sports_market(snapshot)
        if normalized is None:
            continue
        grouped[normalized.event_key].append(normalized)

    events: list[SportsEventGroup] = []
    for event_key, markets in sorted(grouped.items()):
        ordered_markets = tuple(sorted(markets, key=lambda item: item.normalized.market_id))
        first = ordered_markets[0]
        events.append(
            SportsEventGroup(
                event_key=event_key,
                league=first.league,
                market_family=first.market_family,
                start_time=first.start_time,
                markets=ordered_markets,
            )
        )
    return tuple(events)


def _is_live_market(metadata: dict[str, str]) -> bool:
    game_status = str(metadata.get("game_status", "")).strip().lower()
    if game_status in {"in_progress", "final", "halftime"}:
        return True
    if any(key in metadata for key in ("live_yes_probability", "live_state_updated_at")):
        return True
    return False


def _parse_teams(event_title: str) -> tuple[str, str] | None:
    match = _VERSUS_PATTERN.match(event_title)
    if match is None:
        return None
    away_team = match.group(1).strip()
    home_team = match.group(2).strip()
    if not away_team or not home_team:
        return None
    return (away_team, home_team)


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return text.strip("-")


def _parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
