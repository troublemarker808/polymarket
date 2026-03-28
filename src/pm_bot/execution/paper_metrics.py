"""Paper execution metrics and persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PaperExecutionMetrics:
    processed_snapshots: int = 0
    signals_generated: int = 0
    signals_rejected: int = 0
    orders_submitted: int = 0
    orders_rejected: int = 0
    orders_filled: int = 0
    orders_partially_filled: int = 0
    orders_expired: int = 0
    orders_canceled: int = 0
    trades_closed: int = 0
    market_data_failures: int = 0
    market_data_recoveries: int = 0
    generated_by_strategy: dict[str, int] = field(default_factory=dict)
    submitted_by_strategy: dict[str, int] = field(default_factory=dict)
    observed_trading_days: set[str] = field(default_factory=set)
    filled_shares_total: float = 0.0
    maker_filled_shares: float = 0.0
    taker_filled_shares: float = 0.0
    fill_count_for_latency: int = 0
    total_fill_age_ms: float = 0.0
    fill_shares_for_mid: float = 0.0
    total_fill_price_vs_mid_bps_weighted: float = 0.0
    updated_at: str | None = None

    def note_snapshot(self, timestamp: datetime) -> None:
        self.processed_snapshots += 1
        self.observed_trading_days.add(timestamp.astimezone(timezone.utc).date().isoformat())
        self.updated_at = timestamp.isoformat()

    def record_event(self, event_type: str, payload: dict[str, object]) -> None:
        strategy_id = str(payload.get("strategy_id", "")).strip()
        if event_type == "signal.generated":
            self.signals_generated += 1
            if strategy_id:
                self.generated_by_strategy[strategy_id] = self.generated_by_strategy.get(strategy_id, 0) + 1
        elif event_type == "signal.rejected":
            self.signals_rejected += 1
        elif event_type == "order.submitted":
            self.orders_submitted += 1
            if strategy_id:
                self.submitted_by_strategy[strategy_id] = self.submitted_by_strategy.get(strategy_id, 0) + 1
        elif event_type == "order.rejected":
            self.orders_rejected += 1
        elif event_type == "order.filled":
            self.orders_filled += 1
            self._record_fill_metrics(event_type=event_type, payload=payload)
        elif event_type == "order.partially_filled":
            self.orders_partially_filled += 1
            self._record_fill_metrics(event_type=event_type, payload=payload)
        elif event_type == "order.expired":
            self.orders_expired += 1
        elif event_type == "order.canceled":
            self.orders_canceled += 1
        elif event_type == "trade.closed":
            self.trades_closed += 1
        elif event_type == "market_data.failure":
            self.market_data_failures += 1
        elif event_type == "market_data.recovered":
            self.market_data_recoveries += 1

        updated_at = payload.get("updated_at")
        if updated_at:
            self.updated_at = str(updated_at)

    @property
    def paper_days_observed(self) -> int:
        return len(self.observed_trading_days)

    @property
    def fill_rate(self) -> float:
        if self.orders_submitted <= 0:
            return 0.0
        return self.orders_filled / self.orders_submitted

    @property
    def cancel_rate(self) -> float:
        if self.orders_submitted <= 0:
            return 0.0
        return (self.orders_expired + self.orders_canceled) / self.orders_submitted

    @property
    def avg_time_to_fill_ms(self) -> float:
        if self.fill_count_for_latency <= 0:
            return 0.0
        return self.total_fill_age_ms / self.fill_count_for_latency

    @property
    def avg_fill_price_vs_mid_bps(self) -> float:
        if self.fill_shares_for_mid <= 0:
            return 0.0
        return self.total_fill_price_vs_mid_bps_weighted / self.fill_shares_for_mid

    @property
    def maker_fill_share(self) -> float:
        if self.filled_shares_total <= 0:
            return 0.0
        return self.maker_filled_shares / self.filled_shares_total

    @property
    def taker_fill_share(self) -> float:
        if self.filled_shares_total <= 0:
            return 0.0
        return self.taker_filled_shares / self.filled_shares_total

    def to_dict(self) -> dict[str, Any]:
        return {
            "processed_snapshots": self.processed_snapshots,
            "paper_days_observed": self.paper_days_observed,
            "observed_trading_days": sorted(self.observed_trading_days),
            "signals_generated": self.signals_generated,
            "signals_rejected": self.signals_rejected,
            "orders_submitted": self.orders_submitted,
            "orders_rejected": self.orders_rejected,
            "orders_filled": self.orders_filled,
            "orders_partially_filled": self.orders_partially_filled,
            "orders_expired": self.orders_expired,
            "orders_canceled": self.orders_canceled,
            "trades_closed": self.trades_closed,
            "market_data_failures": self.market_data_failures,
            "market_data_recoveries": self.market_data_recoveries,
            "filled_shares_total": self.filled_shares_total,
            "maker_filled_shares": self.maker_filled_shares,
            "taker_filled_shares": self.taker_filled_shares,
            "fill_rate": self.fill_rate,
            "cancel_rate": self.cancel_rate,
            "avg_time_to_fill_ms": self.avg_time_to_fill_ms,
            "avg_fill_price_vs_mid_bps": self.avg_fill_price_vs_mid_bps,
            "maker_fill_share": self.maker_fill_share,
            "taker_fill_share": self.taker_fill_share,
            "generated_by_strategy": dict(sorted(self.generated_by_strategy.items())),
            "submitted_by_strategy": dict(sorted(self.submitted_by_strategy.items())),
            "updated_at": self.updated_at,
        }

    def write(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=True, indent=2)

    def _record_fill_metrics(self, *, event_type: str, payload: dict[str, object]) -> None:
        fill_shares_delta = float(payload.get("fill_shares_delta", 0.0) or 0.0)
        if fill_shares_delta > 0:
            self.filled_shares_total += fill_shares_delta
            fill_source = str(payload.get("fill_source", "")).strip().lower()
            if fill_source == "maker":
                self.maker_filled_shares += fill_shares_delta
            elif fill_source == "taker":
                self.taker_filled_shares += fill_shares_delta

        fill_age_ms = payload.get("fill_age_ms")
        if event_type == "order.filled" and fill_age_ms is not None:
            self.fill_count_for_latency += 1
            self.total_fill_age_ms += float(fill_age_ms)

        mid_price = payload.get("mid_price")
        average_fill_price = payload.get("average_fill_price")
        if mid_price is None or average_fill_price is None or fill_shares_delta <= 0:
            return
        mid = float(mid_price)
        fill = float(average_fill_price)
        if mid <= 0:
            return
        self.fill_shares_for_mid += fill_shares_delta
        self.total_fill_price_vs_mid_bps_weighted += (((fill - mid) / mid) * 10000) * fill_shares_delta
