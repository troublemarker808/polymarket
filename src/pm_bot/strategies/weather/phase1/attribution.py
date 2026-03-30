"""Attribution helpers for Weather Phase 1 replay artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate, ReplayAttributionRow
from pm_bot.core.types import Category
from pm_bot.strategies.common import parse_float


def build_weather_attribution_rows(
    *,
    fair_values: tuple[FairValueEstimate, ...],
    event_path: str | Path,
    strategy_id: str = "weather.phase1.fused",
) -> tuple[ReplayAttributionRow, ...]:
    realized_pnl_by_market: dict[str, float] = {}
    event_path = Path(event_path)
    if event_path.exists():
        for line in event_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event_type") != "trade.closed":
                continue
            payload = event.get("payload", {})
            market_id = str(payload.get("market_id", ""))
            realized_pnl_by_market[market_id] = realized_pnl_by_market.get(market_id, 0.0) + (
                parse_float(payload, "realized_pnl") or 0.0
            )

    rows: list[ReplayAttributionRow] = []
    for fair_value in fair_values:
        observed_probability = fair_value.observed_probability or fair_value.fair_probability
        predicted_edge_bps = (fair_value.fair_probability - observed_probability) * 10000
        threshold_probability = parse_float(fair_value.supporting_values, "threshold_probability")
        if threshold_probability is None:
            threshold_probability = fair_value.fair_probability
        strip_value = parse_float(fair_value.supporting_values, "strip_probability")
        if strip_value is None:
            strip_value = threshold_probability
        realized_pnl = realized_pnl_by_market.get(fair_value.market_id, 0.0)
        rows.append(
            ReplayAttributionRow(
                market_id=fair_value.market_id,
                category=Category.WEATHER,
                strategy_id=strategy_id,
                predicted_edge_bps=predicted_edge_bps,
                realized_pnl=realized_pnl,
                prediction_error_bps=(predicted_edge_bps if realized_pnl == 0 else 0.0),
                execution_error_bps=(fair_value.fair_probability - threshold_probability) * 10000,
                timing_error_bps=(threshold_probability - strip_value) * 10000,
                notes=fair_value.rationale_tags,
            )
        )
    return tuple(rows)
