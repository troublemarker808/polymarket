from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.weather.phase1.reports import (
    format_weather_market_selection_report,
    format_weather_run_scorecard_report,
    format_weather_settlement_audit_report,
    generate_weather_market_selection_report,
    generate_weather_run_scorecard_report,
    generate_weather_settlement_audit_report,
)
from pm_bot.strategies.weather.phase1.final_report import (
    format_weather_final_scorecard,
    generate_weather_final_scorecard,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/weather_phase1/threshold_snapshots.jsonl")
FIXTURE_RUNS = Path("tests/fixtures/weather_phase1/forecast_runs.json")
FIXTURE_SKILLS = Path("tests/fixtures/weather_phase1/model_skill_cases.json")


def test_generate_weather_market_selection_report_identifies_actionable_threshold_subset(tmp_path: Path) -> None:
    report = generate_weather_market_selection_report(
        snapshot_path=FIXTURE_SNAPSHOTS,
        forecast_payloads=json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"],
        skill_payloads=json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"],
        output_dir=tmp_path,
    )

    assert report.actionable_markets >= 1
    assert report.blocked_markets >= 1
    assert any(row.market_id == "w70" and row.action == "actionable" for row in report.rows)
    assert any(row.market_id == "wx-rain" and row.action == "blocked" for row in report.rows)
    rendered = format_weather_market_selection_report(report)
    assert "Weather Market Selection Report" in rendered
    assert (tmp_path / "weather_market_selection_report.md").exists()
    assert (tmp_path / "weather_market_selection_report.json").exists()


def test_generate_weather_settlement_audit_report_writes_auditable_mapping_rows(tmp_path: Path) -> None:
    report = generate_weather_settlement_audit_report(
        snapshot_path=FIXTURE_SNAPSHOTS,
        forecast_payloads=json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"],
        skill_payloads=json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"],
        output_dir=tmp_path,
    )

    assert report.reviewed_markets == 2
    assert report.deterministic_markets == 2
    assert all(row.station_id == "KNYC" for row in report.rows)
    rendered = format_weather_settlement_audit_report(report)
    assert "Weather Settlement Audit Report" in rendered
    assert (tmp_path / "weather_settlement_audit_report.md").exists()
    assert (tmp_path / "weather_settlement_audit_report.json").exists()


def test_generate_weather_run_scorecard_report_summarizes_series_decision(tmp_path: Path) -> None:
    report = generate_weather_run_scorecard_report(
        snapshot_path=FIXTURE_SNAPSHOTS,
        forecast_payloads=json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"],
        skill_payloads=json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"],
        output_dir=tmp_path,
    )

    assert report.reviewed_series >= 1
    assert any(row.recommended_action in {"proceed", "review"} for row in report.rows)
    rendered = format_weather_run_scorecard_report(report)
    assert "Weather Run Scorecard Report" in rendered
    assert (tmp_path / "weather_run_scorecard_report.md").exists()
    assert (tmp_path / "weather_run_scorecard_report.json").exists()


def test_generate_weather_final_scorecard_summarizes_weather_readiness(tmp_path: Path) -> None:
    report = generate_weather_final_scorecard(
        snapshot_path=FIXTURE_SNAPSHOTS,
        forecast_payloads=json.loads(FIXTURE_RUNS.read_text(encoding="utf-8"))["runs"],
        skill_payloads=json.loads(FIXTURE_SKILLS.read_text(encoding="utf-8"))["skills"],
        output_dir=tmp_path,
    )

    assert report.recommended_action in {"proceed", "review", "pause"}
    assert 0.0 <= report.readiness_score <= 1.0
    assert report.profit_focus in {"selection", "settlement", "execution"}
    assert 0.0 <= report.total_profit_loss <= 3.0
    assert report.tuning_actions
    rendered = format_weather_final_scorecard(report)
    assert "Weather Final Scorecard" in rendered
    assert "Profit" in rendered
    assert (tmp_path / "weather_final_scorecard.md").exists()
    assert (tmp_path / "weather_final_scorecard.json").exists()
