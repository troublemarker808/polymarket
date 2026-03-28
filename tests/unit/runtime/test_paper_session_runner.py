import asyncio
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderBookLevel, OrderIntent, SignalSide
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.paper_session import PaperSessionRunner, supervise_paper_session
from pm_bot.storage.recorder import JsonlRecorder, PaperRuntimeRecorder


async def _market_stream(snapshots):
    for snapshot in snapshots:
        yield snapshot


class _StubPaperMarketData:
    def __init__(self, initial_snapshots, streamed_updates) -> None:
        self._initial_snapshots = list(initial_snapshots)
        self._streamed_updates = list(streamed_updates)

    async def bootstrap_snapshots(self):
        return list(self._initial_snapshots)

    async def stream_from_snapshots(self, snapshots, *, include_initial: bool):
        if include_initial:
            for snapshot in snapshots:
                yield snapshot
        for snapshot in self._streamed_updates:
            yield snapshot


def _snapshot(
    *,
    timestamp: datetime,
    last_trade_price: float | None = None,
    last_trade_side: str | None = None,
    last_trade_size: float | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=timestamp,
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.52,
        best_bid_no=0.48,
        best_ask_no=0.51,
        yes_bid_levels=(
            OrderBookLevel(price=0.49, size=3.0),
            OrderBookLevel(price=0.48, size=5.0),
        ),
        yes_ask_levels=(OrderBookLevel(price=0.52, size=10.0),),
        last_traded_price=last_trade_price,
        last_trade_side=last_trade_side,
        last_trade_size=last_trade_size,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )


def test_paper_session_runner_keeps_pending_order_across_snapshots() -> None:
    first = _snapshot(timestamp=datetime(2026, 3, 25, 0, 0, tzinfo=UTC))
    second = _snapshot(
        timestamp=first.timestamp + timedelta(seconds=1),
        last_trade_price=0.48,
        last_trade_side="SELL",
        last_trade_size=9.0,
    )
    third = _snapshot(
        timestamp=first.timestamp + timedelta(seconds=2),
        last_trade_price=0.48,
        last_trade_side="SELL",
        last_trade_size=10.0,
    )

    execution = PaperExecutionAdapter(ttl_seconds=30)
    execution.reconcile_snapshot(first)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.48,
        size=8.0,
        time_in_force="GTC",
        created_at=first.timestamp,
        notional=3.84,
    )
    asyncio.run(execution.submit(intent))

    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second, third]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = PaperSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(first,),
        market_snapshot_stream=_market_stream([second, third]),
        summary_every_snapshots=None,
    )

    stats = asyncio.run(runner.run(max_market_snapshots=2))

    assert stats.market_snapshots_processed == 2
    assert recorder.metrics.processed_snapshots == 2
    assert recorder.metrics.orders_partially_filled == 1
    assert recorder.metrics.orders_filled == 1
    assert recorder.metrics.maker_fill_share == 1.0
    assert recorder.metrics.taker_fill_share == 0.0
    dashboard = risk_manager.dashboard_state()
    assert len(dashboard.open_positions) == 1
    assert dashboard.open_positions[0].shares == 8.0


def test_paper_session_runner_captures_market_snapshots(tmp_path: Path) -> None:
    first = _snapshot(timestamp=datetime(2026, 3, 25, 0, 0, tzinfo=UTC))
    second = _snapshot(timestamp=first.timestamp + timedelta(seconds=1))
    capture_path = tmp_path / "captured.jsonl"

    execution = PaperExecutionAdapter(ttl_seconds=30)
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = PaperSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(first,),
        market_snapshot_stream=_market_stream([first, second]),
        summary_every_snapshots=None,
        snapshot_capture_recorder=JsonlRecorder(capture_path),
    )

    asyncio.run(runner.run(max_market_snapshots=2))

    lines = [json.loads(line) for line in capture_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert all(line["event_type"] == "market.snapshot" for line in lines)
    assert lines[0]["payload"]["market_id"] == "m1"


def test_paper_session_runner_records_signal_edge_on_expired_orders() -> None:
    first = _snapshot(timestamp=datetime(2026, 3, 25, 0, 0, tzinfo=UTC))
    second = _snapshot(timestamp=first.timestamp + timedelta(seconds=2))

    execution = PaperExecutionAdapter(ttl_seconds=1)
    execution.reconcile_snapshot(first)
    intent = OrderIntent(
        strategy_id="crypto.maker",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.48,
        size=8.0,
        time_in_force="GTC",
        created_at=first.timestamp,
        notional=3.84,
        signal_edge_bps=125.0,
        quote_ttl_seconds=1,
    )
    asyncio.run(execution.submit(intent))

    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = PaperSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(first,),
        market_snapshot_stream=_market_stream([second]),
        summary_every_snapshots=None,
    )

    asyncio.run(runner.run(max_market_snapshots=1))

    expired = next(event for event in recorder.events if event["event_type"] == "order.expired")
    assert expired["payload"]["signal_edge_bps"] == 125.0


def test_paper_session_runner_can_cancel_pending_orders_on_stop() -> None:
    first = _snapshot(timestamp=datetime(2026, 3, 25, 0, 0, tzinfo=UTC))
    second = _snapshot(timestamp=first.timestamp + timedelta(seconds=1))

    execution = PaperExecutionAdapter(ttl_seconds=300)
    execution.reconcile_snapshot(first)
    intent = OrderIntent(
        strategy_id="crypto.phase2",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.47,
        size=8.0,
        time_in_force="GTC",
        created_at=first.timestamp,
        notional=3.76,
    )
    asyncio.run(execution.submit(intent))

    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = PaperSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(first,),
        market_snapshot_stream=_market_stream([second]),
        summary_every_snapshots=None,
        cancel_pending_orders_on_stop=True,
    )

    asyncio.run(runner.run(max_market_snapshots=1))

    dashboard = risk_manager.dashboard_state()
    assert dashboard.pending_orders == ()
    assert any(event["event_type"] == "order.canceled" for event in recorder.events)


def test_paper_session_runner_rechecks_open_positions_with_global_tick_timestamp() -> None:
    first = _snapshot(timestamp=datetime(2026, 3, 25, 0, 0, tzinfo=UTC))
    second = MarketSnapshot(
        market_id="m2",
        token_id="yes-token-2",
        slug="eth-above",
        category=Category.CRYPTO,
        timestamp=first.timestamp + timedelta(seconds=5),
        resolution_time=None,
        best_bid_yes=0.47,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.53,
        metadata={"no_token_id": "no-token-2", "condition_id": "0xmarket-2"},
    )

    execution = PaperExecutionAdapter(ttl_seconds=30)
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    execution.reconcile_snapshot(first)
    fill_intent = OrderIntent(
        strategy_id="crypto.phase2",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.52,
        size=10.0,
        time_in_force="IOC",
        created_at=first.timestamp,
        notional=5.2,
    )
    asyncio.run(execution.submit(fill_intent))
    execution.reconcile_snapshot(first)
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )

    seen_calls: list[tuple[str, datetime]] = []
    original_run_once = router.run_once

    async def capture_run_once(*, snapshot, context=None):
        seen_calls.append((snapshot.market_id, snapshot.timestamp))
        return await original_run_once(snapshot=snapshot, context=context)

    router.run_once = capture_run_once  # type: ignore[method-assign]

    runner = PaperSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(first, second),
        market_snapshot_stream=_market_stream([second]),
        summary_every_snapshots=None,
        runtime_context_builder=lambda **kwargs: {"fair_values_by_market_id": {"m1": "stub", "m2": "stub"}},
    )

    asyncio.run(runner.run(max_market_snapshots=1))

    assert seen_calls == [
        ("m2", second.timestamp),
        ("m1", second.timestamp),
    ]


def test_supervise_paper_session_can_exclude_bootstrap_from_snapshot_limit() -> None:
    first = _snapshot(timestamp=datetime(2026, 3, 25, 0, 0, tzinfo=UTC))
    second = MarketSnapshot(
        market_id="m2",
        token_id="yes-token-2",
        slug="eth-above",
        category=Category.CRYPTO,
        timestamp=first.timestamp + timedelta(seconds=1),
        resolution_time=None,
        best_bid_yes=0.48,
        best_ask_yes=0.52,
        best_bid_no=0.48,
        best_ask_no=0.52,
        metadata={"no_token_id": "no-token-2", "condition_id": "0xmarket-2"},
    )
    update = _snapshot(timestamp=first.timestamp + timedelta(seconds=2))
    market_data = _StubPaperMarketData((first, second), (update,))

    execution = PaperExecutionAdapter(ttl_seconds=30)
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second, update]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )

    counted_stats = asyncio.run(
        supervise_paper_session(
            market_data=market_data,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=(first, second),
            max_market_snapshots=1,
            count_initial_snapshots_toward_limit=True,
        )
    )

    assert counted_stats.market_snapshots_processed == 1

    execution = PaperExecutionAdapter(ttl_seconds=30)
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = PaperRuntimeRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first, second, update]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )

    excluded_stats = asyncio.run(
        supervise_paper_session(
            market_data=market_data,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=(first, second),
            max_market_snapshots=1,
            count_initial_snapshots_toward_limit=False,
        )
    )

    assert excluded_stats.market_snapshots_processed == 3
