import asyncio
from datetime import UTC, datetime

from pm_bot.core.settings import PolymarketSettings, RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_reconcile import recover_live_state


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
        return [
            {
                "id": "open-1",
                "market": "0xmarket",
                "asset_id": "yes-token",
                "price": "0.52",
                "original_size": "10",
                "size_matched": "4",
                "status": "LIVE",
                "created_at": "1672290687",
                "timestamp": "1672290701",
            }
        ]

    def get_trades(self, params=None, next_cursor="MA=="):
        return [
            {
                "id": "trade-1",
                "taker_order_id": "filled-1",
                "market": "0xmarket",
                "asset_id": "yes-token",
                "size": "10",
                "price": "0.50",
                "fee_rate_bps": "0",
                "timestamp": "1672290701",
                "maker_orders": [],
            }
        ]

    def create_or_derive_api_creds(self, nonce=None):
        return {
            "api_key": "derived-key",
            "api_secret": "derived-secret",
            "api_passphrase": "derived-passphrase",
        }

    def set_api_creds(self, creds):
        return None


def test_recover_live_state_rebuilds_orders_and_positions() -> None:
    execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
        ),
        ttl_seconds=15,
        env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
        geoblock_status=__import__("pm_bot.adapters.polymarket.geoblock_client", fromlist=["GeoblockStatus"]).GeoblockStatus(
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
            metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
        ),
    )

    stats = asyncio.run(
        recover_live_state(
            risk_manager=manager,
            execution=execution,
            snapshots=snapshots,
        )
    )

    assert stats.open_orders_recovered == 1
    assert stats.trades_replayed == 1
    assert stats.positions_rebuilt == 1
    dashboard = manager.dashboard_state()
    assert len(dashboard.open_positions) == 1
    assert dashboard.today_pnl == 1.0
