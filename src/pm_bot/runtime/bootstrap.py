"""Construct a minimally runnable paper-mode application graph."""

from __future__ import annotations

from pathlib import Path

from pm_bot.config.loader import load_settings
from pm_bot.execution.factory import build_execution_adapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.storage.recorder import JsonlRecorder


def build_paper_runtime(
    market_data,
    base_config_path: str | Path,
    category_config_paths: list[str | Path],
    recorder_path: str | Path = "data/runtime/events.jsonl",
) -> EventRouter:
    settings = load_settings(
        base_config_path=base_config_path,
        category_config_paths=category_config_paths,
    )
    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
    )
    execution = build_execution_adapter(settings=settings)
    recorder = JsonlRecorder(path=recorder_path)
    return EventRouter(
        market_data=market_data,
        strategies=strategies,
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
    )
