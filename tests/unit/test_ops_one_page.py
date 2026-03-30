from __future__ import annotations

import json
from pathlib import Path

from pm_bot.multi_board_ops import build_multi_board_ops_report
from pm_bot.ops_console import build_unified_ops_console
from pm_bot.ops_followup import build_ops_followup_queue
from pm_bot.ops_history import build_ops_history_report
from pm_bot.ops_one_page import build_ops_one_page, format_ops_one_page, write_ops_one_page
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategy_loop_decision import StrategyLoopDecision


def test_build_ops_one_page_combines_runtime_console_and_history(tmp_path: Path) -> None:
    output_root = tmp_path / "ops-runs"
    output_root.mkdir(parents=True, exist_ok=True)
    _write_multi_board_report(
        output_root / "2026-03-31" / "run-001" / "multi-board-ops.md",
        overall_action="review",
    )
    console = build_unified_ops_console(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="review"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=False),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=1, review_series=0),
    )
    report = build_multi_board_ops_report(
        crypto_operator_summary_path=tmp_path / "crypto.md",
        crypto_evidence_path=tmp_path / "crypto-evidence.md",
        sports_scorecard_path=tmp_path / "sports.md",
        weather_scorecard_path=tmp_path / "weather.md",
    )
    history = build_ops_history_report(output_root=output_root)
    followup_queue = build_ops_followup_queue(
        latest_report=report,
        history=history,
    )
    page = build_ops_one_page(
        dashboard=DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(),
            pending_orders=(),
            status=RuntimeStatus.RUNNING,
            halt_reason=HaltReason.NONE,
            halt_message=None,
            last_alert=None,
            daily_order_count=0,
            daily_order_soft_limit_reached=False,
        ),
        runtime_rendered="runtime_dashboard\nrisk_action=review",
        console=console,
        history=history,
        followup_queue=followup_queue,
        strategy_loop_decision=StrategyLoopDecision(
            recommended_mode="learn",
            latest_action="learn",
            primary_board="weather",
            next_step="focus the next experiment cycle on repeatedly weak boards before opening new promotions",
        ),
        strategy_cycle_package={
            "cycle_status": "learn",
            "cycle_reason": "current evidence still points to tuning and additional experimentation",
            "next_step": "refresh experiments on the weakest board and regenerate candidate comparisons",
            "strategy_mode": "learn",
            "primary_board": "weather",
        },
    )

    rendered = format_ops_one_page(page)
    assert "# Ops One Page" in rendered
    assert "## Runtime" in rendered
    assert "triage_action=monitor" in rendered
    assert "## Unified Ops" in rendered
    assert "## History" in rendered
    assert "## Strategy Loop" in rendered
    assert "recommended_mode: learn" in rendered
    assert "## Strategy Cycle" in rendered
    assert "cycle_status: learn" in rendered
    assert "## Follow-Up" in rendered


def test_write_ops_one_page_writes_sidecar_json(tmp_path: Path) -> None:
    console = build_unified_ops_console(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="proceed"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=1, review_series=0),
    )
    page = build_ops_one_page(
        dashboard=DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(),
            pending_orders=(),
            status=RuntimeStatus.RUNNING,
            halt_reason=HaltReason.NONE,
            halt_message=None,
            last_alert=None,
            daily_order_count=0,
            daily_order_soft_limit_reached=False,
        ),
        runtime_rendered="runtime_dashboard\nrisk_action=proceed",
        console=console,
        history=None,
    )

    target = write_ops_one_page(path=tmp_path / "ops-one-page.md", page=page)

    assert target.exists()
    assert target.with_suffix(".json").exists()


def _write_multi_board_report(path: Path, *, overall_action: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Multi-Board Ops Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "overall_action": overall_action,
                "overall_decision": f"{overall_action}:crypto=review",
                "next_step": "review_cross_board_artifacts",
                "rollback_target": "crypto",
                "escalation_actions": ["review crypto"],
                "blockers": [],
                "warnings": [],
                "boards": [{"board": "crypto", "action": "review", "decision": "review:crypto", "source_path": "crypto.md", "evidence_ready": False, "reviewed_items": 1, "actionable_items": 0, "warnings": []}],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


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
                "artifacts": {"session_label": "crypto-live", "event_count": 10, "orders_submitted": 3, "orders_filled": 2},
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
        json.dumps({"reviewed_events": actionable_events + review_events, "actionable_events": actionable_events, "review_events": review_events, "rows": []}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return path


def _write_weather_scorecard(path: Path, *, actionable_series: int, review_series: int) -> Path:
    path.write_text("# Weather Run Scorecard Report\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps({"reviewed_series": actionable_series + review_series, "actionable_series": actionable_series, "review_series": review_series, "rows": []}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return path
