"""Replay entry point."""

from __future__ import annotations

from pathlib import Path

from pm_bot.research.engine import ResearchRunResult, run_replay as _run_replay


async def run_replay(
    snapshot_path: str | Path,
    *,
    config_dir: str = "configs",
    limit: int | None = None,
    recorder_path: str | Path | None = None,
    metrics_path: str | Path | None = None,
) -> ResearchRunResult:
    """Replay recorded market snapshots through the live router in paper mode."""

    return await _run_replay(
        snapshot_path=snapshot_path,
        config_dir=config_dir,
        limit=limit,
        recorder_path=recorder_path,
        metrics_path=metrics_path,
    )
