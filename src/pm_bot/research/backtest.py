"""Backtest entry point."""

from __future__ import annotations

from pathlib import Path

from pm_bot.research.engine import ResearchRunResult, run_backtest as _run_backtest


async def run_backtest(
    snapshot_path: str | Path,
    *,
    config_dir: str = "configs",
    limit: int | None = None,
    recorder_path: str | Path | None = None,
    metrics_path: str | Path | None = None,
) -> ResearchRunResult:
    """Run a file-backed backtest over normalized snapshot inputs."""

    return await _run_backtest(
        snapshot_path=snapshot_path,
        config_dir=config_dir,
        limit=limit,
        recorder_path=recorder_path,
        metrics_path=metrics_path,
    )
