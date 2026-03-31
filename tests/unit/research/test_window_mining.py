import asyncio
import json
from pathlib import Path

from pm_bot.research.window_mining import mine_fixed_windows


def _write_snapshots(path: Path) -> None:
    records = []
    for index in range(8):
        records.append(
            {
                "event_type": "market.snapshot",
                "payload": {
                    "market_id": f"m{index}",
                    "token_id": f"m{index}-yes",
                    "slug": f"m{index}",
                    "category": "crypto",
                    "timestamp": f"2026-03-23T12:0{index}:00Z",
                    "best_bid_yes": 0.4,
                    "best_ask_yes": 0.42,
                    "best_bid_no": 0.58,
                    "best_ask_no": 0.6,
                    "metadata": {"reference_yes_probability": "0.45", "no_token_id": f"m{index}-no"},
                },
            }
        )
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")


def _write_events(path: Path) -> None:
    records = [
        {
            "event_type": "order.expired",
            "payload": {
                "order_id": "paper-1",
                "updated_at": "2026-03-23T12:03:30Z",
            },
        },
        {
            "event_type": "order.canceled",
            "payload": {
                "order_id": "paper-2",
                "updated_at": "2026-03-23T12:06:10Z",
                "reason": "open_order_replaced",
            },
        },
        {
            "event_type": "order.rejected",
            "payload": {
                "created_at": "2026-03-23T12:06:20Z",
                "reason": "daily order hard limit reached",
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")


def test_mine_fixed_windows_writes_ranked_window_artifacts(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "capture.jsonl"
    event_path = tmp_path / "events.jsonl"
    output_dir = tmp_path / "windows"
    _write_snapshots(snapshot_path)
    _write_events(event_path)

    report = asyncio.run(
        mine_fixed_windows(
            snapshot_path=snapshot_path,
            event_path=event_path,
            output_dir=output_dir,
            window_snapshots=4,
            top_windows=2,
        )
    )

    assert len(report.mined_windows) == 1
    assert report.mined_windows[0].labels == ("replacement-heavy", "rejection-heavy")
    assert Path(report.summary_path).exists()
    for window in report.mined_windows:
        assert Path(window.snapshot_path).exists()
        assert Path(window.event_path).exists()
        assert window.snapshot_count == 4
        assert window.score > 0
        assert window.edge_after_cost_proxy != 0.0
        assert window.fill_density >= 0.0
        assert window.rejection_quality_penalty >= 0.0
        assert window.expiry_bucket
        assert window.btc_family_labels


def test_mine_fixed_windows_prefers_fill_bearing_windows_over_expiry_only(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "capture.jsonl"
    event_path = tmp_path / "events.jsonl"
    output_dir = tmp_path / "windows"
    records = []
    for index in range(12):
        records.append(
            {
                "event_type": "market.snapshot",
                "payload": {
                    "market_id": f"m{index}",
                    "token_id": f"m{index}-yes",
                    "slug": f"m{index}",
                    "category": "crypto",
                    "timestamp": f"2026-03-23T12:{index:02d}:00Z",
                    "best_bid_yes": 0.4,
                    "best_ask_yes": 0.42,
                    "best_bid_no": 0.58,
                    "best_ask_no": 0.6,
                    "metadata": {"reference_yes_probability": "0.45", "no_token_id": f"m{index}-no"},
                },
            }
        )
    snapshot_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    event_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "order.expired",
                        "payload": {"order_id": "paper-expiry", "updated_at": "2026-03-23T12:03:30Z"},
                    }
                ),
                json.dumps(
                    {
                        "event_type": "order.expired",
                        "payload": {"order_id": "paper-expiry-2", "updated_at": "2026-03-23T12:04:00Z"},
                    }
                ),
                json.dumps(
                    {
                        "event_type": "order.filled",
                        "payload": {"order_id": "paper-fill", "updated_at": "2026-03-23T12:09:00Z"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = asyncio.run(
        mine_fixed_windows(
            snapshot_path=snapshot_path,
            event_path=event_path,
            output_dir=output_dir,
            window_snapshots=4,
            top_windows=2,
        )
    )

    assert report.mined_windows[0].labels[0] == "fill-bearing"
    assert report.mined_windows[0].score > report.mined_windows[1].score
    assert report.mined_windows[0].edge_after_cost_proxy > report.mined_windows[1].edge_after_cost_proxy


def test_mine_fixed_windows_skips_invalid_event_timestamps(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "capture.jsonl"
    event_path = tmp_path / "events.jsonl"
    output_dir = tmp_path / "windows"
    _write_snapshots(snapshot_path)
    event_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "updated_at": "not-a-timestamp",
                            "reason": "bad-payload",
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "order.rejected",
                        "payload": {
                            "updated_at": "2026-03-23T12:06:20Z",
                            "reason": "daily order hard limit reached",
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = asyncio.run(
        mine_fixed_windows(
            snapshot_path=snapshot_path,
            event_path=event_path,
            output_dir=output_dir,
            window_snapshots=4,
            top_windows=1,
        )
    )

    assert len(report.mined_windows) == 1
    window = report.mined_windows[0]
    assert window.event_counts["order.rejected"] == 1
    assert "order.filled" not in window.event_counts
