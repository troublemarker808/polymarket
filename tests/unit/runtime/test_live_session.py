import asyncio
from datetime import UTC, datetime, timedelta, timezone
import json
from pathlib import Path

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.adapters.polymarket.user_ws_client import UserChannelAuth, UserTradeEvent
from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import (
    Category,
    MarketSnapshot,
    OrderAction,
    OrderIntent,
    SignalSide,
    StrategySignal,
)
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_session import (
    LiveSessionRunner,
    LiveSessionStats,
    LiveSessionStreamError,
    supervise_live_session,
)
from pm_bot.runtime.state import HaltReason, RuntimeStatus
from pm_bot.storage.recorder import InMemoryRecorder, LiveRuntimeRecorder


class FakeLiveClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

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


async def _market_stream(snapshot: MarketSnapshot):
    yield snapshot


async def _empty_market_stream():
    if False:
        yield


async def _user_stream(event: UserTradeEvent):
    yield event


async def _empty_user_stream():
    if False:
        yield


async def _hanging_user_stream():
    await asyncio.Event().wait()
    if False:
        yield


class SubmitOnceStrategy:
    strategy_id = "crypto.execution_sample"

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
                quote_ttl_seconds=15,
            )
        ]


class ReconnectingMarketData:
    def __init__(
        self,
        *,
        bootstrap_cycles: list[list[MarketSnapshot]],
        stream_cycles: list[list[MarketSnapshot]],
    ) -> None:
        self.bootstrap_cycles = bootstrap_cycles
        self.stream_cycles = stream_cycles
        self.bootstrap_index = 0
        self.stream_index = 0

    async def bootstrap_snapshots(self) -> list[MarketSnapshot]:
        index = min(self.bootstrap_index, len(self.bootstrap_cycles) - 1)
        self.bootstrap_index += 1
        return list(self.bootstrap_cycles[index])

    async def stream_from_snapshots(self, snapshots: list[MarketSnapshot], *, include_initial: bool):
        if include_initial:
            for snapshot in snapshots:
                yield snapshot

        index = min(self.stream_index, len(self.stream_cycles) - 1)
        self.stream_index += 1
        for snapshot in self.stream_cycles[index]:
            yield snapshot


class BootstrapFailingMarketData:
    def __init__(self, *, seed_snapshots: list[MarketSnapshot]) -> None:
        self.seed_snapshots = seed_snapshots
        self.bootstrap_calls = 0

    async def bootstrap_snapshots(self) -> list[MarketSnapshot]:
        self.bootstrap_calls += 1
        if self.bootstrap_calls == 1:
            return list(self.seed_snapshots)
        raise RuntimeError("bootstrap failed")

    async def stream_from_snapshots(self, snapshots: list[MarketSnapshot], *, include_initial: bool):
        if include_initial:
            for snapshot in snapshots:
                yield snapshot


class ReconnectingUserClient:
    def __init__(self, *, event_cycles: list[list[UserTradeEvent]]) -> None:
        self.event_cycles = event_cycles
        self.stream_index = 0

    async def stream_events(self, *, auth: object, markets=()):
        del auth, markets
        index = min(self.stream_index, len(self.event_cycles) - 1)
        self.stream_index += 1
        for event in self.event_cycles[index]:
            yield event


class FailingUserClient:
    async def stream_events(self, *, auth: object, markets=()):
        del auth, markets
        raise RuntimeError("user stream failed")
        yield


def test_live_session_runner_syncs_trade_and_marks_dashboard() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.5,
        size=10.0,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc),
        notional=5.0,
    )
    asyncio.run(execution.submit(intent))

    event = UserTradeEvent(
        id="trade-1",
        type="TRADE",
        taker_order_id="live-1",
        market="m1",
        asset_id="yes-token",
        side="BUY",
        size=10.0,
        price=0.5,
        fee_rate_bps=0.0,
        status="MATCHED",
        matchtime=datetime.now(tz=timezone.utc),
        last_update=datetime.now(tz=timezone.utc),
        outcome="YES",
        owner="owner-1",
        trade_owner="owner-1",
        maker_address="0x1234",
        transaction_hash="",
        bucket_index=0,
        maker_orders=(),
        trader_side="TAKER",
        timestamp=datetime.now(tz=timezone.utc),
    )

    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_user_stream(event),
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=1))

    assert stats.market_snapshots_processed == 1
    assert stats.user_events_processed == 1
    dashboard = risk_manager.dashboard_state()
    assert dashboard.today_pnl == 1.0
    assert len(dashboard.open_positions) == 1
    assert dashboard.open_positions[0].mark_price == 0.6
    assert recorder.events[-1]["event_type"] == "user.trade_event"


def test_supervise_live_session_reconnects_and_aggregates_stats() -> None:
    first_snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.44,
        best_ask_no=0.45,
        last_traded_price=0.55,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    second_snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 2, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([first_snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    market_data = ReconnectingMarketData(
        bootstrap_cycles=[[first_snapshot], [second_snapshot]],
        stream_cycles=[[], [second_snapshot]],
    )
    user_client = ReconnectingUserClient(
        event_cycles=[
            [
                UserTradeEvent(
                    id="trade-1",
                    type="TRADE",
                    taker_order_id="order-1",
                    market="m1",
                    asset_id="yes-token",
                    side="BUY",
                    size=5.0,
                    price=0.5,
                    fee_rate_bps=0.0,
                    status="MATCHED",
                    matchtime=datetime.now(tz=timezone.utc),
                    last_update=datetime.now(tz=timezone.utc),
                    outcome="YES",
                    owner="owner-1",
                    trade_owner="owner-1",
                    maker_address="0x1234",
                    transaction_hash="",
                    bucket_index=0,
                    maker_orders=(),
                    trader_side="TAKER",
                    timestamp=datetime.now(tz=timezone.utc),
                )
            ],
            [
                UserTradeEvent(
                    id="trade-2",
                    type="TRADE",
                    taker_order_id="order-2",
                    market="m1",
                    asset_id="yes-token",
                    side="BUY",
                    size=5.0,
                    price=0.5,
                    fee_rate_bps=0.0,
                    status="MATCHED",
                    matchtime=datetime.now(tz=timezone.utc),
                    last_update=datetime.now(tz=timezone.utc),
                    outcome="YES",
                    owner="owner-1",
                    trade_owner="owner-1",
                    maker_address="0x1234",
                    transaction_hash="",
                    bucket_index=0,
                    maker_orders=(),
                    trader_side="TAKER",
                    timestamp=datetime.now(tz=timezone.utc),
                )
            ],
        ]
    )

    stats = asyncio.run(
        supervise_live_session(
            market_data=market_data,
            user_client=user_client,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=[first_snapshot],
            max_market_snapshots=2,
            max_user_events=2,
            reconnect_delay_seconds=0.0,
            max_reconnects=1,
            session_started_at=datetime.now(tz=timezone.utc) - timedelta(seconds=1),
        )
    )

    assert stats == LiveSessionStats(
        market_snapshots_processed=2,
        user_events_processed=2,
        submitted_orders=0,
        stale_orders_cancelled=0,
        recovered_open_orders=0,
        replayed_trades=0,
        rebuilt_positions=1,
        reconnects=1,
    )
    dashboard = risk_manager.dashboard_state()
    assert round(dashboard.today_pnl, 2) == 1.0
    assert any(event["event_type"] == "live.reconnect" for event in recorder.events)


def test_live_session_runner_stops_on_market_limit_without_waiting_for_user_stream() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.44,
        best_ask_no=0.45,
        last_traded_price=0.55,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_hanging_user_stream(),
    )

    stats = asyncio.run(asyncio.wait_for(runner.run(max_market_snapshots=1), timeout=1.0))

    assert stats.market_snapshots_processed == 1
    assert stats.user_events_processed == 0
    assert stats.reconnects == 0


def test_supervise_live_session_returns_when_market_limit_is_reached_before_user_limit() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.44,
        best_ask_no=0.45,
        last_traded_price=0.55,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    market_data = ReconnectingMarketData(
        bootstrap_cycles=[[snapshot], [snapshot]],
        stream_cycles=[[], [snapshot]],
    )
    user_client = ReconnectingUserClient(event_cycles=[[], []])

    stats = asyncio.run(
        supervise_live_session(
            market_data=market_data,
            user_client=user_client,
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            initial_snapshots=[snapshot],
            max_market_snapshots=1,
            max_user_events=10,
            reconnect_delay_seconds=0.0,
            max_reconnects=1,
        )
    )

    assert stats.market_snapshots_processed == 1
    assert stats.user_events_processed == 0
    reconnect_events = [event for event in recorder.events if event["event_type"] == "live.reconnect"]
    assert reconnect_events == []


def test_supervise_live_session_without_limits_reconnects_after_clean_stream_end() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.44,
        best_ask_no=0.45,
        last_traded_price=0.55,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    market_data = ReconnectingMarketData(
        bootstrap_cycles=[[snapshot], [snapshot]],
        stream_cycles=[[], []],
    )
    user_client = ReconnectingUserClient(event_cycles=[[], []])

    try:
        asyncio.run(
            supervise_live_session(
                market_data=market_data,
                user_client=user_client,
                router=router,
                execution=execution,
                risk_manager=risk_manager,
                recorder=recorder,
                initial_snapshots=[snapshot],
                reconnect_delay_seconds=0.0,
                max_reconnects=1,
            )
        )
    except RuntimeError as exc:
        assert "reconnect budget was exhausted" in str(exc)
    else:
        raise AssertionError("Expected reconnect-budget exhaustion after repeated clean stream endings")

    reconnect_events = [event for event in recorder.events if event["event_type"] == "live.reconnect"]
    assert len(reconnect_events) == 1
    assert reconnect_events[0]["payload"]["reason"] == "stream_ended"


def test_live_session_runner_halts_when_market_data_goes_stale() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    risk_manager.record_data_success(
        snapshot.timestamp,
        received_at=datetime.now(tz=timezone.utc) - timedelta(seconds=31),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_empty_market_stream(),
        user_event_stream=_empty_user_stream(),
    )

    stats = asyncio.run(runner.run())

    assert stats.market_snapshots_processed == 0
    dashboard = risk_manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.STALE_DATA
    halted_event = next(event for event in recorder.events if event["event_type"] == "runtime.halted")
    assert halted_event["payload"]["halt_reason"] == "stale_data"


def test_supervise_live_session_halts_on_market_data_refresh_failure_when_configured() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.44,
        best_ask_no=0.45,
        last_traded_price=0.55,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )

    stats = asyncio.run(
        supervise_live_session(
            market_data=BootstrapFailingMarketData(seed_snapshots=[snapshot]),
            user_client=ReconnectingUserClient(event_cycles=[[], []]),
            router=router,
            execution=execution,
            risk_manager=risk_manager,
            recorder=recorder,
            reconnect_delay_seconds=0.0,
            max_reconnects=1,
        )
    )

    assert stats.market_snapshots_processed == 1
    dashboard = risk_manager.dashboard_state()
    assert dashboard.status == RuntimeStatus.HALTED
    assert dashboard.halt_reason == HaltReason.DATA_SOURCE_FAILURE
    event_types = [event["event_type"] for event in recorder.events]
    assert "market_data.failure" in event_types
    assert "runtime.halted" in event_types


def test_live_session_runner_surfaces_stream_errors() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 12, 1, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=FailingUserClient().stream_events(auth=None),
    )

    try:
        asyncio.run(runner.run(max_market_snapshots=1))
    except LiveSessionStreamError as exc:
        assert exc.stream_name == "user"
    else:
        raise AssertionError("Expected LiveSessionStreamError")


def test_live_session_runner_writes_paper_comparable_artifacts(tmp_path: Path) -> None:
    snapshot_time = datetime(2026, 3, 26, 12, 0, tzinfo=UTC)
    fill_time = datetime(2026, 3, 26, 12, 0, 2, tzinfo=UTC)
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=snapshot_time,
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "live.events.jsonl",
        metrics_path=tmp_path / "live.metrics.json",
    )
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[SubmitOnceStrategy()],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    fill_event = UserTradeEvent(
        id="trade-1",
        type="TRADE",
        taker_order_id="live-1",
        market="m1",
        asset_id="yes-token",
        side="BUY",
        size=10.0,
        price=0.5,
        fee_rate_bps=0.0,
        status="MATCHED",
        matchtime=fill_time,
        last_update=fill_time,
        outcome="YES",
        owner="owner-1",
        trade_owner="owner-1",
        maker_address="0x1234",
        transaction_hash="",
        bucket_index=0,
        maker_orders=(),
        trader_side="TAKER",
        timestamp=fill_time,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_user_stream(fill_event),
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=1))

    assert stats.market_snapshots_processed == 1
    assert stats.user_events_processed == 1
    assert recorder.metrics.processed_snapshots == 1
    assert recorder.metrics.orders_submitted == 1
    assert recorder.metrics.orders_filled == 1
    assert recorder.metrics.fill_rate == 1.0

    metrics_payload = json.loads((tmp_path / "live.metrics.json").read_text(encoding="utf-8"))
    assert metrics_payload["processed_snapshots"] == 1
    assert metrics_payload["orders_submitted"] == 1
    assert metrics_payload["orders_filled"] == 1

    events = [
        json.loads(line)
        for line in (tmp_path / "live.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_types = [event["event_type"] for event in events]
    assert "order.submitted" in event_types
    assert "order.filled" in event_types
    assert any(
        event["event_type"] == "market.snapshot_processed"
        and event["payload"]["updated_at"] == snapshot_time.isoformat()
        for event in events
    )


def test_live_session_runner_records_stale_cancel_as_comparable_event(tmp_path: Path) -> None:
    snapshot_time = datetime.now(tz=timezone.utc)
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=snapshot_time,
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    intent = OrderIntent(
        strategy_id="crypto.execution_sample",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_YES,
        price=0.5,
        size=10.0,
        time_in_force="GTC",
        created_at=snapshot_time - timedelta(seconds=20),
        notional=5.0,
    )
    asyncio.run(execution.submit(intent))

    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "cancel.events.jsonl",
        metrics_path=tmp_path / "cancel.metrics.json",
    )
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_empty_user_stream(),
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=0))

    assert stats.stale_orders_cancelled == 1
    assert recorder.metrics.orders_canceled == 1
    events = [
        json.loads(line)
        for line in (tmp_path / "cancel.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    canceled = next(event for event in events if event["event_type"] == "order.canceled")
    assert canceled["payload"]["reason"] == "stale_ttl_cancel"


def test_live_session_runner_records_runtime_diagnostics_for_sync_shadow_context() -> None:
    snapshot_time = datetime(2026, 3, 31, 12, 0, tzinfo=UTC)
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="will-bitcoin-be-above-66000-on-march-31",
        category=Category.CRYPTO,
        timestamp=snapshot_time,
        resolution_time=datetime(2026, 3, 31, 23, 59, tzinfo=UTC),
        best_bid_yes=0.42,
        best_ask_yes=0.44,
        best_bid_no=0.56,
        best_ask_no=0.58,
        last_traded_price=0.43,
        metadata={
            "question": "Will Bitcoin be above $66,000 on March 31?",
            "event_slug": "btc-above-66000-2026-03-31",
        },
    )
    recorder = InMemoryRecorder()
    shadow_recorder = InMemoryRecorder()
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
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
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )

    class ShadowCoordinator:
        def __init__(self) -> None:
            self.recorder = shadow_recorder

        async def before_market_snapshot(self, *, snapshot: MarketSnapshot) -> None:
            del snapshot

        async def after_market_snapshot(self, *, snapshot: MarketSnapshot) -> None:
            del snapshot

    fair_value = FairValueEstimate(
        market_id="m1",
        category=Category.CRYPTO,
        fair_probability=0.39,
        confidence=0.72,
        observed_probability=0.43,
        model_id="crypto.phase1",
        rationale_tags=("barrier", "surface"),
        supporting_values={
            "gross_edge_bps": -200.0,
            "net_edge_bps": -250.0,
            "entry_cost_bps": 50.0,
        },
    )

    def runtime_context_builder(*, snapshot: MarketSnapshot, snapshots_by_market_id, recorder):
        del snapshot, snapshots_by_market_id, recorder
        return {
            "fair_values_by_market_id": {"m1": fair_value},
            "market_selection_actions": {"m1": "watch_market"},
            "market_selection_reasons": {"m1": ("negative_edge",)},
            "blocked_market_ids": {"m1"},
            "blocked_market_reasons": {"m1": ("negative_edge",)},
            "blocked_series_keys": {"btc-above-66000-2026-03-31"},
            "blocked_series_reasons": {"btc-above-66000-2026-03-31": ("negative_edge",)},
        }

    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_empty_user_stream(),
        shadow_coordinator=ShadowCoordinator(),
        runtime_context_builder=runtime_context_builder,
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=0))

    assert stats.market_snapshots_processed == 1
    diagnostic = next(event for event in recorder.events if event["event_type"] == "market.runtime_diagnostics")
    assert diagnostic["payload"]["market_id"] == "m1"
    assert diagnostic["payload"]["strategies_enabled"] is False
    assert diagnostic["payload"]["active_strategy_ids"] == []
    assert diagnostic["payload"]["fair_value_present"] is True
    assert diagnostic["payload"]["net_edge_bps"] == -250.0
    assert diagnostic["payload"]["selection_action"] == "watch_market"
    assert diagnostic["payload"]["selection_reasons"] == ["negative_edge"]
    assert diagnostic["payload"]["market_blocked"] is True
    assert diagnostic["payload"]["market_block_reasons"] == ["negative_edge"]
    assert diagnostic["payload"]["series_blocked"] is True
    shadow_diagnostic = next(
        event for event in shadow_recorder.events if event["event_type"] == "market.runtime_diagnostics"
    )
    assert shadow_diagnostic["payload"] == diagnostic["payload"]


def test_live_session_runner_ignores_historical_user_trade_events_before_session_start() -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 26, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.6,
        best_ask_yes=0.61,
        best_bid_no=0.39,
        best_ask_no=0.4,
        last_traded_price=0.6,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=15,
        post_only=False,
        signature_type=0,
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
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    recorder = InMemoryRecorder()
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[],
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=5.0,
    )
    historical_trade = UserTradeEvent(
        id="trade-old",
        type="TRADE",
        taker_order_id="old-order",
        market="m1",
        asset_id="yes-token",
        side="BUY",
        size=10.0,
        price=0.5,
        fee_rate_bps=0.0,
        status="MATCHED",
        matchtime=datetime(2026, 3, 26, 11, 59, tzinfo=UTC),
        last_update=datetime(2026, 3, 26, 11, 59, tzinfo=UTC),
        outcome="YES",
        owner="owner-1",
        trade_owner="owner-1",
        maker_address="0x1234",
        transaction_hash="",
        bucket_index=0,
        maker_orders=(),
        trader_side="TAKER",
        timestamp=datetime(2026, 3, 26, 11, 59, tzinfo=UTC),
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=risk_manager,
        recorder=recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_user_stream(historical_trade),
        session_started_at=datetime(2026, 3, 26, 12, 0, tzinfo=UTC),
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=1))

    assert stats.user_events_processed == 1
    assert execution.mark_positions_to_market((snapshot,)) == ()
    assert execution.total_unrealized_pnl() == 0.0
    ignored = next(event for event in recorder.events if event["event_type"] == "user.event_ignored")
    assert ignored["payload"]["event_id"] == "trade-old"
