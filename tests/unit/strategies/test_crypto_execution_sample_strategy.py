import asyncio
from datetime import UTC, datetime, timedelta

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PositionState, RuntimeStatus
from pm_bot.strategies.crypto.execution_sample.strategy import CryptoExecutionSampleStrategy


def _snapshot(
    *,
    timestamp: datetime,
    market_id: str = "m1",
    token_id: str = "m1-yes",
    best_bid_yes: float = 0.45,
    best_ask_yes: float = 0.47,
    best_bid_no: float = 0.53,
    best_ask_no: float = 0.55,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        token_id=token_id,
        slug=market_id,
        category=Category.CRYPTO,
        timestamp=timestamp,
        resolution_time=None,
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=best_bid_no,
        best_ask_no=best_ask_no,
        metadata={"no_token_id": f"{market_id}-no"},
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


def _snapshot_events(*, market_id: str, timestamps: tuple[datetime, ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "event_type": "market.snapshot_processed",
            "payload": {
                "market_id": market_id,
                "updated_at": timestamp.isoformat(),
            },
        }
        for timestamp in timestamps
    )


def test_execution_sample_enters_recently_active_market() -> None:
    now = datetime(2026, 3, 26, 0, 0, tzinfo=UTC)
    strategy = CryptoExecutionSampleStrategy(
        {
            "min_spread_bps": 100,
            "min_recent_updates": 3,
            "recent_update_window_seconds": 90,
            "entry_cross_bps": 25,
        }
    )
    snapshot = _snapshot(timestamp=now)

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "recent_events": _snapshot_events(
                    market_id="m1",
                    timestamps=(
                        now - timedelta(seconds=30),
                        now - timedelta(seconds=20),
                        now - timedelta(seconds=10),
                    ),
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.BUY_YES
    assert signal.generated_at == now
    assert signal.quote_ttl_seconds == 30
    assert round(signal.target_price or 0.0, 6) == 0.471175


def test_execution_sample_skips_inactive_market() -> None:
    now = datetime(2026, 3, 26, 0, 0, tzinfo=UTC)
    strategy = CryptoExecutionSampleStrategy({"min_recent_updates": 3})
    snapshot = _snapshot(timestamp=now)

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "recent_events": _snapshot_events(
                    market_id="m1",
                    timestamps=(now - timedelta(seconds=120),),
                ),
            },
        )
    )

    assert signals == []


def test_execution_sample_exits_after_hold_window() -> None:
    now = datetime(2026, 3, 26, 0, 1, tzinfo=UTC)
    strategy = CryptoExecutionSampleStrategy(
        {
            "hold_seconds": 20,
            "exit_cross_bps": 25,
        }
    )
    snapshot = _snapshot(timestamp=now)
    position = PositionState(
        market_id="m1",
        token_id="m1-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.execution_sample",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.47,
        opened_at=now - timedelta(seconds=25),
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position),
                "recent_events": _snapshot_events(
                    market_id="m1",
                    timestamps=(
                        now - timedelta(seconds=8),
                        now - timedelta(seconds=4),
                    ),
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert round(signal.target_price or 0.0, 6) == 0.448875
    assert round(signal.target_size or 0.0, 6) == 4.48875


def test_execution_sample_respects_market_cooldown() -> None:
    now = datetime(2026, 3, 26, 0, 2, tzinfo=UTC)
    strategy = CryptoExecutionSampleStrategy({"market_cooldown_seconds": 30})
    snapshot = _snapshot(timestamp=now)
    recent_events = _snapshot_events(
        market_id="m1",
        timestamps=(
            now - timedelta(seconds=12),
            now - timedelta(seconds=8),
            now - timedelta(seconds=4),
        ),
    ) + (
        {
            "event_type": "order.filled",
            "payload": {
                "market_id": "m1",
                "strategy_id": "crypto.execution_sample",
                "updated_at": (now - timedelta(seconds=5)).isoformat(),
            },
        },
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "recent_events": recent_events,
            },
        )
    )

    assert signals == []
