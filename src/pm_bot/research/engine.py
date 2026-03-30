"""Research helpers for replay and backtest workflows."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.settings import BotSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderBookLevel
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.paper_metrics import PaperExecutionMetrics
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.registry import build_default_registry
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.state import DashboardState, RuntimeState
from pm_bot.runtime.paper_sync import sync_paper_execution_state
from pm_bot.storage.recorder import JsonlRecorder


@dataclass(slots=True)
class ResearchRunResult:
    mode: str
    processed_snapshots: int
    signals_generated: int
    signals_rejected: int
    orders_rejected: int
    submitted_orders: int
    events_recorded: int
    generated_by_strategy: dict[str, int]
    submitted_by_strategy: dict[str, int]
    dashboard: DashboardState


class ResearchRecorder:
    """Capture research events in memory and optionally mirror them to JSONL."""

    def __init__(
        self,
        path: str | Path | None = None,
        metrics_path: str | Path | None = None,
    ) -> None:
        self.events: list[dict[str, Any]] = []
        self._jsonl: JsonlRecorder | None
        if path is not None:
            event_path = Path(path)
            event_path.parent.mkdir(parents=True, exist_ok=True)
            event_path.touch(exist_ok=True)
            self._jsonl = JsonlRecorder(event_path)
        else:
            self._jsonl = None
        self.metrics = PaperExecutionMetrics()
        self._metrics_path = Path(metrics_path) if metrics_path is not None else None

    async def record(self, event_type: str, payload: Mapping[str, object]) -> None:
        event = {"event_type": event_type, "payload": dict(payload)}
        self.events.append(event)
        self.metrics.record_event(event_type=event_type, payload=dict(payload))
        if self._jsonl is not None:
            await self._jsonl.record(event_type=event_type, payload=dict(payload))
        self._persist_metrics()

    def note_snapshot(self, timestamp: datetime) -> None:
        self.metrics.note_snapshot(timestamp)
        self._persist_metrics()

    def _persist_metrics(self) -> None:
        if self._metrics_path is None:
            return
        self.metrics.write(self._metrics_path)


def load_market_snapshots(path: str | Path) -> list[MarketSnapshot]:
    snapshot_path = Path(path)
    if snapshot_path.suffix == ".jsonl":
        raw_records = [
            json.loads(line)
            for line in snapshot_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
    elif snapshot_path.suffix == ".json":
        with snapshot_path.open("r", encoding="utf-8-sig") as handle:
            decoded = json.load(handle)
        if isinstance(decoded, list):
            raw_records = decoded
        elif isinstance(decoded, dict) and isinstance(decoded.get("snapshots"), list):
            raw_records = decoded["snapshots"]
        else:
            raise ValueError("JSON research input must be a list or contain a top-level 'snapshots' list")
    else:
        raise ValueError(f"Unsupported research input format: {snapshot_path.suffix}")

    return [_market_snapshot_from_record(record) for record in raw_records]


async def run_replay(
    *,
    snapshot_path: str | Path,
    config_dir: str = "configs",
    limit: int | None = None,
    recorder_path: str | Path | None = None,
    metrics_path: str | Path | None = None,
) -> ResearchRunResult:
    settings = load_settings_from_directory(config_dir)
    snapshots = load_market_snapshots(snapshot_path)
    if limit is not None:
        snapshots = snapshots[: max(limit, 0)]
    return await run_replay_snapshots(
        mode="replay",
        snapshots=snapshots,
        settings=settings,
        recorder_path=recorder_path,
        metrics_path=metrics_path,
    )


async def run_backtest(
    *,
    snapshot_path: str | Path,
    config_dir: str = "configs",
    limit: int | None = None,
    recorder_path: str | Path | None = None,
    metrics_path: str | Path | None = None,
) -> ResearchRunResult:
    settings = load_settings_from_directory(config_dir)
    snapshots = load_market_snapshots(snapshot_path)
    if limit is not None:
        snapshots = snapshots[: max(limit, 0)]
    return await run_replay_snapshots(
        mode="backtest",
        snapshots=snapshots,
        settings=settings,
        recorder_path=recorder_path,
        metrics_path=metrics_path,
    )


def format_research_summary(result: ResearchRunResult) -> str:
    return "\n".join(
        [
            f"mode={result.mode}",
            f"processed_snapshots={result.processed_snapshots}",
            f"signals_generated={result.signals_generated}",
            f"signals_rejected={result.signals_rejected}",
            f"orders_rejected={result.orders_rejected}",
            f"submitted_orders={result.submitted_orders}",
            f"events_recorded={result.events_recorded}",
            f"generated_by_strategy={_format_counter(result.generated_by_strategy)}",
            f"submitted_by_strategy={_format_counter(result.submitted_by_strategy)}",
            render_dashboard(result.dashboard),
        ]
    )


async def run_replay_snapshots(
    *,
    mode: str,
    snapshots: Sequence[MarketSnapshot],
    settings: BotSettings,
    recorder_path: str | Path | None,
    metrics_path: str | Path | None = None,
) -> ResearchRunResult:
    registry = build_default_registry()
    strategies = registry.build_enabled(settings=settings)
    risk_manager = BasicRiskManager(
        settings=settings.risk,
        trading_settings=settings.trading,
        state=RuntimeState(
            starting_equity=settings.trading.starting_equity,
            day_starting_equity=settings.trading.starting_equity,
            day_started_at=(snapshots[0].timestamp if snapshots else datetime.now(tz=timezone.utc)),
            updated_at=(snapshots[0].timestamp if snapshots else datetime.now(tz=timezone.utc)),
        ),
    )
    execution = PaperExecutionAdapter(
        ttl_seconds=settings.trading.default_quote_ttl_seconds,
        place_latency_ms=settings.trading.paper_place_latency_ms,
        cancel_latency_ms=settings.trading.paper_cancel_latency_ms,
        fee_bps=settings.trading.paper_fee_bps,
        taker_slippage_bps=settings.trading.paper_taker_slippage_bps,
    )
    recorder = ResearchRecorder(path=recorder_path, metrics_path=metrics_path)
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter(snapshots),
        strategies=strategies,
        risk_manager=risk_manager,
        execution=execution,
        recorder=recorder,
        default_order_size=settings.trading.default_order_notional,
    )

    processed = 0
    for snapshot in snapshots:
        risk_manager.record_data_success(snapshot.timestamp)
        recorder.note_snapshot(snapshot.timestamp)
        await sync_paper_execution_state(
            risk_manager=risk_manager,
            execution=execution,
            snapshot=snapshot,
            ttl_seconds=settings.trading.default_quote_ttl_seconds,
            recorder=recorder,
        )
        await router.run_once(snapshot=snapshot)
        await sync_paper_execution_state(
            risk_manager=risk_manager,
            execution=execution,
            snapshot=snapshot,
            ttl_seconds=settings.trading.default_quote_ttl_seconds,
            recorder=recorder,
        )
        processed += 1

    generated_by_strategy = _count_by_strategy(recorder.events, "signal.generated")
    submitted_by_strategy = _count_by_strategy(recorder.events, "order.submitted")
    return ResearchRunResult(
        mode=mode,
        processed_snapshots=processed,
        signals_generated=sum(generated_by_strategy.values()),
        signals_rejected=sum(1 for event in recorder.events if event["event_type"] == "signal.rejected"),
        orders_rejected=sum(1 for event in recorder.events if event["event_type"] == "order.rejected"),
        submitted_orders=len(execution.submitted_orders),
        events_recorded=len(recorder.events),
        generated_by_strategy=generated_by_strategy,
        submitted_by_strategy=submitted_by_strategy,
        dashboard=risk_manager.dashboard_state(),
    )


def _count_by_strategy(events: Sequence[Mapping[str, Any]], event_type: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for event in events:
        if event.get("event_type") != event_type:
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        strategy_id = payload.get("strategy_id")
        if strategy_id:
            counter[str(strategy_id)] += 1
    return dict(sorted(counter.items()))


def _format_counter(counter: Mapping[str, int]) -> str:
    if not counter:
        return ""
    return ",".join(f"{key}:{value}" for key, value in sorted(counter.items()))


def _market_snapshot_from_record(record: Any) -> MarketSnapshot:
    payload = record
    if isinstance(record, Mapping) and isinstance(record.get("snapshot"), Mapping):
        payload = record["snapshot"]
    elif isinstance(record, Mapping) and isinstance(record.get("payload"), Mapping):
        candidate = record["payload"]
        if "market_id" in candidate and "category" in candidate:
            payload = candidate
    if not isinstance(payload, Mapping):
        raise ValueError("Each research record must be a mapping")

    metadata_raw = payload.get("metadata") or {}
    metadata = {
        str(key): "" if value is None else str(value)
        for key, value in dict(metadata_raw).items()
    }

    return MarketSnapshot(
        market_id=str(payload["market_id"]),
        token_id=str(payload["token_id"]),
        slug=str(payload.get("slug", payload["market_id"])),
        category=Category(str(payload["category"])),
        timestamp=_parse_datetime(payload.get("timestamp")) or datetime.now(tz=timezone.utc),
        resolution_time=_parse_datetime(payload.get("resolution_time")),
        best_bid_yes=_parse_optional_float(payload.get("best_bid_yes")),
        best_ask_yes=_parse_optional_float(payload.get("best_ask_yes")),
        best_bid_no=_parse_optional_float(payload.get("best_bid_no")),
        best_ask_no=_parse_optional_float(payload.get("best_ask_no")),
        best_bid_yes_size=_parse_optional_float(payload.get("best_bid_yes_size")),
        best_ask_yes_size=_parse_optional_float(payload.get("best_ask_yes_size")),
        best_bid_no_size=_parse_optional_float(payload.get("best_bid_no_size")),
        best_ask_no_size=_parse_optional_float(payload.get("best_ask_no_size")),
        tick_size=_parse_optional_float(payload.get("tick_size")),
        min_order_size=_parse_optional_float(payload.get("min_order_size")),
        last_traded_price=_parse_optional_float(payload.get("last_traded_price")),
        last_trade_side=_parse_optional_str(payload.get("last_trade_side")),
        last_trade_size=_parse_optional_float(payload.get("last_trade_size")),
        yes_bid_levels=_parse_levels(payload.get("yes_bid_levels")),
        yes_ask_levels=_parse_levels(payload.get("yes_ask_levels")),
        no_bid_levels=_parse_levels(payload.get("no_bid_levels")),
        no_ask_levels=_parse_levels(payload.get("no_ask_levels")),
        liquidity_score=float(payload.get("liquidity_score", 0.0)),
        metadata=metadata,
    )


def _parse_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _parse_levels(raw_levels: Any) -> tuple[OrderBookLevel, ...]:
    if raw_levels is None:
        return ()
    if not isinstance(raw_levels, Sequence) or isinstance(raw_levels, (str, bytes)):
        return ()
    levels: list[OrderBookLevel] = []
    for level in raw_levels:
        if not isinstance(level, Mapping):
            continue
        price = _parse_optional_float(level.get("price"))
        size = _parse_optional_float(level.get("size"))
        if price is None or size is None:
            continue
        levels.append(OrderBookLevel(price=price, size=size))
    return tuple(levels)
