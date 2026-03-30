import asyncio
from datetime import datetime, timezone

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.storage.recorder import InMemoryRecorder
from pm_bot.core.settings import RiskSettings, TradingSettings


class DummyStrategy:
    strategy_id = "sports.anchor"

    async def evaluate(self, snapshot: MarketSnapshot, context: dict[str, object]):
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=snapshot.category,
                market_id=snapshot.market_id,
                token_id=snapshot.token_id,
                fair_probability=0.62,
                side=SignalSide.BUY_YES,
                confidence=0.7,
                edge_bps=250,
                generated_at=snapshot.timestamp,
                target_price=0.58,
                target_size=5.0,
            )
        ]


class ConfigurableStrategy:
    strategy_id = "crypto.maker"

    def __init__(self, *, market_id: str, token_id: str, edge_bps: float, target_price: float) -> None:
        self.market_id = market_id
        self.token_id = token_id
        self.edge_bps = edge_bps
        self.target_price = target_price

    async def evaluate(self, snapshot: MarketSnapshot, context: dict[str, object]):
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=snapshot.category,
                market_id=self.market_id,
                token_id=self.token_id,
                fair_probability=0.62,
                side=SignalSide.BUY_YES,
                confidence=0.7,
                edge_bps=self.edge_bps,
                generated_at=snapshot.timestamp,
                target_price=self.target_price,
                target_size=5.0,
            )
        ]


class RejectingRiskManager(BasicRiskManager):
    async def review_order(self, intent):  # type: ignore[override]
        return type(await super().review_order(intent))(approved=False, reason="max open orders reached")


class FailingExecutionAdapter(PaperExecutionAdapter):
    async def submit(self, intent):  # type: ignore[override]
        raise RuntimeError("exchange rejected order")


def test_event_router_runs_one_signal_through_paper_execution() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="team-a-win",
        category=Category.SPORTS,
        timestamp=datetime.now(tz=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.58,
    )

    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[DummyStrategy()],
        risk_manager=BasicRiskManager(
            settings=RiskSettings(),
            trading_settings=TradingSettings(),
            min_signal_edge_bps=100,
        ),
        execution=PaperExecutionAdapter(),
        recorder=InMemoryRecorder(),
    )

    order_ids = asyncio.run(router.run_once(snapshot=snapshot))

    assert order_ids == ["paper-1"]
    submitted = next(event for event in router.recorder.events if event["event_type"] == "order.submitted")
    assert submitted["payload"]["intent_id"] == "intent-00000001"
    assert submitted["payload"]["rationale_tags"] == []
    assert submitted["payload"]["diagnostics"] == {}


def test_event_router_replaces_pending_order_when_higher_priority_signal_arrives() -> None:
    first_snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.58,
    )
    second_snapshot = MarketSnapshot(
        market_id="m2",
        token_id="t2",
        slug="m2",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 25, 12, 0, 8, tzinfo=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.52,
    )
    recorder = InMemoryRecorder()
    risk_manager = BasicRiskManager(
        settings=RiskSettings(
            max_open_orders=1,
            open_order_replacement_min_edge_improvement_bps=50.0,
        ),
        trading_settings=TradingSettings(),
        min_signal_edge_bps=100,
    )
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first_snapshot, second_snapshot]),
        strategies=[ConfigurableStrategy(market_id="m1", token_id="t1", edge_bps=120.0, target_price=0.58)],
        risk_manager=risk_manager,
        execution=PaperExecutionAdapter(),
        recorder=recorder,
    )

    first_order_ids = asyncio.run(router.run_once(snapshot=first_snapshot))
    router.strategies = [ConfigurableStrategy(market_id="m2", token_id="t2", edge_bps=220.0, target_price=0.52)]
    second_order_ids = asyncio.run(router.run_once(snapshot=second_snapshot))

    assert first_order_ids == ["paper-1"]
    assert second_order_ids == ["paper-2"]
    dashboard = risk_manager.dashboard_state()
    assert len(dashboard.pending_orders) == 1
    assert dashboard.pending_orders[0].order_id == "paper-2"
    assert dashboard.pending_orders[0].market_id == "m2"
    event_types = [event["event_type"] for event in recorder.events]
    assert "order.canceled" in event_types
    canceled = next(event for event in recorder.events if event["event_type"] == "order.canceled")
    assert canceled["payload"]["order_id"] == "paper-1"
    assert canceled["payload"]["reason"] == "open_order_replaced"


def test_event_router_records_signal_edge_on_order_rejection() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.58,
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[ConfigurableStrategy(market_id="m1", token_id="t1", edge_bps=220.0, target_price=0.58)],
        risk_manager=RejectingRiskManager(
            settings=RiskSettings(),
            trading_settings=TradingSettings(),
            min_signal_edge_bps=100,
        ),
        execution=PaperExecutionAdapter(),
        recorder=recorder,
    )

    order_ids = asyncio.run(router.run_once(snapshot=snapshot))

    assert order_ids == []
    rejected = next(event for event in recorder.events if event["event_type"] == "order.rejected")
    assert rejected["payload"]["signal_edge_bps"] == 220.0


def test_event_router_records_execution_submit_failures_without_crashing() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="t1",
        slug="m1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
        resolution_time=None,
        best_ask_yes=0.58,
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[ConfigurableStrategy(market_id="m1", token_id="t1", edge_bps=220.0, target_price=0.58)],
        risk_manager=BasicRiskManager(
            settings=RiskSettings(),
            trading_settings=TradingSettings(),
            min_signal_edge_bps=100,
        ),
        execution=FailingExecutionAdapter(),
        recorder=recorder,
    )

    order_ids = asyncio.run(router.run_once(snapshot=snapshot))

    assert order_ids == []
    rejected = next(event for event in recorder.events if event["event_type"] == "order.rejected")
    assert rejected["payload"]["reason"] == "execution submit failed: RuntimeError: exchange rejected order"
    assert rejected["payload"]["signal_edge_bps"] == 220.0
    assert rejected["payload"]["intent_id"] == "intent-00000001"
