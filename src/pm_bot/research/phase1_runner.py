"""Shared runner for Phase 1 board-specific replay jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate, Phase1RunSummary, ReplayAttributionRow
from pm_bot.core.types import Category
from pm_bot.research.engine import ResearchRunResult
from pm_bot.research.phase1_artifacts import (
    Phase1ArtifactPaths,
    build_phase1_output_dir,
    write_phase1_artifacts,
)
from pm_bot.research.replay import run_replay as _run_replay
from pm_bot.runtime.state import HaltReason, RuntimeStatus


@dataclass(slots=True, frozen=True)
class Phase1ReplayResult:
    board: Category
    run_id: str
    config_dir: str
    snapshot_path: str
    output_dir: Path
    events_path: Path
    engine_metrics_path: Path
    summary: Phase1RunSummary
    artifacts: Phase1ArtifactPaths
    replay: ResearchRunResult


async def run_phase1_replay(
    *,
    board: Category | str,
    snapshot_path: str | Path,
    config_dir: str | Path | None = None,
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    fair_values: tuple[FairValueEstimate, ...] = (),
    attribution_rows: tuple[ReplayAttributionRow, ...] = (),
) -> Phase1ReplayResult:
    normalized_board = _coerce_board(board)
    resolved_run_id = run_id or _default_run_id(normalized_board)
    resolved_config_dir = Path(config_dir) if config_dir is not None else default_phase1_config_dir(normalized_board)
    resolved_output_dir = Path(output_dir) if output_dir is not None else build_phase1_output_dir(
        normalized_board.value,
        resolved_run_id,
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    events_path = resolved_output_dir / "events.jsonl"
    engine_metrics_path = resolved_output_dir / "engine.metrics.json"
    _reset_replay_output_files(events_path=events_path, engine_metrics_path=engine_metrics_path)
    replay_result = await _run_replay(
        snapshot_path=snapshot_path,
        config_dir=str(resolved_config_dir),
        limit=limit,
        recorder_path=events_path,
        metrics_path=engine_metrics_path,
    )
    summary = _build_summary(
        replay_result=replay_result,
        board=normalized_board,
        run_id=resolved_run_id,
        config_dir=resolved_config_dir,
        snapshot_path=Path(snapshot_path),
        output_dir=resolved_output_dir,
    )
    artifacts = write_phase1_artifacts(
        summary=summary,
        fair_values=fair_values,
        attribution_rows=attribution_rows,
    )
    return Phase1ReplayResult(
        board=normalized_board,
        run_id=resolved_run_id,
        config_dir=str(resolved_config_dir),
        snapshot_path=str(Path(snapshot_path)),
        output_dir=resolved_output_dir,
        events_path=events_path,
        engine_metrics_path=engine_metrics_path,
        summary=summary,
        artifacts=artifacts,
        replay=replay_result,
    )


def default_phase1_config_dir(board: Category | str) -> Path:
    normalized_board = _coerce_board(board)
    return Path("configs") / "profiles" / f"research-{normalized_board.value}-phase1-v1"


def format_phase1_replay_result(result: Phase1ReplayResult) -> str:
    return "\n".join(
        [
            f"phase1_board={result.board.value}",
            f"run_id={result.run_id}",
            f"config_dir={result.config_dir}",
            f"snapshot_path={result.snapshot_path}",
            f"output_dir={result.output_dir}",
            f"events_path={result.events_path}",
            f"engine_metrics_path={result.engine_metrics_path}",
            f"summary_path={result.artifacts.summary_path}",
            f"metrics_path={result.artifacts.metrics_path}",
            f"fair_values_path={result.artifacts.fair_values_path}",
            f"attribution_path={result.artifacts.attribution_path}",
            f"processed_snapshots={result.replay.processed_snapshots}",
            f"signals_generated={result.replay.signals_generated}",
            f"submitted_orders={result.replay.submitted_orders}",
        ]
    )


def _coerce_board(board: Category | str) -> Category:
    if isinstance(board, Category):
        return board
    return Category(str(board))


def _default_run_id(board: Category) -> str:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{board.value}-phase1-{timestamp}"


def _build_summary(
    *,
    replay_result: ResearchRunResult,
    board: Category,
    run_id: str,
    config_dir: Path,
    snapshot_path: Path,
    output_dir: Path,
) -> Phase1RunSummary:
    dashboard = replay_result.dashboard
    return Phase1RunSummary(
        generated_at=datetime.now(tz=timezone.utc),
        board=board,
        mode=replay_result.mode,
        run_id=run_id,
        config_dir=str(config_dir),
        snapshot_path=str(snapshot_path),
        output_dir=str(output_dir),
        processed_snapshots=replay_result.processed_snapshots,
        signals_generated=replay_result.signals_generated,
        signals_rejected=replay_result.signals_rejected,
        orders_rejected=replay_result.orders_rejected,
        submitted_orders=replay_result.submitted_orders,
        events_recorded=replay_result.events_recorded,
        generated_by_strategy=dict(sorted(replay_result.generated_by_strategy.items())),
        submitted_by_strategy=dict(sorted(replay_result.submitted_by_strategy.items())),
        total_equity=dashboard.total_equity,
        today_pnl=dashboard.today_pnl,
        status=_resolve_replay_summary_status(
            mode=replay_result.mode,
            dashboard_status=dashboard.status,
            halt_reason=dashboard.halt_reason,
        ),
        halt_reason=dashboard.halt_reason.value,
    )


def _reset_replay_output_files(*, events_path: Path, engine_metrics_path: Path) -> None:
    events_path.write_text("", encoding="utf-8")
    engine_metrics_path.write_text("", encoding="utf-8")


def _resolve_replay_summary_status(
    *,
    mode: str,
    dashboard_status: RuntimeStatus,
    halt_reason: HaltReason,
) -> str:
    if mode in {"replay", "backtest"} and dashboard_status != RuntimeStatus.HALTED and halt_reason == HaltReason.NONE:
        return "completed"
    return dashboard_status.value
