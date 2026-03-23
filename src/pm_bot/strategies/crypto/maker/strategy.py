"""Crypto maker-style quote strategy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.runtime.state import PositionState
from pm_bot.strategies.common import (
    current_position,
    dashboard_state,
    has_pending_order,
    implied_yes_probability,
    parse_probability,
)

_INSIDE_TICK = 0.01


class CryptoMakerConfig:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.min_spread_bps = float(config.get("min_spread_bps", 100))
        self.inventory_skew_strength = float(config.get("inventory_skew_strength", 0.5))
        self.quote_ttl_seconds = int(config.get("quote_ttl_seconds", 10))


class CryptoMakerStrategy:
    strategy_id = "crypto.maker"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = CryptoMakerConfig(config)

    async def evaluate(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object],
    ) -> Sequence[StrategySignal]:
        if snapshot.category != Category.CRYPTO:
            return []

        dashboard = dashboard_state(context)
        if has_pending_order(snapshot=snapshot, dashboard=dashboard):
            return []

        fair_probability = parse_probability(
            snapshot.metadata,
            "reference_yes_probability",
            "external_yes_probability",
            "fair_yes_probability",
            "consensus_yes_probability",
        ) or implied_yes_probability(snapshot)
        if fair_probability is None:
            return []

        position = current_position(snapshot=snapshot, dashboard=dashboard)
        if position is not None:
            exit_signal = self._exit_signal(
                snapshot=snapshot,
                fair_probability=fair_probability,
                position=position,
            )
            return [exit_signal] if exit_signal is not None else []

        yes_spread_bps = _spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
        no_spread_bps = _spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
        if max(yes_spread_bps, no_spread_bps) < self.config.min_spread_bps:
            return []

        yes_candidate = self._entry_candidate(
            snapshot=snapshot,
            fair_probability=fair_probability,
            side=SignalSide.BUY_YES,
            best_bid=snapshot.best_bid_yes,
            best_ask=snapshot.best_ask_yes,
        )
        no_candidate = self._entry_candidate(
            snapshot=snapshot,
            fair_probability=1 - fair_probability,
            side=SignalSide.BUY_NO,
            best_bid=snapshot.best_bid_no,
            best_ask=snapshot.best_ask_no,
        )
        candidates = [candidate for candidate in (yes_candidate, no_candidate) if candidate is not None]
        if not candidates:
            return []

        best_signal = max(
            candidates,
            key=lambda signal: (
                signal.edge_bps,
                signal.side == SignalSide.BUY_YES,
            ),
        )
        return [best_signal]

    def _entry_candidate(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        side: SignalSide,
        best_bid: float | None,
        best_ask: float | None,
    ) -> StrategySignal | None:
        if best_ask is None:
            return None

        quote_price = _maker_buy_price(
            best_bid=best_bid,
            best_ask=best_ask,
            fair_probability=fair_probability,
            min_spread_bps=self.config.min_spread_bps,
        )
        edge_bps = (fair_probability - quote_price) * 10000
        if edge_bps < self.config.min_spread_bps:
            return None

        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.CRYPTO,
            market_id=snapshot.market_id,
            token_id=snapshot.token_id,
            fair_probability=fair_probability if side == SignalSide.BUY_YES else 1 - fair_probability,
            side=side,
            confidence=0.62,
            edge_bps=edge_bps,
            generated_at=datetime.now(tz=timezone.utc),
            target_price=quote_price,
            rationale_tags=("crypto_maker", "inside_spread"),
        )

    def _exit_signal(
        self,
        *,
        snapshot: MarketSnapshot,
        fair_probability: float,
        position: PositionState,
    ) -> StrategySignal | None:
        no_token_id = snapshot.metadata.get("no_token_id")
        yes_spread_bps = _spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
        no_spread_bps = _spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
        spread_floor = self.config.min_spread_bps / 2

        if position.token_id == snapshot.token_id:
            if snapshot.best_bid_yes is None:
                return None
            exit_price = snapshot.best_bid_yes
            fair_exit_price = fair_probability
            side = SignalSide.SELL_YES
            spread_collapsed = yes_spread_bps <= (spread_floor + 1e-6)
        elif no_token_id and position.token_id == no_token_id:
            if snapshot.best_bid_no is None:
                return None
            exit_price = snapshot.best_bid_no
            fair_exit_price = 1 - fair_probability
            side = SignalSide.SELL_NO
            spread_collapsed = no_spread_bps <= (spread_floor + 1e-6)
        else:
            return None

        edge_remaining_bps = (fair_exit_price - exit_price) * 10000
        if edge_remaining_bps > 0 and not spread_collapsed:
            return None

        shares = position.shares or 0.0
        target_notional = shares * exit_price
        if target_notional <= 0:
            return None

        rationale = "spread_collapsed" if spread_collapsed else "fair_value_reached"
        return StrategySignal(
            strategy_id=self.strategy_id,
            category=Category.CRYPTO,
            market_id=snapshot.market_id,
            token_id=position.token_id,
            fair_probability=fair_probability,
            side=side,
            confidence=0.6,
            edge_bps=max(0.0, edge_remaining_bps),
            generated_at=datetime.now(tz=timezone.utc),
            target_price=exit_price,
            target_size=target_notional,
            rationale_tags=("crypto_maker_exit", rationale),
        )


def _maker_buy_price(
    *,
    best_bid: float | None,
    best_ask: float | None,
    fair_probability: float,
    min_spread_bps: float,
) -> float:
    if best_ask is None:
        raise ValueError("best_ask is required for maker quotes")
    if best_bid is None:
        return min(best_ask, max(0.01, fair_probability - (min_spread_bps / 10000)))

    capture_buffer = min_spread_bps / 10000
    target_price = max(best_bid + _INSIDE_TICK, fair_probability - capture_buffer)
    return min(best_ask, max(0.01, target_price))


def _spread_bps(best_bid: float | None, best_ask: float | None) -> float:
    if best_bid is None or best_ask is None:
        return 0.0
    return max(0.0, (best_ask - best_bid) * 10000)
