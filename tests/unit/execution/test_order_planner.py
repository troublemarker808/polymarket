from datetime import datetime, timezone

from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.execution.order_planner import signal_to_order_intent


def test_signal_to_order_intent_maps_fields() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.58,
    )
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="t1",
        fair_probability=0.61,
        side=SignalSide.BUY_YES,
        confidence=0.7,
        edge_bps=320,
        generated_at=datetime.now(tz=timezone.utc),
    )

    intent = signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=25.0)

    assert intent is not None
    assert intent.strategy_id == "crypto.surface"
    assert intent.category == Category.CRYPTO
    assert intent.market_id == "m1"
    assert intent.price == 0.58
    assert intent.notional == 25.0
    assert intent.size == round(25.0 / 0.58, 6)


def test_signal_to_order_intent_returns_none_for_hold() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
    )
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="t1",
        fair_probability=0.5,
        side=SignalSide.HOLD,
        confidence=0.1,
        edge_bps=0,
        generated_at=datetime.now(tz=timezone.utc),
    )

    assert signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=10.0) is None


def test_signal_to_order_intent_maps_buy_no_to_no_token_and_share_size() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
        best_bid_yes=0.63,
        best_ask_no=0.39,
        metadata={"no_token_id": "no-token"},
    )
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        fair_probability=0.55,
        side=SignalSide.BUY_NO,
        confidence=0.8,
        edge_bps=400,
        generated_at=datetime.now(tz=timezone.utc),
    )

    intent = signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=5.0)

    assert intent is not None
    assert intent.token_id == "no-token"
    assert intent.notional == 5.0
    assert intent.size == round(5.0 / 0.39, 6)


def test_signal_to_order_intent_maps_sell_yes_to_bid_price() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
        best_bid_yes=0.62,
        metadata={"no_token_id": "no-token"},
    )
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        fair_probability=0.55,
        side=SignalSide.SELL_YES,
        confidence=0.8,
        edge_bps=400,
        generated_at=datetime.now(tz=timezone.utc),
    )

    intent = signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=5.0)

    assert intent is not None
    assert intent.token_id == "yes-token"
    assert intent.price == 0.62
    assert intent.size == round(5.0 / 0.62, 6)


def test_signal_to_order_intent_maps_sell_no_to_no_token_and_bid_price() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
        best_bid_no=0.41,
        metadata={"no_token_id": "no-token"},
    )
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        fair_probability=0.55,
        side=SignalSide.SELL_NO,
        confidence=0.8,
        edge_bps=400,
        generated_at=datetime.now(tz=timezone.utc),
    )

    intent = signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=5.0)

    assert intent is not None
    assert intent.token_id == "no-token"
    assert intent.price == 0.41
    assert intent.size == round(5.0 / 0.41, 6)
