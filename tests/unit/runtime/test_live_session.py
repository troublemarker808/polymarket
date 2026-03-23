import asyncio
from datetime import UTC, datetime, timezone

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.adapters.polymarket.user_ws_client import UserChannelAuth, UserTradeEvent
from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_session import (
    LiveSessionRunner,
    LiveSessionStats,
    LiveSessionStreamError,
    supervise_live_session,
)
from pm_bot.storage.recorder import InMemoryRecorder


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


async def _user_stream(event: UserTradeEvent):
    yield event


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
