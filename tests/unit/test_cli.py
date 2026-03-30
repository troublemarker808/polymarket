import runpy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace

import pm_bot.cli as cli
import pytest

from pm_bot.execution.paper_metrics import PaperExecutionMetrics
from pm_bot.cli import _load_underlying_states
from pm_bot.runtime.state import RuntimeState, runtime_state_to_dict


def test_module_cli_entrypoint_shows_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["pm_bot.cli", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("pm_bot.cli", run_name="__main__")

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Polymarket bot foundation CLI" in captured.out
    assert "run-paper-crypto-session" in captured.out
    assert "run-sync-crypto-session" in captured.out
    assert "check-paper-integrity" in captured.out
    assert "check-replay-determinism" in captured.out
    assert "phase1-replay" in captured.out
    assert "crypto-calibration-report" in captured.out
    assert "crypto-calibration-experiments" in captured.out
    assert "crypto-market-selection-report" in captured.out
    assert "crypto-phase2-replay" in captured.out
    assert "crypto-phase2-suite" in captured.out
    assert "crypto-phase2-final-report" in captured.out
    assert "crypto-phase2-learning-report" in captured.out
    assert "crypto-phase2-tuning-plan" in captured.out
    assert "crypto-phase2-candidate-presets" in captured.out
    assert "crypto-phase2-auto-experiments" in captured.out
    assert "crypto-phase2-preset-lifecycle" in captured.out
    assert "crypto-phase2-working-preset-patch" in captured.out
    assert "crypto-phase2-preset-promotion-evidence" in captured.out
    assert "crypto-phase2-preset-change-package" in captured.out
    assert "crypto-phase2-preset-apply-plan" in captured.out
    assert "crypto-phase2-apply-package" in captured.out
    assert "crypto-phase2-rollback-package" in captured.out
    assert "crypto-phase2-verify-application" in captured.out
    assert "strategy-governance-report" in captured.out
    assert "strategy-change-window" in captured.out
    assert "strategy-governance-decision" in captured.out
    assert "strategy-execute-window" in captured.out
    assert "strategy-feedback-loop" in captured.out
    assert "strategy-loop-history" in captured.out
    assert "strategy-loop-decision" in captured.out
    assert "sports-final-report" in captured.out
    assert "sports-learning-report" in captured.out
    assert "sports-tuning-plan" in captured.out
    assert "sports-candidate-presets" in captured.out
    assert "sports-auto-experiments" in captured.out
    assert "sports-preset-lifecycle" in captured.out
    assert "sports-preset-promotion-evidence" in captured.out
    assert "sports-preset-change-package" in captured.out
    assert "sports-verify-application" in captured.out
    assert "weather-final-report" in captured.out
    assert "weather-learning-report" in captured.out
    assert "weather-tuning-plan" in captured.out
    assert "weather-candidate-presets" in captured.out
    assert "weather-auto-experiments" in captured.out
    assert "weather-preset-lifecycle" in captured.out
    assert "weather-preset-promotion-evidence" in captured.out
    assert "weather-preset-change-package" in captured.out
    assert "weather-verify-application" in captured.out
    assert "run-paper-crypto-phase2-session" in captured.out
    assert "mine-fixed-windows" in captured.out
    assert "run-fixed-window-experiments" in captured.out
    assert "validate-repo" in captured.out
    assert "ops-console" in captured.out
    assert "ops-control-panel" in captured.out
    assert "ops-history-report" in captured.out
    assert "ops-one-page" in captured.out
    assert "scheduled-ops-bundle" in captured.out
    assert "validate-promotion-readiness" in captured.out
    assert "promotion-artifact-review" in captured.out
    assert "promotion-operator-summary" in captured.out
    assert "write-operator-note-template" in captured.out
    assert "--board" in captured.out
    assert "--train-snapshot-path" in captured.out
    assert "--validation-snapshot-path" in captured.out
    assert "--holdout-snapshot-path" in captured.out
    assert "--candidate-set" in captured.out
    assert "btc_refined" in captured.out
    assert "--underlying-state-path" in captured.out
    assert "--exclude-bootstrap-from-limit" in captured.out
    assert "--shadow-state-path" in captured.out


def test_module_cli_check_paper_integrity(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    metrics_path, event_path, state_path = _write_integrity_artifacts(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "check-paper-integrity",
            "--metrics-path",
            str(metrics_path),
            "--event-path",
            str(event_path),
            "--state-path",
            str(state_path),
        ],
    )

    runpy.run_module("pm_bot.cli", run_name="__main__")

    captured = capsys.readouterr()
    assert "# Paper Integrity Report" in captured.out
    assert "- status: pass" in captured.out


def test_module_cli_check_replay_determinism(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshots.jsonl"
    snapshot_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "market_id": "crypto-1",
                        "token_id": "crypto-1-yes",
                        "slug": "crypto-1",
                        "category": "crypto",
                        "timestamp": "2026-03-23T12:00:00Z",
                        "best_bid_yes": 0.5,
                        "best_ask_yes": 0.6,
                        "best_bid_no": 0.4,
                        "best_ask_no": 0.5,
                        "last_traded_price": 0.55,
                        "metadata": {"reference_yes_probability": "0.56", "no_token_id": "crypto-1-no"},
                    }
                ),
                json.dumps(
                    {
                        "market_id": "sports-1",
                        "token_id": "sports-1-yes",
                        "slug": "sports-1",
                        "category": "sports",
                        "timestamp": "2026-03-23T12:05:00Z",
                        "resolution_time": "2026-03-23T16:00:00Z",
                        "best_bid_yes": 0.59,
                        "best_ask_yes": 0.6,
                        "best_bid_no": 0.4,
                        "best_ask_no": 0.41,
                        "last_traded_price": 0.595,
                        "metadata": {"model_yes_probability": "0.68", "start_time": "2026-03-23T14:00:00Z"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "check-replay-determinism",
            "--snapshot-path",
            str(snapshot_path),
            "--research-mode",
            "replay",
        ],
    )

    runpy.run_module("pm_bot.cli", run_name="__main__")

    captured = capsys.readouterr()
    assert "# Replay Determinism Report" in captured.out
    assert "- status: pass" in captured.out


def test_validate_repo_command_exits_with_validation_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["pm_bot.cli", "validate-repo"])
    monkeypatch.setattr("pm_bot.cli.run_repository_validation", lambda: 7)

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 7


def test_validate_promotion_readiness_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "validate-promotion-readiness",
            "--stage",
            "paper_to_sync_shadow",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--target-config-dir",
            "configs/profiles/sync-normal-shadow-v1",
            "--metrics-path",
            "metrics.json",
            "--state-path",
            "state.json",
            "--event-path",
            "events.jsonl",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.validate_promotion_readiness",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            ready=False,
            source_config_dir=str(kwargs["source_config_dir"]),
            target_config_dir=str(kwargs["target_config_dir"]),
            blockers=("missing evidence",),
            warnings=(),
            checks={"target_live_ready": "false"},
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_promotion_readiness_report",
        lambda report: f"stage={report.stage}\nready={str(report.ready).lower()}\nblocker={report.blockers[0]}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "stage=paper_to_sync_shadow" in captured.out
    assert "ready=false" in captured.out


def test_multi_board_ops_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "multi-board-ops-report",
            "--crypto-operator-summary-path",
            "crypto-summary.md",
            "--sports-scorecard-path",
            "sports-scorecard.md",
            "--weather-scorecard-path",
            "weather-scorecard.md",
            "--ops-summary-path",
            "multi-board.md",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_multi_board_ops_report",
        lambda **kwargs: SimpleNamespace(overall_action="review", overall_decision="review:boards", next_step="review", blockers=(), warnings=(), boards=()),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_multi_board_ops_report",
        lambda **kwargs: Path(kwargs["path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_multi_board_ops_report",
        lambda report: f"multi-board:{report.overall_action}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "multi-board:review" in captured.out


def test_daily_ops_bundle_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "daily-ops-bundle",
            "--crypto-operator-summary-path",
            "crypto-summary.md",
            "--sports-scorecard-path",
            "sports-scorecard.md",
            "--weather-scorecard-path",
            "weather-scorecard.md",
            "--daily-bundle-path",
            "daily-bundle.md",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_daily_ops_bundle",
        lambda **kwargs: SimpleNamespace(report=SimpleNamespace(overall_action="review"), checklist=(), generated_reports=()),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_daily_ops_bundle",
        lambda **kwargs: Path(kwargs["path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_daily_ops_bundle",
        lambda bundle: f"daily-bundle:{bundle.report.overall_action}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "daily-bundle:review" in captured.out


def test_ops_console_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "ops-console",
            "--crypto-operator-summary-path",
            "crypto-summary.md",
            "--sports-scorecard-path",
            "sports-scorecard.md",
            "--weather-scorecard-path",
            "weather-scorecard.md",
            "--console-path",
            "ops-console.md",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_unified_ops_console",
        lambda **kwargs: SimpleNamespace(overall_action="review"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_unified_ops_console",
        lambda **kwargs: Path(kwargs["path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_unified_ops_console",
        lambda console: f"ops-console:{console.overall_action}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "ops-console:review" in captured.out


def test_scheduled_ops_bundle_command_prints_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "scheduled-ops-bundle",
            "--crypto-operator-summary-path",
            "crypto-summary.md",
            "--sports-scorecard-path",
            "sports-scorecard.md",
            "--weather-scorecard-path",
            "weather-scorecard.md",
            "--output-root",
            "ops-runs",
            "--run-id",
            "daily-001",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.run_scheduled_ops_bundle",
        lambda **kwargs: SimpleNamespace(
            run_id=kwargs["run_id"],
            run_date="2026-03-29",
            output_dir="ops-runs\\2026-03-29\\daily-001",
            multi_board_report_path="ops-runs\\2026-03-29\\daily-001\\multi-board-ops.md",
            daily_bundle_path="ops-runs\\2026-03-29\\daily-001\\daily-ops-bundle.md",
            ops_console_path="ops-runs\\2026-03-29\\daily-001\\ops-console.md",
            ops_history_path="ops-runs\\ops-history.md",
            ops_one_page_path="ops-runs\\2026-03-29\\daily-001\\ops-one-page.md",
            ops_followup_queue_path="ops-runs\\2026-03-29\\daily-001\\ops-followup-queue.md",
            ops_decision_path="ops-runs\\2026-03-29\\daily-001\\ops-decision.md",
            promotion_evidence_path="ops-runs\\2026-03-29\\daily-001\\crypto-promotion-evidence.md",
            strategy_loop_history_path="ops-runs\\2026-03-29\\daily-001\\strategy-loop-history.md",
            strategy_loop_decision_path="ops-runs\\2026-03-29\\daily-001\\strategy-loop-decision.md",
            strategy_cycle_package_path="ops-runs\\2026-03-29\\daily-001\\strategy-cycle-package.md",
            latest_multi_board_report_path="ops-runs\\latest-multi-board-ops.md",
            latest_daily_bundle_path="ops-runs\\latest-daily-ops-bundle.md",
            latest_ops_console_path="ops-runs\\latest-ops-console.md",
            latest_ops_history_path="ops-runs\\latest-ops-history.md",
            latest_ops_one_page_path="ops-runs\\latest-ops-one-page.md",
            latest_ops_followup_queue_path="ops-runs\\latest-ops-followup-queue.md",
            latest_ops_decision_path="ops-runs\\latest-ops-decision.md",
            latest_promotion_evidence_path="ops-runs\\latest-crypto-promotion-evidence.md",
            latest_strategy_loop_history_path="ops-runs\\latest-strategy-loop-history.md",
            latest_strategy_loop_decision_path="ops-runs\\latest-strategy-loop-decision.md",
            latest_strategy_cycle_package_path="ops-runs\\latest-strategy-cycle-package.md",
        ),
    )

    cli.main()

    captured = capsys.readouterr()
    assert "run_id=daily-001" in captured.out
    assert "ops_console_path=ops-runs\\2026-03-29\\daily-001\\ops-console.md" in captured.out
    assert "ops_history_path=ops-runs\\ops-history.md" in captured.out
    assert "ops_one_page_path=ops-runs\\2026-03-29\\daily-001\\ops-one-page.md" in captured.out
    assert "ops_followup_queue_path=ops-runs\\2026-03-29\\daily-001\\ops-followup-queue.md" in captured.out
    assert "ops_decision_path=ops-runs\\2026-03-29\\daily-001\\ops-decision.md" in captured.out
    assert "promotion_evidence_path=ops-runs\\2026-03-29\\daily-001\\crypto-promotion-evidence.md" in captured.out
    assert "strategy_loop_history_path=ops-runs\\2026-03-29\\daily-001\\strategy-loop-history.md" in captured.out
    assert "strategy_loop_decision_path=ops-runs\\2026-03-29\\daily-001\\strategy-loop-decision.md" in captured.out
    assert "strategy_cycle_package_path=ops-runs\\2026-03-29\\daily-001\\strategy-cycle-package.md" in captured.out
    assert "latest_ops_one_page_path=ops-runs\\latest-ops-one-page.md" in captured.out
    assert "latest_ops_followup_queue_path=ops-runs\\latest-ops-followup-queue.md" in captured.out
    assert "latest_ops_decision_path=ops-runs\\latest-ops-decision.md" in captured.out
    assert "latest_promotion_evidence_path=ops-runs\\latest-crypto-promotion-evidence.md" in captured.out
    assert "latest_strategy_loop_history_path=ops-runs\\latest-strategy-loop-history.md" in captured.out
    assert "latest_strategy_loop_decision_path=ops-runs\\latest-strategy-loop-decision.md" in captured.out
    assert "latest_strategy_cycle_package_path=ops-runs\\latest-strategy-cycle-package.md" in captured.out


def test_ops_control_panel_command_prints_runtime_and_control_panel(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "ops-control-panel",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--state-path",
            "runtime-state.json",
            "--crypto-operator-summary-path",
            "crypto-summary.md",
            "--sports-scorecard-path",
            "sports-scorecard.md",
            "--weather-scorecard-path",
            "weather-scorecard.md",
            "--strategy-loop-decision-path",
            "strategy-loop-decision.md",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.load_settings_from_directory", lambda path: SimpleNamespace(risk=object(), trading=object()))

    class _RiskManager:
        def __init__(self, **kwargs: object) -> None:
            pass

        def advance_trading_day(self) -> None:
            return None

        def dashboard_state(self) -> object:
            return object()

    monkeypatch.setattr("pm_bot.cli.BasicRiskManager", _RiskManager)
    monkeypatch.setattr("pm_bot.cli.JsonRuntimeStateStore", lambda path: object())
    monkeypatch.setattr("pm_bot.cli.render_dashboard", lambda dashboard, trading_settings=None: "runtime_dashboard\nrisk_action=proceed")
    monkeypatch.setattr("pm_bot.cli.build_unified_ops_console", lambda **kwargs: SimpleNamespace(overall_action="review"))
    monkeypatch.setattr("pm_bot.cli.load_ops_history_report", lambda path: SimpleNamespace(latest_action="review", recent_actions=("review",), review_streak=1, pause_streak=0, recommended_attention="collect_more_runs", recurring_issues=("crypto: evidence blocked=2",)))
    monkeypatch.setattr("pm_bot.cli.load_strategy_loop_decision", lambda path: SimpleNamespace(recommended_mode="learn", primary_board="weather", next_step="focus weaker board"))
    monkeypatch.setattr(
        "pm_bot.cli.build_ops_control_panel",
        lambda **kwargs: SimpleNamespace(runtime_action="proceed", triage_action="escalate", triage_reason="recurring_issues=1", overall_action="review"),
    )
    monkeypatch.setattr("pm_bot.cli.format_ops_control_panel", lambda panel: f"ops_control_panel\ntriage_action={panel.triage_action}\noverall_action={panel.overall_action}")

    cli.main()

    captured = capsys.readouterr()
    assert "runtime_dashboard" in captured.out
    assert "ops_control_panel" in captured.out
    assert "triage_action=escalate" in captured.out
    assert "overall_action=review" in captured.out


def test_show_dashboard_prefers_ops_one_page(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "show-dashboard",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--state-path",
            "runtime-state.json",
            "--one-page-path",
            "ops-one-page.md",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.load_settings_from_directory", lambda path: SimpleNamespace(risk=object(), trading=object()))

    class _RiskManager:
        def __init__(self, **kwargs: object) -> None:
            pass

        def advance_trading_day(self) -> None:
            return None

        def dashboard_state(self) -> object:
            return object()

    monkeypatch.setattr("pm_bot.cli.BasicRiskManager", _RiskManager)
    monkeypatch.setattr("pm_bot.cli.JsonRuntimeStateStore", lambda path: object())
    monkeypatch.setattr("pm_bot.cli._render_dashboard_with_ops_summary", lambda *args, **kwargs: "runtime_dashboard\nops_one_page")

    cli.main()

    captured = capsys.readouterr()
    assert "ops_one_page" in captured.out


def test_ops_history_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "ops-history-report",
            "--output-root",
            "ops-runs",
            "--ops-history-path",
            "ops-runs\\ops-history.md",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_ops_history_report",
        lambda **kwargs: SimpleNamespace(latest_action="review"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_ops_history_report",
        lambda **kwargs: Path(kwargs["path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_ops_history_report",
        lambda report: f"ops-history:{report.latest_action}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "ops-history:review" in captured.out


def test_ops_one_page_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "ops-one-page",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--state-path",
            "runtime-state.json",
            "--crypto-operator-summary-path",
            "crypto-summary.md",
            "--sports-scorecard-path",
            "sports-scorecard.md",
            "--weather-scorecard-path",
            "weather-scorecard.md",
            "--one-page-path",
            "ops-one-page.md",
            "--strategy-loop-decision-path",
            "strategy-loop-decision.md",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.load_settings_from_directory", lambda path: SimpleNamespace(risk=object(), trading=object()))

    class _RiskManager:
        def __init__(self, **kwargs: object) -> None:
            pass

        def advance_trading_day(self) -> None:
            return None

        def dashboard_state(self) -> object:
            return object()

    monkeypatch.setattr("pm_bot.cli.BasicRiskManager", _RiskManager)
    monkeypatch.setattr("pm_bot.cli.JsonRuntimeStateStore", lambda path: object())
    monkeypatch.setattr("pm_bot.cli.render_dashboard", lambda dashboard, trading_settings=None: "runtime_dashboard\nrisk_action=proceed")
    monkeypatch.setattr("pm_bot.cli.build_unified_ops_console", lambda **kwargs: SimpleNamespace(overall_action="review"))
    monkeypatch.setattr("pm_bot.cli.load_strategy_loop_decision", lambda path: SimpleNamespace(recommended_mode="learn", primary_board="weather", next_step="focus weaker board"))
    monkeypatch.setattr("pm_bot.cli.build_ops_one_page", lambda **kwargs: SimpleNamespace(console=SimpleNamespace(overall_action="review")))
    monkeypatch.setattr("pm_bot.cli.write_ops_one_page", lambda **kwargs: Path(kwargs["path"]))
    monkeypatch.setattr("pm_bot.cli.format_ops_one_page", lambda page: f"ops-one-page:{page.console.overall_action}")

    cli.main()

    captured = capsys.readouterr()
    assert "ops-one-page:review" in captured.out


def test_crypto_phase2_final_report_command_prints_scorecard(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-final-report",
            "--snapshot-path",
            "crypto.jsonl",
            "--underlying-state-path",
            "underlying.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli._load_underlying_states",
        lambda path: {"BTC": object()},
    )
    async def _fake_run_crypto_phase2_suite(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(final_scorecard=SimpleNamespace(recommended_action="review"))
    monkeypatch.setattr("pm_bot.cli.run_crypto_phase2_suite", _fake_run_crypto_phase2_suite)
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_final_scorecard",
        lambda scorecard: f"crypto-final:{scorecard.recommended_action}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-final:review" in captured.out


def test_write_operator_note_template_command_prints_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "write-operator-note-template",
            "--stage",
            "sync_shadow_to_small_live_baseline",
            "--note-path",
            "operator-note.md",
            "--run-id",
            "run-1",
            "--market-window",
            "BTC/ETH 15m",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.write_operator_note_template", lambda **kwargs: Path(kwargs["path"]))

    cli.main()

    captured = capsys.readouterr()
    assert "note_path=operator-note.md" in captured.out


def test_promotion_operator_summary_command_prints_combined_view(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "promotion-operator-summary",
            "--stage",
            "paper_to_sync_shadow",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--target-config-dir",
            "configs/profiles/sync-promotion-shadow-v1",
            "--metrics-path",
            "metrics.json",
            "--state-path",
            "state.json",
            "--event-path",
            "events.jsonl",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.validate_promotion_readiness",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            ready=True,
            source_config_dir=str(kwargs["source_config_dir"]),
            target_config_dir=str(kwargs["target_config_dir"]),
            blockers=(),
            warnings=("review drift",),
            checks={},
            rollback_triggers=("runtime halted",),
            escalation_actions=("inspect artifacts",),
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_promotion_artifact_review",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            source_status="running",
            source_halt_reason="none",
            note_present=False,
            shadow_status=None,
            shadow_halt_reason=None,
            source_orders_submitted=2,
            shadow_orders_submitted=None,
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_promotion_operator_summary",
        lambda **kwargs: "operator-summary",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "operator-summary" in captured.out


def test_promotion_evidence_report_command_writes_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "promotion-evidence-report",
            "--stage",
            "small_live_stability",
            "--bundle-paths",
            "bundle-a.md",
            "bundle-b.md",
            "bundle-c.md",
            "--report-path",
            "evidence.md",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_promotion_evidence_report",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            ready=True,
            session_count=3,
            blockers=(),
            warnings=(),
            checks={"session_count": "3"},
            entries=(),
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_promotion_evidence_report",
        lambda **kwargs: captured.update(kwargs) or Path(kwargs["path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_promotion_evidence_report",
        lambda report: "evidence-report",
    )

    cli.main()

    assert captured["path"] == "evidence.md"
    assert captured["report"].stage == "small_live_stability"


def test_sports_market_selection_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "sports-market-selection-report",
            "--snapshot-path",
            "sports.jsonl",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_sports_market_selection_report",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_market_selection_report",
        lambda report: f"sports-selection:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-selection:sports.jsonl" in captured.out


def test_sports_closing_line_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "sports-closing-line-report",
            "--snapshot-path",
            "sports.jsonl",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_sports_closing_line_report",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_closing_line_report",
        lambda report: f"sports-closing:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-closing:sports.jsonl" in captured.out


def test_sports_event_scorecard_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "sports-event-scorecard-report",
            "--snapshot-path",
            "sports.jsonl",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_sports_event_scorecard_report",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_event_scorecard_report",
        lambda report: f"sports-scorecard:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-scorecard:sports.jsonl" in captured.out


def test_sports_final_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "sports-final-report",
            "--snapshot-path",
            "sports.jsonl",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_sports_final_scorecard",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_final_scorecard",
        lambda report: f"sports-final:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-final:sports.jsonl" in captured.out


def test_weather_market_selection_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-market-selection-report",
            "--snapshot-path",
            "weather.jsonl",
            "--forecast-runs-path",
            "forecast_runs.json",
            "--skill-path",
            "skills.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli._load_json_records",
        lambda path, key: [{"path": path, "key": key}],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_weather_market_selection_report",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_market_selection_report",
        lambda report: f"weather-selection:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-selection:weather.jsonl" in captured.out


def test_weather_settlement_audit_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-settlement-audit-report",
            "--snapshot-path",
            "weather.jsonl",
            "--forecast-runs-path",
            "forecast_runs.json",
            "--skill-path",
            "skills.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli._load_json_records",
        lambda path, key: [{"path": path, "key": key}],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_weather_settlement_audit_report",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_settlement_audit_report",
        lambda report: f"weather-audit:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-audit:weather.jsonl" in captured.out


def test_weather_run_scorecard_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-run-scorecard-report",
            "--snapshot-path",
            "weather.jsonl",
            "--forecast-runs-path",
            "forecast_runs.json",
            "--skill-path",
            "skills.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli._load_json_records",
        lambda path, key: [{"path": path, "key": key}],
    )
    monkeypatch.setattr(
        "pm_bot.cli.generate_weather_run_scorecard_report",
        lambda **kwargs: SimpleNamespace(snapshot_path=kwargs["snapshot_path"]),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_run_scorecard_report",
        lambda report: f"weather-scorecard:{report.snapshot_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-scorecard:weather.jsonl" in captured.out


def test_crypto_phase2_learning_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-learning-report",
            "--suite-paths",
            "suite-a.json",
            "suite-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_learning_report",
        lambda **kwargs: SimpleNamespace(run_count=len(kwargs["suite_paths"]), recommended_next_experiment="execution"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_learning_report",
        lambda report: f"crypto-learning:{report.recommended_next_experiment}:{report.run_count}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-learning:execution:2" in captured.out


def test_crypto_phase2_tuning_plan_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-tuning-plan",
            "--suite-paths",
            "suite-a.json",
            "suite-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_tuning_plan",
        lambda **kwargs: SimpleNamespace(experiment_family="execution"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_tuning_plan",
        lambda plan: f"crypto-tuning:{plan.experiment_family}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-tuning:execution" in captured.out


def test_crypto_phase2_candidate_presets_command_prints_registry(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-candidate-presets",
            "--suite-paths",
            "suite-a.json",
            "suite-b.json",
            "--candidate-underlying",
            "ETH",
            "--candidate-event-family",
            "dip",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_tuning_plan",
        lambda **kwargs: SimpleNamespace(variants=(), experiment_family="execution"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_candidate_preset_registry",
        lambda **kwargs: {"execution_variant": {"match": kwargs["base_match"], "overrides": {}}},
    )

    cli.main()

    captured = capsys.readouterr()
    assert '"underlying": "ETH"' in captured.out
    assert '"event_family": "dip"' in captured.out


def test_crypto_phase2_auto_experiments_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-auto-experiments",
            "--suite-paths",
            "suite-a.json",
            "suite-b.json",
            "--snapshot-path",
            "crypto.jsonl",
            "--underlying-state-path",
            "underlying.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_underlying_states", lambda path: {"BTC": object()})
    async def _fake_auto_experiments(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(winner=SimpleNamespace(variant_name="execution_faster_quotes"))
    monkeypatch.setattr(
        "pm_bot.cli.run_crypto_phase2_auto_experiments",
        _fake_auto_experiments,
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_auto_experiments_report",
        lambda report: f"crypto-auto:{report.winner.variant_name}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-auto:execution_faster_quotes" in captured.out


def test_crypto_phase2_preset_lifecycle_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-preset-lifecycle",
            "--suite-paths",
            "suite-a.json",
            "suite-b.json",
            "--snapshot-path",
            "crypto.jsonl",
            "--underlying-state-path",
            "underlying.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_underlying_states", lambda path: {"BTC": object()})
    async def _fake_auto_experiments(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_crypto_phase2_auto_experiments", _fake_auto_experiments)
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_lifecycle",
        lambda **kwargs: SimpleNamespace(next_working_preset="execution_faster_quotes"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_lifecycle",
        lambda lifecycle: f"crypto-lifecycle:{lifecycle.next_working_preset}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-lifecycle:execution_faster_quotes" in captured.out


def test_crypto_phase2_working_preset_patch_command_prints_patch(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-working-preset-patch",
            "--suite-paths",
            "suite-a.json",
            "suite-b.json",
            "--snapshot-path",
            "crypto.jsonl",
            "--underlying-state-path",
            "underlying.json",
            "--candidate-underlying",
            "ETH",
            "--candidate-event-family",
            "dip",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_underlying_states", lambda path: {"BTC": object()})
    async def _fake_auto_experiments(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_crypto_phase2_auto_experiments", _fake_auto_experiments)
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_lifecycle",
        lambda **kwargs: SimpleNamespace(next_working_preset="execution_faster_quotes", promotion_decision="promote_candidate"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_working_preset_patch",
        lambda **kwargs: {"execution_faster_quotes": {"match": kwargs["base_match"], "overrides": {}}},
    )

    cli.main()

    captured = capsys.readouterr()
    assert '"underlying": "ETH"' in captured.out
    assert '"event_family": "dip"' in captured.out


def test_crypto_phase2_preset_promotion_evidence_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-preset-promotion-evidence",
            "--suite-paths",
            "auto-a.json",
            "auto-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_promotion_evidence",
        lambda **kwargs: SimpleNamespace(ready_to_apply=True, winning_variant="execution_faster_quotes"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_promotion_evidence",
        lambda evidence: f"crypto-preset-evidence:{evidence.winning_variant}:{str(evidence.ready_to_apply).lower()}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-preset-evidence:execution_faster_quotes:true" in captured.out


def test_crypto_phase2_preset_change_package_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-preset-change-package",
            "--suite-paths",
            "auto-a.json",
            "auto-b.json",
            "--snapshot-path",
            "crypto.jsonl",
            "--underlying-state-path",
            "underlying.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_underlying_states", lambda path: {"BTC": object()})
    async def _fake_auto_experiments(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_crypto_phase2_auto_experiments", _fake_auto_experiments)
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_promotion_evidence",
        lambda **kwargs: SimpleNamespace(ready_to_apply=True),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_lifecycle",
        lambda **kwargs: SimpleNamespace(next_working_preset="execution_faster_quotes", promotion_decision="promote_candidate", promotion_reason="ok", working_preset="baseline", candidate_presets=("execution_faster_quotes",), retired_presets=("baseline",)),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_change_package",
        lambda **kwargs: SimpleNamespace(next_working_preset="execution_faster_quotes", ready_to_apply=True),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_change_package",
        lambda package: f"crypto-change-package:{package.next_working_preset}:{str(package.ready_to_apply).lower()}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-change-package:execution_faster_quotes:true" in captured.out


def test_crypto_phase2_preset_apply_plan_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-preset-apply-plan",
            "--suite-paths",
            "auto-a.json",
            "auto-b.json",
            "--snapshot-path",
            "crypto.jsonl",
            "--underlying-state-path",
            "underlying.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_underlying_states", lambda path: {"BTC": object()})
    async def _fake_auto_experiments(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_crypto_phase2_auto_experiments", _fake_auto_experiments)
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_promotion_evidence",
        lambda **kwargs: SimpleNamespace(ready_to_apply=True),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_lifecycle",
        lambda **kwargs: SimpleNamespace(next_working_preset="execution_faster_quotes", promotion_decision="promote_candidate", promotion_reason="ok", working_preset="baseline", candidate_presets=("execution_faster_quotes",), retired_presets=("baseline",)),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_change_package",
        lambda **kwargs: SimpleNamespace(next_working_preset="execution_faster_quotes", ready_to_apply=True, patch={"execution_faster_quotes": {}}),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_apply_plan",
        lambda **kwargs: SimpleNamespace(apply_mode="review_then_apply", next_working_preset="execution_faster_quotes", ready_to_apply=True),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_apply_plan",
        lambda plan: f"crypto-apply-plan:{plan.next_working_preset}:{plan.apply_mode}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-apply-plan:execution_faster_quotes:review_then_apply" in captured.out


def test_crypto_phase2_apply_package_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-apply-package",
            "--change-package-path",
            "change-package.json",
            "--target-config-path",
            "crypto.v1.toml",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.apply_crypto_phase2_preset_change_package",
        lambda **kwargs: SimpleNamespace(applied=True, output_config_path="crypto.applied.toml"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_apply_result",
        lambda result: f"crypto-apply:{result.applied}:{result.output_config_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-apply:True:crypto.applied.toml" in captured.out


def test_crypto_phase2_rollback_package_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-rollback-package",
            "--backup-config-path",
            "crypto.applied.backup.toml",
            "--target-config-path",
            "crypto.v1.toml",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.rollback_crypto_phase2_preset_application",
        lambda **kwargs: SimpleNamespace(rolled_back=True, output_config_path="crypto.rolledback.toml"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_rollback_result",
        lambda result: f"crypto-rollback:{result.rolled_back}:{result.output_config_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-rollback:True:crypto.rolledback.toml" in captured.out


def test_crypto_phase2_verify_application_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "crypto-phase2-verify-application",
            "--baseline-suite-path",
            "baseline-suite.json",
            "--candidate-suite-path",
            "candidate-suite.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_crypto_phase2_preset_verification_report",
        lambda **kwargs: SimpleNamespace(verification_decision="pass", next_step="keep candidate"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_crypto_phase2_preset_verification_report",
        lambda report: f"crypto-verify:{report.verification_decision}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "crypto-verify:pass:keep candidate" in captured.out


def test_sports_verify_application_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "sports-verify-application",
            "--baseline-suite-path",
            "baseline-scorecard.json",
            "--candidate-suite-path",
            "candidate-scorecard.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_sports_preset_verification_report",
        lambda **kwargs: SimpleNamespace(verification_decision="pass", next_step="keep sports candidate"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_preset_verification_report",
        lambda report: f"sports-verify:{report.verification_decision}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-verify:pass:keep sports candidate" in captured.out


def test_weather_verify_application_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-verify-application",
            "--baseline-suite-path",
            "baseline-scorecard.json",
            "--candidate-suite-path",
            "candidate-scorecard.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_weather_preset_verification_report",
        lambda **kwargs: SimpleNamespace(verification_decision="pass", next_step="keep weather candidate"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_preset_verification_report",
        lambda report: f"weather-verify:{report.verification_decision}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-verify:pass:keep weather candidate" in captured.out


def test_strategy_governance_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-governance-report",
            "--crypto-change-package-path",
            "crypto-package.json",
            "--sports-change-package-path",
            "sports-package.json",
            "--weather-change-package-path",
            "weather-package.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_governance_report",
        lambda **kwargs: SimpleNamespace(overall_action="apply", next_step="apply ready boards"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_governance_report",
        lambda report: f"strategy-governance:{report.overall_action}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-governance:apply:apply ready boards" in captured.out


def test_strategy_change_window_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-change-window",
            "--strategy-governance-path",
            "strategy-governance.md",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_change_window_from_report_path",
        lambda path: SimpleNamespace(window_action="apply", first_step="apply crypto"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_change_window",
        lambda window: f"strategy-window:{window.window_action}:{window.first_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-window:apply:apply crypto" in captured.out


def test_strategy_governance_decision_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-governance-decision",
            "--crypto-change-package-path",
            "crypto-package.json",
            "--sports-change-package-path",
            "sports-package.json",
            "--weather-change-package-path",
            "weather-package.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_governance_report",
        lambda **kwargs: SimpleNamespace(overall_action="apply", overall_reason="ready", apply_ready_boards=("crypto",), rollback_boards=()),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_change_window",
        lambda report: SimpleNamespace(window_action="apply", first_step="apply crypto"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_governance_decision",
        lambda report, window: SimpleNamespace(governance_action="apply", first_step="apply crypto"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_governance_decision",
        lambda decision: f"strategy-decision:{decision.governance_action}:{decision.first_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-decision:apply:apply crypto" in captured.out


def test_strategy_execute_window_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-execute-window",
            "--crypto-change-package-path",
            "crypto-package.json",
            "--sports-change-package-path",
            "sports-package.json",
            "--weather-change-package-path",
            "weather-package.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_governance_report",
        lambda **kwargs: SimpleNamespace(overall_action="apply"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_change_window",
        lambda report: SimpleNamespace(window_action="apply", first_step="apply crypto"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.execute_strategy_change_window",
        lambda **kwargs: SimpleNamespace(window_action="apply", next_step="verify applied boards"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_execution_window_report",
        lambda report: f"strategy-execution:{report.window_action}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-execution:apply:verify applied boards" in captured.out


def test_strategy_feedback_loop_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-feedback-loop",
            "--crypto-change-package-path",
            "crypto-package.json",
            "--sports-change-package-path",
            "sports-package.json",
            "--weather-change-package-path",
            "weather-package.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_governance_report",
        lambda **kwargs: SimpleNamespace(overall_action="apply"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_change_window",
        lambda report: SimpleNamespace(window_action="apply", first_step="apply crypto"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.execute_strategy_change_window",
        lambda **kwargs: SimpleNamespace(window_action="apply"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_feedback_loop_report",
        lambda **kwargs: SimpleNamespace(overall_loop_action="verify", next_step="run verification"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_feedback_loop_report",
        lambda report: f"strategy-feedback:{report.overall_loop_action}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-feedback:verify:run verification" in captured.out


def test_strategy_loop_history_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-loop-history",
            "--bundle-paths",
            "loop-a.json",
            "loop-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_loop_history_report",
        lambda **kwargs: SimpleNamespace(recommended_mode="stabilize", next_step="freeze unstable boards"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_loop_history_report",
        lambda report: f"strategy-loop-history:{report.recommended_mode}:{report.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-loop-history:stabilize:freeze unstable boards" in captured.out


def test_strategy_loop_decision_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "strategy-loop-decision",
            "--bundle-paths",
            "loop-a.json",
            "loop-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_loop_history_report",
        lambda **kwargs: SimpleNamespace(recommended_mode="stabilize", latest_action="stabilize", next_step="freeze unstable boards"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_strategy_loop_decision",
        lambda report: SimpleNamespace(recommended_mode="stabilize", primary_board="sports", next_step="freeze unstable boards"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_strategy_loop_decision",
        lambda decision: f"strategy-loop-decision:{decision.recommended_mode}:{decision.primary_board}:{decision.next_step}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "strategy-loop-decision:stabilize:sports:freeze unstable boards" in captured.out


def test_sports_learning_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "sports-learning-report",
            "--suite-paths",
            "sports-a.json",
            "sports-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_sports_learning_report",
        lambda **kwargs: SimpleNamespace(recommended_next_experiment="selection"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_learning_report",
        lambda report: f"sports-learning:{report.recommended_next_experiment}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-learning:selection" in captured.out


def test_sports_tuning_plan_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "sports-tuning-plan", "--suite-paths", "sports-a.json", "sports-b.json"],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_sports_tuning_plan",
        lambda **kwargs: SimpleNamespace(experiment_family="selection"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_tuning_plan",
        lambda plan: f"sports-tuning:{plan.experiment_family}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-tuning:selection" in captured.out


def test_sports_candidate_presets_command_prints_registry(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "sports-candidate-presets", "--suite-paths", "sports-a.json", "sports-b.json"],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_sports_tuning_plan",
        lambda **kwargs: SimpleNamespace(experiment_family="selection"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_sports_candidate_preset_registry",
        lambda plan: {"selection_higher_edge_gate": {"match": {"league": "nba"}}},
    )

    cli.main()

    captured = capsys.readouterr()
    assert "selection_higher_edge_gate" in captured.out


def test_sports_auto_experiments_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "sports-auto-experiments", "--suite-paths", "sports-a.json", "sports-b.json", "--snapshot-path", "sports.jsonl"],
    )
    async def _fake_auto(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(promotion_target="selection_higher_edge_gate")
    monkeypatch.setattr("pm_bot.cli.run_sports_auto_experiments", _fake_auto)
    monkeypatch.setattr(
        "pm_bot.cli.format_sports_auto_experiments_report",
        lambda report: f"sports-auto:{report.promotion_target}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "sports-auto:selection_higher_edge_gate" in captured.out


def test_sports_preset_lifecycle_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "sports-preset-lifecycle", "--suite-paths", "sports-a.json", "sports-b.json", "--snapshot-path", "sports.jsonl"],
    )
    async def _fake_auto(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_sports_auto_experiments", _fake_auto)
    monkeypatch.setattr("pm_bot.cli.build_sports_preset_lifecycle", lambda **kwargs: SimpleNamespace(next_working_preset="selection_higher_edge_gate"))
    monkeypatch.setattr("pm_bot.cli.format_sports_preset_lifecycle", lambda lifecycle: f"sports-lifecycle:{lifecycle.next_working_preset}")

    cli.main()

    captured = capsys.readouterr()
    assert "sports-lifecycle:selection_higher_edge_gate" in captured.out


def test_sports_preset_change_package_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "sports-preset-change-package", "--suite-paths", "sports-a.json", "sports-b.json", "--snapshot-path", "sports.jsonl"],
    )
    async def _fake_auto(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_sports_auto_experiments", _fake_auto)
    monkeypatch.setattr("pm_bot.cli.build_sports_preset_promotion_evidence", lambda **kwargs: SimpleNamespace(ready_to_apply=True))
    monkeypatch.setattr("pm_bot.cli.build_sports_preset_lifecycle", lambda **kwargs: SimpleNamespace(next_working_preset="selection_higher_edge_gate"))
    monkeypatch.setattr("pm_bot.cli.build_sports_preset_change_package", lambda **kwargs: SimpleNamespace(next_working_preset="selection_higher_edge_gate", ready_to_apply=True))
    monkeypatch.setattr("pm_bot.cli.format_sports_preset_change_package", lambda package: f"sports-change:{package.next_working_preset}:{str(package.ready_to_apply).lower()}")

    cli.main()

    captured = capsys.readouterr()
    assert "sports-change:selection_higher_edge_gate:true" in captured.out


def test_weather_learning_report_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-learning-report",
            "--suite-paths",
            "weather-a.json",
            "weather-b.json",
        ],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_weather_learning_report",
        lambda **kwargs: SimpleNamespace(recommended_next_experiment="settlement"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_learning_report",
        lambda report: f"weather-learning:{report.recommended_next_experiment}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-learning:settlement" in captured.out


def test_weather_tuning_plan_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "weather-tuning-plan", "--suite-paths", "weather-a.json", "weather-b.json"],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_weather_tuning_plan",
        lambda **kwargs: SimpleNamespace(experiment_family="settlement"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_tuning_plan",
        lambda plan: f"weather-tuning:{plan.experiment_family}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-tuning:settlement" in captured.out


def test_weather_candidate_presets_command_prints_registry(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pm_bot.cli", "weather-candidate-presets", "--suite-paths", "weather-a.json", "weather-b.json"],
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_weather_tuning_plan",
        lambda **kwargs: SimpleNamespace(experiment_family="settlement"),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_weather_candidate_preset_registry",
        lambda plan: {"settlement_higher_strip_gate": {"match": {"event_family": "daily_high_temperature_threshold"}}},
    )

    cli.main()

    captured = capsys.readouterr()
    assert "settlement_higher_strip_gate" in captured.out


def test_weather_auto_experiments_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-auto-experiments",
            "--suite-paths",
            "weather-a.json",
            "weather-b.json",
            "--snapshot-path",
            "weather.jsonl",
            "--forecast-runs-path",
            "forecast_runs.json",
            "--skill-path",
            "skills.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_json_records", lambda *args, **kwargs: [])
    async def _fake_auto(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(promotion_target="settlement_higher_strip_gate")
    monkeypatch.setattr("pm_bot.cli.run_weather_auto_experiments", _fake_auto)
    monkeypatch.setattr(
        "pm_bot.cli.format_weather_auto_experiments_report",
        lambda report: f"weather-auto:{report.promotion_target}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "weather-auto:settlement_higher_strip_gate" in captured.out


def test_weather_preset_lifecycle_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-preset-lifecycle",
            "--suite-paths",
            "weather-a.json",
            "weather-b.json",
            "--snapshot-path",
            "weather.jsonl",
            "--forecast-runs-path",
            "forecast_runs.json",
            "--skill-path",
            "skills.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_json_records", lambda *args, **kwargs: [])
    async def _fake_auto(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_weather_auto_experiments", _fake_auto)
    monkeypatch.setattr("pm_bot.cli.build_weather_preset_lifecycle", lambda **kwargs: SimpleNamespace(next_working_preset="settlement_higher_strip_gate"))
    monkeypatch.setattr("pm_bot.cli.format_weather_preset_lifecycle", lambda lifecycle: f"weather-lifecycle:{lifecycle.next_working_preset}")

    cli.main()

    captured = capsys.readouterr()
    assert "weather-lifecycle:settlement_higher_strip_gate" in captured.out


def test_weather_preset_change_package_command_prints_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "weather-preset-change-package",
            "--suite-paths",
            "weather-a.json",
            "weather-b.json",
            "--snapshot-path",
            "weather.jsonl",
            "--forecast-runs-path",
            "forecast_runs.json",
            "--skill-path",
            "skills.json",
        ],
    )
    monkeypatch.setattr("pm_bot.cli._load_json_records", lambda *args, **kwargs: [])
    async def _fake_auto(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace()
    monkeypatch.setattr("pm_bot.cli.run_weather_auto_experiments", _fake_auto)
    monkeypatch.setattr("pm_bot.cli.build_weather_preset_promotion_evidence", lambda **kwargs: SimpleNamespace(ready_to_apply=True))
    monkeypatch.setattr("pm_bot.cli.build_weather_preset_lifecycle", lambda **kwargs: SimpleNamespace(next_working_preset="settlement_higher_strip_gate"))
    monkeypatch.setattr("pm_bot.cli.build_weather_preset_change_package", lambda **kwargs: SimpleNamespace(next_working_preset="settlement_higher_strip_gate", ready_to_apply=True))
    monkeypatch.setattr("pm_bot.cli.format_weather_preset_change_package", lambda package: f"weather-change:{package.next_working_preset}:{str(package.ready_to_apply).lower()}")

    cli.main()

    captured = capsys.readouterr()
    assert "weather-change:settlement_higher_strip_gate:true" in captured.out


def test_run_paper_crypto_session_writes_promotion_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    async def _fake_run_crypto_paper_session(**kwargs: object) -> object:
        return object()
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "run-paper-crypto-session",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--state-path",
            "paper-state.json",
            "--event-path",
            "paper-events.jsonl",
            "--metrics-path",
            "paper-metrics.json",
            "--promotion-summary-path",
            "promotion-summary.md",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.run_crypto_paper_session", _fake_run_crypto_paper_session)
    monkeypatch.setattr("pm_bot.cli.format_dashboard_summary", lambda result: "paper-summary")
    monkeypatch.setattr(
        "pm_bot.cli.validate_promotion_readiness",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            ready=True,
            source_config_dir=str(kwargs["source_config_dir"]),
            target_config_dir=str(kwargs["target_config_dir"]),
            blockers=(),
            warnings=(),
            checks={},
            rollback_triggers=(),
            escalation_actions=(),
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_promotion_artifact_review",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            source_status="running",
            source_halt_reason="none",
            note_present=False,
            shadow_status=None,
            shadow_halt_reason=None,
            source_orders_submitted=1,
            shadow_orders_submitted=None,
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_promotion_operator_summary",
        lambda **kwargs: captured.update(kwargs) or Path(kwargs["path"]),
    )

    cli.main()

    assert captured["path"] == "promotion-summary.md"
    assert captured["readiness"].stage == "paper_to_sync_shadow"


def test_run_sync_crypto_session_writes_promotion_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    async def _fake_run_crypto_sync_session(**kwargs: object) -> object:
        return object()
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "run-sync-crypto-session",
            "--config-dir",
            "configs/profiles/sync-normal-shadow-v1",
            "--state-path",
            "sync-live-state.json",
            "--event-path",
            "sync-live-events.jsonl",
            "--metrics-path",
            "sync-live-metrics.json",
            "--shadow-state-path",
            "sync-shadow-state.json",
            "--shadow-event-path",
            "sync-shadow-events.jsonl",
            "--shadow-metrics-path",
            "sync-shadow-metrics.json",
            "--promotion-summary-path",
            "sync-promotion-summary.md",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.run_crypto_sync_session", _fake_run_crypto_sync_session)
    monkeypatch.setattr("pm_bot.cli.format_sync_session_summary", lambda result: "sync-summary")
    monkeypatch.setattr(
        "pm_bot.cli.validate_promotion_readiness",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            ready=False,
            source_config_dir=str(kwargs["source_config_dir"]),
            target_config_dir=str(kwargs["target_config_dir"]),
            blockers=("missing note",),
            warnings=(),
            checks={},
            rollback_triggers=(),
            escalation_actions=(),
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.build_promotion_artifact_review",
        lambda **kwargs: SimpleNamespace(
            stage=kwargs["stage"],
            source_status="running",
            source_halt_reason="none",
            note_present=False,
            shadow_status="running",
            shadow_halt_reason="none",
            source_orders_submitted=1,
            shadow_orders_submitted=1,
        ),
    )
    monkeypatch.setattr(
        "pm_bot.cli.write_promotion_operator_summary",
        lambda **kwargs: captured.update(kwargs) or Path(kwargs["path"]),
    )

    cli.main()

    assert captured["path"] == "sync-promotion-summary.md"
    assert captured["readiness"].stage == "sync_shadow_to_small_live_baseline"


def test_show_dashboard_renders_promotion_summary_when_path_is_provided(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "show-dashboard",
            "--config-dir",
            "configs/profiles/paper-baseline-v1",
            "--state-path",
            "runtime-state.json",
            "--promotion-summary-path",
            "promotion-summary.md",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.load_settings_from_directory", lambda path: SimpleNamespace(risk=object(), trading=object()))

    class _RiskManager:
        def __init__(self, **kwargs: object) -> None:
            pass

        def advance_trading_day(self) -> None:
            return None

        def dashboard_state(self) -> object:
            return object()

    monkeypatch.setattr("pm_bot.cli.BasicRiskManager", _RiskManager)
    monkeypatch.setattr("pm_bot.cli.JsonRuntimeStateStore", lambda path: object())
    monkeypatch.setattr(
        "pm_bot.cli._render_dashboard_with_ops_summary",
        lambda dashboard, trading_settings=None, promotion_summary_path=None, combined_summary_path=None, ops_summary_path=None, ops_console_path=None, ops_one_page_path=None: f"dashboard:{promotion_summary_path}:{combined_summary_path}:{ops_summary_path}:{ops_console_path}:{ops_one_page_path}",
    )

    cli.main()

    captured = capsys.readouterr()
    assert "dashboard:promotion-summary.md:None:None:None" in captured.out


def test_run_fixed_window_experiments_cli_passes_window_mining_args(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    async def _fake_run_fixed_window_experiments(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(summary_path="summary.md")

    monkeypatch.setattr(
        "sys.argv",
        [
            "pm_bot.cli",
            "run-fixed-window-experiments",
            "--snapshot-path",
            "capture.jsonl",
            "--event-path",
            "events.jsonl",
            "--window-snapshots",
            "12",
            "--top-windows",
            "2",
        ],
    )
    monkeypatch.setattr("pm_bot.cli.run_fixed_window_experiments", _fake_run_fixed_window_experiments)
    monkeypatch.setattr("pm_bot.cli.format_fixed_window_report", lambda report: "fixed-window-ok")

    cli.main()

    assert captured["snapshot_path"] == "capture.jsonl"
    assert captured["event_path"] == "events.jsonl"
    assert captured["window_snapshots"] == 12
    assert captured["top_windows"] == 2
    assert "fixed-window-ok" in capsys.readouterr().out


def test_load_underlying_states_reads_multiple_underlyings(tmp_path: Path) -> None:
    payload_path = tmp_path / "underlying_states.json"
    payload_path.write_text(
        json.dumps(
            [
                {
                    "underlying": "ETH",
                    "as_of": "2026-03-27T15:14:00Z",
                    "spot_price": 1850.0,
                    "daily_return": -0.032,
                    "realized_volatility": 0.62,
                    "implied_volatility": 0.71,
                },
                {
                    "underlying": "BTC",
                    "as_of": "2026-03-27T15:15:00Z",
                    "spot_price": 79000.0,
                    "daily_return": -0.028,
                    "realized_volatility": 0.58,
                    "implied_volatility": 0.66,
                },
            ],
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    states = _load_underlying_states(str(payload_path))

    assert sorted(states) == ["BTC", "ETH"]
    assert states["ETH"].spot_price == pytest.approx(1850.0)
    assert states["BTC"].spot_price == pytest.approx(79000.0)


def _write_integrity_artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    started_at = datetime(2026, 3, 26, 5, 35, 0, tzinfo=UTC)
    snapshot_at = started_at + timedelta(minutes=1)
    fill_at = snapshot_at + timedelta(seconds=2)
    close_at = snapshot_at + timedelta(seconds=3)
    events = [
        {
            "event_type": "market.snapshot_processed",
            "payload": {
                "market_id": "m1",
                "processed_snapshots": 1,
                "submitted_orders": 1,
                "stale_orders_cancelled": 0,
                "updated_at": snapshot_at.isoformat(),
            },
        },
        {
            "event_type": "signal.generated",
            "payload": {
                "strategy_id": "crypto.execution_sample",
                "market_id": "m1",
                "token_id": "yes-token",
                "side": "buy_yes",
                "generated_at": snapshot_at.isoformat(),
            },
        },
        {
            "event_type": "order.submitted",
            "payload": {
                "order_id": "paper-1",
                "strategy_id": "crypto.execution_sample",
                "market_id": "m1",
                "token_id": "yes-token",
                "side": "buy_yes",
                "price": 0.52,
                "size": 5.0,
                "notional": 2.6,
                "created_at": snapshot_at.isoformat(),
            },
        },
        {
            "event_type": "order.filled",
            "payload": {
                "order_id": "paper-1",
                "market_id": "m1",
                "token_id": "yes-token",
                "strategy_id": "crypto.execution_sample",
                "trade_side": "BUY",
                "status": "filled",
                "matched_shares": 5.0,
                "matched_notional": 2.6,
                "average_fill_price": 0.52,
                "fill_shares_delta": 5.0,
                "fill_notional_delta": 2.6,
                "fill_source": "taker",
                "mid_price": 0.51,
                "fill_age_ms": 2000.0,
                "updated_at": fill_at.isoformat(),
            },
        },
        {
            "event_type": "trade.closed",
            "payload": {
                "market_id": "m1",
                "token_id": "yes-token",
                "strategy_id": "crypto.execution_sample",
                "realized_pnl": 0.11,
                "fees_paid": 0.01,
                "net_pnl": 0.1,
                "closed_at": close_at.isoformat(),
            },
        },
    ]

    metrics = PaperExecutionMetrics()
    metrics.note_snapshot(snapshot_at)
    for event in events[1:]:
        metrics.record_event(event["event_type"], event["payload"])

    state = RuntimeState(
        starting_equity=1000.0,
        day_starting_equity=1000.0,
        realized_pnl_today=0.1,
        orders_today=1,
        day_started_at=started_at,
        updated_at=close_at,
        last_data_success_at=snapshot_at,
    )

    metrics_path = tmp_path / "metrics.json"
    event_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "state.json"
    metrics_path.write_text(json.dumps(metrics.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
    event_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=True) for event in events) + "\n",
        encoding="utf-8",
    )
    state_path.write_text(json.dumps(runtime_state_to_dict(state), ensure_ascii=True, indent=2), encoding="utf-8")
    return metrics_path, event_path, state_path
