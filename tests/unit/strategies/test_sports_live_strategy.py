import asyncio
from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategies.sports.live.strategy import SportsLiveStrategy


def _snapshot(*, metadata: dict[str, str], best_bid_yes: float, best_ask_yes: float) -> MarketSnapshot:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    return MarketSnapshot(
        market_id="sports-live-1",
        token_id="sports-live-1-yes",
        slug="sports-live-1",
        category=Category.SPORTS,
        timestamp=now,
        resolution_time=None,
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=1 - best_ask_yes,
        best_ask_no=1 - best_bid_yes,
        last_traded_price=(best_bid_yes + best_ask_yes) / 2,
        metadata=metadata,
    )


def _dashboard() -> DashboardState:
    return DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )


def test_sports_live_generates_buy_yes_signal_for_fresh_state() -> None:
    snapshot = _snapshot(
        metadata={
            "live_yes_probability": "0.70",
            "live_state_updated_at": "2026-03-23T12:00:00Z",
        },
        best_bid_yes=0.62,
        best_ask_yes=0.63,
    )
    strategy = SportsLiveStrategy({"min_edge_bps": 500, "stale_state_seconds": 5})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_YES
    assert round(signals[0].edge_bps, 2) == 700.0


def test_sports_live_skips_stale_state() -> None:
    snapshot = _snapshot(
        metadata={
            "live_yes_probability": "0.70",
            "live_state_updated_at": "2026-03-23T11:59:40Z",
        },
        best_bid_yes=0.62,
        best_ask_yes=0.63,
    )
    strategy = SportsLiveStrategy({"min_edge_bps": 500, "stale_state_seconds": 5})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert signals == []


def test_sports_live_applies_preset_registry() -> None:
    snapshot = _snapshot(
        metadata={
            "league": "nba",
            "market_family": "moneyline",
            "live_yes_probability": "0.70",
            "live_state_updated_at": "2026-03-23T11:59:56Z",
        },
        best_bid_yes=0.62,
        best_ask_yes=0.63,
    )
    strategy = SportsLiveStrategy(
        {
            "min_edge_bps": 800,
            "stale_state_seconds": 5,
            "preset_registry": {
                "nba_moneyline_live": {
                    "match": {"league": "nba", "market_family": "moneyline", "mode": "live"},
                    "overrides": {"min_edge_bps": 500},
                }
            },
        }
    )

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert len(signals) == 1
    assert signals[0].diagnostics["sports_preset"] == "nba_moneyline_live"
