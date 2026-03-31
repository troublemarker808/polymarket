"""Crypto Phase 2 execution dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pm_bot.core.types import SignalSide


@dataclass(slots=True, frozen=True)
class CryptoSignalClassification:
    market_id: str
    signal_type: str
    side: SignalSide
    urgency_score: float
    expected_exit_mode: str
    rationale_tags: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoTradeEligibility:
    market_id: str
    eligible: bool
    reason: str
    net_edge_bps: float
    market_spread_bps: float
    rationale_tags: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoExecutionDecision:
    market_id: str
    route: str
    side: SignalSide
    target_price: float | None
    quote_ttl_seconds: int | None
    urgency_score: float
    rationale_tags: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoPositionIntent:
    market_id: str
    token_id: str
    signal_type: str
    entry_side: SignalSide
    expected_exit_mode: str
    expected_holding_seconds: int
    effective_horizon_days: float
    entry_fair_probability: float
    entry_observed_probability: float
    net_edge_bps: float
    created_at: datetime
    rationale_tags: tuple[str, ...]
    entry_fill_price: float | None = None
    entry_mid_price: float | None = None
    entry_fill_source: str | None = None


@dataclass(slots=True, frozen=True)
class CryptoExitDecision:
    market_id: str
    should_exit: bool
    exit_side: SignalSide | None
    reason: str
    target_price: float | None
    remaining_edge_bps: float
    rationale_tags: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoReentryState:
    market_id: str
    blocked_until: datetime | None
    stop_out_count: int
    quarantine_active: bool
    reason: str


@dataclass(slots=True, frozen=True)
class CryptoExecutionFeedback:
    maker_fill_rate: float
    taker_shortfall_bps: float
    repeated_expiration_rate: float
    repeated_stop_out_rate: float
    recommended_route_bias: str


@dataclass(slots=True, frozen=True)
class CryptoDynamicEligibilityGate:
    family_key: str
    sample_count: int
    min_net_edge_bps: float
    taker_max_entry_premium_bps: float
    repricing_taker_max_entry_premium_bps: float
    reason_tag: str


@dataclass(slots=True, frozen=True)
class CryptoRoutePolicyState:
    route_key: str
    sample_count: int
    route_bias: str
    aggressiveness_adjustment: float
    taker_urgency_adjustment: float
    taker_premium_adjustment_bps: float
    updated_at: datetime
    cooldown_until: datetime
