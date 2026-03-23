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
                generated_at=datetime.now(tz=timezone.utc),
                target_price=0.58,
                target_size=5.0,
            )
        ]


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
