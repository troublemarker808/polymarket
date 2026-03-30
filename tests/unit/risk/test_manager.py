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


def build_order(
    market_id: str,
    *,
    created_at: datetime | None = None,
    quote_ttl_seconds: int | None = None,
    signal_edge_bps: float | None = 150.0,
    exposure_group_id: str | None = None,
    thesis_group_id: str | None = None,
    underlying_group_id: str | None = None,
) -> OrderIntent:
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
        created_at=created_at or datetime.now(tz=timezone.utc),
        quote_ttl_seconds=quote_ttl_seconds,
        signal_edge_bps=signal_edge_bps,
        exposure_group_id=exposure_group_id,
        thesis_group_id=thesis_group_id,
        underlying_group_id=underlying_group_id,
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
    manager.settings.max_open_orders = 10

    for idx in range(4):
        intent = build_order(f"m{idx}")
        decision = asyncio.run(manager.review_order(intent))
        assert decision.approved
        asyncio.run(manager.record_order_submission(intent, f"o{idx}"))

    rejected = asyncio.run(manager.review_order(build_order("m5")))
    assert not rejected.approved
    assert rejected.reason == "max concurrent positions reached"


def test_risk_manager_rejects_order_when_max_open_orders_reached() -> None:
    import asyncio

    manager = build_manager()
    manager.settings.max_open_orders = 2

    for idx in range(2):
        intent = build_order(f"m{idx}")
        asyncio.run(manager.record_order_submission(intent, f"o{idx}"))

    rejected = asyncio.run(manager.review_order(build_order("m2")))

    assert not rejected.approved
    assert rejected.reason == "max open orders reached"


def test_risk_manager_rejects_order_when_per_market_notional_cap_is_breached() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=5.0,
            max_notional_per_category=50.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    intent = build_order("m1")
    intent.size = 10.0

    rejected = asyncio.run(manager.review_order(intent))

    assert not rejected.approved
    assert rejected.reason == "order exceeds per-market notional cap"


def test_risk_manager_rejects_order_when_per_category_notional_cap_is_breached() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_category=5.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    existing = build_order("m0")
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o0"))

    rejected = asyncio.run(manager.review_order(build_order("m1")))

    assert not rejected.approved
    assert rejected.reason == "order exceeds per-category notional cap"


def test_risk_manager_rejects_order_when_exposure_group_notional_cap_is_breached() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_exposure_group=5.0,
            max_notional_per_category=50.0,
            max_total_gross_notional=100.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    existing = build_order("m0", exposure_group_id="crypto:btc-reach-ladder")
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o0"))

    rejected = asyncio.run(
        manager.review_order(build_order("m1", exposure_group_id="crypto:btc-reach-ladder"))
    )

    assert not rejected.approved
    assert rejected.reason == "order exceeds exposure-group notional cap"
    dashboard = manager.dashboard_state()
    assert dashboard.last_order_rejection_reason == "order exceeds exposure-group notional cap"
    assert dashboard.last_order_rejection_market_id == "m1"
    assert dashboard.last_order_rejection_exposure_group_id == "crypto:btc-reach-ladder"


def test_risk_manager_rejects_order_when_total_gross_notional_cap_is_breached() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_exposure_group=50.0,
            max_notional_per_category=50.0,
            max_total_gross_notional=5.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    existing = build_order("m0", exposure_group_id="crypto:btc-reach-ladder")
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o0"))

    rejected = asyncio.run(manager.review_order(build_order("m1", exposure_group_id="crypto:eth-dip-ladder")))

    assert not rejected.approved
    assert rejected.reason == "order exceeds total gross notional cap"


def test_risk_manager_rejects_order_when_thesis_group_notional_cap_is_breached() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_exposure_group=50.0,
            max_notional_per_thesis_group=5.0,
            max_notional_per_underlying_group=50.0,
            max_notional_per_category=50.0,
            max_total_gross_notional=100.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    existing = build_order(
        "m0",
        exposure_group_id="crypto:btc-reach-ladder-a",
        thesis_group_id="crypto:btc:reach",
        underlying_group_id="crypto:btc",
    )
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o0"))

    rejected = asyncio.run(
        manager.review_order(
            build_order(
                "m1",
                exposure_group_id="crypto:btc-reach-ladder-b",
                thesis_group_id="crypto:btc:reach",
                underlying_group_id="crypto:btc",
            )
        )
    )

    assert not rejected.approved
    assert rejected.reason == "order exceeds thesis-group notional cap"


def test_risk_manager_rejects_order_when_underlying_group_notional_cap_is_breached() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_exposure_group=50.0,
            max_notional_per_thesis_group=50.0,
            max_notional_per_underlying_group=5.0,
            max_notional_per_category=50.0,
            max_total_gross_notional=100.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    existing = build_order(
        "m0",
        exposure_group_id="crypto:btc-reach-ladder-a",
        thesis_group_id="crypto:btc:reach",
        underlying_group_id="crypto:btc",
    )
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o0"))

    rejected = asyncio.run(
        manager.review_order(
            build_order(
                "m1",
                exposure_group_id="crypto:btc-dip-ladder-b",
                thesis_group_id="crypto:btc:dip",
                underlying_group_id="crypto:btc",
            )
        )
    )

    assert not rejected.approved
    assert rejected.reason == "order exceeds underlying-group notional cap"


def test_risk_manager_persists_last_order_rejection_details(tmp_path) -> None:
    import asyncio

    store = JsonRuntimeStateStore(tmp_path / "runtime-state.json")
    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_exposure_group=5.0,
            max_notional_per_category=50.0,
            max_total_gross_notional=100.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
        state_store=store,
    )
    existing = build_order("m0", exposure_group_id="crypto:btc-reach-ladder")
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o0"))

    asyncio.run(manager.review_order(build_order("m1", exposure_group_id="crypto:btc-reach-ladder")))

    loaded = store.load()
    assert loaded is not None
    assert loaded.last_order_rejection_reason == "order exceeds exposure-group notional cap"
    assert loaded.last_order_rejection_market_id == "m1"
    assert loaded.last_order_rejection_exposure_group_id == "crypto:btc-reach-ladder"


def test_risk_manager_approves_replacement_when_new_order_has_better_edge() -> None:
    import asyncio

    manager = build_manager()
    manager.settings.max_open_orders = 1
    manager.settings.open_order_replacement_min_edge_improvement_bps = 50.0
    created_at = datetime(2026, 3, 24, 3, 0, 0, tzinfo=timezone.utc)

    asyncio.run(
        manager.record_order_submission(
            build_order(
                "m1",
                created_at=created_at,
                quote_ttl_seconds=10,
                signal_edge_bps=100.0,
            ),
            "o1",
        )
    )

    decision = asyncio.run(
        manager.review_order(
            build_order(
                "m2",
                created_at=created_at + timedelta(seconds=6),
                quote_ttl_seconds=10,
                signal_edge_bps=180.0,
            )
        )
    )

    assert decision.approved
    assert decision.replacement_order_id == "o1"
    assert decision.reason == "approved_with_replacement"


def test_risk_manager_replacement_subtracts_replaced_order_from_category_cap() -> None:
    import asyncio

    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
            max_open_orders=1,
            open_order_replacement_min_edge_improvement_bps=50.0,
        ),
        trading_settings=TradingSettings(
            starting_equity=100.0,
            default_order_notional=10.0,
            max_notional_per_market=10.0,
            max_notional_per_category=5.0,
            max_concurrent_positions=4,
            daily_order_soft_limit=10,
            daily_order_hard_limit=15,
        ),
    )
    created_at = datetime(2026, 3, 24, 3, 0, 0, tzinfo=timezone.utc)
    existing = build_order(
        "m1",
        created_at=created_at,
        quote_ttl_seconds=10,
        signal_edge_bps=100.0,
    )
    existing.size = round(3.0 / 0.55, 6)
    existing.notional = 3.0
    asyncio.run(manager.record_order_submission(existing, "o1"))

    decision = asyncio.run(
        manager.review_order(
            build_order(
                "m2",
                created_at=created_at + timedelta(seconds=15),
                quote_ttl_seconds=10,
                signal_edge_bps=180.0,
            )
        )
    )

    assert decision.approved
    assert decision.replacement_order_id == "o1"
    assert decision.reason == "approved_with_replacement"


def test_risk_manager_rejects_edge_replacement_when_existing_order_is_too_fresh() -> None:
    import asyncio

    manager = build_manager()
    manager.settings.max_open_orders = 1
    manager.settings.open_order_replacement_min_edge_improvement_bps = 50.0
    created_at = datetime(2026, 3, 24, 3, 0, 0, tzinfo=timezone.utc)

    asyncio.run(
        manager.record_order_submission(
            build_order(
                "m1",
                created_at=created_at,
                quote_ttl_seconds=10,
                signal_edge_bps=100.0,
            ),
            "o1",
        )
    )

    decision = asyncio.run(
        manager.review_order(
            build_order(
                "m2",
                created_at=created_at + timedelta(seconds=2),
                quote_ttl_seconds=10,
                signal_edge_bps=180.0,
            )
        )
    )

    assert not decision.approved
    assert decision.reason == "max open orders reached"


def test_risk_manager_approves_replacement_when_existing_order_is_stale_at_frontier() -> None:
    import asyncio

    manager = build_manager()
    manager.settings.max_open_orders = 1
    created_at = datetime(2026, 3, 24, 3, 0, 0, tzinfo=timezone.utc)
    asyncio.run(
        manager.record_order_submission(
            build_order(
                "m1",
                created_at=created_at,
                quote_ttl_seconds=10,
                signal_edge_bps=100.0,
            ),
            "o1",
        )
    )
    manager.record_data_success(datetime(2026, 3, 24, 3, 0, 15, tzinfo=timezone.utc))

    decision = asyncio.run(
        manager.review_order(
            build_order(
                "m2",
                created_at=datetime(2026, 3, 24, 3, 0, 5, tzinfo=timezone.utc),
                quote_ttl_seconds=10,
                signal_edge_bps=100.0,
            )
        )
    )

    assert decision.approved
    assert decision.replacement_order_id == "o1"


def test_risk_manager_disables_proactive_replacement_after_daily_soft_limit() -> None:
    import asyncio

    manager = build_manager()
    manager.settings.max_open_orders = 1
    manager.settings.open_order_replacement_min_edge_improvement_bps = 50.0
    manager.trading_settings.daily_order_soft_limit = 1
    created_at = datetime(2026, 3, 24, 3, 0, 0, tzinfo=timezone.utc)

    asyncio.run(
        manager.record_order_submission(
            build_order(
                "m1",
                created_at=created_at,
                quote_ttl_seconds=10,
                signal_edge_bps=100.0,
            ),
            "o1",
        )
    )

    decision = asyncio.run(
        manager.review_order(
            build_order(
                "m2",
                created_at=created_at + timedelta(seconds=6),
                quote_ttl_seconds=10,
                signal_edge_bps=180.0,
            )
        )
    )

    assert not decision.approved
    assert decision.reason == "max open orders reached"


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
    assert dashboard.pending_orders[0].signal_edge_bps == 150.0


def test_risk_manager_records_pending_order_submission_exposure_group() -> None:
    import asyncio

    manager = build_manager()
    intent = build_order("m1", exposure_group_id="crypto:btc-reach-ladder")

    asyncio.run(manager.record_order_submission(intent, "o1"))

    dashboard = manager.dashboard_state()
    assert dashboard.pending_orders[0].exposure_group_id == "crypto:btc-reach-ladder"


def test_risk_manager_records_pending_order_submission_concentration_groups() -> None:
    import asyncio

    manager = build_manager()
    intent = build_order(
        "m1",
        exposure_group_id="crypto:btc-reach-ladder",
        thesis_group_id="crypto:btc:reach",
        underlying_group_id="crypto:btc",
    )

    asyncio.run(manager.record_order_submission(intent, "o1"))

    dashboard = manager.dashboard_state()
    assert dashboard.pending_orders[0].thesis_group_id == "crypto:btc:reach"
    assert dashboard.pending_orders[0].underlying_group_id == "crypto:btc"


def test_risk_manager_records_pending_order_cancellation() -> None:
    import asyncio

    manager = build_manager()
    asyncio.run(manager.record_order_submission(build_order("m1"), "o1"))

    asyncio.run(manager.record_order_cancellation("o1"))

    assert manager.dashboard_state().pending_orders == ()


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
    manager = BasicRiskManager(
        settings=RiskSettings(
            max_daily_drawdown_pct=5.0,
            max_consecutive_losses=5,
            manual_resume_required=True,
            halt_on_data_source_failure=False,
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


def test_risk_manager_halts_on_data_source_failure_when_enabled() -> None:
    manager = build_manager()

    manager.record_data_failure(reason="ConnectTimeout: timed out")

    dashboard = manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.DATA_SOURCE_FAILURE
    assert dashboard.last_data_error == "ConnectTimeout: timed out"
    assert dashboard.halt_message == "halted after data source failure: ConnectTimeout: timed out"
    assert dashboard.issue_codes == ("data_source_failure", "runtime_halted_data_source")


def test_risk_manager_halts_on_stale_market_data_threshold_breach() -> None:
    manager = build_manager()
    observed_at = datetime(2026, 3, 24, 5, 0, 0, tzinfo=timezone.utc)
    received_at = datetime(2026, 3, 24, 5, 0, 0, tzinfo=timezone.utc)
    manager.record_data_success(observed_at, received_at=received_at)

    manager.enforce_data_freshness(now=received_at + timedelta(seconds=31))

    dashboard = manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.STALE_DATA
    assert dashboard.halt_message == "halted after market data went stale for 30s"
    assert dashboard.last_data_success_at == observed_at
    assert dashboard.issue_codes == ("stale_data",)


def test_risk_manager_keeps_last_data_success_at_monotonic() -> None:
    manager = build_manager()

    manager.record_data_success(datetime(2026, 3, 24, 5, 0, 0, tzinfo=timezone.utc))
    manager.record_data_success(datetime(2026, 3, 24, 4, 0, 0, tzinfo=timezone.utc))

    dashboard = manager.dashboard_state()
    assert dashboard.last_data_success_at == datetime(2026, 3, 24, 5, 0, 0, tzinfo=timezone.utc)


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
