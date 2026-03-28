"""Net-edge helpers for Crypto Phase 1 ladder research."""

from __future__ import annotations

from pm_bot.core.research_types import FairValueEstimate, NetEdgeEstimate
from pm_bot.core.types import Category


def estimate_net_edge(
    *,
    market_id: str,
    fair_probability: float,
    observed_probability: float,
    entry_cost_bps: float,
    exit_cost_bps: float,
    slippage_bps: float = 0.0,
    adverse_selection_bps: float = 0.0,
) -> NetEdgeEstimate:
    gross_edge_bps = (fair_probability - observed_probability) * 10000
    total_cost_bps = entry_cost_bps + exit_cost_bps + slippage_bps + adverse_selection_bps
    # `gross_edge_bps` preserves fair-vs-observed direction, but net edge is the
    # tradeable edge magnitude after costs. A negative gross edge implies the
    # opposite side is the candidate trade; costs should never flip a losing edge
    # into a positive one.
    net_edge_bps = abs(gross_edge_bps) - total_cost_bps
    return NetEdgeEstimate(
        market_id=market_id,
        category=Category.CRYPTO,
        fair_probability=fair_probability,
        observed_probability=observed_probability,
        gross_edge_bps=gross_edge_bps,
        net_edge_bps=net_edge_bps,
        entry_cost_bps=entry_cost_bps,
        exit_cost_bps=exit_cost_bps,
        slippage_bps=slippage_bps,
        adverse_selection_bps=adverse_selection_bps,
    )


def enrich_fair_value_with_net_edge(
    *,
    estimate: FairValueEstimate,
    net_edge: NetEdgeEstimate,
) -> FairValueEstimate:
    supporting_values = dict(estimate.supporting_values)
    supporting_values.update(
        {
            "gross_edge_bps": net_edge.gross_edge_bps,
            "net_edge_bps": net_edge.net_edge_bps,
            "entry_cost_bps": net_edge.entry_cost_bps,
            "exit_cost_bps": net_edge.exit_cost_bps,
            "slippage_bps": net_edge.slippage_bps,
            "adverse_selection_bps": net_edge.adverse_selection_bps,
        }
    )
    return FairValueEstimate(
        market_id=estimate.market_id,
        category=estimate.category,
        fair_probability=estimate.fair_probability,
        confidence=estimate.confidence,
        half_life_seconds=estimate.half_life_seconds,
        observed_probability=estimate.observed_probability,
        model_id=estimate.model_id,
        rationale_tags=estimate.rationale_tags,
        supporting_values=supporting_values,
    )
