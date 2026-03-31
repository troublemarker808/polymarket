"""Market-universe selection helpers for live and paper sessions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
import re

from pm_bot.core.types import MarketSnapshot


@dataclass(slots=True, frozen=True)
class MarketUniversePolicy:
    min_liquidity_score: float = 0.0
    min_yes_mid_price: float | None = None
    max_yes_mid_price: float | None = None
    max_yes_spread_bps: float | None = None
    max_tradeable_spread_bps: float | None = None
    asset_keywords: tuple[str, ...] = ()
    include_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    expiries: tuple[str, ...] = ()
    event_slugs: tuple[str, ...] = ()
    market_ids: tuple[str, ...] = ()
    preferred_market_ids: tuple[str, ...] = ()
    max_active_markets: int | None = None
    max_markets_per_event: int | None = None
    min_markets_per_event: int = 1


@dataclass(slots=True, frozen=True)
class MarketUniverseDiagnostics:
    total_snapshots: int
    open_snapshots: int
    after_liquidity_score: int
    after_yes_mid_price: int
    after_yes_spread: int
    after_tradeable_spread: int
    after_asset_keywords: int
    after_include_keywords: int
    after_exclude_keywords: int
    after_expiry_bucket: int
    after_event_slug: int
    after_market_ids: int
    grouped_event_count: int
    selected_snapshots: int


class _SnapshotSelector:
    def __init__(self, policy: MarketUniversePolicy) -> None:
        self.policy = policy
        self.last_diagnostics: MarketUniverseDiagnostics | None = None

    def __call__(self, snapshots: Sequence[MarketSnapshot]) -> list[MarketSnapshot]:
        selected, diagnostics = evaluate_market_snapshots(snapshots=snapshots, policy=self.policy)
        self.last_diagnostics = diagnostics
        return selected


def build_snapshot_selector(
    markets_config: Mapping[str, object] | None,
) -> Callable[[Sequence[MarketSnapshot]], list[MarketSnapshot]] | None:
    if not isinstance(markets_config, Mapping):
        return None
    policy = _policy_from_config(markets_config)
    if policy is None:
        return None
    return _SnapshotSelector(policy)


def evaluate_market_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    policy: MarketUniversePolicy,
) -> tuple[list[MarketSnapshot], MarketUniverseDiagnostics]:
    total_snapshots = len(snapshots)
    candidates = [snapshot for snapshot in snapshots if _snapshot_is_open(snapshot)]
    open_snapshots = len(candidates)

    if policy.min_liquidity_score > 0:
        liquidity_filtered = [
            snapshot for snapshot in candidates if snapshot.liquidity_score >= policy.min_liquidity_score
        ]
        if liquidity_filtered:
            candidates = liquidity_filtered
    after_liquidity_score = len(candidates)

    if policy.min_yes_mid_price is not None:
        candidates = [
            snapshot
            for snapshot in candidates
            if (_snapshot_yes_mid_price(snapshot) or 0.0) >= policy.min_yes_mid_price
        ]
    if policy.max_yes_mid_price is not None:
        candidates = [
            snapshot
            for snapshot in candidates
            if (_snapshot_yes_mid_price(snapshot) or 1.0) <= policy.max_yes_mid_price
        ]
    after_yes_mid_price = len(candidates)

    if policy.max_yes_spread_bps is not None:
        candidates = [
            snapshot
            for snapshot in candidates
            if (_snapshot_yes_spread_bps(snapshot) or float("inf")) <= policy.max_yes_spread_bps
        ]
    after_yes_spread = len(candidates)

    if policy.max_tradeable_spread_bps is not None:
        candidates = [
            snapshot
            for snapshot in candidates
            if (_snapshot_tradeable_spread_bps(snapshot) or float("inf")) <= policy.max_tradeable_spread_bps
        ]
    after_tradeable_spread = len(candidates)

    if policy.asset_keywords:
        candidates = [
            snapshot
            for snapshot in candidates
            if _snapshot_matches_assets(snapshot=snapshot, asset_keywords=policy.asset_keywords)
        ]
    after_asset_keywords = len(candidates)

    if policy.include_keywords:
        candidates = [
            snapshot
            for snapshot in candidates
            if _snapshot_matches_required_keywords(
                snapshot=snapshot,
                include_keywords=policy.include_keywords,
            )
        ]
    after_include_keywords = len(candidates)

    if policy.exclude_keywords:
        candidates = [
            snapshot
            for snapshot in candidates
            if not _snapshot_matches_excluded_keywords(
                snapshot=snapshot,
                exclude_keywords=policy.exclude_keywords,
            )
        ]
    after_exclude_keywords = len(candidates)

    if policy.expiries:
        candidates = [
            snapshot
            for snapshot in candidates
            if _snapshot_matches_expiry_buckets(snapshot=snapshot, expiries=policy.expiries)
        ]
    after_expiry_bucket = len(candidates)

    if policy.event_slugs:
        candidates = [
            snapshot
            for snapshot in candidates
            if _snapshot_matches_event_slugs(snapshot=snapshot, event_slugs=policy.event_slugs)
        ]
    after_event_slug = len(candidates)

    if policy.market_ids:
        allowed_market_ids = set(policy.market_ids)
        candidates = [
            snapshot
            for snapshot in candidates
            if snapshot.market_id in allowed_market_ids
        ]
    after_market_ids = len(candidates)

    selected = _select_grouped_candidates(candidates=candidates, policy=policy)
    diagnostics = MarketUniverseDiagnostics(
        total_snapshots=total_snapshots,
        open_snapshots=open_snapshots,
        after_liquidity_score=after_liquidity_score,
        after_yes_mid_price=after_yes_mid_price,
        after_yes_spread=after_yes_spread,
        after_tradeable_spread=after_tradeable_spread,
        after_asset_keywords=after_asset_keywords,
        after_include_keywords=after_include_keywords,
        after_exclude_keywords=after_exclude_keywords,
        after_expiry_bucket=after_expiry_bucket,
        after_event_slug=after_event_slug,
        after_market_ids=after_market_ids,
        grouped_event_count=len(_group_snapshots(candidates)),
        selected_snapshots=len(selected),
    )
    return selected, diagnostics


def select_market_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    policy: MarketUniversePolicy,
) -> list[MarketSnapshot]:
    selected, _ = evaluate_market_snapshots(snapshots=snapshots, policy=policy)
    return selected


def _select_grouped_candidates(
    *,
    candidates: Sequence[MarketSnapshot],
    policy: MarketUniversePolicy,
) -> list[MarketSnapshot]:
    if not candidates:
        return []

    preferred_market_positions = {
        market_id: index
        for index, market_id in enumerate(policy.preferred_market_ids)
    }

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
                    preferred_market_positions.get(snapshot.market_id, len(preferred_market_positions)),
                    _snapshot_spread_rank(snapshot),
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


def _snapshot_is_open(snapshot: MarketSnapshot) -> bool:
    if snapshot.resolution_time is None:
        return True
    return snapshot.resolution_time.astimezone(UTC) > snapshot.timestamp.astimezone(UTC)


def _policy_from_config(markets_config: Mapping[str, object]) -> MarketUniversePolicy | None:
    min_liquidity_score = _parse_optional_float(markets_config.get("min_liquidity_score")) or 0.0
    min_yes_mid_price = _parse_optional_float(markets_config.get("min_yes_mid_price"))
    max_yes_mid_price = _parse_optional_float(markets_config.get("max_yes_mid_price"))
    max_yes_spread_bps = _parse_optional_float(markets_config.get("max_yes_spread_bps"))
    max_tradeable_spread_bps = _parse_optional_float(markets_config.get("max_tradeable_spread_bps"))
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
    include_keywords = tuple(
        keyword
        for keyword in (
            _normalize_keyword(raw_keyword)
            for raw_keyword in _parse_string_list(markets_config.get("include_keywords"))
        )
        if keyword
    )
    exclude_keywords = tuple(
        keyword
        for keyword in (
            _normalize_keyword(raw_keyword)
            for raw_keyword in _parse_string_list(markets_config.get("exclude_keywords"))
        )
        if keyword
    )
    expiries = tuple(
        str(raw_expiry).strip().lower()
        for raw_expiry in _parse_string_list(markets_config.get("expiries"))
        if str(raw_expiry).strip()
    )
    event_slugs = tuple(
        str(raw_slug).strip()
        for raw_slug in _parse_string_list(markets_config.get("event_slugs"))
        if str(raw_slug).strip()
    )
    market_ids = tuple(
        str(raw_market_id).strip()
        for raw_market_id in _parse_string_list(markets_config.get("market_ids"))
        if str(raw_market_id).strip()
    )
    preferred_market_ids = tuple(
        str(raw_market_id).strip()
        for raw_market_id in _parse_string_list(markets_config.get("preferred_market_ids"))
        if str(raw_market_id).strip()
    )
    if (
        min_liquidity_score <= 0
        and min_yes_mid_price is None
        and max_yes_mid_price is None
        and max_yes_spread_bps is None
        and max_tradeable_spread_bps is None
        and max_active_markets is None
        and max_markets_per_event is None
        and min_markets_per_event <= 1
        and not asset_keywords
        and not include_keywords
        and not exclude_keywords
        and not expiries
        and not event_slugs
        and not market_ids
        and not preferred_market_ids
    ):
        return None
    return MarketUniversePolicy(
        min_liquidity_score=min_liquidity_score,
        min_yes_mid_price=min_yes_mid_price,
        max_yes_mid_price=max_yes_mid_price,
        max_yes_spread_bps=max_yes_spread_bps,
        max_tradeable_spread_bps=max_tradeable_spread_bps,
        asset_keywords=asset_keywords,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
        expiries=expiries,
        event_slugs=event_slugs,
        market_ids=market_ids,
        preferred_market_ids=preferred_market_ids,
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


def _snapshot_yes_mid_price(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_yes is not None and snapshot.best_ask_yes is not None:
        return (snapshot.best_bid_yes + snapshot.best_ask_yes) / 2.0
    if snapshot.last_traded_price is not None:
        return snapshot.last_traded_price
    return None


def _snapshot_yes_spread_bps(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_yes is None or snapshot.best_ask_yes is None:
        return None
    return max(0.0, (snapshot.best_ask_yes - snapshot.best_bid_yes) * 10000.0)


def _snapshot_no_spread_bps(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_no is None or snapshot.best_ask_no is None:
        return None
    return max(0.0, (snapshot.best_ask_no - snapshot.best_bid_no) * 10000.0)


def _snapshot_tradeable_spread_bps(snapshot: MarketSnapshot) -> float | None:
    spreads = [
        spread
        for spread in (_snapshot_yes_spread_bps(snapshot), _snapshot_no_spread_bps(snapshot))
        if spread is not None
    ]
    if not spreads:
        return None
    return min(spreads)


def _snapshot_matches_assets(
    *,
    snapshot: MarketSnapshot,
    asset_keywords: tuple[str, ...],
) -> bool:
    tokens = _snapshot_tokens(snapshot)
    return any(_keyword_aliases(keyword) & tokens for keyword in asset_keywords)


def _snapshot_matches_excluded_keywords(
    *,
    snapshot: MarketSnapshot,
    exclude_keywords: tuple[str, ...],
) -> bool:
    tokens = _snapshot_tokens(snapshot)
    return any(_keyword_aliases(keyword) & tokens for keyword in exclude_keywords)


def _snapshot_matches_required_keywords(
    *,
    snapshot: MarketSnapshot,
    include_keywords: tuple[str, ...],
) -> bool:
    tokens = _snapshot_tokens(snapshot)
    return any(_keyword_aliases(keyword) & tokens for keyword in include_keywords)


def _snapshot_matches_event_slugs(
    *,
    snapshot: MarketSnapshot,
    event_slugs: tuple[str, ...],
) -> bool:
    event_slug = str(snapshot.metadata.get("event_slug", "")).strip()
    if not event_slug:
        return False
    return event_slug in event_slugs


def _snapshot_matches_expiry_buckets(
    *,
    snapshot: MarketSnapshot,
    expiries: tuple[str, ...],
) -> bool:
    if snapshot.resolution_time is None:
        return False
    time_to_expiry_days = max(
        (snapshot.resolution_time.astimezone(UTC) - snapshot.timestamp.astimezone(UTC)).total_seconds() / 86400.0,
        0.0,
    )
    return any(_matches_expiry_bucket(time_to_expiry_days=time_to_expiry_days, bucket=bucket) for bucket in expiries)


def _matches_expiry_bucket(*, time_to_expiry_days: float, bucket: str) -> bool:
    normalized = bucket.strip().lower()
    if normalized in {"intraday", "same_day", "today"}:
        return time_to_expiry_days <= 1
    if normalized in {"next_3d", "near", "near_term"}:
        return time_to_expiry_days <= 3
    if normalized in {"next_7d", "week"}:
        return time_to_expiry_days <= 7
    if normalized in {"short", "short_term"}:
        return time_to_expiry_days <= 30
    if normalized in {"medium", "mid", "mid_term"}:
        return 30 < time_to_expiry_days <= 180
    if normalized in {"long", "long_term"}:
        return time_to_expiry_days > 180
    duration_days = _parse_duration_bucket_to_days(normalized)
    if duration_days is None:
        return False
    tolerance_days = max(duration_days * 0.35, 3.0)
    return abs(time_to_expiry_days - duration_days) <= tolerance_days


def _parse_duration_bucket_to_days(value: str) -> float | None:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([dwmy])", value)
    if match is None:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "d":
        return amount
    if unit == "w":
        return amount * 7.0
    if unit == "m":
        return amount * 30.0
    if unit == "y":
        return amount * 365.0
    return None


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


def _snapshot_spread_rank(snapshot: MarketSnapshot) -> float:
    yes_spread = (
        max(0.0, snapshot.best_ask_yes - snapshot.best_bid_yes)
        if snapshot.best_bid_yes is not None and snapshot.best_ask_yes is not None
        else None
    )
    no_spread = (
        max(0.0, snapshot.best_ask_no - snapshot.best_bid_no)
        if snapshot.best_bid_no is not None and snapshot.best_ask_no is not None
        else None
    )
    spreads = [spread for spread in (yes_spread, no_spread) if spread is not None]
    if not spreads:
        return float("inf")
    return min(spreads)


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
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value.strip())
    raise TypeError(f"expected int-like value, got {type(value).__name__}")


def _parse_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise TypeError(f"expected float-like value, got {type(value).__name__}")
