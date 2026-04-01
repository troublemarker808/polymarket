"""Command-line helpers for validating the foundation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from pm_bot.adapters.polymarket import fetch_geoblock_status_sync
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.settings import TradingSettings
from pm_bot.execution import describe_execution_configuration
from pm_bot.execution.metrics_report import compare_metrics, format_metric_comparison, load_metrics_file
from pm_bot.multi_board_ops import (
    build_multi_board_ops_report,
    format_multi_board_ops_report,
    write_multi_board_ops_report,
)
from pm_bot.ops_console import (
    build_unified_ops_console,
    format_unified_ops_console,
    write_unified_ops_console,
)
from pm_bot.ops_control_panel import build_ops_control_panel, format_ops_control_panel
from pm_bot.ops_history import (
    build_ops_history_report,
    format_ops_history_report,
    load_ops_history_report,
    write_ops_history_report,
)
from pm_bot.ops_one_page import build_ops_one_page, format_ops_one_page, write_ops_one_page
from pm_bot.ops_schedule import run_scheduled_ops_bundle
from pm_bot.strategy_governance import (
    build_strategy_governance_report,
    format_strategy_governance_report,
    write_strategy_governance_report,
)
from pm_bot.strategy_change_window import (
    build_strategy_change_window,
    build_strategy_change_window_from_report_path,
    format_strategy_change_window,
    write_strategy_change_window,
)
from pm_bot.strategy_governance_decision import (
    build_strategy_governance_decision,
    format_strategy_governance_decision,
    write_strategy_governance_decision,
)
from pm_bot.strategy_execute_window import (
    execute_strategy_change_window,
    format_strategy_execution_window_report,
    write_strategy_execution_window_report,
)
from pm_bot.strategy_feedback_loop import (
    build_strategy_feedback_loop_report,
    format_strategy_feedback_loop_report,
    write_strategy_feedback_loop_report,
)
from pm_bot.strategy_loop_history import (
    build_strategy_loop_history_report,
    format_strategy_loop_history_report,
    write_strategy_loop_history_report,
)
from pm_bot.strategy_loop_decision import (
    build_strategy_loop_decision,
    format_strategy_loop_decision,
    load_strategy_loop_decision,
    write_strategy_loop_decision,
)
from pm_bot.strategy_cycle_package import load_strategy_cycle_package
from pm_bot.ops_automation import (
    build_daily_ops_bundle,
    format_daily_ops_bundle,
    write_daily_ops_bundle,
)
from pm_bot.promotion import format_promotion_readiness_report, validate_promotion_readiness
from pm_bot.promotion_evidence import (
    build_promotion_evidence_report,
    format_promotion_evidence_report,
    write_promotion_evidence_report,
)
from pm_bot.promotion_artifacts import (
    build_promotion_artifact_review,
    build_promotion_operator_summary,
    format_promotion_artifact_review,
    format_promotion_operator_summary,
    write_combined_operator_summary,
    write_promotion_operator_summary,
    write_operator_note_template,
)
from pm_bot.registry import build_default_registry
from pm_bot.research import (
    default_phase1_config_dir,
    export_crypto_family_window,
    format_crypto_family_export_result,
    format_crypto_signal_report,
    format_crypto_window_family_report,
    format_fixed_window_report,
    format_phase1_replay_result,
    format_paper_integrity_report,
    format_replay_determinism_report,
    format_window_mining_report,
    format_autoresearch_report,
    format_research_summary,
    generate_crypto_signal_report,
    generate_crypto_window_family_report,
    generate_autoresearch_report,
    generate_paper_integrity_report,
    generate_replay_determinism_report,
    mine_fixed_windows,
    run_backtest,
    run_fixed_window_experiments,
    run_phase1_replay,
    run_replay,
    write_crypto_family_export_result,
    write_crypto_signal_report,
    write_crypto_window_family_report,
    write_autoresearch_report,
    write_fixed_window_report,
    write_paper_integrity_report,
    write_replay_determinism_report,
    write_window_mining_report,
)
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.dashboard import render_dashboard, render_dashboard_with_ops_summary
from pm_bot.runtime.live_session import format_live_session_summary, run_crypto_live_session
from pm_bot.runtime.paper_session import (
    format_dashboard_summary,
    run_crypto_phase2_paper_session,
    run_crypto_paper_session,
    run_crypto_paper_session_once,
)
from pm_bot.runtime.sync_session import format_sync_session_summary, run_crypto_sync_session
from pm_bot.runtime.state import DashboardState
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore
from pm_bot.strategies.crypto.phase1.baseline import get_locked_crypto_calibration_baseline_preset
from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.calibration import (
    format_crypto_calibration_experiment_report,
    format_crypto_calibration_report,
    generate_crypto_calibration_report,
    run_crypto_calibration_experiments,
)
from pm_bot.strategies.crypto.phase1.selection import (
    format_crypto_market_selection_report,
    generate_crypto_market_selection_report,
)
from pm_bot.strategies.crypto.phase1.state_loader import load_underlying_states
from pm_bot.strategies.crypto.phase2.replay import run_crypto_phase2_replay
from pm_bot.strategies.crypto.phase2.suite import (
    format_crypto_phase2_suite_result,
    run_crypto_phase2_suite,
)
from pm_bot.strategies.crypto.phase2.final_report import format_crypto_phase2_final_scorecard
from pm_bot.strategies.crypto.phase2.auto_experiments import (
    format_crypto_phase2_auto_experiments_report,
    run_crypto_phase2_auto_experiments,
)
from pm_bot.strategies.crypto.phase2.preset_lifecycle import (
    build_crypto_phase2_preset_lifecycle,
    format_crypto_phase2_preset_lifecycle,
    build_crypto_phase2_working_preset_patch,
)
from pm_bot.strategies.crypto.phase2.preset_promotion_evidence import (
    build_crypto_phase2_preset_promotion_evidence,
    format_crypto_phase2_preset_promotion_evidence,
    write_crypto_phase2_preset_promotion_evidence,
)
from pm_bot.strategies.crypto.phase2.preset_change_package import (
    build_crypto_phase2_preset_change_package,
    format_crypto_phase2_preset_change_package,
    write_crypto_phase2_preset_change_package,
)
from pm_bot.strategies.crypto.phase2.preset_apply_plan import (
    build_crypto_phase2_preset_apply_plan,
    format_crypto_phase2_preset_apply_plan,
    write_crypto_phase2_preset_apply_plan,
)
from pm_bot.strategies.crypto.phase2.preset_apply import (
    apply_crypto_phase2_preset_change_package,
    format_crypto_phase2_preset_apply_result,
    write_crypto_phase2_preset_apply_result,
)
from pm_bot.strategies.crypto.phase2.preset_rollback import (
    format_crypto_phase2_preset_rollback_result,
    rollback_crypto_phase2_preset_application,
    write_crypto_phase2_preset_rollback_result,
)
from pm_bot.strategies.crypto.phase2.preset_verify import (
    build_crypto_phase2_preset_verification_report,
    format_crypto_phase2_preset_verification_report,
    write_crypto_phase2_preset_verification_report,
)
from pm_bot.strategies.crypto.phase2.learning_report import (
    build_crypto_phase2_learning_report,
    format_crypto_phase2_learning_report,
    write_crypto_phase2_learning_report,
)
from pm_bot.strategies.crypto.phase2.tuning_plan import (
    build_crypto_phase2_candidate_preset_registry,
    build_crypto_phase2_tuning_plan,
    format_crypto_phase2_tuning_plan,
    write_crypto_phase2_candidate_preset_registry,
    write_crypto_phase2_tuning_plan,
)
from pm_bot.strategies.sports.phase1 import (
    build_sports_candidate_preset_registry,
    format_sports_closing_line_report,
    format_sports_event_scorecard_report,
    format_sports_final_scorecard,
    format_sports_learning_report,
    format_sports_market_selection_report,
    format_sports_tuning_plan,
    build_sports_learning_report,
    build_sports_tuning_plan,
    generate_sports_closing_line_report,
    generate_sports_event_scorecard_report,
    generate_sports_final_scorecard,
    generate_sports_market_selection_report,
)
from pm_bot.strategies.sports.phase1.auto_experiments import (
    format_sports_auto_experiments_report,
    run_sports_auto_experiments,
    write_sports_auto_experiments_report,
)
from pm_bot.strategies.sports.phase1.preset_change_package import (
    build_sports_preset_change_package,
    format_sports_preset_change_package,
    write_sports_preset_change_package,
)
from pm_bot.strategies.sports.phase1.preset_apply import (
    apply_sports_preset_change_package,
    format_sports_preset_apply_result,
    write_sports_preset_apply_result,
)
from pm_bot.strategies.sports.phase1.preset_apply_plan import (
    build_sports_preset_apply_plan,
    format_sports_preset_apply_plan,
    write_sports_preset_apply_plan,
)
from pm_bot.strategies.sports.phase1.preset_lifecycle import (
    build_sports_preset_lifecycle,
    format_sports_preset_lifecycle,
)
from pm_bot.strategies.sports.phase1.preset_promotion_evidence import (
    build_sports_preset_promotion_evidence,
    format_sports_preset_promotion_evidence,
    write_sports_preset_promotion_evidence,
)
from pm_bot.strategies.sports.phase1.preset_rollback import (
    format_sports_preset_rollback_result,
    rollback_sports_preset_application,
    write_sports_preset_rollback_result,
)
from pm_bot.strategies.sports.phase1.preset_verify import (
    build_sports_preset_verification_report,
    format_sports_preset_verification_report,
    write_sports_preset_verification_report,
)
from pm_bot.strategies.weather.phase1 import (
    build_weather_candidate_preset_registry,
    build_weather_learning_report,
    build_weather_tuning_plan,
    format_weather_final_scorecard,
    format_weather_learning_report,
    format_weather_market_selection_report,
    format_weather_run_scorecard_report,
    format_weather_settlement_audit_report,
    format_weather_tuning_plan,
    generate_weather_final_scorecard,
    generate_weather_market_selection_report,
    generate_weather_run_scorecard_report,
    generate_weather_settlement_audit_report,
)
from pm_bot.strategies.weather.phase1.auto_experiments import (
    format_weather_auto_experiments_report,
    run_weather_auto_experiments,
    write_weather_auto_experiments_report,
)
from pm_bot.strategies.weather.phase1.preset_change_package import (
    build_weather_preset_change_package,
    format_weather_preset_change_package,
    write_weather_preset_change_package,
)
from pm_bot.strategies.weather.phase1.preset_apply import (
    apply_weather_preset_change_package,
    format_weather_preset_apply_result,
    write_weather_preset_apply_result,
)
from pm_bot.strategies.weather.phase1.preset_apply_plan import (
    build_weather_preset_apply_plan,
    format_weather_preset_apply_plan,
    write_weather_preset_apply_plan,
)
from pm_bot.strategies.weather.phase1.preset_lifecycle import (
    build_weather_preset_lifecycle,
    format_weather_preset_lifecycle,
)
from pm_bot.strategies.weather.phase1.preset_promotion_evidence import (
    build_weather_preset_promotion_evidence,
    format_weather_preset_promotion_evidence,
    write_weather_preset_promotion_evidence,
)
from pm_bot.strategies.weather.phase1.preset_rollback import (
    format_weather_preset_rollback_result,
    rollback_weather_preset_application,
    write_weather_preset_rollback_result,
)
from pm_bot.strategies.weather.phase1.preset_verify import (
    build_weather_preset_verification_report,
    format_weather_preset_verification_report,
    write_weather_preset_verification_report,
)
from pm_bot.validation import main as run_repository_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket bot foundation CLI")
    parser.add_argument(
        "command",
        choices=(
            "check-geoblock",
            "run-live-crypto-session",
            "run-sync-crypto-session",
            "validate-repo",
            "validate-config",
            "validate-live-config",
            "multi-board-ops-report",
            "ops-console",
            "ops-control-panel",
            "ops-history-report",
            "ops-one-page",
            "daily-ops-bundle",
            "scheduled-ops-bundle",
            "validate-promotion-readiness",
            "promotion-evidence-report",
            "promotion-artifact-review",
            "promotion-operator-summary",
            "write-operator-note-template",
            "paper-crypto-once",
            "run-paper-crypto-phase2-session",
            "run-paper-crypto-session",
            "compare-execution-metrics",
            "autoresearch-report",
            "mine-fixed-windows",
            "run-fixed-window-experiments",
            "check-paper-integrity",
            "check-replay-determinism",
            "replay",
            "phase1-replay",
            "crypto-calibration-report",
            "crypto-calibration-experiments",
            "crypto-family-export",
            "sports-market-selection-report",
            "sports-closing-line-report",
            "sports-event-scorecard-report",
            "sports-final-report",
            "sports-learning-report",
            "sports-tuning-plan",
            "sports-candidate-presets",
            "sports-auto-experiments",
            "sports-preset-lifecycle",
            "sports-preset-promotion-evidence",
            "sports-preset-change-package",
            "sports-preset-apply-plan",
            "sports-apply-package",
            "sports-rollback-package",
            "sports-verify-application",
            "weather-market-selection-report",
            "weather-settlement-audit-report",
            "weather-run-scorecard-report",
            "weather-final-report",
            "weather-learning-report",
            "weather-tuning-plan",
            "weather-candidate-presets",
            "weather-auto-experiments",
            "weather-preset-lifecycle",
            "weather-preset-promotion-evidence",
            "weather-preset-change-package",
            "weather-preset-apply-plan",
            "weather-apply-package",
            "weather-rollback-package",
            "weather-verify-application",
            "crypto-market-selection-report",
            "crypto-signal-report",
            "crypto-window-family-report",
            "crypto-phase2-replay",
            "crypto-phase2-suite",
            "crypto-phase2-final-report",
            "crypto-phase2-learning-report",
            "crypto-phase2-tuning-plan",
            "crypto-phase2-candidate-presets",
            "crypto-phase2-auto-experiments",
            "crypto-phase2-preset-lifecycle",
            "crypto-phase2-working-preset-patch",
            "crypto-phase2-preset-promotion-evidence",
            "crypto-phase2-preset-change-package",
            "crypto-phase2-preset-apply-plan",
            "crypto-phase2-apply-package",
            "crypto-phase2-rollback-package",
            "crypto-phase2-verify-application",
            "strategy-governance-report",
            "strategy-change-window",
            "strategy-governance-decision",
            "strategy-execute-window",
            "strategy-feedback-loop",
            "strategy-loop-history",
            "strategy-loop-decision",
            "backtest",
            "show-dashboard",
            "manual-resume",
        ),
        help="Run repository validation, config checks, sessions, and research workflows.",
    )
    parser.add_argument(
        "--board",
        choices=("crypto", "sports", "weather"),
        default=None,
        help="Board for board-specific research commands.",
    )
    parser.add_argument(
        "--config-dir",
        default="configs",
        help="Directory containing base and category config files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of snapshots to process for one-shot paper commands.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum number of Gamma pages to scan for one-shot paper commands.",
    )
    parser.add_argument(
        "--max-market-snapshots",
        type=int,
        default=None,
        help="Optional cap for market snapshots in live-session commands.",
    )
    parser.add_argument(
        "--max-user-events",
        type=int,
        default=None,
        help="Optional cap for user-channel events in live-session commands.",
    )
    parser.add_argument(
        "--state-path",
        default="data/runtime/runtime_state.json",
        help="Path to the persisted runtime state JSON file.",
    )
    parser.add_argument(
        "--promotion-scorecard-path",
        default=None,
        help="Optional crypto phase2 final_scorecard.json path used to include promotion gate status in autoresearch reports.",
    )
    parser.add_argument(
        "--shadow-state-path",
        default="data/runtime/shadow-runtime-state.json",
        help="Path to the persisted shadow runtime state JSON file.",
    )
    parser.add_argument(
        "--snapshot-path",
        default=None,
        help="Replay/backtest input path, or optional snapshot capture output path for paper commands.",
    )
    parser.add_argument(
        "--suite-paths",
        nargs="+",
        default=None,
        help="One or more crypto phase2 suite.json paths for cross-run learning reports.",
    )
    parser.add_argument(
        "--candidate-underlying",
        default=None,
        help="Optional underlying match for generated crypto phase2 candidate presets.",
    )
    parser.add_argument(
        "--candidate-event-family",
        default=None,
        help="Optional event_family match for generated crypto phase2 candidate presets.",
    )
    parser.add_argument(
        "--change-package-path",
        default=None,
        help="Path to a crypto phase2 preset change package JSON file.",
    )
    parser.add_argument(
        "--target-config-path",
        default=None,
        help="Path to the target crypto phase2 TOML config to apply a preset package onto.",
    )
    parser.add_argument(
        "--output-config-path",
        default=None,
        help="Optional output path for applied crypto phase2 config files.",
    )
    parser.add_argument(
        "--backup-config-path",
        default=None,
        help="Path to a backup crypto phase2 TOML config used for rollback helpers.",
    )
    parser.add_argument(
        "--train-snapshot-path",
        default=None,
        help="Train dataset snapshot path for crypto calibration reports.",
    )
    parser.add_argument(
        "--validation-snapshot-path",
        default=None,
        help="Validation dataset snapshot path for crypto calibration reports.",
    )
    parser.add_argument(
        "--holdout-snapshot-path",
        default=None,
        help="Holdout dataset snapshot path for crypto calibration reports.",
    )
    parser.add_argument(
        "--candidate-set",
        choices=("default", "refined", "btc_refined"),
        default="default",
        help="Candidate preset for crypto calibration experiments.",
    )
    parser.add_argument(
        "--underlying-state-path",
        default=None,
        help="JSON path containing one or more crypto underlying state payloads for crypto Phase 2 replay.",
    )
    parser.add_argument(
        "--baseline-suite-path",
        default=None,
        help="Baseline suite JSON path for crypto preset verification helpers.",
    )
    parser.add_argument(
        "--candidate-suite-path",
        default=None,
        help="Candidate suite JSON path for crypto preset verification helpers.",
    )
    parser.add_argument(
        "--crypto-change-package-path",
        default=None,
        help="Crypto preset change package JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--sports-change-package-path",
        default=None,
        help="Sports preset change package JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--weather-change-package-path",
        default=None,
        help="Weather preset change package JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--crypto-apply-plan-path",
        default=None,
        help="Optional crypto preset apply plan JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--sports-apply-plan-path",
        default=None,
        help="Optional sports preset apply plan JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--weather-apply-plan-path",
        default=None,
        help="Optional weather preset apply plan JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--crypto-apply-result-path",
        default=None,
        help="Optional crypto preset apply result JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--sports-apply-result-path",
        default=None,
        help="Optional sports preset apply result JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--weather-apply-result-path",
        default=None,
        help="Optional weather preset apply result JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--crypto-verify-path",
        default=None,
        help="Optional crypto preset verification JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--sports-verify-path",
        default=None,
        help="Optional sports preset verification JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--weather-verify-path",
        default=None,
        help="Optional weather preset verification JSON path for unified strategy governance reports.",
    )
    parser.add_argument(
        "--strategy-governance-path",
        default=None,
        help="Strategy governance report markdown path for strategy change window helpers.",
    )
    parser.add_argument(
        "--crypto-target-config-path",
        default=None,
        help="Optional crypto target config path for unified strategy execution windows.",
    )
    parser.add_argument(
        "--sports-target-config-path",
        default=None,
        help="Optional sports target config path for unified strategy execution windows.",
    )
    parser.add_argument(
        "--weather-target-config-path",
        default=None,
        help="Optional weather target config path for unified strategy execution windows.",
    )
    parser.add_argument(
        "--forecast-runs-path",
        default=None,
        help="JSON path containing weather forecast-run payloads.",
    )
    parser.add_argument(
        "--skill-path",
        default=None,
        help="JSON path containing weather model-skill payloads.",
    )
    parser.add_argument(
        "--event-path",
        default=None,
        help="Optional JSONL path where replay/backtest runtime events should be written.",
    )
    parser.add_argument(
        "--metrics-path",
        default=None,
        help="Optional JSON path where paper/live comparable metrics should be written.",
    )
    parser.add_argument(
        "--shadow-event-path",
        default=None,
        help="Optional JSONL path where synchronized shadow runtime events should be written.",
    )
    parser.add_argument(
        "--shadow-metrics-path",
        default=None,
        help="Optional JSON path where synchronized shadow metrics should be written.",
    )
    parser.add_argument(
        "--stage",
        choices=(
            "paper_to_sync_shadow",
            "sync_shadow_to_small_live_baseline",
            "sync_shadow_stability",
            "small_live_stability",
        ),
        default=None,
        help="Promotion readiness stage to validate.",
    )
    parser.add_argument(
        "--target-config-dir",
        default="configs/profiles/sync-normal-shadow-v1",
        help="Target config directory for promotion-readiness validation.",
    )
    parser.add_argument(
        "--note-path",
        default=None,
        help="Optional markdown operator note path for promotion review and readiness validation.",
    )
    parser.add_argument(
        "--promotion-summary-path",
        default=None,
        help="Optional markdown path where a promotion-facing operator summary should be written after a session.",
    )
    parser.add_argument(
        "--operator-summary-path",
        default=None,
        help="Optional markdown path where a combined runtime plus promotion operator summary should be written.",
    )
    parser.add_argument(
        "--ops-summary-path",
        default=None,
        help="Optional markdown path for a unified multi-board ops summary.",
    )
    parser.add_argument(
        "--daily-bundle-path",
        default=None,
        help="Optional markdown path for a generated daily ops bundle.",
    )
    parser.add_argument(
        "--console-path",
        default=None,
        help="Optional markdown path for a generated unified ops console report.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Optional root directory for dated scheduled ops bundle output.",
    )
    parser.add_argument(
        "--bundle-paths",
        nargs="+",
        default=None,
        help="One or more operator summary bundle markdown paths used for multi-session evidence reports.",
    )
    parser.add_argument(
        "--crypto-operator-summary-path",
        default=None,
        help="Crypto combined operator summary bundle path for unified multi-board ops reports.",
    )
    parser.add_argument(
        "--sports-scorecard-path",
        default=None,
        help="Sports event scorecard report path for unified multi-board ops reports.",
    )
    parser.add_argument(
        "--weather-scorecard-path",
        default=None,
        help="Weather run scorecard report path for unified multi-board ops reports.",
    )
    parser.add_argument(
        "--crypto-evidence-path",
        default=None,
        help="Optional crypto evidence report path for unified multi-board ops reports.",
    )
    parser.add_argument(
        "--promotion-evidence-stage",
        choices=("sync_shadow_stability", "small_live_stability"),
        default=None,
        help="Optional crypto promotion-evidence stage to build during scheduled ops bundling.",
    )
    parser.add_argument(
        "--promotion-evidence-bundle-paths",
        nargs="+",
        default=None,
        help="Optional historical crypto operator summary bundle paths used to build scheduled promotion evidence.",
    )
    parser.add_argument(
        "--strategy-feedback-loop-paths",
        nargs="+",
        default=None,
        help="Optional historical strategy feedback loop markdown paths used to build scheduled strategy loop history.",
    )
    parser.add_argument(
        "--ops-console-path",
        default=None,
        help="Optional unified ops console markdown path for dashboard rendering.",
    )
    parser.add_argument(
        "--ops-history-path",
        default=None,
        help="Optional ops history markdown path for control-panel rendering or history generation.",
    )
    parser.add_argument(
        "--one-page-path",
        default=None,
        help="Optional markdown path for a generated single-page ops summary.",
    )
    parser.add_argument(
        "--strategy-loop-decision-path",
        default=None,
        help="Optional strategy loop decision markdown path for ops control-panel and one-page commands.",
    )
    parser.add_argument(
        "--strategy-cycle-package-path",
        default=None,
        help="Optional strategy cycle package markdown path for ops control-panel and one-page commands.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier for generated operator note templates.",
    )
    parser.add_argument(
        "--market-window",
        default=None,
        help="Human-readable market window for generated operator note templates.",
    )
    parser.add_argument(
        "--summary-every-snapshots",
        type=int,
        default=50,
        help="Print a paper session summary every N processed snapshots.",
    )
    parser.add_argument(
        "--exclude-bootstrap-from-limit",
        action="store_true",
        help="Do not count the initial bootstrap snapshot pass toward --max-market-snapshots.",
    )
    parser.add_argument(
        "--baseline-metrics-path",
        default=None,
        help="Baseline metrics JSON path for execution-metric comparison.",
    )
    parser.add_argument(
        "--candidate-metrics-path",
        default=None,
        help="Candidate metrics JSON path for execution-metric comparison.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional output path for generated markdown reports.",
    )
    parser.add_argument(
        "--selection-report-path",
        default=None,
        help="Optional market-selection report JSON path used to pre-block runtime watch-only series.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for fixed-window experiment artifacts.",
    )
    parser.add_argument(
        "--research-mode",
        choices=("replay", "backtest"),
        default="replay",
        help="Replay engine mode for fixed-window experiments.",
    )
    parser.add_argument(
        "--window-snapshots",
        type=int,
        default=30,
        help="Snapshot count per mined fixed window.",
    )
    parser.add_argument(
        "--top-windows",
        type=int,
        default=3,
        help="Maximum number of mined fixed windows to keep.",
    )
    parser.add_argument(
        "--underlying",
        choices=("BTC", "ETH"),
        default=None,
        help="Optional crypto-family underlying filter for export commands.",
    )
    parser.add_argument(
        "--event-family",
        choices=("dip", "reach"),
        default=None,
        help="Optional crypto-family event filter for export commands.",
    )
    parser.add_argument(
        "--series-key-contains",
        default=None,
        help="Optional substring filter for crypto series-key export commands.",
    )
    args = parser.parse_args()

    if args.command == "check-geoblock":
        status = fetch_geoblock_status_sync()
        print(f"blocked={str(status.blocked).lower()}")
        print(f"country={status.country}")
        print(f"region={status.region}")
        print(f"ip={status.ip}")
    elif args.command == "validate-repo":
        raise SystemExit(run_repository_validation())
    elif args.command == "run-live-crypto-session":
        live_session_result = asyncio.run(
            run_crypto_live_session(
                config_dir=args.config_dir,
                state_path=args.state_path,
                recorder_path=args.event_path or "data/runtime/live-events.jsonl",
                metrics_path=args.metrics_path or "data/runtime/live-metrics.latest.json",
                max_pages=args.max_pages,
                max_market_snapshots=args.max_market_snapshots,
                max_user_events=args.max_user_events,
                summary_every_snapshots=args.summary_every_snapshots,
                underlying_state_path=args.underlying_state_path,
            )
        )
        if args.operator_summary_path is not None:
            write_combined_operator_summary(
                path=args.operator_summary_path,
                dashboard=_typed_dashboard(live_session_result["dashboard"]),
                trading_settings=_typed_trading_settings(live_session_result.get("trading_settings")),
                metrics_path=args.metrics_path or "data/runtime/live-metrics.latest.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/live-events.jsonl",
                note_path=args.note_path,
                session_label="run-live-crypto-session",
            )
        print(format_live_session_summary(live_session_result))
    elif args.command == "run-sync-crypto-session":
        sync_session_result = asyncio.run(
            run_crypto_sync_session(
                config_dir=args.config_dir,
                live_state_path=args.state_path,
                live_event_path=args.event_path or "data/runtime/sync-live-events.jsonl",
                live_metrics_path=args.metrics_path or "data/runtime/sync-live-metrics.json",
                shadow_state_path=args.shadow_state_path,
                shadow_event_path=args.shadow_event_path or "data/runtime/sync-shadow-events.jsonl",
                shadow_metrics_path=args.shadow_metrics_path or "data/runtime/sync-shadow-metrics.json",
                max_pages=args.max_pages,
                max_market_snapshots=args.max_market_snapshots,
                max_user_events=args.max_user_events,
                summary_every_snapshots=args.summary_every_snapshots,
                underlying_state_path=args.underlying_state_path,
                selection_report_path=args.selection_report_path,
            )
        )
        if args.promotion_summary_path is not None:
            readiness = validate_promotion_readiness(
                stage="sync_shadow_to_small_live_baseline",
                source_config_dir=args.config_dir,
                target_config_dir=args.target_config_dir,
                metrics_path=args.metrics_path or "data/runtime/sync-live-metrics.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/sync-live-events.jsonl",
                shadow_metrics_path=args.shadow_metrics_path or "data/runtime/sync-shadow-metrics.json",
                shadow_state_path=args.shadow_state_path,
                shadow_event_path=args.shadow_event_path or "data/runtime/sync-shadow-events.jsonl",
                note_path=args.note_path,
            )
            review = build_promotion_artifact_review(
                stage="sync_shadow_to_small_live_baseline",
                metrics_path=args.metrics_path or "data/runtime/sync-live-metrics.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/sync-live-events.jsonl",
                note_path=args.note_path,
                shadow_metrics_path=args.shadow_metrics_path or "data/runtime/sync-shadow-metrics.json",
                shadow_state_path=args.shadow_state_path,
                shadow_event_path=args.shadow_event_path or "data/runtime/sync-shadow-events.jsonl",
            )
            write_promotion_operator_summary(
                path=args.promotion_summary_path,
                readiness=readiness,
                review=review,
            )
        if args.operator_summary_path is not None:
            promotion_summary = None
            if args.promotion_summary_path is not None:
                promotion_summary = build_promotion_operator_summary(
                    readiness=readiness,
                    review=review,
                )
            write_combined_operator_summary(
                path=args.operator_summary_path,
                dashboard=_typed_dashboard(sync_session_result.live_stats["dashboard"]),
                trading_settings=_typed_trading_settings(sync_session_result.live_stats.get("trading_settings")),
                promotion_summary=promotion_summary,
                metrics_path=args.metrics_path or "data/runtime/sync-live-metrics.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/sync-live-events.jsonl",
                note_path=args.note_path,
                session_label="run-sync-crypto-session",
            )
        print(format_sync_session_summary(sync_session_result))
    elif args.command == "validate-config":
        settings = load_settings_from_directory(args.config_dir)
        registry = build_default_registry()
        strategies = registry.build_enabled(settings=settings)
        print(f"mode={settings.app.mode.value}")
        print(f"enabled_categories={[category.value for category in settings.categories.enabled_categories()]}")
        print(f"strategies={[strategy.strategy_id for strategy in strategies]}")
        print(f"starting_equity={settings.trading.starting_equity}")
        print(f"default_order_notional={settings.trading.default_order_notional}")
        print(f"daily_order_limits={settings.trading.daily_order_soft_limit}/{settings.trading.daily_order_hard_limit}")
        print(f"max_daily_drawdown_pct={settings.risk.max_daily_drawdown_pct}")
        print(f"max_consecutive_losses={settings.risk.max_consecutive_losses}")
        execution_summary = describe_execution_configuration(settings=settings, env=os.environ)
        print(f"execution_adapter={execution_summary['adapter']}")
        print(f"live_orders_enabled={str(execution_summary['allow_live_orders']).lower()}")
    elif args.command == "validate-live-config":
        settings = load_settings_from_directory(args.config_dir)
        execution_summary = describe_execution_configuration(settings=settings, env=os.environ)
        for key, value in execution_summary.items():
            print(f"{key}={value}")
    elif args.command == "multi-board-ops-report":
        if args.crypto_operator_summary_path is None:
            parser.error("--crypto-operator-summary-path is required for multi-board-ops-report")
        if args.sports_scorecard_path is None:
            parser.error("--sports-scorecard-path is required for multi-board-ops-report")
        if args.weather_scorecard_path is None:
            parser.error("--weather-scorecard-path is required for multi-board-ops-report")
        multi_board_report = build_multi_board_ops_report(
            crypto_operator_summary_path=args.crypto_operator_summary_path,
            sports_scorecard_path=args.sports_scorecard_path,
            weather_scorecard_path=args.weather_scorecard_path,
            crypto_evidence_path=args.crypto_evidence_path,
        )
        if args.ops_summary_path is not None:
            write_multi_board_ops_report(
                path=args.ops_summary_path,
                report=multi_board_report,
            )
        print(format_multi_board_ops_report(multi_board_report))
    elif args.command == "daily-ops-bundle":
        if args.crypto_operator_summary_path is None:
            parser.error("--crypto-operator-summary-path is required for daily-ops-bundle")
        if args.sports_scorecard_path is None:
            parser.error("--sports-scorecard-path is required for daily-ops-bundle")
        if args.weather_scorecard_path is None:
            parser.error("--weather-scorecard-path is required for daily-ops-bundle")
        daily_bundle = build_daily_ops_bundle(
            crypto_operator_summary_path=args.crypto_operator_summary_path,
            sports_scorecard_path=args.sports_scorecard_path,
            weather_scorecard_path=args.weather_scorecard_path,
            crypto_evidence_path=args.crypto_evidence_path,
        )
        if args.daily_bundle_path is not None:
            write_daily_ops_bundle(
                path=args.daily_bundle_path,
                bundle=daily_bundle,
            )
        print(format_daily_ops_bundle(daily_bundle))
    elif args.command == "ops-console":
        if args.crypto_operator_summary_path is None:
            parser.error("--crypto-operator-summary-path is required for ops-console")
        if args.sports_scorecard_path is None:
            parser.error("--sports-scorecard-path is required for ops-console")
        if args.weather_scorecard_path is None:
            parser.error("--weather-scorecard-path is required for ops-console")
        console = build_unified_ops_console(
            crypto_operator_summary_path=args.crypto_operator_summary_path,
            sports_scorecard_path=args.sports_scorecard_path,
            weather_scorecard_path=args.weather_scorecard_path,
            crypto_evidence_path=args.crypto_evidence_path,
        )
        if args.console_path is not None:
            write_unified_ops_console(
                path=args.console_path,
                console=console,
            )
        print(format_unified_ops_console(console))
    elif args.command == "ops-control-panel":
        if args.crypto_operator_summary_path is None:
            parser.error("--crypto-operator-summary-path is required for ops-control-panel")
        if args.sports_scorecard_path is None:
            parser.error("--sports-scorecard-path is required for ops-control-panel")
        if args.weather_scorecard_path is None:
            parser.error("--weather-scorecard-path is required for ops-control-panel")
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        risk_manager.advance_trading_day()
        dashboard = risk_manager.dashboard_state()
        runtime_rendered = render_dashboard(dashboard, trading_settings=settings.trading)
        console = build_unified_ops_console(
            crypto_operator_summary_path=args.crypto_operator_summary_path,
            sports_scorecard_path=args.sports_scorecard_path,
            weather_scorecard_path=args.weather_scorecard_path,
            crypto_evidence_path=args.crypto_evidence_path,
        )
        history = load_ops_history_report(args.ops_history_path) if args.ops_history_path is not None else None
        strategy_loop_decision = (
            load_strategy_loop_decision(args.strategy_loop_decision_path)
            if args.strategy_loop_decision_path is not None
            else None
        )
        strategy_cycle_package = (
            load_strategy_cycle_package(args.strategy_cycle_package_path)
            if args.strategy_cycle_package_path is not None
            else None
        )
        panel = build_ops_control_panel(
            dashboard=dashboard,
            runtime_rendered=runtime_rendered,
            console=console,
            history=history,
            strategy_loop_decision=strategy_loop_decision,
            strategy_cycle_package=strategy_cycle_package,
        )
        print(runtime_rendered)
        print()
        print(format_ops_control_panel(panel))
    elif args.command == "ops-history-report":
        if args.output_root is None:
            parser.error("--output-root is required for ops-history-report")
        history_report = build_ops_history_report(output_root=args.output_root)
        if args.ops_history_path is not None:
            write_ops_history_report(path=args.ops_history_path, report=history_report)
        print(format_ops_history_report(history_report))
    elif args.command == "ops-one-page":
        if args.crypto_operator_summary_path is None:
            parser.error("--crypto-operator-summary-path is required for ops-one-page")
        if args.sports_scorecard_path is None:
            parser.error("--sports-scorecard-path is required for ops-one-page")
        if args.weather_scorecard_path is None:
            parser.error("--weather-scorecard-path is required for ops-one-page")
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        risk_manager.advance_trading_day()
        dashboard = risk_manager.dashboard_state()
        runtime_rendered = render_dashboard(dashboard, trading_settings=settings.trading)
        console = build_unified_ops_console(
            crypto_operator_summary_path=args.crypto_operator_summary_path,
            sports_scorecard_path=args.sports_scorecard_path,
            weather_scorecard_path=args.weather_scorecard_path,
            crypto_evidence_path=args.crypto_evidence_path,
        )
        history = load_ops_history_report(args.ops_history_path) if args.ops_history_path is not None else None
        strategy_loop_decision = (
            load_strategy_loop_decision(args.strategy_loop_decision_path)
            if args.strategy_loop_decision_path is not None
            else None
        )
        strategy_cycle_package = (
            load_strategy_cycle_package(args.strategy_cycle_package_path)
            if args.strategy_cycle_package_path is not None
            else None
        )
        page = build_ops_one_page(
            dashboard=dashboard,
            runtime_rendered=runtime_rendered,
            console=console,
            history=history,
            strategy_loop_decision=strategy_loop_decision,
            strategy_cycle_package=strategy_cycle_package,
        )
        if args.one_page_path is not None:
            write_ops_one_page(path=args.one_page_path, page=page)
        print(format_ops_one_page(page))
    elif args.command == "scheduled-ops-bundle":
        if args.crypto_operator_summary_path is None:
            parser.error("--crypto-operator-summary-path is required for scheduled-ops-bundle")
        if args.sports_scorecard_path is None:
            parser.error("--sports-scorecard-path is required for scheduled-ops-bundle")
        if args.weather_scorecard_path is None:
            parser.error("--weather-scorecard-path is required for scheduled-ops-bundle")
        if args.output_root is None:
            parser.error("--output-root is required for scheduled-ops-bundle")
        scheduled_result = run_scheduled_ops_bundle(
            crypto_operator_summary_path=args.crypto_operator_summary_path,
            sports_scorecard_path=args.sports_scorecard_path,
            weather_scorecard_path=args.weather_scorecard_path,
            crypto_evidence_path=args.crypto_evidence_path,
            promotion_evidence_stage=args.promotion_evidence_stage,
            promotion_evidence_bundle_paths=args.promotion_evidence_bundle_paths,
            strategy_feedback_loop_paths=args.strategy_feedback_loop_paths,
            output_root=args.output_root,
            run_id=args.run_id,
        )
        print(f"run_id={scheduled_result.run_id}")
        print(f"run_date={scheduled_result.run_date}")
        print(f"output_dir={scheduled_result.output_dir}")
        print(f"multi_board_report_path={scheduled_result.multi_board_report_path}")
        print(f"daily_bundle_path={scheduled_result.daily_bundle_path}")
        print(f"ops_console_path={scheduled_result.ops_console_path}")
        print(f"ops_history_path={scheduled_result.ops_history_path}")
        print(f"ops_one_page_path={scheduled_result.ops_one_page_path}")
        print(f"ops_followup_queue_path={scheduled_result.ops_followup_queue_path}")
        print(f"ops_decision_path={scheduled_result.ops_decision_path}")
        print(f"promotion_evidence_path={scheduled_result.promotion_evidence_path or ''}")
        print(f"strategy_loop_history_path={scheduled_result.strategy_loop_history_path or ''}")
        print(f"strategy_loop_decision_path={scheduled_result.strategy_loop_decision_path or ''}")
        print(f"strategy_cycle_package_path={scheduled_result.strategy_cycle_package_path or ''}")
        print(f"latest_multi_board_report_path={scheduled_result.latest_multi_board_report_path}")
        print(f"latest_daily_bundle_path={scheduled_result.latest_daily_bundle_path}")
        print(f"latest_ops_console_path={scheduled_result.latest_ops_console_path}")
        print(f"latest_ops_history_path={scheduled_result.latest_ops_history_path}")
        print(f"latest_ops_one_page_path={scheduled_result.latest_ops_one_page_path}")
        print(f"latest_ops_followup_queue_path={scheduled_result.latest_ops_followup_queue_path}")
        print(f"latest_ops_decision_path={scheduled_result.latest_ops_decision_path}")
        print(f"latest_promotion_evidence_path={scheduled_result.latest_promotion_evidence_path or ''}")
        print(f"latest_strategy_loop_history_path={scheduled_result.latest_strategy_loop_history_path or ''}")
        print(f"latest_strategy_loop_decision_path={scheduled_result.latest_strategy_loop_decision_path or ''}")
        print(f"latest_strategy_cycle_package_path={scheduled_result.latest_strategy_cycle_package_path or ''}")
    elif args.command == "validate-promotion-readiness":
        if args.stage is None:
            parser.error("--stage is required for validate-promotion-readiness")
        if args.metrics_path is None:
            parser.error("--metrics-path is required for validate-promotion-readiness")
        if args.state_path is None:
            parser.error("--state-path is required for validate-promotion-readiness")
        if args.event_path is None:
            parser.error("--event-path is required for validate-promotion-readiness")
        report = validate_promotion_readiness(
            stage=args.stage,
            source_config_dir=args.config_dir,
            target_config_dir=args.target_config_dir,
            metrics_path=args.metrics_path,
            state_path=args.state_path,
            event_path=args.event_path,
            shadow_metrics_path=args.shadow_metrics_path,
            shadow_state_path=args.shadow_state_path,
            shadow_event_path=args.shadow_event_path,
            note_path=args.note_path,
        )
        print(format_promotion_readiness_report(report))
    elif args.command == "promotion-evidence-report":
        if args.stage is None:
            parser.error("--stage is required for promotion-evidence-report")
        if args.stage not in {"sync_shadow_stability", "small_live_stability"}:
            parser.error("--stage must be sync_shadow_stability or small_live_stability for promotion-evidence-report")
        if not args.bundle_paths:
            parser.error("--bundle-paths is required for promotion-evidence-report")
        evidence_report = build_promotion_evidence_report(
            stage=args.stage,
            bundle_paths=args.bundle_paths,
        )
        if args.report_path is not None:
            write_promotion_evidence_report(
                path=args.report_path,
                report=evidence_report,
            )
        print(format_promotion_evidence_report(evidence_report))
    elif args.command == "promotion-artifact-review":
        if args.stage is None:
            parser.error("--stage is required for promotion-artifact-review")
        if args.metrics_path is None:
            parser.error("--metrics-path is required for promotion-artifact-review")
        if args.state_path is None:
            parser.error("--state-path is required for promotion-artifact-review")
        if args.event_path is None:
            parser.error("--event-path is required for promotion-artifact-review")
        review = build_promotion_artifact_review(
            stage=args.stage,
            metrics_path=args.metrics_path,
            state_path=args.state_path,
            event_path=args.event_path,
            note_path=args.note_path,
            shadow_metrics_path=args.shadow_metrics_path,
            shadow_state_path=args.shadow_state_path,
            shadow_event_path=args.shadow_event_path,
        )
        print(format_promotion_artifact_review(review))
    elif args.command == "promotion-operator-summary":
        if args.stage is None:
            parser.error("--stage is required for promotion-operator-summary")
        if args.metrics_path is None:
            parser.error("--metrics-path is required for promotion-operator-summary")
        if args.state_path is None:
            parser.error("--state-path is required for promotion-operator-summary")
        if args.event_path is None:
            parser.error("--event-path is required for promotion-operator-summary")
        readiness = validate_promotion_readiness(
            stage=args.stage,
            source_config_dir=args.config_dir,
            target_config_dir=args.target_config_dir,
            metrics_path=args.metrics_path,
            state_path=args.state_path,
            event_path=args.event_path,
            shadow_metrics_path=args.shadow_metrics_path,
            shadow_state_path=args.shadow_state_path,
            shadow_event_path=args.shadow_event_path,
            note_path=args.note_path,
        )
        review = build_promotion_artifact_review(
            stage=args.stage,
            metrics_path=args.metrics_path,
            state_path=args.state_path,
            event_path=args.event_path,
            note_path=args.note_path,
            shadow_metrics_path=args.shadow_metrics_path,
            shadow_state_path=args.shadow_state_path,
            shadow_event_path=args.shadow_event_path,
        )
        print(format_promotion_operator_summary(readiness=readiness, review=review))
    elif args.command == "write-operator-note-template":
        if args.stage is None:
            parser.error("--stage is required for write-operator-note-template")
        if args.note_path is None:
            parser.error("--note-path is required for write-operator-note-template")
        if args.run_id is None:
            parser.error("--run-id is required for write-operator-note-template")
        if args.market_window is None:
            parser.error("--market-window is required for write-operator-note-template")
        target = write_operator_note_template(
            path=args.note_path,
            stage=args.stage,
            run_id=args.run_id,
            market_window=args.market_window,
        )
        print(f"note_path={target}")
    elif args.command == "paper-crypto-once":
        result = asyncio.run(
            run_crypto_paper_session_once(
                config_dir=args.config_dir,
                limit=args.limit,
                max_pages=args.max_pages,
                state_path=args.state_path,
                event_path=args.event_path,
                metrics_path=args.metrics_path,
                snapshot_capture_path=args.snapshot_path,
            )
        )
        print(format_dashboard_summary(result))
    elif args.command == "run-paper-crypto-session":
        result = asyncio.run(
            run_crypto_paper_session(
                config_dir=args.config_dir,
                state_path=args.state_path,
                recorder_path=args.event_path or "data/runtime/paper-events.current.jsonl",
                metrics_path=args.metrics_path or "data/runtime/paper-metrics.latest.json",
                max_pages=args.max_pages,
                max_market_snapshots=args.max_market_snapshots,
                summary_every_snapshots=args.summary_every_snapshots,
                snapshot_capture_path=args.snapshot_path,
                count_initial_snapshots_toward_limit=not args.exclude_bootstrap_from_limit,
            )
        )
        if args.promotion_summary_path is not None:
            readiness = validate_promotion_readiness(
                stage="paper_to_sync_shadow",
                source_config_dir=args.config_dir,
                target_config_dir=args.target_config_dir,
                metrics_path=args.metrics_path or "data/runtime/paper-metrics.latest.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/paper-events.current.jsonl",
                note_path=args.note_path,
            )
            review = build_promotion_artifact_review(
                stage="paper_to_sync_shadow",
                metrics_path=args.metrics_path or "data/runtime/paper-metrics.latest.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/paper-events.current.jsonl",
                note_path=args.note_path,
            )
            write_promotion_operator_summary(
                path=args.promotion_summary_path,
                readiness=readiness,
                review=review,
            )
        if args.operator_summary_path is not None:
            promotion_summary = None
            if args.promotion_summary_path is not None:
                promotion_summary = build_promotion_operator_summary(
                    readiness=readiness,
                    review=review,
                )
            write_combined_operator_summary(
                path=args.operator_summary_path,
                dashboard=_typed_dashboard(result["dashboard"]),
                trading_settings=_typed_trading_settings(result.get("trading_settings")),
                promotion_summary=promotion_summary,
                metrics_path=args.metrics_path or "data/runtime/paper-metrics.latest.json",
                state_path=args.state_path,
                event_path=args.event_path or "data/runtime/paper-events.current.jsonl",
                note_path=args.note_path,
                session_label="run-paper-crypto-session",
            )
        print(format_dashboard_summary(result))
    elif args.command == "run-paper-crypto-phase2-session":
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for run-paper-crypto-phase2-session")
        phase2_config_dir = (
            "configs/profiles/paper-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        result = asyncio.run(
            run_crypto_phase2_paper_session(
                config_dir=phase2_config_dir,
                state_path=args.state_path,
                underlying_state_path=args.underlying_state_path,
                selection_report_path=args.selection_report_path,
                recorder_path=args.event_path or "data/runtime/paper-events.current.jsonl",
                metrics_path=args.metrics_path or "data/runtime/paper-metrics.latest.json",
                max_pages=args.max_pages,
                max_market_snapshots=args.max_market_snapshots,
                summary_every_snapshots=args.summary_every_snapshots,
                snapshot_capture_path=args.snapshot_path,
                count_initial_snapshots_toward_limit=not args.exclude_bootstrap_from_limit,
                cancel_pending_orders_on_stop=args.max_market_snapshots is not None,
            )
        )
        print(format_dashboard_summary(result))
    elif args.command == "compare-execution-metrics":
        if args.baseline_metrics_path is None or args.candidate_metrics_path is None:
            parser.error("--baseline-metrics-path and --candidate-metrics-path are required")
        baseline = load_metrics_file(args.baseline_metrics_path)
        candidate = load_metrics_file(args.candidate_metrics_path)
        print(format_metric_comparison(compare_metrics(baseline=baseline, candidate=candidate)))
    elif args.command == "autoresearch-report":
        if args.metrics_path is None:
            parser.error("--metrics-path is required for autoresearch-report")
        autoresearch_report = generate_autoresearch_report(
            metrics_path=args.metrics_path,
            event_path=args.event_path,
            state_path=args.state_path if args.state_path else None,
            promotion_scorecard_path=args.promotion_scorecard_path if args.promotion_scorecard_path else None,
        )
        if args.report_path is not None:
            write_autoresearch_report(autoresearch_report, args.report_path)
        print(format_autoresearch_report(autoresearch_report))
    elif args.command == "check-paper-integrity":
        if args.metrics_path is None:
            parser.error("--metrics-path is required for check-paper-integrity")
        if args.event_path is None:
            parser.error("--event-path is required for check-paper-integrity")
        paper_integrity_report = generate_paper_integrity_report(
            metrics_path=args.metrics_path,
            event_path=args.event_path,
            state_path=args.state_path if args.state_path else None,
        )
        if args.report_path is not None:
            write_paper_integrity_report(paper_integrity_report, args.report_path)
        print(format_paper_integrity_report(paper_integrity_report))
    elif args.command == "check-replay-determinism":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for check-replay-determinism")
        replay_determinism_report = asyncio.run(
            generate_replay_determinism_report(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                mode=args.research_mode,
                limit=args.limit,
            )
        )
        if args.report_path is not None:
            write_replay_determinism_report(replay_determinism_report, args.report_path)
        print(format_replay_determinism_report(replay_determinism_report))
    elif args.command == "run-fixed-window-experiments":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for run-fixed-window-experiments")
        fixed_window_report = asyncio.run(
            run_fixed_window_experiments(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                output_dir=args.output_dir,
                mode=args.research_mode,
                limit=args.limit,
                underlying_state_path=args.underlying_state_path,
                event_path=args.event_path,
                window_snapshots=args.window_snapshots,
                top_windows=args.top_windows,
            )
        )
        if args.report_path is not None and args.report_path != fixed_window_report.summary_path:
            write_fixed_window_report(fixed_window_report, args.report_path)
        print(format_fixed_window_report(fixed_window_report))
    elif args.command == "mine-fixed-windows":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for mine-fixed-windows")
        if args.event_path is None:
            parser.error("--event-path is required for mine-fixed-windows")
        window_mining_report = asyncio.run(
            mine_fixed_windows(
                snapshot_path=args.snapshot_path,
                event_path=args.event_path,
                output_dir=args.output_dir,
                window_snapshots=args.window_snapshots,
                top_windows=args.top_windows,
            )
        )
        if args.report_path is not None and args.report_path != window_mining_report.summary_path:
            write_window_mining_report(window_mining_report, args.report_path)
        print(format_window_mining_report(window_mining_report))
    elif args.command == "crypto-window-family-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-window-family-report")
        family_report = generate_crypto_window_family_report(
            snapshot_path=args.snapshot_path,
            event_path=args.event_path,
            output_dir=args.output_dir,
        )
        if args.report_path is not None and args.report_path != family_report.summary_path:
            write_crypto_window_family_report(family_report, args.report_path)
        print(format_crypto_window_family_report(family_report))
    elif args.command == "crypto-signal-report":
        if args.event_path is None:
            parser.error("--event-path is required for crypto-signal-report")
        signal_report = generate_crypto_signal_report(
            event_path=args.event_path,
            snapshot_path=args.snapshot_path,
            output_dir=args.output_dir,
        )
        signal_report_dir = args.output_dir or Path(signal_report.event_path).parent
        if args.report_path is not None and args.report_path != Path(signal_report.event_path):
            write_crypto_signal_report(report=signal_report, output_dir=signal_report_dir)
        print(format_crypto_signal_report(signal_report))
    elif args.command == "crypto-family-export":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-family-export")
        if args.output_dir is None:
            parser.error("--output-dir is required for crypto-family-export")
        family_export_result = export_crypto_family_window(
            snapshot_path=args.snapshot_path,
            event_path=args.event_path,
            output_dir=args.output_dir,
            underlying=args.underlying,
            event_family=args.event_family,
            series_key_contains=args.series_key_contains,
        )
        if args.report_path is not None and args.report_path != family_export_result.summary_path:
            write_crypto_family_export_result(family_export_result, args.report_path)
        print(format_crypto_family_export_result(family_export_result))
    elif args.command == "sports-market-selection-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-market-selection-report")
        sports_selection_report = generate_sports_market_selection_report(
            snapshot_path=args.snapshot_path,
            output_dir=args.output_dir,
        )
        print(format_sports_market_selection_report(sports_selection_report))
    elif args.command == "sports-closing-line-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-closing-line-report")
        closing_line_report = generate_sports_closing_line_report(
            snapshot_path=args.snapshot_path,
            output_dir=args.output_dir,
        )
        print(format_sports_closing_line_report(closing_line_report))
    elif args.command == "sports-event-scorecard-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-event-scorecard-report")
        sports_scorecard_report = generate_sports_event_scorecard_report(
            snapshot_path=args.snapshot_path,
            output_dir=args.output_dir,
        )
        print(format_sports_event_scorecard_report(sports_scorecard_report))
    elif args.command == "sports-final-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-final-report")
        sports_final_scorecard = generate_sports_final_scorecard(
            snapshot_path=args.snapshot_path,
            output_dir=args.output_dir,
        )
        print(format_sports_final_scorecard(sports_final_scorecard))
    elif args.command == "sports-learning-report":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-learning-report")
        sports_learning_report = build_sports_learning_report(scorecard_paths=args.suite_paths)
        if args.output_dir is not None:
            from pm_bot.strategies.sports.phase1.learning_report import write_sports_learning_report

            write_sports_learning_report(
                report=sports_learning_report,
                output_path=Path(args.output_dir) / "sports_learning_report.md",
            )
        print(format_sports_learning_report(sports_learning_report))
    elif args.command == "sports-tuning-plan":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-tuning-plan")
        sports_tuning_plan = build_sports_tuning_plan(scorecard_paths=args.suite_paths)
        if args.output_dir is not None:
            from pm_bot.strategies.sports.phase1.tuning_plan import write_sports_tuning_plan

            write_sports_tuning_plan(
                plan=sports_tuning_plan,
                output_path=Path(args.output_dir) / "sports_tuning_plan.md",
            )
        print(format_sports_tuning_plan(sports_tuning_plan))
    elif args.command == "sports-candidate-presets":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-candidate-presets")
        sports_tuning_plan = build_sports_tuning_plan(scorecard_paths=args.suite_paths)
        candidate_registry = build_sports_candidate_preset_registry(plan=sports_tuning_plan)
        if args.output_dir is not None:
            from pm_bot.strategies.sports.phase1.tuning_plan import write_sports_candidate_preset_registry

            write_sports_candidate_preset_registry(
                plan=sports_tuning_plan,
                output_path=Path(args.output_dir) / "sports_candidate_presets.json",
            )
        print(json.dumps(candidate_registry, ensure_ascii=True, indent=2))
    elif args.command == "sports-auto-experiments":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-auto-experiments")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-auto-experiments")
        sports_auto_report = asyncio.run(
            run_sports_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                config_dir=(
                    "configs/profiles/research-sports-phase1-v1"
                    if args.config_dir == "configs"
                    else args.config_dir
                ),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        if args.output_dir is not None:
            write_sports_auto_experiments_report(
                report=sports_auto_report,
                output_dir=args.output_dir,
            )
        print(format_sports_auto_experiments_report(sports_auto_report))
    elif args.command == "sports-preset-lifecycle":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-preset-lifecycle")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-preset-lifecycle")
        sports_auto_report = asyncio.run(
            run_sports_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                config_dir=("configs/profiles/research-sports-phase1-v1" if args.config_dir == "configs" else args.config_dir),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        sports_lifecycle = build_sports_preset_lifecycle(report=sports_auto_report)
        if args.output_dir is not None:
            from pm_bot.strategies.sports.phase1.preset_lifecycle import write_sports_preset_lifecycle

            write_sports_preset_lifecycle(
                lifecycle=sports_lifecycle,
                output_dir=args.output_dir,
            )
        print(format_sports_preset_lifecycle(sports_lifecycle))
    elif args.command == "sports-preset-promotion-evidence":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-preset-promotion-evidence")
        sports_evidence = build_sports_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        if args.output_dir is not None:
            write_sports_preset_promotion_evidence(
                evidence=sports_evidence,
                output_path=Path(args.output_dir) / "sports_preset_promotion_evidence.md",
            )
        print(format_sports_preset_promotion_evidence(sports_evidence))
    elif args.command == "sports-preset-change-package":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-preset-change-package")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-preset-change-package")
        sports_auto_report = asyncio.run(
            run_sports_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                config_dir=("configs/profiles/research-sports-phase1-v1" if args.config_dir == "configs" else args.config_dir),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        sports_evidence = build_sports_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        sports_lifecycle = build_sports_preset_lifecycle(report=sports_auto_report)
        sports_package = build_sports_preset_change_package(
            lifecycle=sports_lifecycle,
            evidence=sports_evidence,
            report=sports_auto_report,
            base_match={"league": "nba", "market_family": "moneyline"},
        )
        if args.output_dir is not None:
            write_sports_preset_change_package(
                package=sports_package,
                output_path=Path(args.output_dir) / "sports_preset_change_package.md",
            )
        print(format_sports_preset_change_package(sports_package))
    elif args.command == "sports-preset-apply-plan":
        if not args.suite_paths:
            parser.error("--suite-paths is required for sports-preset-apply-plan")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for sports-preset-apply-plan")
        sports_auto_report = asyncio.run(
            run_sports_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                config_dir=("configs/profiles/research-sports-phase1-v1" if args.config_dir == "configs" else args.config_dir),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        sports_evidence = build_sports_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        sports_lifecycle = build_sports_preset_lifecycle(report=sports_auto_report)
        sports_package = build_sports_preset_change_package(
            lifecycle=sports_lifecycle,
            evidence=sports_evidence,
            report=sports_auto_report,
            base_match={"league": "nba", "market_family": "moneyline"},
        )
        sports_plan = build_sports_preset_apply_plan(package=sports_package)
        if args.output_dir is not None:
            write_sports_preset_apply_plan(
                plan=sports_plan,
                output_path=Path(args.output_dir) / "sports_preset_apply_plan.md",
            )
        print(format_sports_preset_apply_plan(sports_plan))
    elif args.command == "sports-apply-package":
        if args.change_package_path is None:
            parser.error("--change-package-path is required for sports-apply-package")
        if args.target_config_path is None:
            parser.error("--target-config-path is required for sports-apply-package")
        sports_apply_result = apply_sports_preset_change_package(
            change_package_path=args.change_package_path,
            target_config_path=args.target_config_path,
            output_config_path=args.output_config_path,
        )
        if args.report_path is not None:
            write_sports_preset_apply_result(
                result=sports_apply_result,
                output_path=args.report_path,
            )
        print(format_sports_preset_apply_result(sports_apply_result))
    elif args.command == "sports-rollback-package":
        if args.backup_config_path is None:
            parser.error("--backup-config-path is required for sports-rollback-package")
        if args.target_config_path is None:
            parser.error("--target-config-path is required for sports-rollback-package")
        sports_rollback_result = rollback_sports_preset_application(
            backup_config_path=args.backup_config_path,
            target_config_path=args.target_config_path,
            output_config_path=args.output_config_path,
        )
        if args.report_path is not None:
            write_sports_preset_rollback_result(
                result=sports_rollback_result,
                output_path=args.report_path,
            )
        print(format_sports_preset_rollback_result(sports_rollback_result))
    elif args.command == "sports-verify-application":
        if args.baseline_suite_path is None:
            parser.error("--baseline-suite-path is required for sports-verify-application")
        if args.candidate_suite_path is None:
            parser.error("--candidate-suite-path is required for sports-verify-application")
        sports_verification_report = build_sports_preset_verification_report(
            baseline_scorecard_path=args.baseline_suite_path,
            candidate_scorecard_path=args.candidate_suite_path,
        )
        if args.report_path is not None:
            write_sports_preset_verification_report(
                report=sports_verification_report,
                output_path=args.report_path,
            )
        print(format_sports_preset_verification_report(sports_verification_report))
    elif args.command == "weather-market-selection-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-market-selection-report")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-market-selection-report")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-market-selection-report")
        weather_selection_report = generate_weather_market_selection_report(
            snapshot_path=args.snapshot_path,
            forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
            skill_payloads=_load_json_records(args.skill_path, key="skills"),
            output_dir=args.output_dir,
        )
        print(format_weather_market_selection_report(weather_selection_report))
    elif args.command == "weather-settlement-audit-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-settlement-audit-report")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-settlement-audit-report")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-settlement-audit-report")
        weather_audit_report = generate_weather_settlement_audit_report(
            snapshot_path=args.snapshot_path,
            forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
            skill_payloads=_load_json_records(args.skill_path, key="skills"),
            output_dir=args.output_dir,
        )
        print(format_weather_settlement_audit_report(weather_audit_report))
    elif args.command == "weather-run-scorecard-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-run-scorecard-report")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-run-scorecard-report")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-run-scorecard-report")
        weather_scorecard_report = generate_weather_run_scorecard_report(
            snapshot_path=args.snapshot_path,
            forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
            skill_payloads=_load_json_records(args.skill_path, key="skills"),
            output_dir=args.output_dir,
        )
        print(format_weather_run_scorecard_report(weather_scorecard_report))
    elif args.command == "weather-final-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-final-report")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-final-report")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-final-report")
        weather_final_scorecard = generate_weather_final_scorecard(
            snapshot_path=args.snapshot_path,
            forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
            skill_payloads=_load_json_records(args.skill_path, key="skills"),
            output_dir=args.output_dir,
        )
        print(format_weather_final_scorecard(weather_final_scorecard))
    elif args.command == "weather-learning-report":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-learning-report")
        weather_learning_report = build_weather_learning_report(scorecard_paths=args.suite_paths)
        if args.output_dir is not None:
            from pm_bot.strategies.weather.phase1.learning_report import write_weather_learning_report

            write_weather_learning_report(
                report=weather_learning_report,
                output_path=Path(args.output_dir) / "weather_learning_report.md",
            )
        print(format_weather_learning_report(weather_learning_report))
    elif args.command == "weather-tuning-plan":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-tuning-plan")
        weather_tuning_plan = build_weather_tuning_plan(scorecard_paths=args.suite_paths)
        if args.output_dir is not None:
            from pm_bot.strategies.weather.phase1.tuning_plan import write_weather_tuning_plan

            write_weather_tuning_plan(
                plan=weather_tuning_plan,
                output_path=Path(args.output_dir) / "weather_tuning_plan.md",
            )
        print(format_weather_tuning_plan(weather_tuning_plan))
    elif args.command == "weather-candidate-presets":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-candidate-presets")
        weather_tuning_plan = build_weather_tuning_plan(scorecard_paths=args.suite_paths)
        candidate_registry = build_weather_candidate_preset_registry(plan=weather_tuning_plan)
        if args.output_dir is not None:
            from pm_bot.strategies.weather.phase1.tuning_plan import write_weather_candidate_preset_registry

            write_weather_candidate_preset_registry(
                plan=weather_tuning_plan,
                output_path=Path(args.output_dir) / "weather_candidate_presets.json",
            )
        print(json.dumps(candidate_registry, ensure_ascii=True, indent=2))
    elif args.command == "weather-auto-experiments":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-auto-experiments")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-auto-experiments")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-auto-experiments")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-auto-experiments")
        weather_auto_report = asyncio.run(
            run_weather_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
                skill_payloads=_load_json_records(args.skill_path, key="skills"),
                config_dir=(
                    "configs/profiles/research-weather-phase1-v1"
                    if args.config_dir == "configs"
                    else args.config_dir
                ),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        if args.output_dir is not None:
            write_weather_auto_experiments_report(
                report=weather_auto_report,
                output_dir=args.output_dir,
            )
        print(format_weather_auto_experiments_report(weather_auto_report))
    elif args.command == "weather-preset-lifecycle":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-preset-lifecycle")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-preset-lifecycle")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-preset-lifecycle")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-preset-lifecycle")
        weather_auto_report = asyncio.run(
            run_weather_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
                skill_payloads=_load_json_records(args.skill_path, key="skills"),
                config_dir=("configs/profiles/research-weather-phase1-v1" if args.config_dir == "configs" else args.config_dir),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        weather_lifecycle = build_weather_preset_lifecycle(report=weather_auto_report)
        if args.output_dir is not None:
            from pm_bot.strategies.weather.phase1.preset_lifecycle import write_weather_preset_lifecycle

            write_weather_preset_lifecycle(
                lifecycle=weather_lifecycle,
                output_dir=args.output_dir,
            )
        print(format_weather_preset_lifecycle(weather_lifecycle))
    elif args.command == "weather-preset-promotion-evidence":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-preset-promotion-evidence")
        weather_evidence = build_weather_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        if args.output_dir is not None:
            write_weather_preset_promotion_evidence(
                evidence=weather_evidence,
                output_path=Path(args.output_dir) / "weather_preset_promotion_evidence.md",
            )
        print(format_weather_preset_promotion_evidence(weather_evidence))
    elif args.command == "weather-preset-change-package":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-preset-change-package")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-preset-change-package")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-preset-change-package")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-preset-change-package")
        weather_auto_report = asyncio.run(
            run_weather_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
                skill_payloads=_load_json_records(args.skill_path, key="skills"),
                config_dir=("configs/profiles/research-weather-phase1-v1" if args.config_dir == "configs" else args.config_dir),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        weather_evidence = build_weather_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        weather_lifecycle = build_weather_preset_lifecycle(report=weather_auto_report)
        weather_package = build_weather_preset_change_package(
            lifecycle=weather_lifecycle,
            evidence=weather_evidence,
            report=weather_auto_report,
            base_match={"event_family": "daily_high_temperature_threshold", "settlement_source": "official"},
        )
        if args.output_dir is not None:
            write_weather_preset_change_package(
                package=weather_package,
                output_path=Path(args.output_dir) / "weather_preset_change_package.md",
            )
        print(format_weather_preset_change_package(weather_package))
    elif args.command == "weather-preset-apply-plan":
        if not args.suite_paths:
            parser.error("--suite-paths is required for weather-preset-apply-plan")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for weather-preset-apply-plan")
        if args.forecast_runs_path is None:
            parser.error("--forecast-runs-path is required for weather-preset-apply-plan")
        if args.skill_path is None:
            parser.error("--skill-path is required for weather-preset-apply-plan")
        weather_auto_report = asyncio.run(
            run_weather_auto_experiments(
                scorecard_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                forecast_payloads=_load_json_records(args.forecast_runs_path, key="runs"),
                skill_payloads=_load_json_records(args.skill_path, key="skills"),
                config_dir=("configs/profiles/research-weather-phase1-v1" if args.config_dir == "configs" else args.config_dir),
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        weather_evidence = build_weather_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        weather_lifecycle = build_weather_preset_lifecycle(report=weather_auto_report)
        weather_package = build_weather_preset_change_package(
            lifecycle=weather_lifecycle,
            evidence=weather_evidence,
            report=weather_auto_report,
            base_match={"event_family": "daily_high_temperature_threshold", "settlement_source": "official"},
        )
        weather_plan = build_weather_preset_apply_plan(package=weather_package)
        if args.output_dir is not None:
            write_weather_preset_apply_plan(
                plan=weather_plan,
                output_path=Path(args.output_dir) / "weather_preset_apply_plan.md",
            )
        print(format_weather_preset_apply_plan(weather_plan))
    elif args.command == "weather-apply-package":
        if args.change_package_path is None:
            parser.error("--change-package-path is required for weather-apply-package")
        if args.target_config_path is None:
            parser.error("--target-config-path is required for weather-apply-package")
        weather_apply_result = apply_weather_preset_change_package(
            change_package_path=args.change_package_path,
            target_config_path=args.target_config_path,
            output_config_path=args.output_config_path,
        )
        if args.report_path is not None:
            write_weather_preset_apply_result(
                result=weather_apply_result,
                output_path=args.report_path,
            )
        print(format_weather_preset_apply_result(weather_apply_result))
    elif args.command == "weather-rollback-package":
        if args.backup_config_path is None:
            parser.error("--backup-config-path is required for weather-rollback-package")
        if args.target_config_path is None:
            parser.error("--target-config-path is required for weather-rollback-package")
        weather_rollback_result = rollback_weather_preset_application(
            backup_config_path=args.backup_config_path,
            target_config_path=args.target_config_path,
            output_config_path=args.output_config_path,
        )
        if args.report_path is not None:
            write_weather_preset_rollback_result(
                result=weather_rollback_result,
                output_path=args.report_path,
            )
        print(format_weather_preset_rollback_result(weather_rollback_result))
    elif args.command == "weather-verify-application":
        if args.baseline_suite_path is None:
            parser.error("--baseline-suite-path is required for weather-verify-application")
        if args.candidate_suite_path is None:
            parser.error("--candidate-suite-path is required for weather-verify-application")
        weather_verification_report = build_weather_preset_verification_report(
            baseline_scorecard_path=args.baseline_suite_path,
            candidate_scorecard_path=args.candidate_suite_path,
        )
        if args.report_path is not None:
            write_weather_preset_verification_report(
                report=weather_verification_report,
                output_path=args.report_path,
            )
        print(format_weather_preset_verification_report(weather_verification_report))
    elif args.command == "replay":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for replay")
        replay_result = asyncio.run(
            run_replay(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                limit=args.limit,
                recorder_path=args.event_path,
                metrics_path=args.metrics_path,
            )
        )
        print(format_research_summary(replay_result))
    elif args.command == "phase1-replay":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for phase1-replay")
        if args.board is None:
            parser.error("--board is required for phase1-replay")
        phase1_config_dir = (
            default_phase1_config_dir(args.board)
            if args.config_dir == "configs"
            else args.config_dir
        )
        phase1_replay_result = asyncio.run(
            run_phase1_replay(
                board=args.board,
                snapshot_path=args.snapshot_path,
                config_dir=phase1_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        print(format_phase1_replay_result(phase1_replay_result))
    elif args.command == "crypto-calibration-report":
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-calibration-report")
        if args.train_snapshot_path is None:
            parser.error("--train-snapshot-path is required for crypto-calibration-report")
        if args.validation_snapshot_path is None:
            parser.error("--validation-snapshot-path is required for crypto-calibration-report")
        if args.holdout_snapshot_path is None:
            parser.error("--holdout-snapshot-path is required for crypto-calibration-report")
        calibration_report = generate_crypto_calibration_report(
            train_snapshot_path=args.train_snapshot_path,
            validation_snapshot_path=args.validation_snapshot_path,
            holdout_snapshot_path=args.holdout_snapshot_path,
            underlying_states=_load_underlying_states(args.underlying_state_path),
            output_dir=args.output_dir,
        )
        print(format_crypto_calibration_report(calibration_report))
    elif args.command == "crypto-calibration-experiments":
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-calibration-experiments")
        if args.train_snapshot_path is None:
            parser.error("--train-snapshot-path is required for crypto-calibration-experiments")
        if args.validation_snapshot_path is None:
            parser.error("--validation-snapshot-path is required for crypto-calibration-experiments")
        if args.holdout_snapshot_path is None:
            parser.error("--holdout-snapshot-path is required for crypto-calibration-experiments")
        calibration_experiment_report = run_crypto_calibration_experiments(
            train_snapshot_path=args.train_snapshot_path,
            validation_snapshot_path=args.validation_snapshot_path,
            holdout_snapshot_path=args.holdout_snapshot_path,
            underlying_states=_load_underlying_states(args.underlying_state_path),
            output_dir=args.output_dir,
            candidate_set=args.candidate_set,
        )
        print(format_crypto_calibration_experiment_report(calibration_experiment_report))
    elif args.command == "crypto-market-selection-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-market-selection-report")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-market-selection-report")
        crypto_selection_report = generate_crypto_market_selection_report(
            snapshot_path=args.snapshot_path,
            underlying_states=_load_underlying_states(args.underlying_state_path),
            event_path=args.event_path,
            output_dir=args.output_dir,
            barrier_model_config=get_locked_crypto_calibration_baseline_preset().barrier_model_config,
            fusion_model_config=get_locked_crypto_calibration_baseline_preset().fusion_model_config,
        )
        print(format_crypto_market_selection_report(crypto_selection_report))
    elif args.command == "crypto-phase2-replay":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-replay")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-replay")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        result_fair_values = asyncio.run(
            run_crypto_phase2_replay(
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
                run_id="crypto-phase2-cli" if args.output_dir is not None else None,
                selection_report_path=args.selection_report_path,
            )
        )
        print("phase2_board=crypto")
        print(f"fair_values={len(result_fair_values)}")
        if args.output_dir is not None:
            print(f"output_dir={args.output_dir}")
    elif args.command == "crypto-phase2-suite":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-suite")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-suite")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        suite_result = asyncio.run(
            run_crypto_phase2_suite(
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
                run_id="crypto-phase2-suite-cli" if args.output_dir is not None else None,
            )
        )
        print(format_crypto_phase2_suite_result(suite_result))
    elif args.command == "crypto-phase2-final-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-final-report")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-final-report")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        suite_result = asyncio.run(
            run_crypto_phase2_suite(
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
                run_id="crypto-phase2-final-cli" if args.output_dir is not None else None,
            )
        )
        print(format_crypto_phase2_final_scorecard(suite_result.final_scorecard))
    elif args.command == "crypto-phase2-learning-report":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-learning-report")
        learning_report = build_crypto_phase2_learning_report(suite_paths=args.suite_paths)
        if args.output_dir is not None:
            write_crypto_phase2_learning_report(
                report=learning_report,
                output_path=Path(args.output_dir) / "learning_report.md",
            )
        print(format_crypto_phase2_learning_report(learning_report))
    elif args.command == "crypto-phase2-tuning-plan":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-tuning-plan")
        tuning_plan = build_crypto_phase2_tuning_plan(suite_paths=args.suite_paths)
        if args.output_dir is not None:
            write_crypto_phase2_tuning_plan(
                plan=tuning_plan,
                output_path=Path(args.output_dir) / "tuning_plan.md",
            )
        print(format_crypto_phase2_tuning_plan(tuning_plan))
    elif args.command == "crypto-phase2-candidate-presets":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-candidate-presets")
        tuning_plan = build_crypto_phase2_tuning_plan(suite_paths=args.suite_paths)
        base_match: dict[str, str] = {}
        if args.candidate_underlying:
            base_match["underlying"] = args.candidate_underlying
        if args.candidate_event_family:
            base_match["event_family"] = args.candidate_event_family
        candidate_registry = build_crypto_phase2_candidate_preset_registry(
            plan=tuning_plan,
            base_match=base_match or None,
        )
        if args.output_dir is not None:
            write_crypto_phase2_candidate_preset_registry(
                plan=tuning_plan,
                output_path=Path(args.output_dir) / "candidate_preset_registry.json",
                base_match=base_match or None,
            )
        print(json.dumps(candidate_registry, ensure_ascii=True, indent=2))
    elif args.command == "crypto-phase2-auto-experiments":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-auto-experiments")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-auto-experiments")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-auto-experiments")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        auto_report = asyncio.run(
            run_crypto_phase2_auto_experiments(
                suite_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        print(format_crypto_phase2_auto_experiments_report(auto_report))
    elif args.command == "crypto-phase2-preset-lifecycle":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-preset-lifecycle")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-preset-lifecycle")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-preset-lifecycle")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        auto_report = asyncio.run(
            run_crypto_phase2_auto_experiments(
                suite_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        crypto_lifecycle = build_crypto_phase2_preset_lifecycle(report=auto_report)
        print(format_crypto_phase2_preset_lifecycle(crypto_lifecycle))
    elif args.command == "crypto-phase2-working-preset-patch":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-working-preset-patch")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-working-preset-patch")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-working-preset-patch")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        auto_report = asyncio.run(
            run_crypto_phase2_auto_experiments(
                suite_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        crypto_lifecycle = build_crypto_phase2_preset_lifecycle(report=auto_report)
        patch_base_match: dict[str, str] = {}
        if args.candidate_underlying:
            patch_base_match["underlying"] = args.candidate_underlying
        if args.candidate_event_family:
            patch_base_match["event_family"] = args.candidate_event_family
        patch = build_crypto_phase2_working_preset_patch(
            lifecycle=crypto_lifecycle,
            report=auto_report,
            base_match=patch_base_match or None,
        )
        print(json.dumps(patch, ensure_ascii=True, indent=2))
    elif args.command == "crypto-phase2-preset-promotion-evidence":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-preset-promotion-evidence")
        crypto_evidence = build_crypto_phase2_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        if args.output_dir is not None:
            write_crypto_phase2_preset_promotion_evidence(
                evidence=crypto_evidence,
                output_path=Path(args.output_dir) / "preset_promotion_evidence.md",
            )
        print(format_crypto_phase2_preset_promotion_evidence(crypto_evidence))
    elif args.command == "crypto-phase2-preset-change-package":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-preset-change-package")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-preset-change-package")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-preset-change-package")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        auto_report = asyncio.run(
            run_crypto_phase2_auto_experiments(
                suite_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        crypto_evidence = build_crypto_phase2_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        crypto_lifecycle = build_crypto_phase2_preset_lifecycle(report=auto_report)
        package_base_match: dict[str, str] = {}
        if args.candidate_underlying:
            package_base_match["underlying"] = args.candidate_underlying
        if args.candidate_event_family:
            package_base_match["event_family"] = args.candidate_event_family
        crypto_package = build_crypto_phase2_preset_change_package(
            lifecycle=crypto_lifecycle,
            evidence=crypto_evidence,
            report=auto_report,
            base_match=package_base_match or None,
        )
        if args.output_dir is not None:
            write_crypto_phase2_preset_change_package(
                package=crypto_package,
                output_path=Path(args.output_dir) / "preset_change_package.md",
            )
        print(format_crypto_phase2_preset_change_package(crypto_package))
    elif args.command == "crypto-phase2-preset-apply-plan":
        if not args.suite_paths:
            parser.error("--suite-paths is required for crypto-phase2-preset-apply-plan")
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-phase2-preset-apply-plan")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-phase2-preset-apply-plan")
        phase2_config_dir = (
            "configs/profiles/research-crypto-phase2-v1"
            if args.config_dir == "configs"
            else args.config_dir
        )
        auto_report = asyncio.run(
            run_crypto_phase2_auto_experiments(
                suite_paths=args.suite_paths,
                snapshot_path=args.snapshot_path,
                underlying_states=_load_underlying_states(args.underlying_state_path),
                config_dir=phase2_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        crypto_evidence = build_crypto_phase2_preset_promotion_evidence(auto_experiment_paths=args.suite_paths)
        crypto_lifecycle = build_crypto_phase2_preset_lifecycle(report=auto_report)
        apply_base_match: dict[str, str] = {}
        if args.candidate_underlying:
            apply_base_match["underlying"] = args.candidate_underlying
        if args.candidate_event_family:
            apply_base_match["event_family"] = args.candidate_event_family
        crypto_package = build_crypto_phase2_preset_change_package(
            lifecycle=crypto_lifecycle,
            evidence=crypto_evidence,
            report=auto_report,
            base_match=apply_base_match or None,
        )
        plan = build_crypto_phase2_preset_apply_plan(package=crypto_package)
        if args.output_dir is not None:
            write_crypto_phase2_preset_apply_plan(
                plan=plan,
                output_path=Path(args.output_dir) / "preset_apply_plan.md",
            )
        print(format_crypto_phase2_preset_apply_plan(plan))
    elif args.command == "crypto-phase2-apply-package":
        if args.change_package_path is None:
            parser.error("--change-package-path is required for crypto-phase2-apply-package")
        if args.target_config_path is None:
            parser.error("--target-config-path is required for crypto-phase2-apply-package")
        apply_result = apply_crypto_phase2_preset_change_package(
            change_package_path=args.change_package_path,
            target_config_path=args.target_config_path,
            output_config_path=args.output_config_path,
        )
        if args.report_path is not None:
            write_crypto_phase2_preset_apply_result(
                result=apply_result,
                output_path=args.report_path,
            )
        print(format_crypto_phase2_preset_apply_result(apply_result))
    elif args.command == "crypto-phase2-rollback-package":
        if args.backup_config_path is None:
            parser.error("--backup-config-path is required for crypto-phase2-rollback-package")
        if args.target_config_path is None:
            parser.error("--target-config-path is required for crypto-phase2-rollback-package")
        rollback_result = rollback_crypto_phase2_preset_application(
            backup_config_path=args.backup_config_path,
            target_config_path=args.target_config_path,
            output_config_path=args.output_config_path,
        )
        if args.report_path is not None:
            write_crypto_phase2_preset_rollback_result(
                result=rollback_result,
                output_path=args.report_path,
            )
        print(format_crypto_phase2_preset_rollback_result(rollback_result))
    elif args.command == "crypto-phase2-verify-application":
        if args.baseline_suite_path is None:
            parser.error("--baseline-suite-path is required for crypto-phase2-verify-application")
        if args.candidate_suite_path is None:
            parser.error("--candidate-suite-path is required for crypto-phase2-verify-application")
        verification_report = build_crypto_phase2_preset_verification_report(
            baseline_suite_path=args.baseline_suite_path,
            candidate_suite_path=args.candidate_suite_path,
        )
        if args.report_path is not None:
            write_crypto_phase2_preset_verification_report(
                report=verification_report,
                output_path=args.report_path,
            )
        print(format_crypto_phase2_preset_verification_report(verification_report))
    elif args.command == "strategy-governance-report":
        if args.crypto_change_package_path is None:
            parser.error("--crypto-change-package-path is required for strategy-governance-report")
        if args.sports_change_package_path is None:
            parser.error("--sports-change-package-path is required for strategy-governance-report")
        if args.weather_change_package_path is None:
            parser.error("--weather-change-package-path is required for strategy-governance-report")
        governance_report = build_strategy_governance_report(
            crypto_change_package_path=args.crypto_change_package_path,
            sports_change_package_path=args.sports_change_package_path,
            weather_change_package_path=args.weather_change_package_path,
            crypto_apply_plan_path=args.crypto_apply_plan_path,
            sports_apply_plan_path=args.sports_apply_plan_path,
            weather_apply_plan_path=args.weather_apply_plan_path,
            crypto_apply_result_path=args.crypto_apply_result_path,
            sports_apply_result_path=args.sports_apply_result_path,
            weather_apply_result_path=args.weather_apply_result_path,
            crypto_verify_path=args.crypto_verify_path,
            sports_verify_path=args.sports_verify_path,
            weather_verify_path=args.weather_verify_path,
        )
        if args.report_path is not None:
            write_strategy_governance_report(
                path=args.report_path,
                report=governance_report,
            )
        print(format_strategy_governance_report(governance_report))
    elif args.command == "strategy-change-window":
        if args.strategy_governance_path is not None:
            change_window = build_strategy_change_window_from_report_path(args.strategy_governance_path)
        else:
            if args.crypto_change_package_path is None:
                parser.error("--crypto-change-package-path is required for strategy-change-window")
            if args.sports_change_package_path is None:
                parser.error("--sports-change-package-path is required for strategy-change-window")
            if args.weather_change_package_path is None:
                parser.error("--weather-change-package-path is required for strategy-change-window")
            change_window = build_strategy_change_window(
                build_strategy_governance_report(
                    crypto_change_package_path=args.crypto_change_package_path,
                    sports_change_package_path=args.sports_change_package_path,
                    weather_change_package_path=args.weather_change_package_path,
                    crypto_apply_plan_path=args.crypto_apply_plan_path,
                    sports_apply_plan_path=args.sports_apply_plan_path,
                    weather_apply_plan_path=args.weather_apply_plan_path,
                    crypto_apply_result_path=args.crypto_apply_result_path,
                    sports_apply_result_path=args.sports_apply_result_path,
                    weather_apply_result_path=args.weather_apply_result_path,
                    crypto_verify_path=args.crypto_verify_path,
                    sports_verify_path=args.sports_verify_path,
                    weather_verify_path=args.weather_verify_path,
                )
            )
        if args.report_path is not None:
            write_strategy_change_window(
                path=args.report_path,
                window=change_window,
            )
        print(format_strategy_change_window(change_window))
    elif args.command == "strategy-governance-decision":
        if args.crypto_change_package_path is None:
            parser.error("--crypto-change-package-path is required for strategy-governance-decision")
        if args.sports_change_package_path is None:
            parser.error("--sports-change-package-path is required for strategy-governance-decision")
        if args.weather_change_package_path is None:
            parser.error("--weather-change-package-path is required for strategy-governance-decision")
        governance_report = build_strategy_governance_report(
            crypto_change_package_path=args.crypto_change_package_path,
            sports_change_package_path=args.sports_change_package_path,
            weather_change_package_path=args.weather_change_package_path,
            crypto_apply_plan_path=args.crypto_apply_plan_path,
            sports_apply_plan_path=args.sports_apply_plan_path,
            weather_apply_plan_path=args.weather_apply_plan_path,
            crypto_apply_result_path=args.crypto_apply_result_path,
            sports_apply_result_path=args.sports_apply_result_path,
            weather_apply_result_path=args.weather_apply_result_path,
            crypto_verify_path=args.crypto_verify_path,
            sports_verify_path=args.sports_verify_path,
            weather_verify_path=args.weather_verify_path,
        )
        change_window = build_strategy_change_window(governance_report)
        decision = build_strategy_governance_decision(governance_report, change_window)
        if args.report_path is not None:
            write_strategy_governance_decision(
                path=args.report_path,
                decision=decision,
            )
        print(format_strategy_governance_decision(decision))
    elif args.command == "strategy-execute-window":
        if args.crypto_change_package_path is None:
            parser.error("--crypto-change-package-path is required for strategy-execute-window")
        if args.sports_change_package_path is None:
            parser.error("--sports-change-package-path is required for strategy-execute-window")
        if args.weather_change_package_path is None:
            parser.error("--weather-change-package-path is required for strategy-execute-window")
        governance_report = build_strategy_governance_report(
            crypto_change_package_path=args.crypto_change_package_path,
            sports_change_package_path=args.sports_change_package_path,
            weather_change_package_path=args.weather_change_package_path,
            crypto_apply_plan_path=args.crypto_apply_plan_path,
            sports_apply_plan_path=args.sports_apply_plan_path,
            weather_apply_plan_path=args.weather_apply_plan_path,
            crypto_apply_result_path=args.crypto_apply_result_path,
            sports_apply_result_path=args.sports_apply_result_path,
            weather_apply_result_path=args.weather_apply_result_path,
            crypto_verify_path=args.crypto_verify_path,
            sports_verify_path=args.sports_verify_path,
            weather_verify_path=args.weather_verify_path,
        )
        change_window = build_strategy_change_window(governance_report)
        execution_report = execute_strategy_change_window(
            governance_report=governance_report,
            change_window=change_window,
            crypto_change_package_path=args.crypto_change_package_path,
            sports_change_package_path=args.sports_change_package_path,
            weather_change_package_path=args.weather_change_package_path,
            crypto_target_config_path=args.crypto_target_config_path,
            sports_target_config_path=args.sports_target_config_path,
            weather_target_config_path=args.weather_target_config_path,
            crypto_apply_result_path=args.crypto_apply_result_path,
            sports_apply_result_path=args.sports_apply_result_path,
            weather_apply_result_path=args.weather_apply_result_path,
        )
        if args.report_path is not None:
            write_strategy_execution_window_report(
                path=args.report_path,
                report=execution_report,
            )
        print(format_strategy_execution_window_report(execution_report))
    elif args.command == "strategy-feedback-loop":
        if args.crypto_change_package_path is None:
            parser.error("--crypto-change-package-path is required for strategy-feedback-loop")
        if args.sports_change_package_path is None:
            parser.error("--sports-change-package-path is required for strategy-feedback-loop")
        if args.weather_change_package_path is None:
            parser.error("--weather-change-package-path is required for strategy-feedback-loop")
        governance_report = build_strategy_governance_report(
            crypto_change_package_path=args.crypto_change_package_path,
            sports_change_package_path=args.sports_change_package_path,
            weather_change_package_path=args.weather_change_package_path,
            crypto_apply_plan_path=args.crypto_apply_plan_path,
            sports_apply_plan_path=args.sports_apply_plan_path,
            weather_apply_plan_path=args.weather_apply_plan_path,
            crypto_apply_result_path=args.crypto_apply_result_path,
            sports_apply_result_path=args.sports_apply_result_path,
            weather_apply_result_path=args.weather_apply_result_path,
            crypto_verify_path=args.crypto_verify_path,
            sports_verify_path=args.sports_verify_path,
            weather_verify_path=args.weather_verify_path,
        )
        change_window = build_strategy_change_window(governance_report)
        execution_report = execute_strategy_change_window(
            governance_report=governance_report,
            change_window=change_window,
            crypto_change_package_path=args.crypto_change_package_path,
            sports_change_package_path=args.sports_change_package_path,
            weather_change_package_path=args.weather_change_package_path,
            crypto_target_config_path=args.crypto_target_config_path,
            sports_target_config_path=args.sports_target_config_path,
            weather_target_config_path=args.weather_target_config_path,
            crypto_apply_result_path=args.crypto_apply_result_path,
            sports_apply_result_path=args.sports_apply_result_path,
            weather_apply_result_path=args.weather_apply_result_path,
        )
        feedback_report = build_strategy_feedback_loop_report(
            governance_report=governance_report,
            execution_report=execution_report,
            crypto_verify_path=args.crypto_verify_path,
            sports_verify_path=args.sports_verify_path,
            weather_verify_path=args.weather_verify_path,
        )
        if args.report_path is not None:
            write_strategy_feedback_loop_report(
                path=args.report_path,
                report=feedback_report,
            )
        print(format_strategy_feedback_loop_report(feedback_report))
    elif args.command == "strategy-loop-history":
        if not args.bundle_paths:
            parser.error("--bundle-paths is required for strategy-loop-history")
        strategy_history_report = build_strategy_loop_history_report(
            feedback_loop_paths=args.bundle_paths,
        )
        if args.report_path is not None:
            write_strategy_loop_history_report(
                path=args.report_path,
                report=strategy_history_report,
            )
        print(format_strategy_loop_history_report(strategy_history_report))
    elif args.command == "strategy-loop-decision":
        if not args.bundle_paths:
            parser.error("--bundle-paths is required for strategy-loop-decision")
        strategy_history_report = build_strategy_loop_history_report(
            feedback_loop_paths=args.bundle_paths,
        )
        strategy_loop_decision = build_strategy_loop_decision(strategy_history_report)
        if args.report_path is not None:
            write_strategy_loop_decision(
                path=args.report_path,
                decision=strategy_loop_decision,
            )
        print(format_strategy_loop_decision(strategy_loop_decision))
    elif args.command == "backtest":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for backtest")
        backtest_result = asyncio.run(
            run_backtest(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                limit=args.limit,
                recorder_path=args.event_path,
                metrics_path=args.metrics_path,
            )
        )
        print(format_research_summary(backtest_result))
    elif args.command == "show-dashboard":
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        risk_manager.advance_trading_day()
        print(
            _render_dashboard_with_ops_summary(
                risk_manager.dashboard_state(),
                trading_settings=settings.trading,
                promotion_summary_path=args.promotion_summary_path,
                combined_summary_path=args.operator_summary_path,
                ops_summary_path=args.ops_summary_path,
                ops_console_path=args.ops_console_path,
                ops_one_page_path=args.one_page_path,
            )
        )
    elif args.command == "manual-resume":
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        risk_manager.advance_trading_day()
        resume_result = asyncio.run(risk_manager.manual_resume())
        print(f"manual_resume={str(resume_result.approved).lower()}")
        print(f"reason={resume_result.reason}")
        print(
            _render_dashboard_with_ops_summary(
                risk_manager.dashboard_state(),
                trading_settings=settings.trading,
                promotion_summary_path=args.promotion_summary_path,
                combined_summary_path=args.operator_summary_path,
                ops_summary_path=args.ops_summary_path,
                ops_console_path=args.ops_console_path,
                ops_one_page_path=args.one_page_path,
            )
        )


def _typed_dashboard(value: object) -> DashboardState:
    if not isinstance(value, DashboardState):
        raise TypeError("operator summary requires a DashboardState result")
    return value


def _typed_trading_settings(value: object) -> TradingSettings | None:
    return value if isinstance(value, TradingSettings) else None


def _load_underlying_states(path: str) -> dict[str, CryptoUnderlyingState]:
    return load_underlying_states(path)


def _render_dashboard_with_ops_summary(
    dashboard: DashboardState,
    *,
    trading_settings: TradingSettings | None,
    promotion_summary_path: str | None,
    combined_summary_path: str | None,
    ops_summary_path: str | None,
    ops_console_path: str | None = None,
    ops_one_page_path: str | None = None,
) -> str:
    return render_dashboard_with_ops_summary(
        dashboard,
        trading_settings=trading_settings,
        promotion_summary_path=promotion_summary_path,
        combined_summary_path=combined_summary_path,
        ops_summary_path=ops_summary_path,
        ops_console_path=ops_console_path,
        ops_one_page_path=ops_one_page_path,
    )


def _load_json_records(path: str, *, key: str) -> list[dict[str, object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level object")
    rows = payload.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a top-level '{key}' list")
    return [dict(item) for item in rows if isinstance(item, dict)]


if __name__ == "__main__":
    main()
