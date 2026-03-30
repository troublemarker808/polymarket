from __future__ import annotations

import json
from pathlib import Path

from pm_bot.ops_console import (
    build_unified_ops_console,
    build_unified_ops_console_from_specs,
    format_unified_ops_console,
    load_unified_ops_console,
    write_unified_ops_console,
)
from pm_bot.multi_board_ops import default_multi_board_input_specs


def test_build_unified_ops_console_aggregates_reports(tmp_path: Path) -> None:
    console = build_unified_ops_console(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="proceed"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=1, review_series=0),
    )

    assert console.overall_action == "proceed"
    assert console.rollback_target is None
    assert console.checklist_completion_ratio == 1.0
    assert len(console.boards) == 3
    assert "Unified Ops Console" in format_unified_ops_console(console)


def test_build_unified_ops_console_from_specs_uses_registry_style_inputs(tmp_path: Path) -> None:
    specs = default_multi_board_input_specs(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="proceed"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=1, review_series=0),
    )

    console = build_unified_ops_console_from_specs(specs)

    assert console.overall_action == "proceed"
    assert len(console.boards) == 3


def test_write_unified_ops_console_writes_sidecar_json(tmp_path: Path) -> None:
    console = build_unified_ops_console(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto.md", overall_action="review"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=False),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports.md", actionable_events=1, review_events=1),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather.md", actionable_series=0, review_series=1),
    )

    target = write_unified_ops_console(path=tmp_path / "ops-console.md", console=console)

    loaded = load_unified_ops_console(target)
    assert loaded is not None
    assert loaded.overall_action == "review"
    assert loaded.rollback_target == "crypto"
    assert target.with_suffix(".json").exists()


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
