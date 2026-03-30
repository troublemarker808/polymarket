from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.weather.phase1.learning_report import (
    build_weather_learning_report,
    format_weather_learning_report,
)


def test_build_weather_learning_report_summarizes_recurring_focus(tmp_path: Path) -> None:
    scorecard_a = tmp_path / "weather-a.json"
    scorecard_b = tmp_path / "weather-b.json"
    scorecard_c = tmp_path / "weather-c.json"
    scorecard_a.write_text(
        json.dumps(
            {
                "profit_focus": "settlement",
                "secondary_profit_focus": "selection",
                "tradable_subset_status": "ready",
                "settlement_audit_status": "fragile",
                "selection_loss": 0.2,
                "settlement_loss": 0.55,
                "execution_loss": 0.18,
                "average_monotonicity_gap_bps": 180.0,
                "actionable_markets": 5,
                "blocked_markets": 5,
                "reasons": ["strip monotonicity gap exceeds weather threshold"],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    scorecard_b.write_text(
        json.dumps(
            {
                "profit_focus": "settlement",
                "secondary_profit_focus": "selection",
                "tradable_subset_status": "ready",
                "settlement_audit_status": "fragile",
                "selection_loss": 0.22,
                "settlement_loss": 0.5,
                "execution_loss": 0.2,
                "average_monotonicity_gap_bps": 170.0,
                "actionable_markets": 4,
                "blocked_markets": 6,
                "reasons": ["strip monotonicity gap exceeds weather threshold"],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    scorecard_c.write_text(
        json.dumps(
            {
                "profit_focus": "selection",
                "secondary_profit_focus": "settlement",
                "tradable_subset_status": "thin",
                "settlement_audit_status": "ready",
                "selection_loss": 0.45,
                "settlement_loss": 0.25,
                "execution_loss": 0.2,
                "average_monotonicity_gap_bps": 120.0,
                "actionable_markets": 2,
                "blocked_markets": 8,
                "reasons": ["no actionable weather markets"],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_weather_learning_report(scorecard_paths=[scorecard_a, scorecard_b, scorecard_c])

    assert report.run_count == 3
    assert report.recurring_focuses == ("settlement",)
    assert report.recurring_secondary_focuses == ("selection",)
    assert report.recommended_next_experiment == "settlement"
    assert report.recurring_loss_ranking[0] == "settlement"
    assert report.average_monotonicity_gap_bps > 150
    assert "review settlement mapping" in format_weather_learning_report(report)
