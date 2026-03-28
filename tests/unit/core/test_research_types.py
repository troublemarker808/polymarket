from datetime import UTC, datetime

from pm_bot.core.research_types import (
    FairValueEstimate,
    NetEdgeEstimate,
    NormalizedMarketDefinition,
    Phase1RunSummary,
    ReplayAttributionRow,
)
from pm_bot.core.types import Category


def test_phase1_research_types_store_board_specific_values() -> None:
    normalized = NormalizedMarketDefinition(
        market_id="crypto-1",
        category=Category.CRYPTO,
        market_family="price_ladder_barrier",
        scope_key="btc-2026",
        instrument_key="btc-dip-55000",
        resolution_time=datetime(2026, 12, 31, tzinfo=UTC),
        attributes={"underlying": "BTC"},
    )
    fair_value = FairValueEstimate(
        market_id="crypto-1",
        category=Category.CRYPTO,
        fair_probability=0.44,
        confidence=0.72,
        half_life_seconds=3600,
        observed_probability=0.39,
        model_id="barrier.v1",
        rationale_tags=("curve_fit",),
        supporting_values={"spot": 62000.0},
    )
    net_edge = NetEdgeEstimate(
        market_id="crypto-1",
        category=Category.CRYPTO,
        fair_probability=0.44,
        observed_probability=0.39,
        gross_edge_bps=500.0,
        net_edge_bps=320.0,
        entry_cost_bps=80.0,
        exit_cost_bps=70.0,
        slippage_bps=20.0,
        adverse_selection_bps=10.0,
    )
    attribution = ReplayAttributionRow(
        market_id="crypto-1",
        category=Category.CRYPTO,
        strategy_id="crypto.surface",
        predicted_edge_bps=320.0,
        realized_pnl=1.25,
        prediction_error_bps=40.0,
        execution_error_bps=15.0,
        timing_error_bps=5.0,
        notes=("repricing",),
    )
    summary = Phase1RunSummary(
        generated_at=datetime(2026, 3, 28, tzinfo=UTC),
        board=Category.CRYPTO,
        mode="replay",
        run_id="crypto-phase1-test",
        config_dir="configs/profiles/research-crypto-phase1-v1",
        snapshot_path="data/research/sample_snapshots.jsonl",
        output_dir="data/research/phase1/crypto/crypto-phase1-test",
        processed_snapshots=10,
        signals_generated=2,
        signals_rejected=1,
        orders_rejected=0,
        submitted_orders=2,
        events_recorded=12,
        generated_by_strategy={"crypto.surface": 1},
        submitted_by_strategy={"crypto.surface": 1},
        total_equity=1000.5,
        today_pnl=0.5,
        status="running",
        halt_reason="none",
    )

    assert normalized.attributes["underlying"] == "BTC"
    assert fair_value.supporting_values["spot"] == 62000.0
    assert net_edge.net_edge_bps == 320.0
    assert attribution.notes == ("repricing",)
    assert summary.board is Category.CRYPTO
    assert summary.generated_by_strategy["crypto.surface"] == 1
