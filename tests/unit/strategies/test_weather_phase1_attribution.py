import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.weather.phase1.attribution import build_weather_attribution_rows


def test_build_weather_attribution_rows_reads_trade_closed_events(tmp_path: Path) -> None:
    fair_values = (
        FairValueEstimate(
            market_id="w70",
            category=Category.WEATHER,
            fair_probability=0.8464,
            confidence=0.77,
            half_life_seconds=7200,
            observed_probability=0.79,
            model_id="weather.phase1.fused",
            rationale_tags=("forecast_distribution", "threshold_probability", "strip_consistency"),
            supporting_values={
                "threshold_probability": 0.8963,
                "strip_probability": 0.73,
            },
        ),
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        json.dumps(
            {
                "event_type": "trade.closed",
                "payload": {
                    "market_id": "w70",
                    "strategy_id": "weather.threshold",
                    "realized_pnl": 0.55,
                },
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    rows = build_weather_attribution_rows(fair_values=fair_values, event_path=event_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.market_id == "w70"
    assert row.realized_pnl == 0.55
    assert round(row.predicted_edge_bps, 1) == 564.0
    assert round(row.execution_error_bps, 1) == -499.0
    assert round(row.timing_error_bps, 1) == 1663.0
