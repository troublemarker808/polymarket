from datetime import datetime, timezone

from pm_bot.core.types import Category, SignalSide, StrategySignal
from pm_bot.risk.guards import basic_signal_guard


def test_basic_signal_guard_rejects_weak_edge() -> None:
    signal = StrategySignal(
        strategy_id="weather.ensemble",
        category=Category.WEATHER,
        market_id="m1",
        token_id="t1",
        fair_probability=0.54,
        side=SignalSide.BUY_YES,
        confidence=0.5,
        edge_bps=150,
        generated_at=datetime.now(tz=timezone.utc),
    )

    decision = basic_signal_guard(signal=signal, max_edge_floor_bps=200)

    assert not decision.approved


def test_basic_signal_guard_allows_exit_signals_below_floor() -> None:
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="t1",
        fair_probability=0.54,
        side=SignalSide.SELL_YES,
        confidence=0.5,
        edge_bps=10,
        generated_at=datetime.now(tz=timezone.utc),
    )

    decision = basic_signal_guard(signal=signal, max_edge_floor_bps=200)

    assert decision.approved
