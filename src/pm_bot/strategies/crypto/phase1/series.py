"""Series grouping for supported crypto ladder markets."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from pm_bot.core.types import MarketSnapshot
from pm_bot.strategies.crypto.phase1.models import CryptoLadderSeries, CryptoMarketDefinition
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market


def build_crypto_ladder_series(snapshots: Sequence[MarketSnapshot]) -> tuple[CryptoLadderSeries, ...]:
    grouped: dict[str, list[CryptoMarketDefinition]] = defaultdict(list)
    for snapshot in snapshots:
        normalized = normalize_crypto_market(snapshot)
        if normalized is None:
            continue
        grouped[normalized.normalized.scope_key].append(normalized)

    series: list[CryptoLadderSeries] = []
    for scope_key, markets in sorted(grouped.items()):
        ordered_markets = tuple(sorted(markets, key=_market_sort_key))
        if not ordered_markets:
            continue
        first = ordered_markets[0]
        series.append(
            CryptoLadderSeries(
                series_key=scope_key,
                underlying=first.underlying,
                event_family=first.event_family,
                direction=first.direction,
                markets=ordered_markets,
            )
        )
    return tuple(series)


def _market_sort_key(market: CryptoMarketDefinition) -> float:
    if market.direction == "down":
        return -market.barrier_price
    return market.barrier_price
