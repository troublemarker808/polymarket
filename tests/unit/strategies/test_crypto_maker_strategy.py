import asyncio
from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PositionState, RuntimeStatus
from pm_bot.strategies.crypto.maker.strategy import CryptoMakerStrategy


def _snapshot(*, best_bid_yes: float, best_ask_yes: float) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="crypto-maker-1",
        token_id="crypto-maker-1-yes",
        slug="crypto-maker-1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
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


def test_crypto_maker_quotes_inside_spread() -> None:
    snapshot = _snapshot(best_bid_yes=0.5, best_ask_yes=0.6)
    strategy = CryptoMakerStrategy({"min_spread_bps": 100})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_YES
    assert round(signals[0].target_price or 0.0, 2) == 0.55
    assert round(signals[0].edge_bps, 2) == 100.0


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

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard(position)}))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.SELL_YES
    assert round(signals[0].target_size or 0.0, 2) == 5.5
