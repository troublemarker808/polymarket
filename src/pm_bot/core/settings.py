"""Configuration models.

The implementation is intentionally lightweight in V1. Settings are kept separate
from strategy logic so each category can evolve through config changes first.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from pm_bot.core.types import Category, RuntimeMode


class AppSettings(BaseModel):
    environment: str = "dev"
    mode: RuntimeMode = RuntimeMode.PAPER
    log_level: str = "INFO"


class CategoryToggles(BaseModel):
    sports: bool = True
    crypto: bool = True
    weather: bool = True

    def enabled_categories(self) -> tuple[Category, ...]:
        enabled: list[Category] = []
        if self.sports:
            enabled.append(Category.SPORTS)
        if self.crypto:
            enabled.append(Category.CRYPTO)
        if self.weather:
            enabled.append(Category.WEATHER)
        return tuple(enabled)


class TradingSettings(BaseModel):
    default_quote_ttl_seconds: int = Field(ge=1, default=15)
    starting_equity: float = Field(ge=0, default=100.0)
    default_order_notional: float = Field(ge=0, default=5.0)
    paper_place_latency_ms: int = Field(ge=0, default=250)
    paper_cancel_latency_ms: int = Field(ge=0, default=250)
    paper_replace_latency_ms: int = Field(ge=0, default=250)
    paper_fee_bps: float = Field(ge=0, default=0.0)
    paper_taker_slippage_bps: float = Field(ge=0, default=5.0)
    max_notional_per_market: float = Field(ge=0, default=5.0)
    max_notional_per_category: float = Field(ge=0, default=50.0)
    max_concurrent_positions: int = Field(ge=1, default=4)
    max_positions_per_market: int = Field(ge=1, default=1)
    daily_order_soft_limit: int = Field(ge=1, default=10)
    daily_order_hard_limit: int = Field(ge=1, default=15)
    live_allowed_categories: tuple[Category, ...] = (Category.CRYPTO,)


class RiskSettings(BaseModel):
    max_daily_drawdown_pct: float = Field(ge=0, default=5.0)
    max_consecutive_losses: int = Field(ge=1, default=5)
    max_open_orders: int = Field(ge=0, default=4)
    open_order_replacement_min_edge_improvement_bps: float = Field(ge=0, default=50.0)
    kill_switch_on_stale_data_seconds: int = Field(ge=1, default=30)
    manual_resume_required: bool = True
    halt_on_data_source_failure: bool = True


class PolymarketSettings(BaseModel):
    api_url: str = "https://clob.polymarket.com"
    gamma_url: str = "https://gamma-api.polymarket.com"
    market_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    user_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
    chain_id: int = Field(ge=1, default=137)
    signature_type: int = Field(ge=0, default=1)
    allow_live_orders: bool = False
    derive_api_creds_if_missing: bool = False
    post_only_live_orders: bool = False
    private_key_env: str = "POLYMARKET_PRIVATE_KEY"
    api_key_env: str = "POLYMARKET_API_KEY"
    api_secret_env: str = "POLYMARKET_API_SECRET"
    api_passphrase_env: str = "POLYMARKET_API_PASSPHRASE"
    funder_env: str = "POLYMARKET_FUNDER"
    live_recovery_scope: Literal["full", "session"] = "full"


class CategoryRuntimeConfig(BaseModel):
    category: Category
    enabled_strategies: tuple[str, ...]
    markets: dict[str, Any] = Field(default_factory=dict)
    strategy: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BotSettings(BaseModel):
    app: AppSettings
    categories: CategoryToggles
    trading: TradingSettings
    risk: RiskSettings
    polymarket: PolymarketSettings = Field(default_factory=PolymarketSettings)
    category_configs: dict[Category, CategoryRuntimeConfig] = Field(default_factory=dict)
