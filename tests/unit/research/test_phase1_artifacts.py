from datetime import UTC, datetime
import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate, Phase1RunSummary, ReplayAttributionRow
from pm_bot.core.types import Category
from pm_bot.research.phase1_artifacts import write_phase1_artifacts


def test_write_phase1_artifacts_writes_summary_metrics_and_jsonl(tmp_path: Path) -> None:
    summary = Phase1RunSummary(
        generated_at=datetime(2026, 3, 28, tzinfo=UTC),
        board=Category.CRYPTO,
        mode="replay",
        run_id="crypto-phase1-test",
        config_dir="configs/profiles/research-crypto-phase1-v1",
        snapshot_path="data/research/sample_snapshots.jsonl",
        output_dir=str(tmp_path),
        processed_snapshots=10,
        signals_generated=2,
        signals_rejected=1,
        orders_rejected=0,
        submitted_orders=2,
        events_recorded=12,
        generated_by_strategy={"crypto.surface": 2},
        submitted_by_strategy={"crypto.surface": 2},
        total_equity=1000.5,
        today_pnl=0.5,
        status="running",
        halt_reason="none",
    )
    fair_values = (
        FairValueEstimate(
            market_id="crypto-1",
            category=Category.CRYPTO,
            fair_probability=0.44,
            confidence=0.72,
            observed_probability=0.39,
            model_id="barrier.v1",
        ),
    )
    attribution_rows = (
        ReplayAttributionRow(
            market_id="crypto-1",
            category=Category.CRYPTO,
            strategy_id="crypto.surface",
            predicted_edge_bps=320.0,
            realized_pnl=1.25,
        ),
    )

    paths = write_phase1_artifacts(
        summary=summary,
        fair_values=fair_values,
        attribution_rows=attribution_rows,
    )

    assert paths.summary_path.exists()
    assert paths.metrics_path.exists()
    assert paths.fair_values_path.exists()
    assert paths.attribution_path.exists()
    assert "# Phase 1 Summary" in paths.summary_path.read_text(encoding="utf-8")

    metrics = json.loads(paths.metrics_path.read_text(encoding="utf-8"))
    assert metrics["board"] == "crypto"
    assert metrics["processed_snapshots"] == 10

    fair_value_rows = _read_jsonl(paths.fair_values_path)
    attribution_rows_out = _read_jsonl(paths.attribution_path)
    assert fair_value_rows[0]["market_id"] == "crypto-1"
    assert fair_value_rows[0]["category"] == "crypto"
    assert attribution_rows_out[0]["strategy_id"] == "crypto.surface"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
