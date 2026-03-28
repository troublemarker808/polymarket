"""Market-universe selection helpers for live and paper sessions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re

from pm_bot.core.types import MarketSnapshot


@dataclass(slots=True, frozen=True)
class MarketUniversePolicy:
    min_liquidity_score: float = 0.0
    asset_keywords: tuple[str, ...] = ()
    max_active_markets: int | None = None
    max_markets_per_event: int | None = None
    min_markets_per_event: int = 1


def build_snapshot_selector(
    markets_config: Mapping[str, object] | None,
):
    if not isinstance(markets_config, Mapping):
        return None
    policy = _policy_from_config(markets_config)
    if policy is None:
        return None
    return lambda snapshots: select_market_snapshots(snapshots=snapshots, policy=policy)


def select_market_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    policy: MarketUniversePolicy,
) -> list[MarketSnapshot]:
    candidates = list(snapshots)
    if not candidates:
        return []

    if policy.min_liquidity_score > 0:
        liquidity_filtered = [
            snapshot for snapshot in candidates if snapshot.liquidity_score >= policy.min_liquidity_score
        ]
        if liquidity_filtered:
            candidates = liquidity_filtered

    if policy.asset_keywords:
        asset_filtered = [
            snapshot
            for snapshot in candidates
            if _snapshot_matches_assets(snapshot=snapshot, asset_keywords=policy.asset_keywords)
        ]
        if asset_filtered:
            candidates = asset_filtered

    grouped = _group_snapshots(candidates)
    if policy.min_markets_per_event > 1:
        grouped_filtered = {
            event_key: event_snapshots
            for event_key, event_snapshots in grouped.items()
            if len(event_snapshots) >= policy.min_markets_per_event
        }
        if grouped_filtered:
            grouped = grouped_filtered

    grouped_items = [
        (
            event_key,
            sorted(
                event_snapshots,
                key=lambda snapshot: (
                    -snapshot.liquidity_score,
                    snapshot.slug,
                    snapshot.market_id,
                ),
            ),
        )
        for event_key, event_snapshots in grouped.items()
    ]
    grouped_items.sort(
        key=lambda item: (
            -len(item[1]),
            -max(snapshot.liquidity_score for snapshot in item[1]),
            item[0],
        )
    )

    if policy.max_active_markets is None and policy.max_markets_per_event is None:
        return [snapshot for _, event_snapshots in grouped_items for snapshot in event_snapshots]

    market_limit = policy.max_active_markets if policy.max_active_markets is not None else len(candidates)
    per_event_limit = policy.max_markets_per_event if policy.max_markets_per_event is not None else market_limit
    selected: list[MarketSnapshot] = []
    selected_by_event: dict[str, int] = defaultdict(int)
    indices = {event_key: 0 for event_key, _ in grouped_items}

    while len(selected) < market_limit:
        advanced = False
        for event_key, event_snapshots in grouped_items:
            if len(selected) >= market_limit:
                break
            if selected_by_event[event_key] >= per_event_limit:
                continue
            current_index = indices[event_key]
            if current_index >= len(event_snapshots):
                continue
            selected.append(event_snapshots[current_index])
            selected_by_event[event_key] += 1
            indices[event_key] = current_index + 1
            advanced = True
        if not advanced:
            break

    return selected


def _policy_from_config(markets_config: Mapping[str, object]) -> MarketUniversePolicy | None:
    min_liquidity_score = _parse_optional_float(markets_config.get("min_liquidity_score")) or 0.0
    max_active_markets = _parse_optional_int(markets_config.get("max_active_markets"))
    max_markets_per_event = _parse_optional_int(markets_config.get("max_markets_per_event"))
    min_markets_per_event = _parse_optional_int(markets_config.get("min_markets_per_event")) or 1
    asset_keywords = tuple(
        keyword
        for keyword in (
            _normalize_keyword(raw_keyword)
            for raw_keyword in _parse_string_list(markets_config.get("assets"))
        )
        if keyword
    )
    if (
        min_liquidity_score <= 0
        and max_active_markets is None
        and max_markets_per_event is None
        and min_markets_per_event <= 1
        and not asset_keywords
    ):
        return None
    return MarketUniversePolicy(
        min_liquidity_score=min_liquidity_score,
        asset_keywords=asset_keywords,
        max_active_markets=max_active_markets,
        max_markets_per_event=max_markets_per_event,
        min_markets_per_event=max(1, min_markets_per_event),
    )


def _group_snapshots(snapshots: Sequence[MarketSnapshot]) -> dict[str, list[MarketSnapshot]]:
    grouped: dict[str, list[MarketSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        event_key = (
            snapshot.metadata.get("event_slug")
            or snapshot.metadata.get("event_id")
            or snapshot.market_id
        )
        grouped[event_key].append(snapshot)
    return grouped


def _snapshot_matches_assets(
    *,
    snapshot: MarketSnapshot,
    asset_keywords: tuple[str, ...],
) -> bool:
    tokens = _snapshot_tokens(snapshot)
    return any(_keyword_aliases(keyword) & tokens for keyword in asset_keywords)


def _snapshot_tokens(snapshot: MarketSnapshot) -> set[str]:
    raw_parts = (
        snapshot.slug,
        snapshot.metadata.get("question", ""),
        snapshot.metadata.get("event_slug", ""),
        snapshot.metadata.get("event_title", ""),
        snapshot.metadata.get("group_item_title", ""),
    )
    tokens: set[str] = set()
    for raw_part in raw_parts:
        normalized = str(raw_part).lower()
        tokens.update(token for token in re.split(r"[^a-z0-9]+", normalized) if token)
    return tokens


def _parse_string_list(raw_value: object) -> tuple[str, ...]:
    if isinstance(raw_value, str):
        value = raw_value.strip()
        return (value,) if value else ()
    if isinstance(raw_value, Sequence):
        return tuple(str(item).strip() for item in raw_value if str(item).strip())
    return ()


def _normalize_keyword(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _keyword_aliases(keyword: str) -> set[str]:
    aliases = {keyword}
    if keyword == "btc":
        aliases.add("bitcoin")
    elif keyword == "eth":
        aliases.add("ethereum")
    elif keyword == "sol":
        aliases.add("solana")
    return aliases


def _parse_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _parse_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
