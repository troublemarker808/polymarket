import asyncio
from datetime import UTC, datetime, timedelta

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PositionState, RuntimeStatus
from pm_bot.strategies.sports.anchor.strategy import SportsAnchorStrategy


def _snapshot(*, market_id: str, metadata: dict[str, str], best_bid_yes: float, best_ask_yes: float) -> MarketSnapshot:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=market_id,
        category=Category.SPORTS,
        timestamp=now,
        resolution_time=now + timedelta(hours=4),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=1 - best_ask_yes,
        best_ask_no=1 - best_bid_yes,
        last_traded_price=(best_bid_yes + best_ask_yes) / 2,
        metadata=metadata,
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


def test_sports_anchor_generates_buy_yes_signal() -> None:
    snapshot = _snapshot(
        market_id="sports-1",
        metadata={
            "model_yes_probability": "0.68",
            "start_time": "2026-03-23T14:00:00Z",
        },
        best_bid_yes=0.59,
        best_ask_yes=0.6,
    )
    strategy = SportsAnchorStrategy({"min_edge_bps": 300, "max_time_to_start_minutes": 240})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_YES
    assert round(signals[0].edge_bps, 2) == 800.0


def test_sports_anchor_exits_existing_position_before_start() -> None:
    snapshot = _snapshot(
        market_id="sports-1",
        metadata={
            "model_yes_probability": "0.55",
            "start_time": "2026-03-23T12:03:00Z",
        },
        best_bid_yes=0.54,
        best_ask_yes=0.56,
    )
    position = PositionState(
        market_id="sports-1",
        token_id="sports-1-yes",
        category=Category.SPORTS,
        strategy_id="sports.anchor",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.5,
        opened_at=datetime(2026, 3, 23, 11, 30, tzinfo=UTC),
    )
    strategy = SportsAnchorStrategy({"min_edge_bps": 300, "cancel_before_start_minutes": 5})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard(position)}))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.SELL_YES
    assert round(signals[0].target_size or 0.0, 2) == 5.4


def test_sports_anchor_applies_preset_registry() -> None:
    snapshot = _snapshot(
        market_id="sports-1",
        metadata={
            "league": "nba",
            "market_family": "moneyline",
            "model_yes_probability": "0.68",
            "start_time": "2026-03-23T14:00:00Z",
        },
        best_bid_yes=0.59,
        best_ask_yes=0.6,
    )
    strategy = SportsAnchorStrategy(
        {
            "min_edge_bps": 900,
            "max_time_to_start_minutes": 240,
            "preset_registry": {
                "nba_moneyline_fast": {
                    "match": {"league": "nba", "market_family": "moneyline", "mode": "pregame"},
                    "overrides": {"min_edge_bps": 300},
                }
            },
        }
    )

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert len(signals) == 1
    assert signals[0].diagnostics["sports_preset"] == "nba_moneyline_fast"
