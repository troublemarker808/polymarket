from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.crypto.phase2.preset_verify import (
    build_crypto_phase2_preset_verification_report,
    format_crypto_phase2_preset_verification_report,
)


def test_build_crypto_phase2_preset_verification_report_passes_stronger_candidate(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline-suite.json"
    candidate_path = tmp_path / "candidate-suite.json"
    baseline_path.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "recommended_action": "proceed",
                    "readiness_score": 0.74,
                    "total_profit_loss": 1.4,
                    "filtered_pnl": 0.06,
                    "profit_focus": "execution",
                    "secondary_profit_focus": "exit",
                    "execution_loss": 0.45,
                    "exit_loss": 0.22,
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "recommended_action": "proceed",
                    "readiness_score": 0.81,
                    "total_profit_loss": 1.1,
                    "filtered_pnl": 0.08,
                    "profit_focus": "execution",
                    "secondary_profit_focus": "exit",
                    "execution_loss": 0.22,
                    "exit_loss": 0.12,
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_crypto_phase2_preset_verification_report(
        baseline_suite_path=baseline_path,
        candidate_suite_path=candidate_path,
    )

    assert report.verification_decision == "pass"
    assert report.rollback_recommended is False
    assert report.targeted_loss_delta < 0
    assert "remains stronger" in format_crypto_phase2_preset_verification_report(report)


def test_build_crypto_phase2_preset_verification_report_rolls_back_regression(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline-suite.json"
    candidate_path = tmp_path / "candidate-suite.json"
    baseline_path.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "recommended_action": "proceed",
                    "readiness_score": 0.8,
                    "total_profit_loss": 1.0,
                    "filtered_pnl": 0.09,
                    "profit_focus": "execution",
                    "secondary_profit_focus": "exit",
                    "execution_loss": 0.22,
                    "exit_loss": 0.12,
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(
            {
                "final_scorecard": {
                    "recommended_action": "pause",
                    "readiness_score": 0.72,
                    "total_profit_loss": 1.4,
                    "filtered_pnl": 0.05,
                    "profit_focus": "execution",
                    "secondary_profit_focus": "exit",
                    "execution_loss": 0.35,
                    "exit_loss": 0.18,
                }
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    report = build_crypto_phase2_preset_verification_report(
        baseline_suite_path=baseline_path,
        candidate_suite_path=candidate_path,
    )

    assert report.verification_decision == "rollback"
    assert report.rollback_recommended is True
    assert report.targeted_loss_delta > 0
