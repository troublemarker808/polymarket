from __future__ import annotations

from pathlib import Path

from pm_bot.strategies.sports.phase1.reports import (
    format_sports_closing_line_report,
    format_sports_event_scorecard_report,
    format_sports_market_selection_report,
    generate_sports_closing_line_report,
    generate_sports_event_scorecard_report,
    generate_sports_market_selection_report,
)
from pm_bot.strategies.sports.phase1.final_report import (
    format_sports_final_scorecard,
    generate_sports_final_scorecard,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/sports_phase1/nba_pregame_snapshots.jsonl")


def test_generate_sports_market_selection_report_identifies_actionable_nba_subset(tmp_path: Path) -> None:
    report = generate_sports_market_selection_report(
        snapshot_path=FIXTURE_SNAPSHOTS,
        output_dir=tmp_path,
    )

    assert report.actionable_markets >= 1
    assert report.blocked_markets >= 1
    assert any(row.market_id == "nba-1" and row.action == "actionable" for row in report.rows)
    assert any(row.market_id == "nfl-1" and row.action == "blocked" for row in report.rows)
    rendered = format_sports_market_selection_report(report)
    assert "Sports Market Selection Report" in rendered
    assert (tmp_path / "sports_market_selection_report.md").exists()
    assert (tmp_path / "sports_market_selection_report.json").exists()


def test_generate_sports_closing_line_report_computes_clv_rows(tmp_path: Path) -> None:
    report = generate_sports_closing_line_report(
        snapshot_path=FIXTURE_SNAPSHOTS,
        output_dir=tmp_path,
    )

    assert report.reviewed_markets >= 1
    assert any(row.league == "nba" for row in report.rows)
    rendered = format_sports_closing_line_report(report)
    assert "Sports Closing Line Report" in rendered
    assert (tmp_path / "sports_closing_line_report.md").exists()
    assert (tmp_path / "sports_closing_line_report.json").exists()


def test_generate_sports_event_scorecard_report_summarizes_event_decision(tmp_path: Path) -> None:
    report = generate_sports_event_scorecard_report(
        snapshot_path=FIXTURE_SNAPSHOTS,
        output_dir=tmp_path,
    )

    assert report.reviewed_events >= 1
    assert any(row.recommended_action in {"proceed", "review"} for row in report.rows)
    rendered = format_sports_event_scorecard_report(report)
    assert "Sports Event Scorecard Report" in rendered
    assert (tmp_path / "sports_event_scorecard_report.md").exists()
    assert (tmp_path / "sports_event_scorecard_report.json").exists()


def test_generate_sports_final_scorecard_summarizes_readiness(tmp_path: Path) -> None:
    scorecard = generate_sports_final_scorecard(
        snapshot_path=FIXTURE_SNAPSHOTS,
        output_dir=tmp_path,
    )

    assert scorecard.recommended_action in {"proceed", "review", "pause"}
    assert scorecard.profit_focus in {"selection", "pricing", "execution"}
    assert 0.0 <= scorecard.total_profit_loss <= 3.0
    assert scorecard.tuning_actions
    rendered = format_sports_final_scorecard(scorecard)
    assert "Sports Final Scorecard" in rendered
    assert "Profit" in rendered
    assert (tmp_path / "sports_final_scorecard.md").exists()
    assert (tmp_path / "sports_final_scorecard.json").exists()
