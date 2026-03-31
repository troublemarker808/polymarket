import asyncio
import json
from pathlib import Path

import pytest

from pm_bot.config.loader import load_settings_from_directory
from pm_bot.research.experiments import (
    ExperimentRunArtifact,
    _default_candidates,
    _pick_validation_winner,
    run_fixed_window_experiments,
)


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
            "timestamp": "2026-03-23T12:05:00Z",
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
            "timestamp": "2026-03-23T12:10:00Z",
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


def test_run_fixed_window_experiments_writes_split_artifacts(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "window.jsonl"
    output_dir = tmp_path / "experiments"
    _write_snapshots(snapshot_path)

    report = asyncio.run(
        run_fixed_window_experiments(
            snapshot_path=snapshot_path,
            config_dir="configs",
            output_dir=output_dir,
        )
    )

    assert report.experiment_matrix[0].name == "baseline"
    assert [candidate.name for candidate in report.experiment_matrix[1:]] == [
        "maker_ttl_plus5_failure_plus20",
        "maker_spread_plus25_failure_plus20",
        "maker_failure_plus20_requote_plus50",
    ]
    assert tuple(split.snapshot_count for split in report.dataset_splits) == (1, 1, 1)
    assert report.finalists[0] == "baseline"
    assert Path(report.summary_path).exists()
    assert len(report.train_results) >= 1
    assert len(report.validation_results) >= 1
    assert len(report.holdout_results) >= 1
    for artifact in report.train_results + report.validation_results + report.holdout_results:
        assert Path(artifact.metrics_path).exists()
        assert Path(artifact.event_path).exists()
        assert Path(artifact.autoresearch_path).exists()


def test_run_fixed_window_experiments_sorts_snapshots_before_splitting(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "window-out-of-order.jsonl"
    output_dir = tmp_path / "experiments-sorted"
    records = [
        {
            "market_id": "m2",
            "token_id": "m2-yes",
            "slug": "m2",
            "category": "crypto",
            "timestamp": "2026-03-23T12:10:00Z",
            "best_bid_yes": 0.5,
            "best_ask_yes": 0.6,
            "best_bid_no": 0.4,
            "best_ask_no": 0.5,
            "metadata": {"reference_yes_probability": "0.56", "no_token_id": "m2-no"},
        },
        {
            "market_id": "m1",
            "token_id": "m1-yes",
            "slug": "m1",
            "category": "sports",
            "timestamp": "2026-03-23T12:00:00Z",
            "resolution_time": "2026-03-23T16:00:00Z",
            "best_bid_yes": 0.59,
            "best_ask_yes": 0.6,
            "best_bid_no": 0.4,
            "best_ask_no": 0.41,
            "metadata": {"model_yes_probability": "0.68", "start_time": "2026-03-23T14:00:00Z"},
        },
        {
            "market_id": "m3",
            "token_id": "m3-yes",
            "slug": "m3",
            "category": "weather",
            "timestamp": "2026-03-23T12:20:00Z",
            "resolution_time": "2026-03-24T00:00:00Z",
            "best_bid_yes": 0.71,
            "best_ask_yes": 0.72,
            "best_bid_no": 0.28,
            "best_ask_no": 0.29,
            "metadata": {"ensemble_probabilities": "0.78,0.80,0.76", "forecast_run_utc": "12:00"},
        },
    ]
    snapshot_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    report = asyncio.run(
        run_fixed_window_experiments(
            snapshot_path=snapshot_path,
            config_dir="configs",
            output_dir=output_dir,
        )
    )

    split_ranges = {split.name: (split.started_at, split.ended_at) for split in report.dataset_splits}
    assert split_ranges["train"][0] <= split_ranges["train"][1]
    assert split_ranges["validation"][0] <= split_ranges["validation"][1]
    assert split_ranges["holdout"][0] <= split_ranges["holdout"][1]
    assert split_ranges["train"][1] <= split_ranges["validation"][0]
    assert split_ranges["validation"][1] <= split_ranges["holdout"][0]


def test_run_fixed_window_experiments_promotes_mined_windows_when_event_log_is_available(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "window-eventful.jsonl"
    event_path = tmp_path / "window-eventful.events.jsonl"
    output_dir = tmp_path / "eventful-experiments"
    records = []
    for index in range(18):
        records.append(
            {
                "market_id": f"crypto-{index}",
                "token_id": f"crypto-{index}-yes",
                "slug": f"crypto-{index}",
                "category": "crypto",
                "timestamp": f"2026-03-23T12:{index:02d}:00Z",
                "best_bid_yes": 0.5,
                "best_ask_yes": 0.52,
                "best_bid_no": 0.48,
                "best_ask_no": 0.5,
                "last_traded_price": 0.51,
                "metadata": {
                    "reference_yes_probability": "0.53",
                    "no_token_id": f"crypto-{index}-no",
                },
            }
        )
    snapshot_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    event_path.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "order.filled", "payload": {"updated_at": "2026-03-23T12:02:30Z"}}),
                json.dumps({"event_type": "trade.closed", "payload": {"closed_at": "2026-03-23T12:02:40Z", "net_pnl": 0.1}}),
                json.dumps({"event_type": "order.canceled", "payload": {"updated_at": "2026-03-23T12:08:30Z", "reason": "open_order_replaced"}}),
                json.dumps({"event_type": "order.rejected", "payload": {"created_at": "2026-03-23T12:08:40Z", "reason": "daily order hard limit reached"}}),
                json.dumps({"event_type": "order.partially_filled", "payload": {"updated_at": "2026-03-23T12:14:30Z"}}),
                json.dumps({"event_type": "trade.closed", "payload": {"closed_at": "2026-03-23T12:14:45Z", "net_pnl": 0.2}}),
            ]
        ),
        encoding="utf-8",
    )

    report = asyncio.run(
        run_fixed_window_experiments(
            snapshot_path=snapshot_path,
            event_path=event_path,
            config_dir="configs",
            output_dir=output_dir,
            window_snapshots=4,
            top_windows=3,
        )
    )

    assert report.window_selection_mode == "eventful_mined"
    assert Path(report.mining_summary_path or "").exists()
    assert tuple(split.source for split in report.dataset_splits) == ("mined_window", "mined_window", "mined_window")
    assert tuple(split.source_name for split in report.dataset_splits) == ("window-01", "window-02", "window-03")
    assert all(split.score is not None for split in report.dataset_splits)
    assert all(Path(split.source_snapshot_path).exists() for split in report.dataset_splits)
    assert all(split.expiry_bucket for split in report.dataset_splits)
    assert all(split.btc_family_labels for split in report.dataset_splits)


def test_pick_validation_winner_rejects_candidate_that_only_reduces_activity() -> None:
    baseline = ExperimentRunArtifact(
        split_name="validation",
        candidate_name="baseline",
        overrides=(),
        classification="execution-bound",
        score=-4.0,
        metrics_path="baseline.metrics.json",
        event_path="baseline.events.jsonl",
        autoresearch_path="baseline.autoresearch.md",
        signals_generated=3,
        orders_submitted=3,
        orders_rejected=0,
        orders_filled=0,
        orders_expired=2,
        orders_canceled=0,
        fill_rate=0.0,
        cancel_rate=0.6667,
        dominant_rejection_reasons=(),
    )
    challenger = ExperimentRunArtifact(
        split_name="validation",
        candidate_name="maker_spread_plus25_failure_plus20",
        overrides=(("strategy.maker.min_spread_bps", 150),),
        classification="capacity-bound",
        score=0.0,
        metrics_path="candidate.metrics.json",
        event_path="candidate.events.jsonl",
        autoresearch_path="candidate.autoresearch.md",
        signals_generated=0,
        orders_submitted=0,
        orders_rejected=0,
        orders_filled=0,
        orders_expired=0,
        orders_canceled=0,
        fill_rate=0.0,
        cancel_rate=0.0,
        dominant_rejection_reasons=(),
    )

    winner, reason = _pick_validation_winner([baseline, challenger])

    assert winner == "baseline"
    assert "collapsing activity" in reason


def test_pick_validation_winner_uses_promotion_score_not_raw_score() -> None:
    baseline = ExperimentRunArtifact(
        split_name="validation",
        candidate_name="baseline",
        overrides=(),
        classification="execution-bound",
        score=-2.0,
        metrics_path="baseline.metrics.json",
        event_path="baseline.events.jsonl",
        autoresearch_path="baseline.autoresearch.md",
        signals_generated=4,
        orders_submitted=4,
        orders_rejected=0,
        orders_filled=0,
        orders_expired=2,
        orders_canceled=0,
        fill_rate=0.0,
        cancel_rate=0.5,
        dominant_rejection_reasons=(),
    )
    challenger = ExperimentRunArtifact(
        split_name="validation",
        candidate_name="maker_spread_plus25_failure_plus20",
        overrides=(("strategy.maker.min_spread_bps", 150),),
        classification="execution-bound",
        score=0.0,
        metrics_path="candidate.metrics.json",
        event_path="candidate.events.jsonl",
        autoresearch_path="candidate.autoresearch.md",
        signals_generated=2,
        orders_submitted=2,
        orders_rejected=0,
        orders_filled=0,
        orders_expired=2,
        orders_canceled=0,
        fill_rate=0.0,
        cancel_rate=1.0,
        dominant_rejection_reasons=(),
    )

    winner, reason = _pick_validation_winner([baseline, challenger])

    assert winner == "baseline"
    assert "promotion score" in reason


def test_default_candidates_support_phase2_settings() -> None:
    settings = load_settings_from_directory("configs/profiles/paper-crypto-phase2-v1")

    candidates = _default_candidates(classification="execution-bound", settings=settings)

    assert [candidate.name for candidate in candidates] == [
        "phase2_resolution_ttl_plus45",
        "phase2_resolution_edge_minus25_ttl_plus45",
        "phase2_maker_aggr_plus075_ttl_plus15",
        "phase2_resolution_edge_minus25_aggr_plus075_ttl_plus45",
    ]


def test_run_fixed_window_experiments_requires_underlying_state_for_phase2(tmp_path: Path) -> None:
    output_dir = tmp_path / "phase2-experiments"

    with pytest.raises(ValueError, match="underlying_state_path"):
        asyncio.run(
            run_fixed_window_experiments(
                snapshot_path=Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl"),
                config_dir="configs/profiles/paper-crypto-phase2-v1",
                output_dir=output_dir,
            )
        )
