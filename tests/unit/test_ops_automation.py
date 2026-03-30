from __future__ import annotations

from pathlib import Path

from pm_bot.multi_board_ops import MultiBoardBoardStatus, MultiBoardOpsReport
from pm_bot.ops_automation import (
    build_daily_ops_bundle,
    build_daily_ops_bundle_from_specs,
    format_daily_ops_bundle,
    write_daily_ops_bundle,
)
from pm_bot.multi_board_ops import default_multi_board_input_specs


def test_build_daily_ops_bundle_creates_checklist_from_multi_board_report(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "pm_bot.ops_automation.build_multi_board_ops_report",
        lambda **kwargs: MultiBoardOpsReport(
            overall_action="review",
            overall_decision="review:crypto=proceed,sports=review,weather=proceed",
            next_step="review_cross_board_artifacts",
            rollback_target="sports",
            escalation_actions=("review sports board scorecard and refresh supporting evidence",),
            blockers=(),
            warnings=("sports: review_events=1",),
            boards=(
                MultiBoardBoardStatus("crypto", "proceed", "crypto ready", "crypto.md", True, 1, 1, ()),
                MultiBoardBoardStatus("sports", "review", "sports review", "sports.md", None, 1, 0, ("review_events=1",)),
                MultiBoardBoardStatus("weather", "proceed", "weather ready", "weather.md", None, 1, 1, ()),
            ),
        ),
    )

    bundle = build_daily_ops_bundle(
        crypto_operator_summary_path=tmp_path / "crypto.md",
        sports_scorecard_path=tmp_path / "sports.md",
        weather_scorecard_path=tmp_path / "weather.md",
        crypto_evidence_path=tmp_path / "crypto-evidence.md",
    )

    assert bundle.report.overall_action == "review"
    assert any(item.status == "todo" for item in bundle.checklist)
    assert "Daily Ops Bundle" in format_daily_ops_bundle(bundle)


def test_write_daily_ops_bundle_writes_sidecar_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "pm_bot.ops_automation.build_multi_board_ops_report",
        lambda **kwargs: MultiBoardOpsReport(
            overall_action="proceed",
            overall_decision="proceed:all",
            next_step="prepare_unified_ops_window",
            rollback_target=None,
            escalation_actions=("proceed with unified ops window and operator handoff",),
            blockers=(),
            warnings=(),
            boards=(),
        ),
    )
    bundle = build_daily_ops_bundle(
        crypto_operator_summary_path=tmp_path / "crypto.md",
        sports_scorecard_path=tmp_path / "sports.md",
        weather_scorecard_path=tmp_path / "weather.md",
    )

    target = write_daily_ops_bundle(
        path=tmp_path / "daily-bundle.md",
        bundle=bundle,
    )

    assert target.exists()
    assert target.with_suffix(".json").exists()


def test_build_daily_ops_bundle_from_specs_collects_generated_reports(tmp_path: Path) -> None:
    specs = default_multi_board_input_specs(
        crypto_operator_summary_path=tmp_path / "crypto.md",
        crypto_evidence_path=tmp_path / "crypto-evidence.md",
        sports_scorecard_path=tmp_path / "sports.md",
        weather_scorecard_path=tmp_path / "weather.md",
    )
    for path in (tmp_path / "crypto.md", tmp_path / "crypto-evidence.md", tmp_path / "sports.md", tmp_path / "weather.md"):
        path.write_text("", encoding="utf-8")
        if path.suffix == ".md":
            path.with_suffix(".json").write_text("{}", encoding="utf-8")

    bundle = build_daily_ops_bundle_from_specs(specs)

    assert len(bundle.generated_reports) == 4
