"""Unified research pipeline for the current Crypto Phase 2 module."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig, CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.selection import (
    CryptoMarketSelectionReport,
    generate_crypto_market_selection_report,
    recommended_skip_series_keys,
)
from pm_bot.strategies.crypto.phase2.replay import run_crypto_phase2_replay


WORKING_BARRIER_MODEL_CONFIG = CryptoBarrierModelConfig(steepness=1.65)
WORKING_FUSION_MODEL_CONFIG = CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65)


@dataclass(slots=True, frozen=True)
class CryptoPhase2ReplayDigest:
    label: str
    output_dir: str
    signals_generated: int
    submitted_orders: int
    events_recorded: int
    today_pnl: float
    total_equity: float
    status: str


@dataclass(slots=True, frozen=True)
class CryptoPhase2SuiteResult:
    generated_at: datetime
    snapshot_path: str
    selection_output_dir: str
    selection_skip_series_keys: tuple[str, ...]
    unfiltered_replay: CryptoPhase2ReplayDigest
    filtered_replay: CryptoPhase2ReplayDigest


async def run_crypto_phase2_suite(
    *,
    snapshot_path: str | Path,
    underlying_states: dict[str, CryptoUnderlyingState],
    config_dir: str | Path = "configs/profiles/research-crypto-phase2-v1",
    limit: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> CryptoPhase2SuiteResult:
    resolved_output_dir = Path(output_dir) if output_dir is not None else Path("data/research") / "crypto-phase2-suite"
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    selection_output_dir = resolved_output_dir / "selection"
    selection_report = generate_crypto_market_selection_report(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        output_dir=selection_output_dir,
        barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
        fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
    )
    skip_series_keys = recommended_skip_series_keys(selection_report)

    unfiltered_output_dir = resolved_output_dir / "replay-unfiltered"
    filtered_output_dir = resolved_output_dir / "replay-filtered"
    suite_run_id = run_id or "crypto-phase2-suite"

    await run_crypto_phase2_replay(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        config_dir=config_dir,
        limit=limit,
        output_dir=unfiltered_output_dir,
        run_id=f"{suite_run_id}-unfiltered",
        barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
        fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
        apply_series_filter=False,
    )
    await run_crypto_phase2_replay(
        snapshot_path=snapshot_path,
        underlying_states=underlying_states,
        config_dir=config_dir,
        limit=limit,
        output_dir=filtered_output_dir,
        run_id=f"{suite_run_id}-filtered",
        barrier_model_config=WORKING_BARRIER_MODEL_CONFIG,
        fusion_model_config=WORKING_FUSION_MODEL_CONFIG,
        apply_series_filter=True,
    )

    result = CryptoPhase2SuiteResult(
        generated_at=datetime.now(tz=timezone.utc),
        snapshot_path=str(Path(snapshot_path)),
        selection_output_dir=str(selection_output_dir),
        selection_skip_series_keys=skip_series_keys,
        unfiltered_replay=_load_replay_digest("unfiltered", unfiltered_output_dir),
        filtered_replay=_load_replay_digest("filtered", filtered_output_dir),
    )
    write_crypto_phase2_suite_result(result=result, output_dir=resolved_output_dir)
    return result


def write_crypto_phase2_suite_result(*, result: CryptoPhase2SuiteResult, output_dir: str | Path) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "suite.json").write_text(
        json.dumps(_normalize(asdict(result)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "suite.md").write_text(format_crypto_phase2_suite_result(result), encoding="utf-8")


def format_crypto_phase2_suite_result(result: CryptoPhase2SuiteResult) -> str:
    lines = [
        "# Crypto Phase 2 Suite",
        "",
        f"- generated_at: {result.generated_at.isoformat()}",
        f"- snapshot_path: {result.snapshot_path}",
        f"- selection_output_dir: {result.selection_output_dir}",
        f"- skip_series_keys: {', '.join(result.selection_skip_series_keys) if result.selection_skip_series_keys else 'none'}",
        "",
        "## Replays",
        "",
    ]
    for replay in (result.unfiltered_replay, result.filtered_replay):
        lines.extend(
            [
                f"### {replay.label}",
                "",
                f"- output_dir: {replay.output_dir}",
                f"- signals_generated: {replay.signals_generated}",
                f"- submitted_orders: {replay.submitted_orders}",
                f"- events_recorded: {replay.events_recorded}",
                f"- today_pnl: {replay.today_pnl:.6f}",
                f"- total_equity: {replay.total_equity:.6f}",
                f"- status: {replay.status}",
                "",
            ]
        )
    lines.extend(
        [
            "## Delta",
            "",
            f"- signals_delta: {result.filtered_replay.signals_generated - result.unfiltered_replay.signals_generated}",
            f"- orders_delta: {result.filtered_replay.submitted_orders - result.unfiltered_replay.submitted_orders}",
            f"- pnl_delta: {result.filtered_replay.today_pnl - result.unfiltered_replay.today_pnl:.6f}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _load_replay_digest(label: str, output_dir: Path) -> CryptoPhase2ReplayDigest:
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    return CryptoPhase2ReplayDigest(
        label=label,
        output_dir=str(output_dir),
        signals_generated=int(metrics.get("signals_generated", 0)),
        submitted_orders=int(metrics.get("submitted_orders", 0)),
        events_recorded=int(metrics.get("events_recorded", 0)),
        today_pnl=float(metrics.get("today_pnl", 0.0)),
        total_equity=float(metrics.get("total_equity", 0.0)),
        status=str(metrics.get("status", "")),
    )


def _normalize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
