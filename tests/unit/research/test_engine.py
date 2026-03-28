import asyncio
import json
from pathlib import Path

from pm_bot.research import format_research_summary, load_market_snapshots, run_backtest, run_replay


def _write_snapshots(path: Path) -> None:
    records = [
        {
            "market_id": "sports-1",
            "token_id": "sports-1-yes",
            "slug": "sports-1",
            "category": "sports",
            "timestamp": "2026-03-23T12:00:00Z",
            "resolution_time": "2026-03-23T16:00:00Z",
            "best_bid_yes": 0.59,
            "best_ask_yes": 0.6,
            "best_bid_no": 0.4,
            "best_ask_no": 0.41,
            "last_traded_price": 0.595,
            "metadata": {
                "model_yes_probability": "0.68",
                "start_time": "2026-03-23T14:00:00Z",
            },
        },
        {
            "market_id": "crypto-1",
            "token_id": "crypto-1-yes",
            "slug": "crypto-1",
            "category": "crypto",
            "timestamp": "2026-03-23T12:00:00Z",
            "resolution_time": "",
            "best_bid_yes": 0.5,
            "best_ask_yes": 0.6,
            "best_bid_no": 0.4,
            "best_ask_no": 0.5,
            "last_traded_price": 0.55,
            "metadata": {
                "reference_yes_probability": "0.56",
                "no_token_id": "crypto-1-no",
            },
        },
        {
            "market_id": "weather-1",
            "token_id": "weather-1-yes",
            "slug": "weather-1",
            "category": "weather",
            "timestamp": "2026-03-23T12:00:00Z",
            "resolution_time": "2026-03-24T00:00:00Z",
            "best_bid_yes": 0.71,
            "best_ask_yes": 0.72,
            "best_bid_no": 0.28,
            "best_ask_no": 0.29,
            "last_traded_price": 0.715,
            "metadata": {
                "ensemble_probabilities": "0.78,0.80,0.76",
                "forecast_run_utc": "12:00",
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")


def test_load_market_snapshots_reads_jsonl(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    _write_snapshots(snapshot_path)

    snapshots = load_market_snapshots(snapshot_path)

    assert len(snapshots) == 3
    assert snapshots[0].category.value == "sports"
    assert snapshots[1].metadata["reference_yes_probability"] == "0.56"


def test_load_market_snapshots_reads_jsonl_with_utf8_bom(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots-bom.jsonl"
    _write_snapshots(snapshot_path)
    snapshot_path.write_text(snapshot_path.read_text(encoding="utf-8"), encoding="utf-8-sig")

    snapshots = load_market_snapshots(snapshot_path)

    assert len(snapshots) == 3
    assert snapshots[2].category.value == "weather"


def test_run_replay_and_backtest_produce_summary(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    events_path = tmp_path / "events.jsonl"
    metrics_path = tmp_path / "metrics.json"
    _write_snapshots(snapshot_path)

    replay_result = asyncio.run(
        run_replay(
            snapshot_path=snapshot_path,
            config_dir="configs",
            recorder_path=events_path,
            metrics_path=metrics_path,
        )
    )
    backtest_result = asyncio.run(run_backtest(snapshot_path=snapshot_path, config_dir="configs"))

    assert replay_result.processed_snapshots == 3
    assert replay_result.submitted_orders == 3
    assert replay_result.generated_by_strategy == {
        "crypto.maker": 1,
        "sports.anchor": 1,
        "weather.ensemble": 1,
    }
    assert backtest_result.submitted_by_strategy == {
        "crypto.maker": 1,
        "sports.anchor": 1,
        "weather.ensemble": 1,
    }
    assert events_path.exists()
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["processed_snapshots"] == 3
    assert metrics["orders_submitted"] == 3


def test_format_research_summary_includes_dashboard(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "research-summary.jsonl"
    _write_snapshots(snapshot_path)
    result = asyncio.run(run_replay(snapshot_path=snapshot_path, config_dir="configs"))
    summary = format_research_summary(result)

    assert "mode=replay" in summary
    assert "runtime_dashboard" in summary
    assert "submitted_orders=3" in summary


def test_run_replay_creates_empty_event_file_even_without_events(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "empty-events.jsonl"
    events_path = tmp_path / "events.jsonl"
    metrics_path = tmp_path / "metrics.json"
    records = [
        {
            "market_id": "crypto-1",
            "token_id": "crypto-1-yes",
            "slug": "crypto-1",
            "category": "crypto",
            "timestamp": "2026-03-23T12:00:00Z",
            "resolution_time": "",
            "best_bid_yes": 0.50,
            "best_ask_yes": 0.51,
            "best_bid_no": 0.49,
            "best_ask_no": 0.50,
            "last_traded_price": 0.505,
            "metadata": {
                "reference_yes_probability": "0.505",
                "no_token_id": "crypto-1-no",
            },
        }
    ]
    snapshot_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    result = asyncio.run(
        run_replay(
            snapshot_path=snapshot_path,
            config_dir="configs",
            recorder_path=events_path,
            metrics_path=metrics_path,
        )
    )

    assert result.processed_snapshots == 1
    assert events_path.exists()
    assert events_path.read_text(encoding="utf-8") == ""
