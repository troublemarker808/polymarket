import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.sports.phase1.attribution import build_sports_attribution_rows


def test_build_sports_attribution_rows_reads_trade_closed_events(tmp_path: Path) -> None:
    fair_values = (
        FairValueEstimate(
            market_id="nba-1",
            category=Category.SPORTS,
            fair_probability=0.526,
            confidence=0.75,
            half_life_seconds=3600,
            observed_probability=0.48,
            model_id="sports.phase1.pregame",
            rationale_tags=("pregame_anchor", "feature_adjusted"),
            supporting_values={"context_adjusted_edge_bps": 345.0},
        ),
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        json.dumps(
            {
                "event_type": "trade.closed",
                "payload": {
                    "market_id": "nba-1",
                    "strategy_id": "sports.anchor",
                    "realized_pnl": 0.8,
                },
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    rows = build_sports_attribution_rows(fair_values=fair_values, event_path=event_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.market_id == "nba-1"
    assert row.realized_pnl == 0.8
    assert round(row.predicted_edge_bps, 1) == 460.0
    assert round(row.execution_error_bps, 1) == 115.0
