import asyncio
from datetime import UTC, datetime, timezone

from pm_bot.adapters.polymarket.geoblock_client import GeoblockStatus
from pm_bot.adapters.polymarket.user_ws_client import UserTradeEvent
from pm_bot.core.settings import PolymarketSettings, RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_sync import sync_live_execution_state


class FakeLiveClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def create_order(self, order_args, options=None):
        return order_args

    def post_order(self, order, orderType, post_only=False):
        return {"orderID": "live-1"}

    def cancel(self, order_id):
        return {"cancelled": order_id}

    def create_or_derive_api_creds(self, nonce=None):
        return {
            "api_key": f"derived-key-{nonce or 0}",
            "api_secret": "derived-secret",
            "api_passphrase": "derived-passphrase",
        }

    def set_api_creds(self, creds):
        return None


def test_sync_live_execution_state_pushes_positions_and_unrealized() -> None:
    execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
        ),
        ttl_seconds=15,
        env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
        geoblock_status=GeoblockStatus(
            blocked=False,
            country="HK",
            region="",
            ip="141.11.22.34",
        ),
        client_factory=FakeLiveClient,
    )
    manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
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
    execution.apply_user_trade_event(
        UserTradeEvent(
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
    )

    snapshots = (
        MarketSnapshot(
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
            metadata={"no_token_id": "no-token"},
        ),
    )

    marked = asyncio.run(
        sync_live_execution_state(
            risk_manager=manager,
            execution=execution,
            snapshots=snapshots,
        )
    )

    assert len(marked) == 1
    dashboard = manager.dashboard_state()
    assert dashboard.today_pnl == 1.0
    assert len(dashboard.open_positions) == 1
    assert len(dashboard.pending_orders) == 0
    assert dashboard.open_positions[0].shares == 10.0
    assert dashboard.open_positions[0].mark_price == 0.6


def test_sync_live_execution_state_pushes_pending_orders_separately() -> None:
    execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
        ),
        ttl_seconds=15,
        env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
        geoblock_status=GeoblockStatus(
            blocked=False,
            country="HK",
            region="",
            ip="141.11.22.34",
        ),
        client_factory=FakeLiveClient,
    )
    manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
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

    snapshots = (
        MarketSnapshot(
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
            metadata={"no_token_id": "no-token"},
        ),
    )

    marked = asyncio.run(
        sync_live_execution_state(
            risk_manager=manager,
            execution=execution,
            snapshots=snapshots,
        )
    )

    assert len(marked) == 0
    dashboard = manager.dashboard_state()
    assert len(dashboard.open_positions) == 0
    assert len(dashboard.pending_orders) == 1
    assert dashboard.pending_orders[0].status == "pending"
