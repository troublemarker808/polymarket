from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.crypto.phase1.edge import enrich_fair_value_with_net_edge, estimate_net_edge


def test_estimate_net_edge_subtracts_costs_from_positive_gross_edge() -> None:
    edge = estimate_net_edge(
        market_id="eth-dip-1000",
        fair_probability=0.19,
        observed_probability=0.11,
        entry_cost_bps=50.0,
        exit_cost_bps=50.0,
        slippage_bps=5.0,
        adverse_selection_bps=10.0,
    )

    assert round(edge.gross_edge_bps, 2) == 800.0
    assert round(edge.net_edge_bps, 2) == 685.0


def test_estimate_net_edge_preserves_negative_gross_direction_but_not_positive_net() -> None:
    edge = estimate_net_edge(
        market_id="btc-reach-150k",
        fair_probability=0.0885990334,
        observed_probability=0.095,
        entry_cost_bps=50.0,
        exit_cost_bps=50.0,
        slippage_bps=5.0,
        adverse_selection_bps=10.0,
    )

    assert round(edge.gross_edge_bps, 2) == -64.01
    assert round(edge.net_edge_bps, 2) == -50.99


def test_enrich_fair_value_with_net_edge_adds_cost_breakdown() -> None:
    estimate = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.19,
        confidence=0.75,
        half_life_seconds=3600,
        observed_probability=0.11,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"distance_ratio": 0.12},
    )
    edge = estimate_net_edge(
        market_id="eth-dip-1000",
        fair_probability=0.19,
        observed_probability=0.11,
        entry_cost_bps=50.0,
        exit_cost_bps=50.0,
        slippage_bps=5.0,
        adverse_selection_bps=10.0,
    )

    enriched = enrich_fair_value_with_net_edge(estimate=estimate, net_edge=edge)

    assert enriched.supporting_values["gross_edge_bps"] == 800.0
    assert enriched.supporting_values["net_edge_bps"] == 685.0
    assert enriched.supporting_values["distance_ratio"] == 0.12
