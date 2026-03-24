from datetime import datetime, timedelta, timezone

from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, OrderAction, OrderIntent, SignalSide, StrategySignal
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.state import (
    ClosedTrade,
    HaltReason,
    PendingOrderState,
    PositionState,
    RuntimeState,
    RuntimeStatus,
)
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore


def build_manager(state_store: JsonRuntimeStateStore | None = None) -> BasicRiskManager:
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
        state_store=state_store,
    )


async def _approve_signal(manager: BasicRiskManager) -> None:
    signal = StrategySignal(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="t1",
        fair_probability=0.55,
        side=SignalSide.BUY_YES,
        confidence=0.7,
        edge_bps=300,
        generated_at=datetime.now(tz=timezone.utc),
        target_price=0.55,
        target_size=5.0,
    )
    decision = await manager.review_signal(signal)
    assert decision.approved


def build_order(market_id: str) -> OrderIntent:
    return OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id=market_id,
        token_id=f"{market_id}-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.55,
        size=5.0,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc),
    )


def test_risk_manager_halts_after_consecutive_losses() -> None:
    import asyncio

    manager = build_manager()
    asyncio.run(_approve_signal(manager))

    for idx in range(4):
        asyncio.run(
            manager.record_trade_close(
                ClosedTrade(
                    market_id=f"m{idx}",
                    token_id=f"t{idx}",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    realized_pnl=-0.5,
                    fees_paid=0.0,
                    closed_at=datetime.now(tz=timezone.utc),
                )
            )
        )

    assert manager.dashboard_state().status == RuntimeStatus.RUNNING

    asyncio.run(
        manager.record_trade_close(
            ClosedTrade(
                market_id="m5",
                token_id="t5",
                category=Category.CRYPTO,
                strategy_id="crypto.surface",
                realized_pnl=-0.5,
                fees_paid=0.0,
                closed_at=datetime.now(tz=timezone.utc),
            )
        )
    )

    dashboard = manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.CONSECUTIVE_LOSSES


def test_risk_manager_halts_after_daily_drawdown() -> None:
    import asyncio

    manager = build_manager()

    asyncio.run(manager.update_unrealized_pnl(-5.1))

    dashboard = manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.DAILY_DRAWDOWN


def test_risk_manager_rejects_fifth_open_position() -> None:
    import asyncio

    manager = build_manager()

    for idx in range(4):
        intent = build_order(f"m{idx}")
        decision = asyncio.run(manager.review_order(intent))
        assert decision.approved
        asyncio.run(manager.record_order_submission(intent, f"o{idx}"))

    rejected = asyncio.run(manager.review_order(build_order("m5")))
    assert not rejected.approved
    assert rejected.reason == "max concurrent positions reached"


def test_risk_manager_manual_resume_clears_halt() -> None:
    import asyncio

    manager = build_manager()
    asyncio.run(manager.update_unrealized_pnl(-5.1))
    assert manager.dashboard_state().status == RuntimeStatus.HALTED

    resumed = asyncio.run(manager.manual_resume())

    assert resumed.approved
    dashboard = manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.RUNNING
    assert dashboard.halt_reason == HaltReason.NONE
    assert manager.state.consecutive_losses == 0


def test_risk_manager_persists_halt_and_resume(tmp_path) -> None:
    import asyncio

    store = JsonRuntimeStateStore(tmp_path / "runtime-state.json")
    manager = build_manager(state_store=store)

    asyncio.run(manager.update_unrealized_pnl(-5.1))
    loaded = store.load()
    assert loaded is not None
    assert loaded.status == RuntimeStatus.HALTED
    assert loaded.halt_reason == HaltReason.DAILY_DRAWDOWN

    asyncio.run(manager.manual_resume())
    loaded_after_resume = store.load()
    assert loaded_after_resume is not None
    assert loaded_after_resume.status == RuntimeStatus.RUNNING
    assert loaded_after_resume.halt_reason == HaltReason.NONE


def test_risk_manager_syncs_open_positions_and_unrealized() -> None:
    import asyncio

    manager = build_manager()
    asyncio.run(
        manager.sync_open_positions(
            [
                PositionState(
                    market_id="m1",
                    token_id="yes-token",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    notional=5.0,
                    shares=10.0,
                    average_entry_price=0.5,
                    mark_price=0.6,
                    unrealized_pnl=1.0,
                    opened_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
    )

    dashboard = manager.dashboard_state()
    assert dashboard.today_pnl == 1.0
    assert len(dashboard.open_positions) == 1
    assert dashboard.open_positions[0].shares == 10.0
    assert len(dashboard.pending_orders) == 0


def test_risk_manager_records_pending_order_submission() -> None:
    import asyncio

    manager = build_manager()
    created_at = datetime(2026, 3, 24, 3, 0, 0, tzinfo=timezone.utc)
    intent = build_order("m1")
    intent.created_at = created_at

    asyncio.run(manager.record_order_submission(intent, "o1"))

    dashboard = manager.dashboard_state()
    assert len(dashboard.open_positions) == 0
    assert len(dashboard.pending_orders) == 1
    assert dashboard.pending_orders[0].order_id == "o1"
    assert dashboard.pending_orders[0].requested_notional == 2.75
    assert dashboard.pending_orders[0].side == "buy_yes"
    assert dashboard.pending_orders[0].created_at == created_at


def test_risk_manager_rejects_order_when_market_has_pending_order() -> None:
    import asyncio

    manager = build_manager()
    asyncio.run(
        manager.sync_pending_orders(
            [
                PendingOrderState(
                    order_id="o1",
                    market_id="m1",
                    token_id="m1-token",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    side="buy_yes",
                    limit_price=0.55,
                    requested_shares=5.0,
                    requested_notional=2.75,
                    matched_shares=0.0,
                    matched_notional=0.0,
                    fees_paid=0.0,
                    status="pending",
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
    )

    rejected = asyncio.run(manager.review_order(build_order("m1")))
    assert not rejected.approved
    assert rejected.reason == "market already has a pending order"


def test_risk_manager_rolls_daily_counters_on_new_utc_day() -> None:
    yesterday = datetime.now(tz=timezone.utc) - timedelta(days=1)
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
        state=RuntimeState(
            starting_equity=100.0,
            day_starting_equity=100.0,
            realized_pnl_today=3.0,
            unrealized_pnl=2.0,
            orders_today=4,
            day_started_at=yesterday,
            updated_at=yesterday,
        ),
    )

    dashboard = manager.dashboard_state()

    assert dashboard.daily_order_count == 0
    assert dashboard.today_pnl == 0.0
    assert manager.state.day_starting_equity == 105.0
    assert manager.state.day_open_unrealized_pnl == 2.0


def test_risk_manager_tracks_data_source_failures_and_recovery() -> None:
    manager = build_manager()

    manager.record_data_failure(reason="ConnectTimeout: timed out")
    manager.record_data_failure(reason="ConnectTimeout: timed out")

    dashboard = manager.dashboard_state()
    assert dashboard.consecutive_data_failures == 2
    assert dashboard.last_data_error == "ConnectTimeout: timed out"
    assert dashboard.issue_codes == ("data_source_failure",)

    manager.record_data_success(datetime(2026, 3, 24, 4, 0, 0, tzinfo=timezone.utc))

    recovered = manager.dashboard_state()
    assert recovered.consecutive_data_failures == 0
    assert recovered.last_data_error is None
    assert recovered.last_data_success_at == datetime(2026, 3, 24, 4, 0, 0, tzinfo=timezone.utc)
    assert recovered.issue_codes == ()


def test_risk_manager_allows_sell_to_close_existing_position() -> None:
    import asyncio

    manager = build_manager()
    asyncio.run(
        manager.sync_open_positions(
            [
                PositionState(
                    market_id="m1",
                    token_id="m1-token",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    notional=5.0,
                    shares=5.0,
                    average_entry_price=0.55,
                    mark_price=0.6,
                    unrealized_pnl=0.25,
                    opened_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
    )
    close_intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="m1-token",
        action=OrderAction.PLACE,
        side=SignalSide.SELL_YES,
        price=0.6,
        size=5.0,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc),
        notional=3.0,
    )

    decision = asyncio.run(manager.review_order(close_intent))

    assert decision.approved


def test_risk_manager_rejects_sell_without_open_position() -> None:
    import asyncio

    manager = build_manager()
    close_intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="m1-token",
        action=OrderAction.PLACE,
        side=SignalSide.SELL_YES,
        price=0.6,
        size=5.0,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc),
        notional=3.0,
    )

    decision = asyncio.run(manager.review_order(close_intent))

    assert not decision.approved
    assert decision.reason == "no open position to close"
