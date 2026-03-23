from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SNAPSHOTS = ROOT / "data" / "research" / "sample_snapshots.jsonl"


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


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pm_bot", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
