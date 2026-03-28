import asyncio
from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PositionState, RuntimeStatus
from pm_bot.strategies.crypto.maker.strategy import CryptoMakerStrategy


def _snapshot(
    *,
    market_id: str = "crypto-maker-1",
    token_id: str = "crypto-maker-1-yes",
    best_bid_yes: float,
    best_ask_yes: float,
    timestamp: datetime | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        token_id=token_id,
        slug=market_id,
        category=Category.CRYPTO,
        timestamp=timestamp or datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=1 - best_ask_yes,
        best_ask_no=1 - best_bid_yes,
        last_traded_price=(best_bid_yes + best_ask_yes) / 2,
        metadata={
            "reference_yes_probability": "0.56",
            "no_token_id": "crypto-maker-1-no",
        },
    )


def _dashboard(position: PositionState | None = None) -> DashboardState:
    return DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=() if position is None else (position,),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )


def _context(
    *,
    position: PositionState | None = None,
    recent_events: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    return {
        "dashboard_state": _dashboard(position),
        "recent_events": recent_events,
    }


def test_crypto_maker_quotes_inside_spread() -> None:
    snapshot = _snapshot(best_bid_yes=0.5, best_ask_yes=0.6)
    strategy = CryptoMakerStrategy({"min_spread_bps": 100})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context=_context()))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_YES
    assert round(signals[0].target_price or 0.0, 2) == 0.55
    assert round(signals[0].edge_bps, 2) == 100.0
    assert signals[0].generated_at == snapshot.timestamp
    assert signals[0].quote_ttl_seconds == 10


def test_crypto_maker_exits_when_spread_collapses() -> None:
    snapshot = _snapshot(best_bid_yes=0.55, best_ask_yes=0.555)
    position = PositionState(
        market_id="crypto-maker-1",
        token_id="crypto-maker-1-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.maker",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.5,
        opened_at=datetime(2026, 3, 23, 11, 0, tzinfo=UTC),
    )
    strategy = CryptoMakerStrategy({"min_spread_bps": 100})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context=_context(position=position)))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.SELL_YES
    assert round(signals[0].target_size or 0.0, 2) == 5.5
    assert signals[0].generated_at == snapshot.timestamp


def test_crypto_maker_suppresses_repeat_entry_within_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 30,
            "min_requote_edge_improvement_bps": 50,
        }
    )
    first_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
    )
    second_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, 5, tzinfo=UTC),
    )

    first_signals = asyncio.run(
        strategy.evaluate(snapshot=first_snapshot, context=_context())
    )
    second_signals = asyncio.run(
        strategy.evaluate(snapshot=second_snapshot, context=_context())
    )

    assert len(first_signals) == 1
    assert second_signals == []


def test_crypto_maker_allows_repeat_entry_after_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 30,
            "min_requote_edge_improvement_bps": 50,
        }
    )
    first_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
    )
    second_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, 31, tzinfo=UTC),
    )

    asyncio.run(strategy.evaluate(snapshot=first_snapshot, context=_context()))
    second_signals = asyncio.run(
        strategy.evaluate(snapshot=second_snapshot, context=_context())
    )

    assert len(second_signals) == 1
    assert second_signals[0].generated_at == second_snapshot.timestamp


def test_crypto_maker_allows_materially_better_requote_within_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 30,
            "min_requote_edge_improvement_bps": 150,
        }
    )
    first_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
    )
    improved_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.53,
        timestamp=datetime(2026, 3, 23, 12, 0, 5, tzinfo=UTC),
    )

    first_signals = asyncio.run(
        strategy.evaluate(snapshot=first_snapshot, context=_context())
    )
    improved_signals = asyncio.run(
        strategy.evaluate(snapshot=improved_snapshot, context=_context())
    )

    assert len(first_signals) == 1
    assert len(improved_signals) == 1
    assert improved_signals[0].edge_bps > first_signals[0].edge_bps


def test_crypto_maker_suppresses_cross_market_entry_within_global_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "global_cooldown_seconds": 30,
            "market_cooldown_seconds": 0,
        }
    )
    first_snapshot = _snapshot(
        market_id="crypto-maker-1",
        token_id="crypto-maker-1-yes",
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
    )
    second_snapshot = _snapshot(
        market_id="crypto-maker-2",
        token_id="crypto-maker-2-yes",
        best_bid_yes=0.45,
        best_ask_yes=0.55,
        timestamp=datetime(2026, 3, 23, 12, 0, 10, tzinfo=UTC),
    )

    first_signals = asyncio.run(
        strategy.evaluate(snapshot=first_snapshot, context=_context())
    )
    second_signals = asyncio.run(
        strategy.evaluate(snapshot=second_snapshot, context=_context())
    )

    assert len(first_signals) == 1
    assert second_signals == []


def test_crypto_maker_allows_cross_market_entry_after_global_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "global_cooldown_seconds": 30,
            "market_cooldown_seconds": 0,
        }
    )
    first_snapshot = _snapshot(
        market_id="crypto-maker-1",
        token_id="crypto-maker-1-yes",
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
    )
    second_snapshot = _snapshot(
        market_id="crypto-maker-2",
        token_id="crypto-maker-2-yes",
        best_bid_yes=0.45,
        best_ask_yes=0.55,
        timestamp=datetime(2026, 3, 23, 12, 0, 31, tzinfo=UTC),
    )

    asyncio.run(strategy.evaluate(snapshot=first_snapshot, context=_context()))
    second_signals = asyncio.run(
        strategy.evaluate(snapshot=second_snapshot, context=_context())
    )

    assert len(second_signals) == 1


def test_crypto_maker_allows_same_market_improvement_despite_global_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "global_cooldown_seconds": 30,
            "market_cooldown_seconds": 30,
            "min_requote_edge_improvement_bps": 150,
        }
    )
    first_snapshot = _snapshot(
        market_id="crypto-maker-1",
        token_id="crypto-maker-1-yes",
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
    )
    improved_snapshot = _snapshot(
        market_id="crypto-maker-1",
        token_id="crypto-maker-1-yes",
        best_bid_yes=0.5,
        best_ask_yes=0.53,
        timestamp=datetime(2026, 3, 23, 12, 0, 5, tzinfo=UTC),
    )

    first_signals = asyncio.run(
        strategy.evaluate(snapshot=first_snapshot, context=_context())
    )
    improved_signals = asyncio.run(
        strategy.evaluate(snapshot=improved_snapshot, context=_context())
    )

    assert len(first_signals) == 1
    assert len(improved_signals) == 1


def test_crypto_maker_suppresses_recently_expired_market_within_failure_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 0,
            "failure_cooldown_seconds": 30,
            "failure_reentry_edge_improvement_bps": 75,
        }
    )
    snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, 10, tzinfo=UTC),
    )
    recent_expiry = {
        "event_type": "order.expired",
        "payload": {
            "market_id": "crypto-maker-1",
            "strategy_id": "crypto.maker",
            "signal_edge_bps": 100.0,
            "updated_at": "2026-03-23T12:00:00+00:00",
        },
    }

    signals = asyncio.run(
        strategy.evaluate(snapshot=snapshot, context=_context(recent_events=(recent_expiry,)))
    )

    assert signals == []


def test_crypto_maker_allows_market_after_failure_cooldown_expires() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 0,
            "failure_cooldown_seconds": 30,
            "failure_reentry_edge_improvement_bps": 75,
        }
    )
    snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, 31, tzinfo=UTC),
    )
    recent_expiry = {
        "event_type": "order.expired",
        "payload": {
            "market_id": "crypto-maker-1",
            "strategy_id": "crypto.maker",
            "signal_edge_bps": 100.0,
            "updated_at": "2026-03-23T12:00:00+00:00",
        },
    }

    signals = asyncio.run(
        strategy.evaluate(snapshot=snapshot, context=_context(recent_events=(recent_expiry,)))
    )

    assert len(signals) == 1


def test_crypto_maker_allows_materially_better_entry_after_recent_failure() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 0,
            "failure_cooldown_seconds": 30,
            "failure_reentry_edge_improvement_bps": 150,
        }
    )
    improved_snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.53,
        timestamp=datetime(2026, 3, 23, 12, 0, 10, tzinfo=UTC),
    )
    recent_expiry = {
        "event_type": "order.expired",
        "payload": {
            "market_id": "crypto-maker-1",
            "strategy_id": "crypto.maker",
            "signal_edge_bps": 100.0,
            "updated_at": "2026-03-23T12:00:00+00:00",
        },
    }

    signals = asyncio.run(
        strategy.evaluate(snapshot=improved_snapshot, context=_context(recent_events=(recent_expiry,)))
    )

    assert len(signals) == 1
    assert signals[0].edge_bps >= 300.0


def test_crypto_maker_ignores_daily_limit_rejection_for_failure_cooldown() -> None:
    strategy = CryptoMakerStrategy(
        {
            "min_spread_bps": 100,
            "market_cooldown_seconds": 0,
            "failure_cooldown_seconds": 30,
        }
    )
    snapshot = _snapshot(
        best_bid_yes=0.5,
        best_ask_yes=0.6,
        timestamp=datetime(2026, 3, 23, 12, 0, 10, tzinfo=UTC),
    )
    daily_limit_reject = {
        "event_type": "order.rejected",
        "payload": {
            "market_id": "crypto-maker-1",
            "strategy_id": "crypto.maker",
            "reason": "daily order hard limit reached",
            "created_at": "2026-03-23T12:00:05+00:00",
            "signal_edge_bps": 100.0,
        },
    }

    signals = asyncio.run(
        strategy.evaluate(snapshot=snapshot, context=_context(recent_events=(daily_limit_reject,)))
    )

    assert len(signals) == 1
