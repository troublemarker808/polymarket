import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from pm_bot.adapters.polymarket.user_ws_client import UserTradeEvent
from pm_bot.core.settings import (
    AppSettings,
    BotSettings,
    CategoryToggles,
    PolymarketSettings,
    RiskSettings,
    TradingSettings,
)
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, RuntimeMode, SignalSide
from pm_bot.execution.factory import build_execution_adapter, describe_execution_configuration
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.polymarket_live import (
    PolymarketLiveExecutionAdapter,
    describe_live_execution_configuration,
    resolve_polymarket_credentials,
)
from pm_bot.adapters.polymarket.geoblock_client import GeoblockStatus


class FakeLiveClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.created_orders: list[object] = []
        self.posted_orders: list[tuple[object, object, bool]] = []
        self.cancelled: list[str] = []
        self.api_creds = None

    def create_order(self, order_args: object, options: object | None = None) -> object:
        self.created_orders.append(order_args)
        return {"signed": order_args, "options": options}

    def post_order(self, order: object, orderType: object, post_only: bool = False) -> object:
        self.posted_orders.append((order, orderType, post_only))
        return {"orderID": f"live-{len(self.posted_orders)}"}

    def cancel(self, order_id: str) -> object:
        self.cancelled.append(order_id)
        return {"cancelled": order_id}

    def create_or_derive_api_creds(self, nonce: int | None = None) -> object:
        return {
            "api_key": f"derived-key-{nonce or 0}",
            "api_secret": "derived-secret",
            "api_passphrase": "derived-passphrase",
        }

    def set_api_creds(self, creds: object) -> None:
        self.api_creds = creds


def _live_bot_settings() -> BotSettings:
    return BotSettings(
        app=AppSettings(mode=RuntimeMode.LIVE),
        categories=CategoryToggles(),
        trading=TradingSettings(),
        risk=RiskSettings(),
        polymarket=PolymarketSettings(
            allow_live_orders=True,
            derive_api_creds_if_missing=True,
            post_only_live_orders=True,
        ),
        category_configs={},
    )


def test_resolve_polymarket_credentials_requires_private_key() -> None:
    with pytest.raises(ValueError, match="POLYMARKET_PRIVATE_KEY"):
        resolve_polymarket_credentials(PolymarketSettings(), env={})


def test_describe_live_execution_configuration_surfaces_missing_dependency_and_env() -> None:
    summary = describe_live_execution_configuration(PolymarketSettings(), env={})

    assert summary["allow_live_orders"] is False
    assert summary["private_key_present"] is False
    assert summary["ready"] is False
    assert "allow_live_orders is false" in summary["issues"]


def test_build_execution_adapter_returns_paper_outside_live_mode() -> None:
    settings = BotSettings(
        app=AppSettings(mode=RuntimeMode.PAPER),
        categories=CategoryToggles(),
        trading=TradingSettings(),
        risk=RiskSettings(),
        category_configs={},
    )

    adapter = build_execution_adapter(settings=settings)

    assert isinstance(adapter, PaperExecutionAdapter)


def test_live_adapter_submits_buy_orders_and_cancels_stale() -> None:
    env = {"POLYMARKET_PRIVATE_KEY": "0xabc"}
    live_adapter = build_execution_adapter(
        settings=_live_bot_settings(),
        env=env,
        client_factory=FakeLiveClient,
    )

    assert isinstance(live_adapter, PolymarketLiveExecutionAdapter)

    intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="no-token",
        action=OrderAction.PLACE,
        side=SignalSide.BUY_NO,
        price=0.4,
        size=12.5,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc) - timedelta(seconds=20),
        notional=5.0,
    )

    order_id = asyncio.run(live_adapter.submit(intent))

    assert order_id == "live-1"
    assert live_adapter.client.created_orders[0]["token_id"] == "no-token"
    assert live_adapter.client.created_orders[0]["size"] == 12.5
    assert live_adapter.client.posted_orders[0][1] == "GTC"
    assert live_adapter.client.posted_orders[0][2] is True
    assert live_adapter.user_channel_auth.api_key == "derived-key-0"

    cancelled = asyncio.run(live_adapter.cancel_stale())

    assert cancelled == 1
    assert live_adapter.client.cancelled == ["live-1"]
    tracked = live_adapter.tracker.get("live-1")
    assert tracked is not None
    assert tracked.status.value == "canceled"


def test_live_adapter_submits_sell_orders() -> None:
    env = {"POLYMARKET_PRIVATE_KEY": "0xabc"}
    live_adapter = build_execution_adapter(
        settings=_live_bot_settings(),
        env=env,
        client_factory=FakeLiveClient,
    )

    assert isinstance(live_adapter, PolymarketLiveExecutionAdapter)

    intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.SELL_YES,
        price=0.62,
        size=8.064516,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc),
        notional=5.0,
    )

    order_id = asyncio.run(live_adapter.submit(intent))

    assert order_id == "live-1"
    assert live_adapter.client.created_orders[0]["side"] == "SELL"
    tracked = live_adapter.tracker.get("live-1")
    assert tracked is not None
    assert tracked.trade_side == "SELL"


def test_describe_execution_configuration_marks_live_adapter() -> None:
    summary = describe_execution_configuration(
        settings=_live_bot_settings(),
        env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
    )

    assert summary["mode"] == "live"
    assert summary["adapter"] == "polymarket_live"


def test_live_adapter_rejects_blocked_geography() -> None:
    with pytest.raises(ValueError, match="Live trading blocked"):
        PolymarketLiveExecutionAdapter.from_settings(
            settings=_live_bot_settings().polymarket,
            ttl_seconds=15,
            env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
            geoblock_status=GeoblockStatus(
                blocked=True,
                country="US",
                region="NY",
                ip="203.0.113.42",
            ),
            client_factory=FakeLiveClient,
        )


def test_live_adapter_updates_position_ledger_from_trade_and_marks_unrealized() -> None:
    live_adapter = build_execution_adapter(
        settings=_live_bot_settings(),
        env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
        client_factory=FakeLiveClient,
    )
    assert isinstance(live_adapter, PolymarketLiveExecutionAdapter)

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
    asyncio.run(live_adapter.submit(intent))

    positions = live_adapter.apply_user_trade_event(
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

    assert len(positions) == 1
    assert positions[0].shares == 10.0
    assert positions[0].cost_basis == 5.0

    marked = live_adapter.mark_positions_to_market(
        (
            MarketSnapshot(
                market_id="m1",
                token_id="yes-token",
                slug="btc-above",
                category=Category.CRYPTO,
                timestamp=datetime.now(tz=timezone.utc),
                resolution_time=None,
                best_bid_yes=0.6,
                best_ask_yes=0.61,
                best_bid_no=0.39,
                best_ask_no=0.4,
                last_traded_price=0.6,
                metadata={"no_token_id": "no-token"},
            ),
        )
    )

    assert len(marked) == 1
    assert live_adapter.total_unrealized_pnl() == 1.0


def test_live_adapter_drains_closed_trades_after_sell_fill() -> None:
    live_adapter = build_execution_adapter(
        settings=_live_bot_settings(),
        env={"POLYMARKET_PRIVATE_KEY": "0xabc"},
        client_factory=FakeLiveClient,
    )
    assert isinstance(live_adapter, PolymarketLiveExecutionAdapter)

    buy_intent = OrderIntent(
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
    sell_intent = OrderIntent(
        strategy_id="crypto.surface",
        category=Category.CRYPTO,
        market_id="m1",
        token_id="yes-token",
        action=OrderAction.PLACE,
        side=SignalSide.SELL_YES,
        price=0.62,
        size=10.0,
        time_in_force="GTC",
        created_at=datetime.now(tz=timezone.utc),
        notional=6.2,
    )
    asyncio.run(live_adapter.submit(buy_intent))
    asyncio.run(live_adapter.submit(sell_intent))

    live_adapter.apply_user_trade_event(
        UserTradeEvent(
            id="trade-buy",
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
    live_adapter.apply_user_trade_event(
        UserTradeEvent(
            id="trade-sell",
            type="TRADE",
            taker_order_id="live-2",
            market="m1",
            asset_id="yes-token",
            side="SELL",
            size=10.0,
            price=0.62,
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

    closed_trades = live_adapter.drain_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].realized_pnl == pytest.approx(1.2)
    assert closed_trades[0].net_pnl == pytest.approx(1.2)
