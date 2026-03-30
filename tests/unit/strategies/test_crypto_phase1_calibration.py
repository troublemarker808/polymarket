from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pm_bot.strategies.crypto.phase1.baseline import (
    get_locked_crypto_calibration_baseline_preset,
    resolve_crypto_calibration_model_configs,
)
from pm_bot.strategies.crypto.phase1.calibration import (
    build_crypto_calibration_candidates,
    format_crypto_calibration_experiment_report,
    format_crypto_calibration_report,
    generate_crypto_calibration_report,
    run_crypto_calibration_experiments,
)
from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state


def test_generate_crypto_calibration_report_writes_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "calibration"
    report = generate_crypto_calibration_report(
        train_snapshot_path=Path("tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl"),
        validation_snapshot_path=Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"),
        holdout_snapshot_path=Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl"),
        underlying_states={
            "ETH": build_underlying_state(
                underlying="ETH",
                as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
                spot_price=1850.0,
                realized_volatility=0.62,
                implied_volatility=0.71,
            )
        },
        output_dir=output_dir,
    )

    assert report.baseline_classification in {"alpha-bound", "execution-bound", "mixed"}
    assert len(report.datasets) == 3
    assert output_dir.joinpath("report.json").exists()
    assert output_dir.joinpath("markets.jsonl").exists()
    assert output_dir.joinpath("summary.md").exists()

    payload = json.loads(output_dir.joinpath("report.json").read_text(encoding="utf-8"))
    assert payload["dataset_split"]["train"].endswith("eth_runtime_ladder_window.jsonl")
    assert payload["dataset_split"]["baseline_preset"] == "crypto-calibration-baseline-20260328"
    assert payload["dataset_split"]["baseline_candidate"] == "btc-r1-s165-b35-s65"
    assert payload["locked_parameters"]
    assert "mean_barrier_miss_bps" in payload["datasets"][0]
    assert "selection_miss_count" in payload["datasets"][0]


def test_format_crypto_calibration_report_contains_core_sections(tmp_path: Path) -> None:
    report = generate_crypto_calibration_report(
        train_snapshot_path=Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"),
        validation_snapshot_path=Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl"),
        holdout_snapshot_path=Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"),
        underlying_states={
            "ETH": build_underlying_state(
                underlying="ETH",
                as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
                spot_price=1850.0,
                realized_volatility=0.62,
                implied_volatility=0.71,
            )
        },
    )

    summary = format_crypto_calibration_report(report)
    assert "Crypto Calibration Report" in summary
    assert "Locked Parameters" in summary
    assert "Dataset Reports" in summary
    assert "mean_barrier_miss_bps" in summary
    assert "mean_fusion_miss_bps" in summary


def test_run_crypto_calibration_experiments_returns_ranked_candidates(tmp_path: Path) -> None:
    report = run_crypto_calibration_experiments(
        train_snapshot_path=Path("tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl"),
        validation_snapshot_path=Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"),
        holdout_snapshot_path=Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl"),
        underlying_states={
            "ETH": build_underlying_state(
                underlying="ETH",
                as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
                spot_price=1850.0,
                realized_volatility=0.62,
                implied_volatility=0.71,
            )
        },
        output_dir=tmp_path / "experiments",
    )

    assert report.results
    assert report.results[0].aggregate_score >= report.results[-1].aggregate_score
    assert report.promotion_decision.decision == "keep_locked_baseline"
    assert report.promotion_decision.evaluated_locked_baseline is False
    assert (tmp_path / "experiments" / "experiments.json").exists()
    assert (tmp_path / "experiments" / "experiments.md").exists()


def test_run_crypto_calibration_experiments_reports_locked_baseline_gate_when_evaluated() -> None:
    report = run_crypto_calibration_experiments(
        train_snapshot_path=Path("tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl"),
        validation_snapshot_path=Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"),
        holdout_snapshot_path=Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"),
        underlying_states={
            "BTC": build_underlying_state(
                underlying="BTC",
                as_of=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
                spot_price=79000.0,
                daily_return=-0.028,
                realized_volatility=0.58,
                implied_volatility=0.66,
            ),
            "ETH": build_underlying_state(
                underlying="ETH",
                as_of=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
                spot_price=1850.0,
                realized_volatility=0.62,
                implied_volatility=0.71,
            ),
        },
        candidate_set="btc_refined",
    )

    assert report.promotion_decision.evaluated_locked_baseline is True
    assert report.promotion_decision.locked_baseline_candidate == "btc-r1-s165-b35-s65"
    assert report.promotion_decision.recommended_candidate

    summary = format_crypto_calibration_experiment_report(report)
    assert "Promotion Decision" in summary
    assert "decision:" in summary
    assert "recommended_candidate:" in summary


def test_build_crypto_calibration_candidates_supports_refined_set() -> None:
    default_candidates = build_crypto_calibration_candidates("default")
    refined_candidates = build_crypto_calibration_candidates("refined")
    btc_refined_candidates = build_crypto_calibration_candidates("btc_refined")

    assert len(refined_candidates) > len(default_candidates)
    assert refined_candidates[0].name == "baseline"
    assert len(btc_refined_candidates) > len(refined_candidates)
    assert btc_refined_candidates[1].name == "btc-r1-s175-b45-s55"


def test_locked_crypto_calibration_baseline_preset_matches_resolved_defaults() -> None:
    preset = get_locked_crypto_calibration_baseline_preset()
    resolved_preset, barrier_model_config, fusion_model_config = resolve_crypto_calibration_model_configs()

    assert resolved_preset == preset
    assert preset.candidate_name == "btc-r1-s165-b35-s65"
    assert barrier_model_config == preset.barrier_model_config
    assert fusion_model_config == preset.fusion_model_config
