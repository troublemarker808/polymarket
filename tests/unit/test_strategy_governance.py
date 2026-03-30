from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategy_governance import (
    build_strategy_governance_report,
    format_strategy_governance_report,
)


def test_build_strategy_governance_report_marks_apply_and_hold_states(tmp_path: Path) -> None:
    crypto_package = _write_json(
        tmp_path / "crypto-package.json",
        {
            "next_working_preset": "btc_family_fast",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_package = _write_json(
        tmp_path / "sports-package.json",
        {
            "next_working_preset": "nba_tighter_selection",
            "promotion_decision": "collect_more_evidence",
            "ready_to_apply": False,
        },
    )
    weather_package = _write_json(
        tmp_path / "weather-package.json",
        {
            "next_working_preset": "threshold_strip_focus",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    crypto_plan = _write_json(tmp_path / "crypto-plan.json", {"apply_mode": "review_then_apply"})
    weather_plan = _write_json(tmp_path / "weather-plan.json", {"apply_mode": "review_then_apply"})

    report = build_strategy_governance_report(
        crypto_change_package_path=crypto_package,
        sports_change_package_path=sports_package,
        weather_change_package_path=weather_package,
        crypto_apply_plan_path=crypto_plan,
        weather_apply_plan_path=weather_plan,
    )

    assert report.overall_action == "hold"
    assert report.apply_ready_boards == ("crypto", "weather")
    assert any(board.board == "sports" and board.action == "hold" for board in report.boards)
    assert "Strategy Governance Report" in format_strategy_governance_report(report)


def test_build_strategy_governance_report_marks_rollback_when_verification_fails(tmp_path: Path) -> None:
    crypto_package = _write_json(
        tmp_path / "crypto-package.json",
        {
            "next_working_preset": "btc_family_fast",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_package = _write_json(
        tmp_path / "sports-package.json",
        {
            "next_working_preset": "nba_tighter_selection",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    weather_package = _write_json(
        tmp_path / "weather-package.json",
        {
            "next_working_preset": "threshold_strip_focus",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_verify = _write_json(
        tmp_path / "sports-verify.json",
        {"verification_decision": "rollback", "rollback_recommended": True},
    )

    report = build_strategy_governance_report(
        crypto_change_package_path=crypto_package,
        sports_change_package_path=sports_package,
        weather_change_package_path=weather_package,
        sports_verify_path=sports_verify,
    )

    assert report.overall_action == "rollback"
    assert report.rollback_boards == ("sports",)


def test_build_strategy_governance_report_respects_version_quarantine(tmp_path: Path) -> None:
    crypto_package = _write_json(
        tmp_path / "crypto-package.json",
        {
            "next_working_preset": "btc_family_fast",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_package = _write_json(
        tmp_path / "sports-package.json",
        {
            "next_working_preset": "nba_tighter_selection",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    weather_package = _write_json(
        tmp_path / "weather-package.json",
        {
            "next_working_preset": "threshold_strip_focus",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_version = _write_json(
        tmp_path / "sports-version.json",
        {"recommendation": "quarantine", "strategy_state": "quarantined"},
    )

    report = build_strategy_governance_report(
        crypto_change_package_path=crypto_package,
        sports_change_package_path=sports_package,
        weather_change_package_path=weather_package,
        sports_version_compare_path=sports_version,
    )

    sports_board = next(board for board in report.boards if board.board == "sports")
    assert sports_board.action == "hold"
    assert sports_board.strategy_state == "quarantined"


def test_build_strategy_governance_report_prefers_version_promote_signal_when_ready(tmp_path: Path) -> None:
    crypto_package = _write_json(
        tmp_path / "crypto-package.json",
        {
            "next_working_preset": "btc_family_fast",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_package = _write_json(
        tmp_path / "sports-package.json",
        {
            "next_working_preset": "nba_tighter_selection",
            "promotion_decision": "collect_more_evidence",
            "ready_to_apply": True,
        },
    )
    weather_package = _write_json(
        tmp_path / "weather-package.json",
        {
            "next_working_preset": "threshold_strip_focus",
            "promotion_decision": "promote_candidate",
            "ready_to_apply": True,
        },
    )
    sports_version = _write_json(
        tmp_path / "sports-version.json",
        {"recommendation": "promote", "strategy_state": "candidate"},
    )

    report = build_strategy_governance_report(
        crypto_change_package_path=crypto_package,
        sports_change_package_path=sports_package,
        weather_change_package_path=weather_package,
        sports_version_compare_path=sports_version,
    )

    sports_board = next(board for board in report.boards if board.board == "sports")
    assert sports_board.action == "apply"
    assert sports_board.reason == "version comparison and evidence both support controlled application"


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path
