from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SNAPSHOTS = ROOT / "data" / "research" / "sample_snapshots.jsonl"
CRYPTO_PHASE2_SNAPSHOTS = ROOT / "tests" / "fixtures" / "crypto_phase1" / "ladder_snapshots.jsonl"
CRYPTO_PHASE2_UNDERLYING = ROOT / "tests" / "fixtures" / "crypto_phase1" / "underlying_state.json"
CRYPTO_CALIBRATION_TRAIN = ROOT / "tests" / "fixtures" / "crypto_phase2" / "eth_runtime_ladder_window.jsonl"
CRYPTO_CALIBRATION_VALIDATION = ROOT / "tests" / "fixtures" / "crypto_phase2" / "compare_snapshots.jsonl"
CRYPTO_CALIBRATION_HOLDOUT = ROOT / "tests" / "fixtures" / "crypto_phase1" / "ladder_snapshots.jsonl"


def test_cli_replay_runs_against_sample_snapshots(tmp_path: Path) -> None:
    events_path = tmp_path / "replay-events.jsonl"

    completed = _run_cli(
        "replay",
        "--config-dir",
        "configs",
        "--snapshot-path",
        str(SAMPLE_SNAPSHOTS),
        "--event-path",
        str(events_path),
    )

    assert "mode=replay" in completed.stdout
    assert "processed_snapshots=10" in completed.stdout
    assert "runtime_dashboard" in completed.stdout
    assert events_path.exists()


def test_cli_backtest_runs_against_sample_snapshots() -> None:
    completed = _run_cli(
        "backtest",
        "--config-dir",
        "configs",
        "--snapshot-path",
        str(SAMPLE_SNAPSHOTS),
    )

    assert "mode=backtest" in completed.stdout
    assert "processed_snapshots=10" in completed.stdout
    assert "submitted_orders=" in completed.stdout


def test_cli_phase1_replay_runs_against_sample_snapshots(tmp_path: Path) -> None:
    output_dir = tmp_path / "phase1-crypto"

    completed = _run_cli(
        "phase1-replay",
        "--board",
        "crypto",
        "--snapshot-path",
        str(SAMPLE_SNAPSHOTS),
        "--output-dir",
        str(output_dir),
    )

    assert "phase1_board=crypto" in completed.stdout
    assert "processed_snapshots=10" in completed.stdout
    assert (output_dir / "events.jsonl").exists()
    assert (output_dir / "engine.metrics.json").exists()
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "metrics.json").exists()


def test_cli_crypto_phase2_replay_runs_against_crypto_phase1_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "phase2-crypto"

    completed = _run_cli(
        "crypto-phase2-replay",
        "--snapshot-path",
        str(CRYPTO_PHASE2_SNAPSHOTS),
        "--underlying-state-path",
        str(CRYPTO_PHASE2_UNDERLYING),
        "--output-dir",
        str(output_dir),
        "--limit",
        "20",
    )

    assert "phase2_board=crypto" in completed.stdout
    assert "fair_values=3" in completed.stdout
    assert (output_dir / "events.jsonl").exists()
    assert (output_dir / "engine.metrics.json").exists()
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "metrics.json").exists()


def test_cli_crypto_calibration_report_runs_against_fixed_split(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-calibration"

    completed = _run_cli(
        "crypto-calibration-report",
        "--train-snapshot-path",
        str(CRYPTO_CALIBRATION_TRAIN),
        "--validation-snapshot-path",
        str(CRYPTO_CALIBRATION_VALIDATION),
        "--holdout-snapshot-path",
        str(CRYPTO_CALIBRATION_HOLDOUT),
        "--underlying-state-path",
        str(CRYPTO_PHASE2_UNDERLYING),
        "--output-dir",
        str(output_dir),
    )

    assert "Crypto Calibration Report" in completed.stdout
    assert "baseline_classification" in completed.stdout
    assert (output_dir / "report.json").exists()
    assert (output_dir / "markets.jsonl").exists()
    assert (output_dir / "summary.md").exists()


def test_cli_crypto_calibration_experiments_runs_against_fixed_split(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-calibration-experiments"

    completed = _run_cli(
        "crypto-calibration-experiments",
        "--train-snapshot-path",
        str(CRYPTO_CALIBRATION_TRAIN),
        "--validation-snapshot-path",
        str(CRYPTO_CALIBRATION_VALIDATION),
        "--holdout-snapshot-path",
        str(CRYPTO_CALIBRATION_HOLDOUT),
        "--underlying-state-path",
        str(CRYPTO_PHASE2_UNDERLYING),
        "--output-dir",
        str(output_dir),
    )

    assert "Crypto Calibration Experiments" in completed.stdout
    assert "aggregate_score" in completed.stdout
    assert (output_dir / "experiments.json").exists()
    assert (output_dir / "experiments.md").exists()


def test_cli_crypto_calibration_experiments_supports_btc_refined_candidate_set(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-calibration-btc-experiments"

    completed = _run_cli(
        "crypto-calibration-experiments",
        "--candidate-set",
        "btc_refined",
        "--train-snapshot-path",
        str(CRYPTO_CALIBRATION_TRAIN),
        "--validation-snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "btc_runtime_ladder_window.jsonl"),
        "--holdout-snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "compare_snapshots.jsonl"),
        "--underlying-state-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "runtime_underlying_states.json"),
        "--output-dir",
        str(output_dir),
    )

    assert "btc-r1-s175-b45-s55" in completed.stdout
    assert "aggregate_score" in completed.stdout
    assert (output_dir / "experiments.json").exists()
    assert (output_dir / "experiments.md").exists()


def test_cli_crypto_market_selection_report_runs_against_btc_runtime_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-market-selection"

    completed = _run_cli(
        "crypto-market-selection-report",
        "--snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "btc_runtime_ladder_window.jsonl"),
        "--underlying-state-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "runtime_underlying_states.json"),
        "--output-dir",
        str(output_dir),
    )

    assert "Crypto Market Selection Report" in completed.stdout
    assert "recommended_action: tradable" in completed.stdout
    assert (output_dir / "report.json").exists()
    assert (output_dir / "summary.md").exists()


def test_cli_crypto_market_selection_report_supports_event_overlay(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-market-selection-overlay"

    completed = _run_cli(
        "crypto-market-selection-report",
        "--snapshot-path",
        str(ROOT / "data" / "research" / "family-export-phase2-v35-btc-reach" / "snapshots.jsonl"),
        "--event-path",
        str(ROOT / "data" / "research" / "family-export-phase2-v35-btc-reach" / "events.jsonl"),
        "--underlying-state-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "runtime_underlying_states.json"),
        "--output-dir",
        str(output_dir),
    )

    assert "execution_no_fill" in completed.stdout
    assert "recommended_action: watch_only" in completed.stdout
    assert (output_dir / "report.json").exists()


def test_cli_crypto_window_family_report_runs_against_crypto_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-window-family"

    completed = _run_cli(
        "crypto-window-family-report",
        "--snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase1" / "ladder_snapshots.jsonl"),
        "--output-dir",
        str(output_dir),
    )

    assert "Crypto Window Family Report" in completed.stdout
    assert "bucket_count=" in completed.stdout
    assert (output_dir / "summary.md").exists()


def test_cli_crypto_family_export_filters_family_subset(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-family-export"

    completed = _run_cli(
        "crypto-family-export",
        "--snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase1" / "ladder_snapshots.jsonl"),
        "--output-dir",
        str(output_dir),
        "--underlying",
        "ETH",
        "--event-family",
        "dip",
    )

    assert "Crypto Family Export" in completed.stdout
    assert "retained_snapshot_count=3" in completed.stdout
    assert (output_dir / "snapshots.jsonl").exists()
    assert (output_dir / "summary.md").exists()


def test_cli_crypto_signal_report_runs_against_phase2_events(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-signal-report"

    completed = _run_cli(
        "crypto-signal-report",
        "--event-path",
        str(ROOT / "data" / "research" / "fixed-window-phase2-v35-btc-reach-v7" / "train" / "baseline" / "events.jsonl"),
        "--snapshot-path",
        str(ROOT / "data" / "research" / "family-export-phase2-v35-btc-reach" / "snapshots.jsonl"),
        "--output-dir",
        str(output_dir),
    )

    assert "Crypto Signal Report" in completed.stdout
    assert "signal_count:" in completed.stdout
    assert (output_dir / "report.json").exists()
    assert (output_dir / "summary.md").exists()


def test_cli_fixed_window_experiments_supports_phase2_with_underlying_states(tmp_path: Path) -> None:
    output_dir = tmp_path / "fixed-window-phase2"

    completed = _run_cli(
        "run-fixed-window-experiments",
        "--snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "compare_snapshots.jsonl"),
        "--config-dir",
        "configs/profiles/paper-crypto-phase2-v1",
        "--underlying-state-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "runtime_underlying_states.json"),
        "--output-dir",
        str(output_dir),
    )

    assert "baseline_classification=" in completed.stdout
    assert (output_dir / "summary.md").exists()


def test_cli_crypto_phase2_suite_runs_end_to_end(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-phase2-suite"

    completed = _run_cli(
        "crypto-phase2-suite",
        "--snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "btc_runtime_ladder_window.jsonl"),
        "--underlying-state-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "runtime_underlying_states.json"),
        "--output-dir",
        str(output_dir),
    )

    assert "Crypto Phase 2 Suite" in completed.stdout
    assert "skip_series_keys: none" in completed.stdout
    assert (output_dir / "suite.json").exists()
    assert (output_dir / "suite.md").exists()
    assert (output_dir / "selection" / "summary.md").exists()
    assert (output_dir / "replay-unfiltered" / "metrics.json").exists()
    assert (output_dir / "replay-filtered" / "metrics.json").exists()


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pm_bot", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
