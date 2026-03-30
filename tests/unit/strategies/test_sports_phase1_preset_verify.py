from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.sports.phase1.preset_verify import (
    build_sports_preset_verification_report,
    format_sports_preset_verification_report,
)


def test_build_sports_preset_verification_report_passes_stronger_candidate(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline-scorecard.json"
    candidate_path = tmp_path / "candidate-scorecard.json"
    baseline_path.write_text(
        json.dumps(
            {
                "recommended_action": "proceed",
                "readiness_score": 0.72,
                "total_profit_loss": 1.2,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(
            {
                "recommended_action": "proceed",
                "readiness_score": 0.8,
                "total_profit_loss": 1.0,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_sports_preset_verification_report(
        baseline_scorecard_path=baseline_path,
        candidate_scorecard_path=candidate_path,
    )

    assert report.verification_decision == "pass"
    assert report.rollback_recommended is False
    assert "remains stronger" in format_sports_preset_verification_report(report)


def test_build_sports_preset_verification_report_rolls_back_regression(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline-scorecard.json"
    candidate_path = tmp_path / "candidate-scorecard.json"
    baseline_path.write_text(
        json.dumps(
            {
                "recommended_action": "proceed",
                "readiness_score": 0.79,
                "total_profit_loss": 0.95,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(
            {
                "recommended_action": "pause",
                "readiness_score": 0.71,
                "total_profit_loss": 1.35,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_sports_preset_verification_report(
        baseline_scorecard_path=baseline_path,
        candidate_scorecard_path=candidate_path,
    )

    assert report.verification_decision == "rollback"
    assert report.rollback_recommended is True
