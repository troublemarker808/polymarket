import asyncio
from datetime import UTC, datetime, timedelta

from pm_bot.core.settings import PolymarketSettings, RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_reconcile import recover_live_state


def _now_timestamp(offset_seconds: int = 0) -> str:
    return str(int((datetime.now(tz=UTC) + timedelta(seconds=offset_seconds)).timestamp()))


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
                "created_at": _now_timestamp(-30),
                "timestamp": _now_timestamp(-5),
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
                "timestamp": _now_timestamp(-5),
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


class MixedMakerTradeClient(FakeLiveClient):
    def get_orders(self, params=None, next_cursor="MA=="):
        return []

    def get_trades(self, params=None, next_cursor="MA=="):
        return [
            {
                "id": "trade-open",
                "taker_order_id": "buy-1",
                "market": "0xmarket",
                "asset_id": "yes-token",
                "side": "BUY",
                "size": "10",
                "price": "0.40",
                "fee_rate_bps": "0",
                "timestamp": _now_timestamp(-20),
                "trader_side": "TAKER",
                "maker_address": "0xme",
                "maker_orders": [
                    {
                        "order_id": "counterparty-buy-1",
                        "asset_id": "yes-token",
                        "matched_amount": "10",
                        "price": "0.40",
                        "side": "SELL",
                        "maker_address": "0xother",
                    }
                ],
            },
            {
                "id": "trade-close",
                "taker_order_id": "counterparty-taker-2",
                "market": "0xmarket",
                "asset_id": "no-token",
                "side": "BUY",
                "size": "10",
                "price": "0.60",
                "fee_rate_bps": "0",
                "timestamp": _now_timestamp(-5),
                "trader_side": "MAKER",
                "maker_orders": [
                    {
                        "order_id": "sell-ours",
                        "asset_id": "yes-token",
                        "matched_amount": "10",
                        "price": "0.60",
                        "side": "SELL",
                        "maker_address": "0xme",
                    },
                    {
                        "order_id": "sell-other",
                        "asset_id": "yes-token",
                        "matched_amount": "10",
                        "price": "0.60",
                        "side": "SELL",
                        "maker_address": "0xother",
                    },
                ],
            },
        ]


class SyntheticHistoryMarketClient(FakeLiveClient):
    def get_orders(self, params=None, next_cursor="MA=="):
        return []

    def get_trades(self, params=None, next_cursor="MA=="):
        return [
            {
                "id": "trade-buy",
                "taker_order_id": "buy-1",
                "market": "0xmissing",
                "asset_id": "yes-token",
                "side": "BUY",
                "size": "10",
                "price": "0.40",
                "fee_rate_bps": "0",
                "timestamp": _now_timestamp(-20),
                "trader_side": "TAKER",
                "maker_address": "0xme",
                "maker_orders": [
                    {
                        "order_id": "counterparty-no-1",
                        "asset_id": "no-token",
                        "matched_amount": "10",
                        "price": "0.60",
                        "side": "BUY",
                        "maker_address": "0xother",
                    }
                ],
            },
            {
                "id": "trade-sell",
                "taker_order_id": "sell-1",
                "market": "0xmissing",
                "asset_id": "yes-token",
                "side": "SELL",
                "size": "15",
                "price": "0.60",
                "fee_rate_bps": "0",
                "timestamp": _now_timestamp(-5),
                "trader_side": "TAKER",
                "maker_address": "0xme",
                "maker_orders": [
                    {
                        "order_id": "counterparty-yes-1",
                        "asset_id": "yes-token",
                        "matched_amount": "15",
                        "price": "0.60",
                        "side": "BUY",
                        "maker_address": "0xother",
                    }
                ],
            },
        ]


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


def test_recover_live_state_filters_counterparty_maker_legs() -> None:
    execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
        ),
        ttl_seconds=15,
        env={
            "POLYMARKET_PRIVATE_KEY": "0xabc",
            "POLYMARKET_FUNDER": "0xme",
        },
        geoblock_status=__import__("pm_bot.adapters.polymarket.geoblock_client", fromlist=["GeoblockStatus"]).GeoblockStatus(
            blocked=False,
            country="HK",
            region="",
            ip="141.11.22.34",
        ),
        client_factory=MixedMakerTradeClient,
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

    assert stats.open_orders_recovered == 0
    assert stats.trades_replayed == 2
    assert stats.positions_rebuilt == 0
    dashboard = manager.dashboard_state()
    assert len(dashboard.open_positions) == 0
    assert dashboard.today_pnl == 2.0


def test_recover_live_state_infers_missing_market_pairs_from_history() -> None:
    execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
        ),
        ttl_seconds=15,
        env={
            "POLYMARKET_PRIVATE_KEY": "0xabc",
            "POLYMARKET_FUNDER": "0xme",
        },
        geoblock_status=__import__("pm_bot.adapters.polymarket.geoblock_client", fromlist=["GeoblockStatus"]).GeoblockStatus(
            blocked=False,
            country="HK",
            region="",
            ip="141.11.22.34",
        ),
        client_factory=SyntheticHistoryMarketClient,
    )
    manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )

    stats = asyncio.run(
        recover_live_state(
            risk_manager=manager,
            execution=execution,
            snapshots=(),
        )
    )

    assert stats.open_orders_recovered == 0
    assert stats.trades_replayed == 2
    assert stats.positions_rebuilt == 0
    dashboard = manager.dashboard_state()
    assert len(dashboard.open_positions) == 1
    assert dashboard.open_positions[0].token_id == "no-token"
    assert dashboard.open_positions[0].shares == 5.0
    assert dashboard.today_pnl == 2.0


class HistoricalClosedTradeClient(FakeLiveClient):
    def get_orders(self, params=None, next_cursor="MA=="):
        return []

    def get_trades(self, params=None, next_cursor="MA=="):
        return [
            {
                "id": "old-buy",
                "taker_order_id": "old-buy-1",
                "market": "0xmarket",
                "asset_id": "yes-token",
                "side": "BUY",
                "size": "10",
                "price": "0.40",
                "fee_rate_bps": "0",
                "timestamp": "1672290600",
                "trader_side": "TAKER",
                "maker_address": "0xme",
                "maker_orders": [],
            },
            {
                "id": "old-sell",
                "taker_order_id": "old-sell-1",
                "market": "0xmarket",
                "asset_id": "yes-token",
                "side": "SELL",
                "size": "10",
                "price": "0.60",
                "fee_rate_bps": "0",
                "timestamp": "1672290701",
                "trader_side": "TAKER",
                "maker_address": "0xme",
                "maker_orders": [],
            },
        ]


def test_recover_live_state_does_not_count_historical_closed_trades_as_today_pnl() -> None:
    execution = PolymarketLiveExecutionAdapter.from_settings(
        settings=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
        ),
        ttl_seconds=15,
        env={
            "POLYMARKET_PRIVATE_KEY": "0xabc",
            "POLYMARKET_FUNDER": "0xme",
        },
        geoblock_status=__import__("pm_bot.adapters.polymarket.geoblock_client", fromlist=["GeoblockStatus"]).GeoblockStatus(
            blocked=False,
            country="HK",
            region="",
            ip="141.11.22.34",
        ),
        client_factory=HistoricalClosedTradeClient,
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
            timestamp=datetime.now(tz=UTC),
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

    assert stats.trades_replayed == 2
    dashboard = manager.dashboard_state()
    assert len(dashboard.open_positions) == 0
    assert dashboard.today_pnl == 0.0
