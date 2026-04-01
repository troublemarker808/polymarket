# Crypto Market Selection Report

- generated_at: 2026-03-31T21:07:07.981323+00:00
- snapshot_path: tests\fixtures\crypto_phase2\compare_snapshots.jsonl
- barrier_steepness: 1.65
- fusion_barrier_weight: 0.35
- fusion_surface_weight: 0.65

## Series Reports

### eth-dip-ladder-2026

- underlying: ETH
- event_family: dip
- market_count: 3
- runtime_actionable_market_count: 3
- positive_net_edge_count: 3
- mean_net_edge_bps: 519.07
- median_net_edge_bps: 323.39
- mean_entry_cost_bps: 66.67
- min_liquidity_score: 0.0000
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.6264
- selection_rank: 1
- recommended_action: tradable
- reasons: thin_liquidity

## Market Rows

- eth-dip-1000: series_key=eth-dip-ladder-2026, instrument_key=ETH:dip:2026-12-31:1000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=188.17, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.0000, profit_quality_score=0.6542
  top_book_depth=, nearby_book_depth=, quote_age_seconds=
- eth-dip-1500: series_key=eth-dip-ladder-2026, instrument_key=ETH:dip:2026-12-31:1500, action=selective_market, reasons=wide_spread, thin_liquidity
  net_edge_bps=1045.66, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.0000, profit_quality_score=0.5708
  top_book_depth=, nearby_book_depth=, quote_age_seconds=
- eth-dip-800: series_key=eth-dip-ladder-2026, instrument_key=ETH:dip:2026-12-31:800, action=selective_market, reasons=thin_liquidity
  net_edge_bps=323.39, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.0000, profit_quality_score=0.6542
  top_book_depth=, nearby_book_depth=, quote_age_seconds=
