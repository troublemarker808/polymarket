import asyncio
from datetime import UTC, datetime, timedelta

from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.paper_session import PaperSessionRunner, format_dashboard_summary
from pm_bot.runtime.paper_sync import sync_paper_execution_state
from pm_bot.runtime.state import DashboardState, HaltReason, PositionState, RuntimeStatus
from pm_bot.storage.recorder import InMemoryRecorder


class _IdleRouter:
    async def run_once(self, snapshot, context=None) -> list[str]:
        del snapshot, context
        return []


async def _empty_market_stream():
    if False:
        yield


def test_format_dashboard_summary_includes_operator_fields() -> None:
    summary = format_dashboard_summary(
        {
            "processed_snapshots": 25,
            "submitted_orders": 2,
            "events_recorded": 7,
            "dashboard": DashboardState(
                total_equity=101.5,
                today_pnl=1.5,
                open_positions=(
                    PositionState(
                        market_id="m1",
                        token_id="t1",
                        category=Category.CRYPTO,
                        strategy_id="crypto.surface",
                        notional=5.0,
                        opened_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                    ),
                ),
                pending_orders=(),
                status=RuntimeStatus.RUNNING,
                halt_reason=HaltReason.NONE,
                halt_message=None,
                last_alert=None,
                daily_order_count=2,
                daily_order_soft_limit_reached=False,
            ),
        }
    )

    assert "runtime_dashboard" in summary
    assert "processed_snapshots=25" in summary
    assert "submitted_orders=2" in summary
    assert "total_equity=101.50" in summary
    assert "status=running" in summary
    assert "open_positions=1" in summary


def _build_manager() -> BasicRiskManager:
    return BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=5.0,
            max_notional_per_market=5.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )


def test_sync_paper_execution_state_records_fill_and_day_rollover() -> None:
    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=5.0,
            max_notional_per_market=5.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
        state=None,
    )
    manager.state.day_started_at = datetime(2026, 3, 23, 0, 0, 0, tzinfo=UTC)
    execution = PaperExecutionAdapter(ttl_seconds=15)
    recorder = InMemoryRecorder()
    snapshot_time = datetime(2026, 3, 24, 2, 36, 30, tzinfo=UTC)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.41,
        size=10.0,
        time_in_force="GTC",
        created_at=snapshot_time,
        notional=4.1,
    )
    asyncio.run(execution.submit(intent))

    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=snapshot_time,
        resolution_time=None,
        best_bid_yes=0.39,
        best_ask_yes=0.40,
        best_bid_no=0.60,
        best_ask_no=0.61,
        metadata={"no_token_id": "no-token"},
    )

    asyncio.run(
        sync_paper_execution_state(
            risk_manager=manager,
            execution=execution,
            snapshot=snapshot,
            ttl_seconds=15,
            recorder=recorder,
        )
    )

    dashboard = manager.dashboard_state()
    assert len(dashboard.pending_orders) == 0
    assert len(dashboard.open_positions) == 1
    assert dashboard.open_positions[0].average_entry_price == 0.40
    assert dashboard.open_positions[0].mark_price == 0.39
    assert any(event["event_type"] == "runtime.day_rollover" for event in recorder.events)
    assert any(event["event_type"] == "order.filled" for event in recorder.events)


def test_sync_paper_execution_state_expires_stale_orders() -> None:
    now = datetime(2026, 3, 24, 2, 37, 0, tzinfo=UTC)
    manager = _build_manager()
    execution = PaperExecutionAdapter(ttl_seconds=15)
    recorder = InMemoryRecorder()
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.30,
        size=10.0,
        time_in_force="GTC",
        created_at=now - timedelta(seconds=30),
        notional=3.0,
    )
    asyncio.run(execution.submit(intent))

    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=None,
        best_bid_yes=0.45,
        best_ask_yes=0.46,
        best_bid_no=0.54,
        best_ask_no=0.55,
        metadata={"no_token_id": "no-token"},
    )

    asyncio.run(
        sync_paper_execution_state(
            risk_manager=manager,
            execution=execution,
            snapshot=snapshot,
            ttl_seconds=15,
            recorder=recorder,
        )
    )

    dashboard = manager.dashboard_state()
    assert len(dashboard.pending_orders) == 0
    assert any(event["event_type"] == "order.expired" for event in recorder.events)


def test_paper_session_runner_halts_when_market_data_goes_stale() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 24, 2, 37, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.45,
        best_ask_yes=0.46,
        best_bid_no=0.54,
        best_ask_no=0.55,
        metadata={"no_token_id": "no-token"},
    )
    manager = _build_manager()
    manager.record_data_success(
        snapshot.timestamp,
        received_at=datetime.now(tz=UTC) - timedelta(seconds=31),
    )
    recorder = InMemoryRecorder()
    runner = PaperSessionRunner(
        router=_IdleRouter(),
        execution=PaperExecutionAdapter(ttl_seconds=15),
        risk_manager=manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_empty_market_stream(),
    )

    stats = asyncio.run(runner.run())

    assert stats.market_snapshots_processed == 0
    dashboard = manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.STALE_DATA
    halted_event = next(event for event in recorder.events if event["event_type"] == "runtime.halted")
    assert halted_event["payload"]["halt_reason"] == "stale_data"
