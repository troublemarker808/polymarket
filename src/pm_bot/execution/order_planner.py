"""Translate approved signals into executable order intents."""

from __future__ import annotations

from pm_bot.core.types import MarketSnapshot, OrderAction, OrderIntent, SignalSide, StrategySignal
from pm_bot.execution.exposure_keys import derive_exposure_keys


def signal_to_order_intent(
    signal: StrategySignal,
    snapshot: MarketSnapshot,
    default_size: float,
) -> OrderIntent | None:
    """Map a strategy signal into a normalized order intent.

    Price and size selection remain outside the strategy package so execution logic
    can change independently of alpha logic.
    """

    if signal.side == SignalSide.HOLD:
        return None

    if signal.target_price is not None:
        price = signal.target_price
    elif signal.side == SignalSide.BUY_YES:
        price = snapshot.best_ask_yes or signal.fair_probability
    elif signal.side == SignalSide.BUY_NO:
        price = snapshot.best_ask_no or (1 - signal.fair_probability)
    elif signal.side == SignalSide.SELL_YES:
        price = snapshot.best_bid_yes or signal.fair_probability
    else:
        price = snapshot.best_bid_no or (1 - signal.fair_probability)

    notional = signal.target_size or default_size
    if price <= 0:
        return None

    size = round(notional / price, 6)
    if size <= 0:
        return None
    if snapshot.min_order_size is not None and size + 1e-9 < snapshot.min_order_size:
        return None

    token_id = signal.token_id
    if signal.side in {SignalSide.BUY_NO, SignalSide.SELL_NO}:
        token_id = snapshot.metadata.get("no_token_id", token_id)
    exposure_keys = derive_exposure_keys(snapshot, side=signal.side)

    return OrderIntent(
        strategy_id=signal.strategy_id,
        category=signal.category,
        market_id=signal.market_id,
        token_id=token_id,
        action=OrderAction.PLACE,
        side=signal.side,
        price=price,
        size=size,
        time_in_force=signal.time_in_force,
        created_at=signal.generated_at,
        notional=notional,
        quote_ttl_seconds=signal.quote_ttl_seconds,
        signal_edge_bps=signal.edge_bps,
        exposure_group_id=exposure_keys.exposure_group_id,
        thesis_group_id=exposure_keys.thesis_group_id,
        underlying_group_id=exposure_keys.underlying_group_id,
        rationale_tags=tuple(signal.rationale_tags),
        signal_type=str(signal.diagnostics.get("signal_type", "")).strip() or None,
        execution_route=str(signal.diagnostics.get("execution_route", "")).strip() or None,
        decision_reason=(signal.rationale_tags[0] if signal.rationale_tags else None),
    )
