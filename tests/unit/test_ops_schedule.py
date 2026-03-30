from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from pm_bot.ops_schedule import run_scheduled_ops_bundle


def test_run_scheduled_ops_bundle_writes_dated_artifacts(tmp_path: Path) -> None:
    prior_bundle_a = _write_crypto_bundle(tmp_path / "bundle-a.md", overall_action="proceed")
    prior_bundle_b = _write_crypto_bundle(tmp_path / "bundle-b.md", overall_action="review")
    loop_a = _write_strategy_feedback_loop(tmp_path / "loop-a.md", overall_loop_action="learn", board_actions={"weather": "learn"})
    loop_b = _write_strategy_feedback_loop(tmp_path / "loop-b.md", overall_loop_action="stabilize", board_actions={"sports": "stabilize"})
    result = run_scheduled_ops_bundle(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="proceed"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=1, review_series=0),
        promotion_evidence_stage="small_live_stability",
        promotion_evidence_bundle_paths=[prior_bundle_a, prior_bundle_b],
        strategy_feedback_loop_paths=[loop_a, loop_b],
        output_root=tmp_path / "ops-runs",
        run_id="daily-001",
        now=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
    )

    assert result.run_date == "2026-03-29"
    assert result.run_id == "daily-001"
    assert Path(result.multi_board_report_path).exists()
    assert Path(result.daily_bundle_path).exists()
    assert Path(result.ops_console_path).exists()
    assert Path(result.ops_history_path).exists()
    assert Path(result.ops_one_page_path).exists()
    assert Path(result.ops_followup_queue_path).exists()
    assert Path(result.ops_decision_path).exists()
    assert result.promotion_evidence_path is not None
    assert Path(result.promotion_evidence_path).exists()
    assert result.strategy_loop_history_path is not None
    assert Path(result.strategy_loop_history_path).exists()
    assert result.strategy_loop_decision_path is not None
    assert Path(result.strategy_loop_decision_path).exists()
    assert result.strategy_cycle_package_path is not None
    assert Path(result.strategy_cycle_package_path).exists()
    assert Path(result.latest_multi_board_report_path).exists()
    assert Path(result.latest_daily_bundle_path).exists()
    assert Path(result.latest_ops_console_path).exists()
    assert Path(result.latest_ops_history_path).exists()
    assert Path(result.latest_ops_one_page_path).exists()
    assert Path(result.latest_ops_followup_queue_path).exists()
    assert Path(result.latest_ops_decision_path).exists()
    assert result.latest_promotion_evidence_path is not None
    assert Path(result.latest_promotion_evidence_path).exists()
    assert result.latest_strategy_loop_history_path is not None
    assert Path(result.latest_strategy_loop_history_path).exists()
    assert result.latest_strategy_loop_decision_path is not None
    assert Path(result.latest_strategy_loop_decision_path).exists()
    assert result.latest_strategy_cycle_package_path is not None
    assert Path(result.latest_strategy_cycle_package_path).exists()
    latest_ops_decision_payload = json.loads(Path(result.latest_ops_decision_path).with_suffix(".json").read_text(encoding="utf-8"))
    assert latest_ops_decision_payload["strategy_mode"] == "advance"
    assert latest_ops_decision_payload["strategy_primary_board"] is None
    cycle_package_payload = json.loads(Path(result.latest_strategy_cycle_package_path).with_suffix(".json").read_text(encoding="utf-8"))
    assert cycle_package_payload["cycle_status"] == "advance"
    assert cycle_package_payload["strategy_mode"] == "advance"
    latest_followup_payload = json.loads(Path(result.latest_ops_followup_queue_path).with_suffix(".json").read_text(encoding="utf-8"))
    assert latest_followup_payload["recommended_attention"] == "continue_scheduled_ops"


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
                "artifacts": {
                    "session_label": "crypto-live",
                    "event_count": 10,
                    "orders_submitted": 3,
                    "orders_filled": 2,
                },
                "execution_feedback": {
                    "recommended_route_bias": "stable",
                },
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
        json.dumps(
            {
                "ready": ready,
                "blockers": [] if ready else ["evidence blocked"],
                "warnings": [],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_sports_scorecard(path: Path, *, actionable_events: int, review_events: int) -> Path:
    path.write_text("# Sports Event Scorecard Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "reviewed_events": actionable_events + review_events,
                "actionable_events": actionable_events,
                "review_events": review_events,
                "rows": [],
            },
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
            {
                "reviewed_series": actionable_series + review_series,
                "actionable_series": actionable_series,
                "review_series": review_series,
                "rows": [],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_strategy_feedback_loop(path: Path, *, overall_loop_action: str, board_actions: dict[str, str]) -> Path:
    path.write_text("# Strategy Feedback Loop Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "overall_loop_action": overall_loop_action,
                "next_step": "continue",
                "boards": [
                    {"board": board, "loop_action": action}
                    for board, action in board_actions.items()
                ],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
