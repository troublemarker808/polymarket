from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path

import pytest

from pm_bot.core.research_types import Phase1RunSummary
from pm_bot.core.types import Category
from pm_bot.research.engine import ResearchRunResult
from pm_bot.research.phase1_artifacts import Phase1ArtifactPaths
from pm_bot.research.phase1_runner import Phase1ReplayResult
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategies.weather.phase1.replay import (
    compute_weather_phase1_fair_values,
    run_weather_phase1_replay,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")
FIXTURE_RUNS = Path("tests/fixtures/weather_phase1/forecast_runs.json")
FIXTURE_SKILLS = Path("tests/fixtures/weather_phase1/model_skill_cases.json")


def test_compute_weather_phase1_fair_values_returns_supported_threshold_estimates() -> None:
    forecast_payloads = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    skill_payloads = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]

    fair_values = compute_weather_phase1_fair_values(
        snapshot_path=FIXTURE_SNAPSHOTS,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
    )

    assert tuple(item.market_id for item in fair_values) == ("w70", "w75")
    assert all(item.model_id == "weather.phase1.fused" for item in fair_values)
    assert all("threshold_probability" in item.supporting_values for item in fair_values)


def test_run_weather_phase1_replay_rewrites_attribution_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    forecast_payloads = json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"]
    skill_payloads = json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"]

    async def _fake_run_phase1_replay(**kwargs) -> Phase1ReplayResult:
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        events_path = output_dir / "events.jsonl"
        events_path.write_text(
            json.dumps(
                {
                    "event_type": "trade.closed",
                    "payload": {"market_id": "w70", "realized_pnl": 0.45},
                },
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        engine_metrics_path = output_dir / "engine.metrics.json"
        engine_metrics_path.write_text(json.dumps({"processed_snapshots": 2}, ensure_ascii=True), encoding="utf-8")
        summary = Phase1RunSummary(
            generated_at=datetime.fromisoformat("2026-03-28T00:00:00+00:00"),
            board=Category.WEATHER,
            mode="replay",
            run_id="weather-phase1-test",
            config_dir="configs/profiles/research-weather-phase1-v1",
            snapshot_path=str(FIXTURE_SNAPSHOTS),
            output_dir=str(output_dir),
            processed_snapshots=2,
            signals_generated=1,
            signals_rejected=0,
            orders_rejected=0,
            submitted_orders=1,
            events_recorded=2,
            generated_by_strategy={"weather.threshold": 1},
            submitted_by_strategy={"weather.threshold": 1},
            total_equity=1000.0,
            today_pnl=0.0,
            status="running",
            halt_reason="none",
        )
        artifacts = Phase1ArtifactPaths(
            output_dir=output_dir,
            summary_path=output_dir / "summary.md",
            metrics_path=output_dir / "metrics.json",
            fair_values_path=output_dir / "fair_values.jsonl",
            attribution_path=output_dir / "attribution.jsonl",
        )
        for path in (artifacts.summary_path, artifacts.metrics_path, artifacts.fair_values_path, artifacts.attribution_path):
            path.write_text("", encoding="utf-8")
        return Phase1ReplayResult(
            board=Category.WEATHER,
            run_id="weather-phase1-test",
            config_dir="configs/profiles/research-weather-phase1-v1",
            snapshot_path=str(FIXTURE_SNAPSHOTS),
            output_dir=output_dir,
            events_path=events_path,
            engine_metrics_path=engine_metrics_path,
            summary=summary,
            artifacts=artifacts,
            replay=ResearchRunResult(
                mode="replay",
                processed_snapshots=2,
                signals_generated=1,
                signals_rejected=0,
                orders_rejected=0,
                submitted_orders=1,
                events_recorded=2,
                generated_by_strategy={"weather.threshold": 1},
                submitted_by_strategy={"weather.threshold": 1},
                dashboard=_dashboard(),
            ),
        )

    monkeypatch.setattr("pm_bot.strategies.weather.phase1.replay.run_phase1_replay", _fake_run_phase1_replay)

    asyncio.run(
        run_weather_phase1_replay(
            snapshot_path=FIXTURE_SNAPSHOTS,
            forecast_payloads=forecast_payloads,
            skill_payloads=skill_payloads,
            output_dir=tmp_path / "weather-phase1-run",
            run_id="weather-phase1-test",
        )
    )

    attribution_rows = [
        json.loads(line)
        for line in (tmp_path / "weather-phase1-run" / "attribution.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert attribution_rows
    assert attribution_rows[0]["market_id"] == "w70"
    assert attribution_rows[0]["realized_pnl"] == 0.45


def _dashboard() -> DashboardState:
    return DashboardState(
        total_equity=1000.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )
