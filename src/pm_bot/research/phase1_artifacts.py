"""Artifact helpers for Phase 1 board-specific research runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any

from pm_bot.core.research_types import FairValueEstimate, Phase1RunSummary, ReplayAttributionRow


@dataclass(slots=True, frozen=True)
class Phase1ArtifactPaths:
    output_dir: Path
    summary_path: Path
    metrics_path: Path
    fair_values_path: Path
    attribution_path: Path


def build_phase1_output_dir(
    board: str,
    run_id: str,
    *,
    root_dir: str | Path = "data/research/phase1",
) -> Path:
    return Path(root_dir) / board / run_id


def write_phase1_artifacts(
    *,
    summary: Phase1RunSummary,
    fair_values: tuple[FairValueEstimate, ...] = (),
    attribution_rows: tuple[ReplayAttributionRow, ...] = (),
) -> Phase1ArtifactPaths:
    output_dir = Path(summary.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = Phase1ArtifactPaths(
        output_dir=output_dir,
        summary_path=output_dir / "summary.md",
        metrics_path=output_dir / "metrics.json",
        fair_values_path=output_dir / "fair_values.jsonl",
        attribution_path=output_dir / "attribution.jsonl",
    )
    paths.summary_path.write_text(format_phase1_summary(summary), encoding="utf-8")
    paths.metrics_path.write_text(
        json.dumps(_normalize(summary), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    _write_jsonl(paths.fair_values_path, fair_values)
    _write_jsonl(paths.attribution_path, attribution_rows)
    return paths


def format_phase1_summary(summary: Phase1RunSummary) -> str:
    lines = [
        "# Phase 1 Summary",
        "",
        f"- generated_at: {summary.generated_at.isoformat()}",
        f"- board: {summary.board.value}",
        f"- mode: {summary.mode}",
        f"- run_id: {summary.run_id}",
        f"- config_dir: {summary.config_dir}",
        f"- snapshot_path: {summary.snapshot_path}",
        f"- output_dir: {summary.output_dir}",
        "",
        "## Core Metrics",
        "",
        f"- processed_snapshots: {summary.processed_snapshots}",
        f"- signals_generated: {summary.signals_generated}",
        f"- signals_rejected: {summary.signals_rejected}",
        f"- orders_rejected: {summary.orders_rejected}",
        f"- submitted_orders: {summary.submitted_orders}",
        f"- events_recorded: {summary.events_recorded}",
        "",
        "## Dashboard",
        "",
        f"- total_equity: {summary.total_equity}",
        f"- today_pnl: {summary.today_pnl}",
        f"- status: {summary.status}",
        f"- halt_reason: {summary.halt_reason}",
        "",
        "## Strategy Breakdown",
        "",
        f"- generated_by_strategy: {_format_counter(summary.generated_by_strategy)}",
        f"- submitted_by_strategy: {_format_counter(summary.submitted_by_strategy)}",
    ]
    return "\n".join(lines)


def _write_jsonl(path: Path, rows: tuple[Any, ...]) -> None:
    payload = "\n".join(
        json.dumps(_normalize(row), ensure_ascii=True)
        for row in rows
    )
    path.write_text((payload + "\n") if payload else "", encoding="utf-8")


def _format_counter(counter: dict[str, int]) -> str:
    if not counter:
        return ""
    return ",".join(f"{key}:{value}" for key, value in sorted(counter.items()))


def _normalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    return value
