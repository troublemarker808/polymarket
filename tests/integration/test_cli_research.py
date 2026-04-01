from __future__ import annotations

import json
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
    assert "Promotion Decision" in completed.stdout
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


def test_cli_mine_fixed_windows_is_deterministic_on_same_fixture(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    event_path = tmp_path / "events.jsonl"
    output_dir = tmp_path / "mined"
    snapshot_path.write_text(
        "\n".join(
            [
                "{\"event_type\":\"market.snapshot\",\"payload\":{\"market_id\":\"m1\",\"token_id\":\"m1-yes\",\"slug\":\"will-bitcoin-dip-1\",\"category\":\"crypto\",\"timestamp\":\"2026-03-23T12:00:00Z\",\"resolution_time\":\"2026-06-01T00:00:00Z\",\"best_bid_yes\":0.40,\"best_ask_yes\":0.42,\"best_bid_no\":0.58,\"best_ask_no\":0.60,\"metadata\":{\"tag_slugs\":\"bitcoin,price\"}}}",
                "{\"event_type\":\"market.snapshot\",\"payload\":{\"market_id\":\"m2\",\"token_id\":\"m2-yes\",\"slug\":\"will-bitcoin-dip-2\",\"category\":\"crypto\",\"timestamp\":\"2026-03-23T12:01:00Z\",\"resolution_time\":\"2026-06-01T00:00:00Z\",\"best_bid_yes\":0.40,\"best_ask_yes\":0.42,\"best_bid_no\":0.58,\"best_ask_no\":0.60,\"metadata\":{\"tag_slugs\":\"bitcoin,price\"}}}",
                "{\"event_type\":\"market.snapshot\",\"payload\":{\"market_id\":\"m3\",\"token_id\":\"m3-yes\",\"slug\":\"will-bitcoin-dip-3\",\"category\":\"crypto\",\"timestamp\":\"2026-03-23T12:02:00Z\",\"resolution_time\":\"2026-06-01T00:00:00Z\",\"best_bid_yes\":0.40,\"best_ask_yes\":0.42,\"best_bid_no\":0.58,\"best_ask_no\":0.60,\"metadata\":{\"tag_slugs\":\"bitcoin,price\"}}}",
                "{\"event_type\":\"market.snapshot\",\"payload\":{\"market_id\":\"m4\",\"token_id\":\"m4-yes\",\"slug\":\"will-bitcoin-dip-4\",\"category\":\"crypto\",\"timestamp\":\"2026-03-23T12:03:00Z\",\"resolution_time\":\"2026-06-01T00:00:00Z\",\"best_bid_yes\":0.40,\"best_ask_yes\":0.42,\"best_bid_no\":0.58,\"best_ask_no\":0.60,\"metadata\":{\"tag_slugs\":\"bitcoin,price\"}}}",
                "{\"event_type\":\"market.snapshot\",\"payload\":{\"market_id\":\"m5\",\"token_id\":\"m5-yes\",\"slug\":\"will-bitcoin-dip-5\",\"category\":\"crypto\",\"timestamp\":\"2026-03-23T12:04:00Z\",\"resolution_time\":\"2026-06-01T00:00:00Z\",\"best_bid_yes\":0.40,\"best_ask_yes\":0.42,\"best_bid_no\":0.58,\"best_ask_no\":0.60,\"metadata\":{\"tag_slugs\":\"bitcoin,price\"}}}",
                "{\"event_type\":\"market.snapshot\",\"payload\":{\"market_id\":\"m6\",\"token_id\":\"m6-yes\",\"slug\":\"will-bitcoin-dip-6\",\"category\":\"crypto\",\"timestamp\":\"2026-03-23T12:05:00Z\",\"resolution_time\":\"2026-06-01T00:00:00Z\",\"best_bid_yes\":0.40,\"best_ask_yes\":0.42,\"best_bid_no\":0.58,\"best_ask_no\":0.60,\"metadata\":{\"tag_slugs\":\"bitcoin,price\"}}}"
            ]
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        "\n".join(
            [
                "{\"event_type\":\"order.filled\",\"payload\":{\"updated_at\":\"2026-03-23T12:02:30Z\"}}",
                "{\"event_type\":\"trade.closed\",\"payload\":{\"updated_at\":\"2026-03-23T12:02:40Z\",\"net_pnl\":0.15}}",
                "{\"event_type\":\"order.rejected\",\"payload\":{\"updated_at\":\"2026-03-23T12:04:10Z\",\"reason\":\"daily order hard limit reached\"}}"
            ]
        ),
        encoding="utf-8",
    )

    first = _run_cli(
        "mine-fixed-windows",
        "--snapshot-path",
        str(snapshot_path),
        "--event-path",
        str(event_path),
        "--output-dir",
        str(output_dir),
        "--window-snapshots",
        "4",
        "--top-windows",
        "2",
    )
    second = _run_cli(
        "mine-fixed-windows",
        "--snapshot-path",
        str(snapshot_path),
        "--event-path",
        str(event_path),
        "--output-dir",
        str(output_dir),
        "--window-snapshots",
        "4",
        "--top-windows",
        "2",
    )

    assert first.stdout == second.stdout
    assert "windows_found=2" in first.stdout
    assert "window_scores=" in first.stdout


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
    assert "blocked_series_keys: none" in completed.stdout
    assert (output_dir / "suite.json").exists()
    assert (output_dir / "suite.md").exists()
    assert (output_dir / "selection" / "summary.md").exists()
    assert (output_dir / "replay-unfiltered" / "metrics.json").exists()
    assert (output_dir / "replay-filtered" / "metrics.json").exists()


def test_cli_crypto_phase2_final_report_prints_btc_promotion_gate_payload(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-phase2-final-report"

    completed = _run_cli(
        "crypto-phase2-final-report",
        "--snapshot-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "btc_runtime_ladder_window.jsonl"),
        "--underlying-state-path",
        str(ROOT / "tests" / "fixtures" / "crypto_phase2" / "runtime_underlying_states.json"),
        "--output-dir",
        str(output_dir),
    )

    assert "promotion_decision:" in completed.stdout
    assert "promotion_stage_label:" in completed.stdout
    assert "route_stage_acceptance_decision:" in completed.stdout
    assert "## Route Stage Gates" in completed.stdout
    assert "promotion_max_single_loss_pnl:" in completed.stdout
    assert "promotion_max_top3_loss_concentration_ratio:" in completed.stdout
    assert "observed_max_single_loss_pnl:" in completed.stdout
    assert "observed_top3_loss_concentration_ratio:" in completed.stdout
    assert (output_dir / "final_scorecard.json").exists()
    scorecard = json.loads((output_dir / "final_scorecard.json").read_text(encoding="utf-8"))
    assert "route_stage_acceptance_decision" in scorecard
    assert "route_stage_statuses" in scorecard
    assert "route_stage_blockers" in scorecard
    assert "promotion_max_single_loss_pnl" in scorecard
    assert "promotion_max_top3_loss_concentration_ratio" in scorecard
    assert "observed_max_single_loss_pnl" in scorecard
    assert "observed_top3_loss_concentration_ratio" in scorecard


def test_cli_autoresearch_compare_ranks_candidates_from_bundle_paths(tmp_path: Path) -> None:
    metrics_a = tmp_path / "metrics_a.json"
    metrics_b = tmp_path / "metrics_b.json"
    scorecard_a = tmp_path / "scorecard_a.json"
    scorecard_b = tmp_path / "scorecard_b.json"
    for path, variant_id in ((metrics_a, "candidate-a"), (metrics_b, "candidate-b")):
        path.write_text(
            json.dumps(
                {
                    "signals_generated": 10,
                    "orders_submitted": 8,
                    "orders_rejected": 0,
                    "orders_filled": 6,
                    "orders_partially_filled": 0,
                    "orders_expired": 0,
                    "orders_canceled": 0,
                    "trades_closed": 2,
                    "fill_rate": 0.75,
                    "cancel_rate": 0.0,
                    "avg_fill_price_vs_mid_bps": 1.0,
                    "market_data_failures": 0,
                    "window_set_id": "btc-window-v1",
                    "variant_id": variant_id,
                    "evidence_tier": "paper",
                    "loop_stage_set": "btc-closure-v1",
                }
            ),
            encoding="utf-8",
        )
    scorecard_a.write_text(
        json.dumps(
            {
                "route_stage_acceptance_decision": "proceed",
                "route_stage_failed_stages": [],
                "promotion_decision": "proceed",
                "promotion_stage_label": "shadow validation",
                "promotion_blocking_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    scorecard_b.write_text(
        json.dumps(
            {
                "route_stage_acceptance_decision": "review",
                "route_stage_failed_stages": ["close_out_quality"],
                "promotion_decision": "review",
                "promotion_stage_label": "paper available",
                "promotion_blocking_reasons": ["insufficient_closed_trade_count"],
            }
        ),
        encoding="utf-8",
    )

    completed = _run_cli(
        "autoresearch-compare",
        "--bundle-paths",
        str(metrics_a),
        str(metrics_b),
        "--promotion-scorecard-paths",
        str(scorecard_a),
        str(scorecard_b),
    )

    assert "Autoresearch Candidate Ranking" in completed.stdout
    assert "loop_stage_set: btc-closure-v1" in completed.stdout
    assert "candidate-a" in completed.stdout
    assert "candidate-b" in completed.stdout


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pm_bot", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
