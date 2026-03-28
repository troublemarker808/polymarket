"""Shared Phase 1 research dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pm_bot.core.types import Category

JsonScalar = str | int | float | bool | None


@dataclass(slots=True)
class NormalizedMarketDefinition:
    market_id: str
    category: Category
    market_family: str
    scope_key: str
    instrument_key: str
    resolution_time: datetime | None = None
    attributes: dict[str, JsonScalar] = field(default_factory=dict)


@dataclass(slots=True)
class FairValueEstimate:
    market_id: str
    category: Category
    fair_probability: float
    confidence: float
    half_life_seconds: int | None = None
    observed_probability: float | None = None
    model_id: str | None = None
    rationale_tags: tuple[str, ...] = ()
    supporting_values: dict[str, JsonScalar] = field(default_factory=dict)


@dataclass(slots=True)
class NetEdgeEstimate:
    market_id: str
    category: Category
    fair_probability: float
    observed_probability: float
    gross_edge_bps: float
    net_edge_bps: float
    entry_cost_bps: float = 0.0
    exit_cost_bps: float = 0.0
    slippage_bps: float = 0.0
    adverse_selection_bps: float = 0.0


@dataclass(slots=True)
class ReplayAttributionRow:
    market_id: str
    category: Category
    strategy_id: str
    predicted_edge_bps: float
    realized_pnl: float
    prediction_error_bps: float = 0.0
    execution_error_bps: float = 0.0
    timing_error_bps: float = 0.0
    notes: tuple[str, ...] = ()


@dataclass(slots=True)
class Phase1RunSummary:
    generated_at: datetime
    board: Category
    mode: str
    run_id: str
    config_dir: str
    snapshot_path: str
    output_dir: str
    processed_snapshots: int
    signals_generated: int
    signals_rejected: int
    orders_rejected: int
    submitted_orders: int
    events_recorded: int
    generated_by_strategy: dict[str, int] = field(default_factory=dict)
    submitted_by_strategy: dict[str, int] = field(default_factory=dict)
    total_equity: float = 0.0
    today_pnl: float = 0.0
    status: str = ""
    halt_reason: str = ""
