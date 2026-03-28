"""Attribution helpers for Sports Phase 1 replay artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate, ReplayAttributionRow
from pm_bot.core.types import Category


def build_sports_attribution_rows(
    *,
    fair_values: tuple[FairValueEstimate, ...],
    event_path: str | Path,
    strategy_id: str = "sports.phase1.pregame",
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
            realized_pnl_by_market[market_id] = realized_pnl_by_market.get(market_id, 0.0) + float(
                payload.get("realized_pnl", 0.0)
            )

    rows: list[ReplayAttributionRow] = []
    for fair_value in fair_values:
        observed_probability = fair_value.observed_probability or fair_value.fair_probability
        predicted_edge_bps = (fair_value.fair_probability - observed_probability) * 10000
        context_adjusted_edge_bps = float(
            fair_value.supporting_values.get("context_adjusted_edge_bps", predicted_edge_bps)
        )
        realized_pnl = realized_pnl_by_market.get(fair_value.market_id, 0.0)
        rows.append(
            ReplayAttributionRow(
                market_id=fair_value.market_id,
                category=Category.SPORTS,
                strategy_id=strategy_id,
                predicted_edge_bps=predicted_edge_bps,
                realized_pnl=realized_pnl,
                prediction_error_bps=(predicted_edge_bps if realized_pnl == 0 else 0.0),
                execution_error_bps=predicted_edge_bps - context_adjusted_edge_bps,
                timing_error_bps=0.0,
                notes=fair_value.rationale_tags,
            )
        )
    return tuple(rows)
