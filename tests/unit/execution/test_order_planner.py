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
        quote_ttl_seconds=12,
    )

    intent = signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=25.0)

    assert intent is not None
    assert intent.strategy_id == "crypto.surface"
    assert intent.category == Category.CRYPTO
    assert intent.market_id == "m1"
    assert intent.price == 0.58
    assert intent.notional == 25.0
    assert intent.size == round(25.0 / 0.58, 6)
    assert intent.quote_ttl_seconds == 12
    assert intent.signal_edge_bps == 320
    assert intent.exposure_group_id == "crypto:m1"
    assert intent.thesis_group_id == "crypto:btc:above"
    assert intent.underlying_group_id == "crypto:btc"


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


def test_signal_to_order_intent_prefers_event_slug_for_exposure_group() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.58,
        metadata={"event_slug": "btc-reach-ladder", "series_key": "ignored"},
    )
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        fair_probability=0.61,
        side=SignalSide.BUY_YES,
        confidence=0.7,
        edge_bps=320,
        generated_at=datetime.now(tz=timezone.utc),
    )

    intent = signal_to_order_intent(signal=signal, snapshot=snapshot, default_size=25.0)

    assert intent is not None
    assert intent.exposure_group_id == "crypto:btc-reach-ladder"
    assert intent.thesis_group_id == "crypto:btc:reach"
    assert intent.underlying_group_id == "crypto:btc"


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


def test_signal_to_order_intent_groups_btc_macro_direction_by_traded_side() -> None:
    dip_snapshot = MarketSnapshot(
        market_id="dip-50k",
        token_id="dip-yes",
        slug="will-bitcoin-dip-to-50000-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        best_ask_no=0.65,
        metadata={"question": "Will Bitcoin dip to $50,000 by December 31, 2026?", "no_token_id": "dip-no"},
    )
    reach_snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        best_ask_yes=0.10,
        metadata={"question": "Will Bitcoin hit $150K by December 31, 2026?"},
    )
    dip_no_signal = StrategySignal(
        strategy_id="crypto.phase2",
        category=Category.CRYPTO,
        market_id="dip-50k",
        token_id="dip-yes",
        fair_probability=0.40,
        side=SignalSide.BUY_NO,
        confidence=0.8,
        edge_bps=120,
        generated_at=datetime.now(tz=timezone.utc),
    )
    reach_yes_signal = StrategySignal(
        strategy_id="crypto.phase2",
        category=Category.CRYPTO,
        market_id="reach-150k",
        token_id="reach-yes",
        fair_probability=0.14,
        side=SignalSide.BUY_YES,
        confidence=0.8,
        edge_bps=120,
        generated_at=datetime.now(tz=timezone.utc),
    )

    dip_intent = signal_to_order_intent(signal=dip_no_signal, snapshot=dip_snapshot, default_size=5.0)
    reach_intent = signal_to_order_intent(signal=reach_yes_signal, snapshot=reach_snapshot, default_size=5.0)

    assert dip_intent is not None
    assert reach_intent is not None
    assert dip_intent.thesis_group_id == "crypto:btc:bullish"
    assert reach_intent.thesis_group_id == "crypto:btc:bullish"
