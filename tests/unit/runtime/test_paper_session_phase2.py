import asyncio
from datetime import UTC, datetime

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.paper_session import PaperSessionRunner
from pm_bot.runtime.state import PendingOrderState, PositionState
from pm_bot.storage.recorder import PaperRuntimeRecorder


async def _market_stream(snapshot: MarketSnapshot):
    yield snapshot


def test_paper_session_runner_passes_runtime_context_to_router() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.51,
        metadata={"no_token_id": "t2"},
    )
    contexts: list[dict[str, object] | None] = []

    execution = PaperExecutionAdapter(ttl_seconds=30)
    risk_manager = BasicRiskManager(settings=RiskSettings(), trading_settings=TradingSettings())
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )

    original_run_once = router.run_once

    async def capture_run_once(*, snapshot, context=None):
        contexts.append(context)
        return await original_run_once(snapshot=snapshot, context=context)

    router.run_once = capture_run_once  # type: ignore[method-assign]

    runner = PaperSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        runtime_context_builder=lambda **kwargs: {"fair_values_by_market_id": {"m1": "stub"}},
    )

    asyncio.run(runner.run(max_market_snapshots=1))

    assert contexts == [{"fair_values_by_market_id": {"m1": "stub"}}]


def test_phase2_exit_repricing_is_not_blocked_by_existing_pending_exit() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.51,
        metadata={"no_token_id": "t2"},
    )

    risk_manager = BasicRiskManager(settings=RiskSettings(), trading_settings=TradingSettings())
    asyncio.run(
        risk_manager.sync_open_positions(
            [
                PositionState(
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.phase2",
                    notional=5.0,
                    opened_at=snapshot.timestamp,
                    shares=10.0,
                    average_entry_price=0.5,
                )
            ]
        )
    )
    asyncio.run(
        risk_manager.sync_pending_orders(
            [
                PendingOrderState(
                    order_id="paper-1",
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.phase2",
                    side="sell_yes",
                    limit_price=0.52,
                    requested_shares=10.0,
                    requested_notional=5.2,
                    matched_shares=0.0,
                    matched_notional=0.0,
                    fees_paid=0.0,
                    status="pending",
                    created_at=snapshot.timestamp,
                    updated_at=snapshot.timestamp,
                    quote_ttl_seconds=60,
                )
            ]
        )
    )

    decision = asyncio.run(
        risk_manager.review_order(
            OrderIntent(
                strategy_id="crypto.phase2",
                category=Category.CRYPTO,
                market_id="m1",
                token_id="t1",
                action=OrderAction.PLACE,
                side=SignalSide.SELL_YES,
                price=0.5,
                size=10.0,
                time_in_force="GTC",
                created_at=snapshot.timestamp,
                notional=5.0,
            )
        )
    )

    assert decision.approved
    assert decision.replacement_order_id == "paper-1"
