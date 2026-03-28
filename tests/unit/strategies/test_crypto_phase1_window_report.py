import json
from pathlib import Path

from pm_bot.strategies.crypto.phase1.window_report import (
    export_crypto_family_window,
    generate_crypto_window_family_report,
)


def test_generate_crypto_window_family_report_buckets_by_underlying_family_and_series(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    event_path = tmp_path / "events.jsonl"
    output_dir = tmp_path / "report"
    snapshot_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "market.snapshot",
                        "payload": {
                            "market_id": "btc-1",
                            "token_id": "btc-1-yes",
                            "slug": "will-bitcoin-dip-to-50000",
                            "category": "crypto",
                            "timestamp": "2026-03-23T12:00:00Z",
                            "resolution_time": "2026-12-31T00:00:00Z",
                            "best_bid_yes": 0.4,
                            "best_ask_yes": 0.42,
                            "best_bid_no": 0.58,
                            "best_ask_no": 0.6,
                            "best_bid_yes_size": 10,
                            "best_ask_yes_size": 10,
                            "best_bid_no_size": 10,
                            "best_ask_no_size": 10,
                            "tick_size": 0.01,
                            "min_order_size": 1,
                            "last_traded_price": 0.41,
                            "last_trade_side": "buy",
                            "last_trade_size": 2,
                            "yes_bid_levels": [],
                            "yes_ask_levels": [],
                            "no_bid_levels": [],
                            "no_ask_levels": [],
                            "liquidity_score": 0.9,
                            "metadata": {
                                "question": "Will Bitcoin dip to $50,000 by December 31, 2026?",
                                "event_slug": "btc-yearly-dip",
                                "no_token_id": "btc-1-no",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "market.snapshot",
                        "payload": {
                            "market_id": "btc-2",
                            "token_id": "btc-2-yes",
                            "slug": "will-bitcoin-dip-to-45000",
                            "category": "crypto",
                            "timestamp": "2026-03-23T12:01:00Z",
                            "resolution_time": "2026-12-31T00:00:00Z",
                            "best_bid_yes": 0.3,
                            "best_ask_yes": 0.32,
                            "best_bid_no": 0.68,
                            "best_ask_no": 0.7,
                            "best_bid_yes_size": 10,
                            "best_ask_yes_size": 10,
                            "best_bid_no_size": 10,
                            "best_ask_no_size": 10,
                            "tick_size": 0.01,
                            "min_order_size": 1,
                            "last_traded_price": 0.31,
                            "last_trade_side": "buy",
                            "last_trade_size": 2,
                            "yes_bid_levels": [],
                            "yes_ask_levels": [],
                            "no_bid_levels": [],
                            "no_ask_levels": [],
                            "liquidity_score": 0.9,
                            "metadata": {
                                "question": "Will Bitcoin dip to $45,000 by December 31, 2026?",
                                "event_slug": "btc-yearly-dip",
                                "no_token_id": "btc-2-no",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "market.snapshot",
                        "payload": {
                            "market_id": "eth-1",
                            "token_id": "eth-1-yes",
                            "slug": "will-ethereum-reach-5000",
                            "category": "crypto",
                            "timestamp": "2026-03-23T12:02:00Z",
                            "resolution_time": "2026-12-31T00:00:00Z",
                            "best_bid_yes": 0.2,
                            "best_ask_yes": 0.22,
                            "best_bid_no": 0.78,
                            "best_ask_no": 0.8,
                            "best_bid_yes_size": 10,
                            "best_ask_yes_size": 10,
                            "best_bid_no_size": 10,
                            "best_ask_no_size": 10,
                            "tick_size": 0.01,
                            "min_order_size": 1,
                            "last_traded_price": 0.21,
                            "last_trade_side": "buy",
                            "last_trade_size": 2,
                            "yes_bid_levels": [],
                            "yes_ask_levels": [],
                            "no_bid_levels": [],
                            "no_ask_levels": [],
                            "liquidity_score": 0.9,
                            "metadata": {
                                "question": "Will Ethereum reach $5,000 by December 31, 2026?",
                                "event_slug": "eth-yearly-reach",
                                "no_token_id": "eth-1-no",
                            },
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "order.submitted", "payload": {"market_id": "btc-1"}}),
                json.dumps({"event_type": "order.expired", "payload": {"market_id": "btc-2"}}),
                json.dumps({"event_type": "order.submitted", "payload": {"market_id": "eth-1"}}),
            ]
        ),
        encoding="utf-8",
    )

    report = generate_crypto_window_family_report(
        snapshot_path=snapshot_path,
        event_path=event_path,
        output_dir=output_dir,
    )

    assert report.normalized_snapshot_count == 3
    assert report.skipped_snapshot_count == 0
    assert len(report.buckets) == 2
    assert report.buckets[0].underlying == "BTC"
    assert report.buckets[0].event_family == "dip"
    assert report.buckets[0].unique_markets == 2
    assert report.buckets[0].event_counts["order.submitted"] == 1
    assert report.buckets[0].event_counts["order.expired"] == 1
    assert report.buckets[1].underlying == "ETH"
    assert Path(report.summary_path).exists()


def test_export_crypto_family_window_filters_snapshots_and_events(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    event_path = tmp_path / "events.jsonl"
    output_dir = tmp_path / "export"
    snapshot_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "market.snapshot",
                        "payload": {
                            "market_id": "btc-reach",
                            "token_id": "btc-reach-yes",
                            "slug": "will-bitcoin-reach-150000",
                            "category": "crypto",
                            "timestamp": "2026-03-23T12:00:00Z",
                            "resolution_time": "2026-12-31T00:00:00Z",
                            "best_bid_yes": 0.2,
                            "best_ask_yes": 0.22,
                            "best_bid_no": 0.78,
                            "best_ask_no": 0.8,
                            "best_bid_yes_size": 10,
                            "best_ask_yes_size": 10,
                            "best_bid_no_size": 10,
                            "best_ask_no_size": 10,
                            "tick_size": 0.01,
                            "min_order_size": 1,
                            "last_traded_price": 0.21,
                            "last_trade_side": "buy",
                            "last_trade_size": 2,
                            "yes_bid_levels": [],
                            "yes_ask_levels": [],
                            "no_bid_levels": [],
                            "no_ask_levels": [],
                            "liquidity_score": 0.9,
                            "metadata": {
                                "question": "Will Bitcoin reach $150,000 by December 31, 2026?",
                                "event_slug": "btc-reach-ladder",
                                "no_token_id": "btc-reach-no",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "market.snapshot",
                        "payload": {
                            "market_id": "eth-dip",
                            "token_id": "eth-dip-yes",
                            "slug": "will-ethereum-dip-to-1000",
                            "category": "crypto",
                            "timestamp": "2026-03-23T12:01:00Z",
                            "resolution_time": "2026-12-31T00:00:00Z",
                            "best_bid_yes": 0.3,
                            "best_ask_yes": 0.32,
                            "best_bid_no": 0.68,
                            "best_ask_no": 0.7,
                            "best_bid_yes_size": 10,
                            "best_ask_yes_size": 10,
                            "best_bid_no_size": 10,
                            "best_ask_no_size": 10,
                            "tick_size": 0.01,
                            "min_order_size": 1,
                            "last_traded_price": 0.31,
                            "last_trade_side": "buy",
                            "last_trade_size": 2,
                            "yes_bid_levels": [],
                            "yes_ask_levels": [],
                            "no_bid_levels": [],
                            "no_ask_levels": [],
                            "liquidity_score": 0.9,
                            "metadata": {
                                "question": "Will Ethereum dip to $1,000 by December 31, 2026?",
                                "event_slug": "eth-dip-ladder",
                                "no_token_id": "eth-dip-no",
                            },
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "order.submitted", "payload": {"market_id": "btc-reach"}}),
                json.dumps({"event_type": "order.submitted", "payload": {"market_id": "eth-dip"}}),
            ]
        ),
        encoding="utf-8",
    )

    result = export_crypto_family_window(
        snapshot_path=snapshot_path,
        event_path=event_path,
        output_dir=output_dir,
        underlying="BTC",
        event_family="reach",
    )

    assert result.retained_snapshot_count == 1
    assert result.retained_market_count == 1
    assert result.retained_event_count == 1
    assert Path(result.filtered_snapshot_path).exists()
    assert Path(result.filtered_event_path).exists()
