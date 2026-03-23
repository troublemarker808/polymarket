"""Command-line helpers for validating the foundation."""

from __future__ import annotations

import argparse
import asyncio
import os

from pm_bot.adapters.polymarket import fetch_geoblock_status_sync
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.execution import describe_execution_configuration
from pm_bot.registry import build_default_registry
from pm_bot.research import format_research_summary, run_backtest, run_replay
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.live_session import format_live_session_stats, run_crypto_live_session
from pm_bot.runtime.paper_session import format_dashboard_summary, run_crypto_paper_session_once
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket bot foundation CLI")
    parser.add_argument(
        "command",
        choices=(
            "check-geoblock",
            "run-live-crypto-session",
            "validate-config",
            "validate-live-config",
            "paper-crypto-once",
            "replay",
            "backtest",
            "show-dashboard",
            "manual-resume",
        ),
        help="Validate configs and print enabled strategies.",
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
        "--snapshot-path",
        default=None,
        help="Path to a JSON or JSONL file containing normalized research snapshots.",
    )
    parser.add_argument(
        "--event-path",
        default=None,
        help="Optional JSONL path where replay/backtest runtime events should be written.",
    )
    args = parser.parse_args()

    if args.command == "check-geoblock":
        status = fetch_geoblock_status_sync()
        print(f"blocked={str(status.blocked).lower()}")
        print(f"country={status.country}")
        print(f"region={status.region}")
        print(f"ip={status.ip}")
    elif args.command == "run-live-crypto-session":
        stats = asyncio.run(
            run_crypto_live_session(
                config_dir=args.config_dir,
                state_path=args.state_path,
                max_pages=args.max_pages,
                max_market_snapshots=args.max_market_snapshots,
                max_user_events=args.max_user_events,
            )
        )
        print(format_live_session_stats(stats))
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
            )
        )
        print(format_dashboard_summary(result))
    elif args.command == "replay":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for replay")
        result = asyncio.run(
            run_replay(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                limit=args.limit,
                recorder_path=args.event_path,
            )
        )
        print(format_research_summary(result))
    elif args.command == "backtest":
        if args.snapshot_path is None:
            parser.error("--snapshot-path is required for backtest")
        result = asyncio.run(
            run_backtest(
                snapshot_path=args.snapshot_path,
                config_dir=args.config_dir,
                limit=args.limit,
                recorder_path=args.event_path,
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
        print(render_dashboard(risk_manager.dashboard_state()))
    elif args.command == "manual-resume":
        settings = load_settings_from_directory(args.config_dir)
        state_store = JsonRuntimeStateStore(args.state_path)
        risk_manager = BasicRiskManager(
            settings=settings.risk,
            trading_settings=settings.trading,
            state_store=state_store,
        )
        result = asyncio.run(risk_manager.manual_resume())
        print(f"manual_resume={str(result.approved).lower()}")
        print(f"reason={result.reason}")
        print(render_dashboard(risk_manager.dashboard_state()))
