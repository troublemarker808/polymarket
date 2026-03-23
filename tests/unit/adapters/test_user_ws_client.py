import json
from datetime import UTC, datetime

from pm_bot.adapters.polymarket.user_ws_client import (
    UserOrderEvent,
    UserTradeEvent,
    parse_user_channel_payload,
)


def test_parse_user_channel_payload_order_event() -> None:
    raw = json.dumps(
        {
            "event_type": "order",
            "id": "0xorder",
            "owner": "owner-1",
            "market": "0xmarket",
            "asset_id": "yes-token",
            "side": "BUY",
            "order_owner": "owner-1",
            "original_size": "10",
            "size_matched": "3",
            "price": "0.57",
            "associate_trades": ["trade-1"],
            "outcome": "YES",
            "type": "UPDATE",
            "created_at": "1672290687",
            "expiration": "1672290787",
            "order_type": "GTC",
            "status": "LIVE",
            "maker_address": "0x1234",
            "timestamp": "1672290701",
        }
    )

    events = parse_user_channel_payload(raw)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, UserOrderEvent)
    assert event.id == "0xorder"
    assert event.size_matched == 3.0
    assert event.associate_trades == ("trade-1",)
    assert event.timestamp == datetime.fromtimestamp(1672290701, tz=UTC)


def test_parse_user_channel_payload_trade_event() -> None:
    raw = json.dumps(
        {
            "event_type": "trade",
            "type": "TRADE",
            "id": "trade-1",
            "taker_order_id": "0xtaker",
            "market": "0xmarket",
            "asset_id": "yes-token",
            "side": "BUY",
            "size": "10",
            "price": "0.57",
            "fee_rate_bps": "0",
            "status": "MATCHED",
            "matchtime": "1672290701",
            "last_update": "1672290701",
            "outcome": "YES",
            "owner": "owner-1",
            "trade_owner": "owner-1",
            "maker_address": "0x1234",
            "transaction_hash": "",
            "bucket_index": 0,
            "maker_orders": [
                {
                    "order_id": "0xmaker",
                    "owner": "owner-1",
                    "maker_address": "0x5678",
                    "matched_amount": "4",
                    "price": "0.57",
                    "fee_rate_bps": "0",
                    "asset_id": "yes-token",
                    "outcome": "YES",
                    "side": "SELL",
                }
            ],
            "trader_side": "TAKER",
            "timestamp": "1672290701",
        }
    )

    events = parse_user_channel_payload(raw)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, UserTradeEvent)
    assert event.taker_order_id == "0xtaker"
    assert event.size == 10.0
    assert len(event.maker_orders) == 1
    assert event.maker_orders[0].matched_amount == 4.0
