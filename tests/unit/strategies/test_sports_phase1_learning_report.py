from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.sports.phase1.learning_report import (
    build_sports_learning_report,
    format_sports_learning_report,
)


def test_build_sports_learning_report_summarizes_recurring_focus(tmp_path: Path) -> None:
    scorecard_a = tmp_path / "sports-a.json"
    scorecard_b = tmp_path / "sports-b.json"
    scorecard_c = tmp_path / "sports-c.json"
    scorecard_a.write_text(
        json.dumps(
            {
                "profit_focus": "selection",
                "secondary_profit_focus": "pricing",
                "tradable_subset_status": "thin",
                "closing_line_status": "ready",
                "selection_loss": 0.55,
                "pricing_loss": 0.25,
                "execution_loss": 0.2,
                "average_clv_bps": 2.0,
                "actionable_markets": 2,
                "blocked_markets": 6,
                "reasons": ["review events dominate actionable events"],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    scorecard_b.write_text(
        json.dumps(
            {
                "profit_focus": "selection",
                "secondary_profit_focus": "pricing",
                "tradable_subset_status": "thin",
                "closing_line_status": "fragile",
                "selection_loss": 0.5,
                "pricing_loss": 0.35,
                "execution_loss": 0.22,
                "average_clv_bps": -1.0,
                "actionable_markets": 3,
                "blocked_markets": 7,
                "reasons": ["review events dominate actionable events"],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    scorecard_c.write_text(
        json.dumps(
            {
                "profit_focus": "pricing",
                "secondary_profit_focus": "selection",
                "tradable_subset_status": "ready",
                "closing_line_status": "fragile",
                "selection_loss": 0.3,
                "pricing_loss": 0.4,
                "execution_loss": 0.18,
                "average_clv_bps": -3.0,
                "actionable_markets": 5,
                "blocked_markets": 5,
                "reasons": ["closing line moved against sports fair value"],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_sports_learning_report(scorecard_paths=[scorecard_a, scorecard_b, scorecard_c])

    assert report.run_count == 3
    assert report.recurring_focuses == ("selection",)
    assert report.recurring_secondary_focuses == ("pricing",)
    assert report.recommended_next_experiment == "selection"
    assert report.recurring_loss_ranking[0] == "selection"
    assert report.average_actionable_market_ratio < 0.5
    assert "tighten sports market selection" in format_sports_learning_report(report)
