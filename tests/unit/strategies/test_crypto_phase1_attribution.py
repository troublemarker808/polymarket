import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.crypto.phase1.attribution import build_crypto_attribution_rows


def test_build_crypto_attribution_rows_reads_trade_closed_events(tmp_path: Path) -> None:
    fair_values = (
        FairValueEstimate(
            market_id="eth-dip-1000",
            category=Category.CRYPTO,
            fair_probability=0.19,
            confidence=0.75,
            half_life_seconds=3600,
            observed_probability=0.11,
            model_id="crypto.phase1.fused",
            rationale_tags=("barrier_model", "surface_consistency"),
            supporting_values={"net_edge_bps": 685.0},
        ),
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        json.dumps(
            {
                "event_type": "trade.closed",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "strategy_id": "crypto.surface",
                    "realized_pnl": 1.25,
                },
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    rows = build_crypto_attribution_rows(fair_values=fair_values, event_path=event_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.market_id == "eth-dip-1000"
    assert row.realized_pnl == 1.25
    assert round(row.predicted_edge_bps, 2) == 800.0
    assert round(row.execution_error_bps, 2) == 115.0
