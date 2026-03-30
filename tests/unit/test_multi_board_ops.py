from __future__ import annotations

import json
from pathlib import Path

from pm_bot.multi_board_ops import (
    MultiBoardInputSpec,
    build_multi_board_ops_report,
    build_multi_board_ops_report_from_specs,
    format_multi_board_ops_report,
    load_multi_board_ops_report,
    write_multi_board_ops_report,
)


def test_build_multi_board_ops_report_merges_board_statuses(tmp_path: Path) -> None:
    crypto_bundle = _write_crypto_bundle(tmp_path / "crypto-summary.md", overall_action="proceed")
    crypto_evidence = _write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True)
    sports_scorecard = _write_sports_scorecard(tmp_path / "sports-scorecard.md", actionable_events=1, review_events=0)
    weather_scorecard = _write_weather_scorecard(tmp_path / "weather-scorecard.md", actionable_series=1, review_series=0)

    report = build_multi_board_ops_report(
        crypto_operator_summary_path=crypto_bundle,
        crypto_evidence_path=crypto_evidence,
        sports_scorecard_path=sports_scorecard,
        weather_scorecard_path=weather_scorecard,
    )

    assert report.overall_action == "proceed"
    assert report.next_step == "prepare_unified_ops_window"
    assert report.rollback_target is None
    assert report.escalation_actions == ("proceed with unified ops window and operator handoff",)
    assert len(report.boards) == 3
    assert "Multi-Board Ops Report" in format_multi_board_ops_report(report)


def test_write_multi_board_ops_report_writes_sidecar_json(tmp_path: Path) -> None:
    report = build_multi_board_ops_report(
        crypto_operator_summary_path=_write_crypto_bundle(tmp_path / "crypto-summary.md", overall_action="review"),
        crypto_evidence_path=_write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=False),
        sports_scorecard_path=_write_sports_scorecard(tmp_path / "sports-scorecard.md", actionable_events=1, review_events=0),
        weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather-scorecard.md", actionable_series=0, review_series=1),
    )

    target = write_multi_board_ops_report(
        path=tmp_path / "multi-board.md",
        report=report,
    )

    loaded = load_multi_board_ops_report(target)
    assert loaded is not None
    assert loaded.overall_action == "review"
    assert loaded.rollback_target == "crypto"
    assert target.with_suffix(".json").exists()


def test_build_multi_board_ops_report_from_specs_supports_registry_style_inputs(tmp_path: Path) -> None:
    crypto_bundle = _write_crypto_bundle(tmp_path / "crypto-summary.md", overall_action="proceed")
    crypto_evidence = _write_crypto_evidence(tmp_path / "crypto-evidence.md", ready=True)
    sports_scorecard = _write_sports_scorecard(tmp_path / "sports-scorecard.md", actionable_events=1, review_events=0)

    def _load_generic(path: str, evidence_path: str | None) -> object:
        if "crypto" in path:
            return build_multi_board_ops_report(
                crypto_operator_summary_path=crypto_bundle,
                crypto_evidence_path=crypto_evidence,
                sports_scorecard_path=sports_scorecard,
                weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather-scorecard.md", actionable_series=1, review_series=0),
            ).boards[0]
        del evidence_path
        return build_multi_board_ops_report(
            crypto_operator_summary_path=crypto_bundle,
            crypto_evidence_path=crypto_evidence,
            sports_scorecard_path=sports_scorecard,
            weather_scorecard_path=_write_weather_scorecard(tmp_path / "weather-scorecard.md", actionable_series=1, review_series=0),
        ).boards[1]

    report = build_multi_board_ops_report_from_specs(
        (
            MultiBoardInputSpec("crypto", str(crypto_bundle), str(crypto_evidence), _load_generic),
            MultiBoardInputSpec("sports", str(sports_scorecard), None, _load_generic),
        )
    )

    assert len(report.boards) == 2
    assert report.overall_action == "proceed"


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
