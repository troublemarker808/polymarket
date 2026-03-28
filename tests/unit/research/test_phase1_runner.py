from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from pm_bot.research.engine import ResearchRunResult
from pm_bot.research.phase1_runner import default_phase1_config_dir, run_phase1_replay
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus


def test_default_phase1_config_dir_uses_board_specific_profile() -> None:
    assert default_phase1_config_dir("crypto") == Path("configs/profiles/research-crypto-phase1-v1")
    assert default_phase1_config_dir("sports") == Path("configs/profiles/research-sports-phase1-v1")
    assert default_phase1_config_dir("weather") == Path("configs/profiles/research-weather-phase1-v1")


def test_run_phase1_replay_writes_expected_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def _fake_run_replay(
        snapshot_path: str | Path,
        *,
        config_dir: str = "configs",
        limit: int | None = None,
        recorder_path: str | Path | None = None,
        metrics_path: str | Path | None = None,
    ) -> ResearchRunResult:
        assert str(config_dir).endswith("research-crypto-phase1-v1")
        assert limit == 7
        assert recorder_path is not None
        assert metrics_path is not None
        Path(recorder_path).write_text(
            json.dumps({"event_type": "signal.generated", "payload": {"strategy_id": "crypto.surface"}}) + "\n",
            encoding="utf-8",
        )
        Path(metrics_path).write_text(
            json.dumps({"processed_snapshots": 1, "orders_submitted": 1}, ensure_ascii=True),
            encoding="utf-8",
        )
        return ResearchRunResult(
            mode="replay",
            processed_snapshots=1,
            signals_generated=1,
            signals_rejected=0,
            orders_rejected=0,
            submitted_orders=1,
            events_recorded=1,
            generated_by_strategy={"crypto.surface": 1},
            submitted_by_strategy={"crypto.surface": 1},
            dashboard=_dashboard(),
        )

    monkeypatch.setattr("pm_bot.research.phase1_runner._run_replay", _fake_run_replay)

    result = asyncio.run(
        run_phase1_replay(
            board="crypto",
            snapshot_path=tmp_path / "snapshots.jsonl",
            limit=7,
            output_dir=tmp_path / "phase1-run",
            run_id="crypto-phase1-test",
        )
    )

    assert result.output_dir == tmp_path / "phase1-run"
    assert result.events_path.exists()
    assert result.engine_metrics_path.exists()
    assert result.artifacts.summary_path.exists()
    assert result.artifacts.metrics_path.exists()
    assert result.artifacts.fair_values_path.exists()
    assert result.artifacts.attribution_path.exists()
    assert Path(result.config_dir).name == "research-crypto-phase1-v1"

    metrics = json.loads(result.artifacts.metrics_path.read_text(encoding="utf-8"))
    assert metrics["board"] == "crypto"
    assert metrics["processed_snapshots"] == 1
    assert metrics["status"] == "completed"


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
        last_data_success_at=datetime(2026, 3, 28, tzinfo=UTC),
        last_data_error=None,
        consecutive_data_failures=0,
        issue_codes=(),
    )
