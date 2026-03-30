from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from pm_bot.ops_history import (
    build_ops_history_report,
    format_ops_history_report,
    load_ops_history_report,
    write_ops_history_report,
)
from pm_bot.ops_schedule import run_scheduled_ops_bundle


def test_build_ops_history_report_summarizes_recent_streaks(tmp_path: Path) -> None:
    output_root = tmp_path / "ops-runs"
    run_scheduled_ops_bundle(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto-1.md", overall_action="review"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence-1.md", ready=False),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports-1.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather-1.md", actionable_series=1, review_series=0),
        output_root=output_root,
        run_id="run-001",
        now=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )
    run_scheduled_ops_bundle(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto-2.md", overall_action="review"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence-2.md", ready=False),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports-2.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather-2.md", actionable_series=1, review_series=0),
        output_root=output_root,
        run_id="run-002",
        now=datetime(2026, 3, 31, 12, 0, tzinfo=UTC),
    )

    report = build_ops_history_report(output_root=output_root)

    assert report.total_runs == 2
    assert report.latest_action == "review"
    assert report.review_streak == 2
    assert report.recommended_attention == "escalate_review_streak"
    assert "crypto: evidence blocked=2" in report.recurring_issues
    assert "Ops History Report" in format_ops_history_report(report)


def test_write_ops_history_report_writes_sidecar_json(tmp_path: Path) -> None:
    output_root = tmp_path / "ops-runs"
    run_scheduled_ops_bundle(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="proceed"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=1, review_series=0),
        output_root=output_root,
        run_id="run-001",
        now=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
    )

    report = build_ops_history_report(output_root=output_root)
    target = write_ops_history_report(path=tmp_path / "ops-history.md", report=report)

    loaded = load_ops_history_report(target)
    assert loaded is not None
    assert loaded.latest_action == "proceed"
    assert target.with_suffix(".json").exists()
    assert loaded.recurring_issues == ()


def _write_crypto_bundle(path: Path, *, overall_action: str) -> Path:
    path.write_text("# Combined Operator Summary\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "combined": {
                    "overall_action": overall_action,
                    "overall_decision": f"{overall_action}:runtime=clear",
                    "next_step": "continue_current_window",
                    "rollback_target": None,
                    "alert_count": 0,
                    "alert_codes": [],
                    "runtime_action": overall_action,
                    "runtime_decision": f"{overall_action}:clear",
                    "promotion_action": overall_action,
                    "promotion_decision": f"{overall_action}:ready=true:blockers=0:warnings=0",
                    "last_rejection_reason": None,
                },
                "artifacts": {"session_label": "crypto-live", "event_count": 1, "orders_submitted": 1, "orders_filled": 1},
                "execution_feedback": {"recommended_route_bias": "stable"},
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_crypto_evidence(path: Path, *, ready: bool) -> Path:
    path.write_text("# Promotion Evidence Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps({"ready": ready, "blockers": [] if ready else ["evidence blocked"], "warnings": []}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return path


def _write_sports_scorecard(path: Path, *, actionable_events: int, review_events: int) -> Path:
    path.write_text("# Sports Event Scorecard Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {"reviewed_events": actionable_events + review_events, "actionable_events": actionable_events, "review_events": review_events, "rows": []},
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_weather_scorecard(path: Path, *, actionable_series: int, review_series: int) -> Path:
    path.write_text("# Weather Run Scorecard Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {"reviewed_series": actionable_series + review_series, "actionable_series": actionable_series, "review_series": review_series, "rows": []},
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
