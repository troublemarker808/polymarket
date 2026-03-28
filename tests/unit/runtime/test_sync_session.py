import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.adapters.polymarket.user_ws_client import UserChannelAuth
from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, SignalSide, StrategySignal
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_session import LiveSessionRunner
from pm_bot.runtime.sync_session import ShadowPaperCoordinator, SynchronizedLiveExecutionAdapter
from pm_bot.storage.recorder import LiveRuntimeRecorder, PaperRuntimeRecorder


class FakeLiveClient:
    def create_order(self, order_args, options=None):
        return order_args

    def post_order(self, order, orderType, post_only=False):
        return {"orderID": "live-1"}

    def cancel(self, order_id):
        return {"cancelled": order_id}

    def get_orders(self, params=None, next_cursor="MA=="):
        return []

    def get_trades(self, params=None, next_cursor="MA=="):
        return []

    def create_or_derive_api_creds(self, nonce=None):
        return {
            "api_key": "derived-key",
            "api_secret": "derived-secret",
            "api_passphrase": "derived-passphrase",
        }

    def set_api_creds(self, creds):
        return None


class SubmitOnceStrategy:
    strategy_id = "crypto.surface"

    def __init__(self) -> None:
        self._submitted = False

    async def evaluate(self, snapshot: MarketSnapshot, context) -> list[StrategySignal]:
        del context
        if self._submitted:
            return []
        self._submitted = True
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=snapshot.token_id,
                fair_probability=0.61,
                side=SignalSide.BUY_YES,
                confidence=0.6,
                edge_bps=150.0,
                generated_at=snapshot.timestamp,
                target_price=0.5,
                target_size=5.0,
                quote_ttl_seconds=20,
            )
        ]


async def _market_stream(snapshot: MarketSnapshot):
    yield snapshot


async def _empty_user_stream():
    if False:
        yield


def test_sync_session_mirrors_same_intent_into_live_and_shadow(tmp_path: Path) -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.51,
        last_traded_price=0.495,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    live_execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=20,
        post_only=False,
        build_order_args=lambda intent: {
            "token_id": intent.token_id,
            "price": intent.price,
            "size": intent.size,
            "side": "BUY",
        },
        resolve_order_type=lambda tif: tif,
        user_channel_auth=UserChannelAuth(
            api_key="key",
            secret="secret",
            passphrase="passphrase",
        ),
    )
    shadow_execution = PaperExecutionAdapter(ttl_seconds=20, taker_slippage_bps=20.0)
    live_risk = BasicRiskManager(settings=RiskSettings(), trading_settings=TradingSettings())
    shadow_risk = BasicRiskManager(settings=RiskSettings(), trading_settings=TradingSettings())
    live_recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "live.events.jsonl",
        metrics_path=tmp_path / "live.metrics.json",
    )
    shadow_recorder = PaperRuntimeRecorder(
        event_path=tmp_path / "shadow.events.jsonl",
        metrics_path=tmp_path / "shadow.metrics.json",
    )
    shadow = ShadowPaperCoordinator(
        execution=shadow_execution,
        risk_manager=shadow_risk,
        recorder=shadow_recorder,
    )
    execution = SynchronizedLiveExecutionAdapter(
        live_execution=live_execution,
        shadow_coordinator=shadow,
    )
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[SubmitOnceStrategy()],
        risk_manager=live_risk,
        execution=execution,
        recorder=live_recorder,
        default_order_size=1.1,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=live_risk,
        recorder=live_recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_empty_user_stream(),
        shadow_coordinator=shadow,
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=0))

    assert stats.market_snapshots_processed == 1
    assert live_recorder.metrics.orders_submitted == 1
    assert shadow_recorder.metrics.orders_submitted == 1

    live_events = [
        json.loads(line)
        for line in (tmp_path / "live.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    shadow_events = [
        json.loads(line)
        for line in (tmp_path / "shadow.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    live_submitted = next(event for event in live_events if event["event_type"] == "order.submitted")
    shadow_submitted = next(event for event in shadow_events if event["event_type"] == "order.submitted")

    assert live_submitted["payload"]["intent_id"] == "intent-00000001"
    assert shadow_submitted["payload"]["intent_id"] == "intent-00000001"
    assert shadow_submitted["payload"]["live_order_id"] == "live-1"
    assert shadow_submitted["payload"]["order_id"] == "paper-1"
