from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pm_bot.research import run_replay
from pm_bot.research.replay_determinism import _research_result_to_dict


def test_replay_baseline_matches_expected_outputs(tmp_path: Path) -> None:
    fixture_dir = Path("tests/fixtures/replay_baseline")
    snapshot_path = fixture_dir / "snapshots.jsonl"
    expected_metrics = json.loads((fixture_dir / "expected.metrics.json").read_text(encoding="utf-8"))
    expected_summary = json.loads((fixture_dir / "expected.summary.json").read_text(encoding="utf-8"))
    expected_events = [
        json.loads(line)
        for line in (fixture_dir / "expected.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    events_path = tmp_path / "actual.events.jsonl"
    metrics_path = tmp_path / "actual.metrics.json"
    result = asyncio.run(
        run_replay(
            snapshot_path=snapshot_path,
            config_dir="configs",
            recorder_path=events_path,
            metrics_path=metrics_path,
        )
    )

    actual_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    actual_summary = json.loads(json.dumps(_research_result_to_dict(result), ensure_ascii=True))
    actual_events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert actual_metrics == expected_metrics
    assert actual_summary == expected_summary
    assert actual_events == expected_events
