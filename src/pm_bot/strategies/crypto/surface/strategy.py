"""Crypto series-consistency strategy.

V1 focuses on crypto event ladders that share one event and multiple ordered
milestones. The strategy looks for monotonicity breaks across those milestones,
opens when the curve is obviously wrong, and exits when the edge normalizes or
the position moves too far against us.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import re
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import DashboardState, PendingOrderState, PositionState


class CryptoSurfaceConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_edge_bps = float(config.get("min_edge_bps", 250))
        self.max_curve_mispricing_bps = float(config.get("max_curve_mispricing_bps", 1500))
        self.min_peer_count = int(config.get("min_peer_count", 3))
        self.exit_edge_bps = float(config.get("exit_edge_bps", 75))
        self.stop_loss_bps = float(config.get("stop_loss_bps", 250))


class CryptoSurfaceStrategy:
    strategy_id = "crypto.surface"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = CryptoSurfaceConfig(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.CRYPTO:
            return []

        dashboard = _dashboard_state(context)
        if dashboard is not None and self._has_pending_order(snapshot=snapshot, dashboard=dashboard):
            return []

        series_key = snapshot.metadata.get("event_slug")
        if not series_key:
            return []

        peers = self._series_peers(snapshot=snapshot, context=context)
        if len(peers) < self.config.min_peer_count:
            return []

        ranked_peers = self._ranked_peers(peers)
        current_index = next(
            (index for index, peer in enumerate(ranked_peers) if peer.market_id == snapshot.market_id),
            None,
        )
        if current_index is None:
            return []

        direction = self._monotonic_direction(snapshot)
        if direction is None:
            return []

        current_probability = implied_yes_probability(snapshot)
        if current_probability is None:
            return []

        lower_bound, upper_bound = monotonic_bounds(
            ranked_peers=ranked_peers,
            current_index=current_index,
            direction=direction,
        )
        if lower_bound is None and upper_bound is None:
            return []

        fair_probability = project_fair_probability(
            current_probability=current_probability,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        if fair_probability is None:
            return []

        current_position = self._current_position(snapshot=snapshot, dashboard=dashboard)
        if current_position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=current_position,
            )
            return [exit_signal] if exit_signal is not None else []

        return self._entry_signals(snapshot=snapshot, fair_probability=fair_probability, lower_bound=lower_bound, upper_bound=upper_bound)

    def _series_peers(
        self,
        *,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> list[MarketSnapshot]:
        raw_snapshots = context.get("snapshot_cache")
        if not isinstance(raw_snapshots, tuple):
            return [snapshot]

        series_key = snapshot.metadata.get("event_slug")
        return [
            peer
            for peer in raw_snapshots
            if isinstance(peer, MarketSnapshot)
            and peer.category == Category.CRYPTO
            and peer.metadata.get("event_slug") == series_key
        ]

    def _ranked_peers(self, peers: Sequence[MarketSnapshot]) -> list[MarketSnapshot]:
        def rank(peer: MarketSnapshot) -> tuple[float, str]:
            threshold = peer.metadata.get("group_item_threshold", "")
            parsed_threshold = parse_numeric_threshold(threshold)
            if parsed_threshold is not None:
                return (parsed_threshold, peer.market_id)
            date_rank = parse_deadline_rank(peer)
            if date_rank is not None:
                return (date_rank, peer.market_id)
            return (10_000_000.0, peer.market_id)

        return sorted(peers, key=rank)

    def _monotonic_direction(self, snapshot: MarketSnapshot) -> int | None:
        question = snapshot.metadata.get("question", "").lower()
        slug = snapshot.slug.lower()
        event_title = snapshot.metadata.get("event_title", "").lower()
        combined = " ".join((question, slug, event_title))

        if " by " in f" {question} " or " before " in f" {question} ":
            return 1
        if any(token in combined for token in ("above", "over", "greater-than")):
            return -1
        if any(token in combined for token in ("below", "under", "less-than")):
            return 1
        return None

    def _entry_signals(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        lower_bound: float | None,
        upper_bound: float | None,
    ) -> list[StrategySignal]:
        if snapshot.best_ask_yes is not None:
            buy_yes_edge_bps = (fair_probability - snapshot.best_ask_yes) * 10000
            if self.config.min_edge_bps <= buy_yes_edge_bps <= self.config.max_curve_mispricing_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.CRYPTO,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_YES,
                        confidence=signal_confidence(lower_bound=lower_bound, upper_bound=upper_bound),
                        edge_bps=buy_yes_edge_bps,
                        generated_at=datetime.now(tz=timezone.utc),
                        rationale_tags=("crypto_series_monotonicity", "buy_yes"),
                    )
                ]

        if snapshot.best_bid_yes is not None:
            buy_no_edge_bps = (snapshot.best_bid_yes - fair_probability) * 10000
            if self.config.min_edge_bps <= buy_no_edge_bps <= self.config.max_curve_mispricing_bps:
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        category=Category.CRYPTO,
                        market_id=snapshot.market_id,
                        token_id=snapshot.token_id,
                        fair_probability=fair_probability,
                        side=SignalSide.BUY_NO,
                        confidence=signal_confidence(lower_bound=lower_bound, upper_bound=upper_bound),
                        edge_bps=buy_no_edge_bps,
                        generated_at=datetime.now(tz=timezone.utc),
                        rationale_tags=("crypto_series_monotonicity", "buy_no"),
                    )
                ]

        return []

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        position: PositionState,
    ) -> StrategySignal | None:
        no_token_id = snapshot.metadata.get("no_token_id")
        if position.token_id == snapshot.token_id:
            if snapshot.best_bid_yes is None:
                return None
            exit_price = snapshot.best_bid_yes
            fair_exit_price = fair_probability
            side = SignalSide.SELL_YES
        elif no_token_id and position.token_id == no_token_id:
            if snapshot.best_bid_no is None:
                return None
            exit_price = snapshot.best_bid_no
            fair_exit_price = 1.0 - fair_probability
            side = SignalSide.SELL_NO
        else:
            return None

        exit_gap_bps = (fair_exit_price - exit_price) * 10000
        stop_loss_triggered = False
        if position.average_entry_price is not None:
            stop_loss_price = position.average_entry_price * (1 - (self.config.stop_loss_bps / 10000))
            stop_loss_triggered = exit_price <= stop_loss_price

        if exit_gap_bps <= self.config.exit_edge_bps or stop_loss_triggered:
            target_notional = (position.shares or 0.0) * exit_price
            if target_notional <= 0:
                return None
            rationale = "stop_loss" if stop_loss_triggered else "curve_normalized"
            return StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=position.token_id,
                fair_probability=fair_probability,
                side=side,
                confidence=0.7 if stop_loss_triggered else 0.65,
                edge_bps=max(0.0, exit_gap_bps),
                generated_at=datetime.now(tz=timezone.utc),
                target_price=exit_price,
                target_size=target_notional,
                rationale_tags=("crypto_series_exit", rationale),
            )
        return None

    def _current_position(
        self,
        *,
        snapshot: MarketSnapshot,
        dashboard: DashboardState | None,
    ) -> PositionState | None:
        if dashboard is None:
            return None
        return next(
            (
                position
                for position in dashboard.open_positions
                if position.market_id == snapshot.market_id
            ),
            None,
        )

    def _has_pending_order(
        self,
        *,
        snapshot: MarketSnapshot,
        dashboard: DashboardState,
    ) -> bool:
        return any(order.market_id == snapshot.market_id for order in dashboard.pending_orders)


def implied_yes_probability(snapshot: MarketSnapshot) -> float | None:
    if snapshot.best_bid_yes is not None and snapshot.best_ask_yes is not None:
        return (snapshot.best_bid_yes + snapshot.best_ask_yes) / 2
    if snapshot.last_traded_price is not None:
        return snapshot.last_traded_price
    if snapshot.best_ask_yes is not None:
        return snapshot.best_ask_yes
    if snapshot.best_bid_yes is not None:
        return snapshot.best_bid_yes
    return None


def monotonic_bounds(
    *,
    ranked_peers: Sequence[MarketSnapshot],
    current_index: int,
    direction: int,
) -> tuple[float | None, float | None]:
    probabilities = [implied_yes_probability(peer) for peer in ranked_peers]
    current_probability = probabilities[current_index]
    if current_probability is None:
        return (None, None)

    previous = [prob for prob in probabilities[:current_index] if prob is not None]
    following = [prob for prob in probabilities[current_index + 1 :] if prob is not None]

    if direction > 0:
        lower_bound = previous[-1] if previous else None
        upper_bound = following[0] if following else None
    else:
        lower_bound = following[0] if following else None
        upper_bound = previous[-1] if previous else None

    return (lower_bound, upper_bound)


def project_fair_probability(
    *,
    current_probability: float,
    lower_bound: float | None,
    upper_bound: float | None,
) -> float | None:
    if lower_bound is not None and upper_bound is not None and lower_bound > upper_bound:
        return None
    if lower_bound is not None and current_probability < lower_bound:
        return lower_bound
    if upper_bound is not None and current_probability > upper_bound:
        return upper_bound
    return None


def signal_confidence(*, lower_bound: float | None, upper_bound: float | None) -> float:
    if lower_bound is not None and upper_bound is not None:
        return 0.75
    return 0.6


def parse_numeric_threshold(raw_value: str) -> float | None:
    if not raw_value:
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def parse_deadline_rank(snapshot: MarketSnapshot) -> float | None:
    question = snapshot.metadata.get("question", "")
    slug = snapshot.slug
    combined = f"{question} {slug}".lower()
    month_pattern = (
        r"(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"\s+(\d{1,2})(?:,\s*(\d{4}))?"
    )
    match = re.search(month_pattern, combined)
    if match is None:
        return None

    month_name, day_raw, year_raw = match.groups()
    month_lookup = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    year = int(year_raw) if year_raw is not None else 2100
    day = int(day_raw)
    month = month_lookup[month_name]
    return float(year * 10_000 + month * 100 + day)


def _dashboard_state(context: Mapping[str, object]) -> DashboardState | None:
    dashboard = context.get("dashboard_state")
    if isinstance(dashboard, DashboardState):
        return dashboard
    return None
