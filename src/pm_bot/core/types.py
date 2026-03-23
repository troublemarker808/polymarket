"""Domain types shared across category strategies, execution, and risk."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Category(str, Enum):
    SPORTS = "sports"
    CRYPTO = "crypto"
    WEATHER = "weather"


class RuntimeMode(str, Enum):
    RESEARCH = "research"
    PAPER = "paper"
    SHADOW = "shadow"
    LIVE = "live"


class SignalSide(str, Enum):
    BUY_YES = "buy_yes"
    BUY_NO = "buy_no"
    SELL_YES = "sell_yes"
    SELL_NO = "sell_no"
    HOLD = "hold"


class OrderAction(str, Enum):
    PLACE = "place"
    CANCEL = "cancel"


@dataclass(slots=True)
class MarketSnapshot:
    market_id: str
    token_id: str
    slug: str
    category: Category
    timestamp: datetime
    resolution_time: datetime | None
    best_bid_yes: float | None = None
    best_ask_yes: float | None = None
    best_bid_no: float | None = None
    best_ask_no: float | None = None
    last_traded_price: float | None = None
    liquidity_score: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class StrategySignal:
    strategy_id: str
    category: Category
    market_id: str
    token_id: str
    fair_probability: float
    side: SignalSide
    confidence: float
    edge_bps: float
    generated_at: datetime
    target_price: float | None = None
    target_size: float | None = None
    time_in_force: str = "GTC"
    rationale_tags: tuple[str, ...] = ()


@dataclass(slots=True)
class OrderIntent:
    strategy_id: str
    category: Category
    market_id: str
    token_id: str
    action: OrderAction
    side: SignalSide
    price: float | None
    size: float
    time_in_force: str
    created_at: datetime
    notional: float | None = None


@dataclass(slots=True)
class RiskDecision:
    approved: bool
    reason: str
