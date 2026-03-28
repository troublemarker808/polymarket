"""Command-line helpers for validating the foundation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from pm_bot.adapters.polymarket import fetch_geoblock_status_sync
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.execution import describe_execution_configuration
from pm_bot.execution.metrics_report import compare_metrics, format_metric_comparison, load_metrics_file
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
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.live_session import format_live_session_summary, run_crypto_live_session
from pm_bot.runtime.paper_session import (
    format_dashboard_summary,
    run_crypto_phase2_paper_session,
    run_crypto_paper_session,
    run_crypto_paper_session_once,
)
from pm_bot.runtime.sync_session import format_sync_session_summary, run_crypto_sync_session
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket bot foundation CLI")
    parser.add_argument(
        "command",
        choices=(
            "check-geoblock",
            "run-live-crypto-session",
            "run-sync-crypto-session",
            "validate-config",
            "validate-live-config",
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
            "crypto-market-selection-report",
            "crypto-signal-report",
            "crypto-window-family-report",
            "crypto-phase2-replay",
            "crypto-phase2-suite",
            "backtest",
            "show-dashboard",
            "manual-resume",
        ),
        help="Validate configs and print enabled strategies.",
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
    elif args.command == "run-live-crypto-session":
        result = asyncio.run(
            run_crypto_live_session(
                config_dir=args.config_dir,
                state_path=args.state_path,
                recorder_path=args.event_path or "data/runtime/live-events.jsonl",
                metrics_path=args.metrics_path or "data/runtime/live-metrics.latest.json",
                max_pages=args.max_pages,
                max_market_snapshots=args.max_market_snapshots,
                max_user_events=args.max_user_events,
                summary_every_snapshots=args.summary_every_snapshots,
            )
        )
        print(format_live_session_summary(result))
    elif args.command == "run-sync-crypto-session":
        result = asyncio.run(
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
            )
        )
        print(format_sync_session_summary(result))
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
        report = generate_autoresearch_report(
            metrics_path=args.metrics_path,
            event_path=args.event_path,
            state_path=args.state_path if args.state_path else None,
        )
        if args.report_path is not None:
            write_autoresearch_report(report, args.report_path)
        print(format_autoresearch_report(report))
    elif args.command == "check-paper-integrity":
        if args.metrics_path is None:
            parser.error("--metrics-path is required for check-paper-integrity")
        if args.event_path is None:
            parser.error("--event-path is required for check-paper-integrity")
        report = generate_paper_integrity_report(
            metrics_path=args.metrics_path,
            event_path=args.event_path,
            state_path=args.state_path if args.state_path else None,
        )
        if args.report_path is not None:
            write_paper_integrity_report(report, args.report_path)
        print(format_paper_integrity_report(report))
    elif args.command == "check-replay-determinism":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for check-replay-determinism")
        report = asyncio.run(
            generate_replay_determinism_report(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                mode=args.research_mode,
                limit=args.limit,
            )
        )
        if args.report_path is not None:
            write_replay_determinism_report(report, args.report_path)
        print(format_replay_determinism_report(report))
    elif args.command == "run-fixed-window-experiments":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for run-fixed-window-experiments")
        report = asyncio.run(
            run_fixed_window_experiments(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                output_dir=args.output_dir,
                mode=args.research_mode,
                limit=args.limit,
                underlying_state_path=args.underlying_state_path,
            )
        )
        if args.report_path is not None and args.report_path != report.summary_path:
            write_fixed_window_report(report, args.report_path)
        print(format_fixed_window_report(report))
    elif args.command == "mine-fixed-windows":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for mine-fixed-windows")
        if args.event_path is None:
            parser.error("--event-path is required for mine-fixed-windows")
        report = asyncio.run(
            mine_fixed_windows(
                snapshot_path=args.snapshot_path,
                event_path=args.event_path,
                output_dir=args.output_dir,
                window_snapshots=args.window_snapshots,
                top_windows=args.top_windows,
            )
        )
        if args.report_path is not None and args.report_path != report.summary_path:
            write_window_mining_report(report, args.report_path)
        print(format_window_mining_report(report))
    elif args.command == "crypto-window-family-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-window-family-report")
        report = generate_crypto_window_family_report(
            snapshot_path=args.snapshot_path,
            event_path=args.event_path,
            output_dir=args.output_dir,
        )
        if args.report_path is not None and args.report_path != report.summary_path:
            write_crypto_window_family_report(report, args.report_path)
        print(format_crypto_window_family_report(report))
    elif args.command == "crypto-signal-report":
        if args.event_path is None:
            parser.error("--event-path is required for crypto-signal-report")
        report = generate_crypto_signal_report(
            event_path=args.event_path,
            snapshot_path=args.snapshot_path,
            output_dir=args.output_dir,
        )
        if args.report_path is not None and args.report_path != Path(report.event_path):
            write_crypto_signal_report(report, args.output_dir or Path(report.event_path).parent)
        print(format_crypto_signal_report(report))
    elif args.command == "crypto-family-export":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-family-export")
        if args.output_dir is None:
            parser.error("--output-dir is required for crypto-family-export")
        result = export_crypto_family_window(
            snapshot_path=args.snapshot_path,
            event_path=args.event_path,
            output_dir=args.output_dir,
            underlying=args.underlying,
            event_family=args.event_family,
            series_key_contains=args.series_key_contains,
        )
        if args.report_path is not None and args.report_path != result.summary_path:
            write_crypto_family_export_result(result, args.report_path)
        print(format_crypto_family_export_result(result))
    elif args.command == "replay":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for replay")
        result = asyncio.run(
            run_replay(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                limit=args.limit,
                recorder_path=args.event_path,
                metrics_path=args.metrics_path,
            )
        )
        print(format_research_summary(result))
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
        result = asyncio.run(
            run_phase1_replay(
                board=args.board,
                snapshot_path=args.snapshot_path,
                config_dir=phase1_config_dir,
                limit=args.limit,
                output_dir=args.output_dir,
            )
        )
        print(format_phase1_replay_result(result))
    elif args.command == "crypto-calibration-report":
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-calibration-report")
        if args.train_snapshot_path is None:
            parser.error("--train-snapshot-path is required for crypto-calibration-report")
        if args.validation_snapshot_path is None:
            parser.error("--validation-snapshot-path is required for crypto-calibration-report")
        if args.holdout_snapshot_path is None:
            parser.error("--holdout-snapshot-path is required for crypto-calibration-report")
        report = generate_crypto_calibration_report(
            train_snapshot_path=args.train_snapshot_path,
            validation_snapshot_path=args.validation_snapshot_path,
            holdout_snapshot_path=args.holdout_snapshot_path,
            underlying_states=_load_underlying_states(args.underlying_state_path),
            output_dir=args.output_dir,
        )
        print(format_crypto_calibration_report(report))
    elif args.command == "crypto-calibration-experiments":
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-calibration-experiments")
        if args.train_snapshot_path is None:
            parser.error("--train-snapshot-path is required for crypto-calibration-experiments")
        if args.validation_snapshot_path is None:
            parser.error("--validation-snapshot-path is required for crypto-calibration-experiments")
        if args.holdout_snapshot_path is None:
            parser.error("--holdout-snapshot-path is required for crypto-calibration-experiments")
        report = run_crypto_calibration_experiments(
            train_snapshot_path=args.train_snapshot_path,
            validation_snapshot_path=args.validation_snapshot_path,
            holdout_snapshot_path=args.holdout_snapshot_path,
            underlying_states=_load_underlying_states(args.underlying_state_path),
            output_dir=args.output_dir,
            candidate_set=args.candidate_set,
        )
        print(format_crypto_calibration_experiment_report(report))
    elif args.command == "crypto-market-selection-report":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for crypto-market-selection-report")
        if args.underlying_state_path is None:
            parser.error("--underlying-state-path is required for crypto-market-selection-report")
        report = generate_crypto_market_selection_report(
            snapshot_path=args.snapshot_path,
            underlying_states=_load_underlying_states(args.underlying_state_path),
            event_path=args.event_path,
            output_dir=args.output_dir,
            barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
            fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
        )
        print(format_crypto_market_selection_report(report))
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
            )
        )
        print(f"phase2_board=crypto")
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
    elif args.command == "backtest":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for backtest")
        result = asyncio.run(
            run_backtest(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                limit=args.limit,
                recorder_path=args.event_path,
                metrics_path=args.metrics_path,
            )
        )
        print(format_research_summary(result))
    elif args.command == "show-dashboard":
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        risk_manager.advance_trading_day()
        print(render_dashboard(risk_manager.dashboard_state()))
    elif args.command == "manual-resume":
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        risk_manager.advance_trading_day()
        result = asyncio.run(risk_manager.manual_resume())
        print(f"manual_resume={str(result.approved).lower()}")
        print(f"reason={result.reason}")
        print(render_dashboard(risk_manager.dashboard_state()))


def _load_underlying_states(path: str) -> dict[str, object]:
    return load_underlying_states(path)


if __name__ == "__main__":
    main()
