# Crypto Market Selection Report

- generated_at: 2026-04-01T06:59:22.023459+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- barrier_steepness: 1.65
- fusion_barrier_weight: 0.35
- fusion_surface_weight: 0.65

## Series Reports

### when-will-bitcoin-hit-150k

- underlying: BTC
- event_family: reach
- market_count: 3
- runtime_actionable_market_count: 1
- positive_net_edge_count: 3
- mean_net_edge_bps: 3215.12
- median_net_edge_bps: 3292.00
- mean_entry_cost_bps: 28.33
- min_liquidity_score: 0.8016
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.8426
- selection_rank: 1
- recommended_action: tradable
- reasons: thin_liquidity

### what-price-will-bitcoin-hit-before-2027

- underlying: BTC
- event_family: dip
- market_count: 27
- runtime_actionable_market_count: 11
- positive_net_edge_count: 16
- mean_net_edge_bps: 261.35
- median_net_edge_bps: 40.71
- mean_entry_cost_bps: 52.22
- min_liquidity_score: 0.8105
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.6484
- selection_rank: 2
- recommended_action: selective_only
- reasons: thin_liquidity

## Market Rows

- 1057883: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:250000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=142.62, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8275, profit_quality_score=0.8947
  top_book_depth=2729.50, nearby_book_depth=5172.35, quote_age_seconds=504.87
- 1057916: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:15000, action=watch_market, reasons=stale_quote, thin_liquidity
  net_edge_bps=22.20, entry_cost_bps=25.00, spread_bps=50.00, liquidity_score=0.8491, profit_quality_score=0.6382
  top_book_depth=47.71, nearby_book_depth=417.52, quote_age_seconds=800.85
- 1339767: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:50000, action=watch_market, reasons=contract_price_too_low, wide_spread
  net_edge_bps=1276.07, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9808, profit_quality_score=0.7470
  top_book_depth=734.15, nearby_book_depth=1672.24, quote_age_seconds=737.23
- 1339768: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:40000, action=tradable_market, reasons=none
  net_edge_bps=749.22, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9891, profit_quality_score=0.8645
  top_book_depth=360.32, nearby_book_depth=5865.86, quote_age_seconds=779.66
- 1339769: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:30000, action=watch_market, reasons=wide_spread, thin_liquidity
  net_edge_bps=100.37, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9123, profit_quality_score=0.7333
  top_book_depth=1583.73, nearby_book_depth=1965.73, quote_age_seconds=685.23
- 1343219: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:20000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-14.10, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8591, profit_quality_score=0.5017
  top_book_depth=28.90, nearby_book_depth=7121.12, quote_age_seconds=639.50
- 1343220: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:10000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-10.25, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8300, profit_quality_score=0.5812
  top_book_depth=255.30, nearby_book_depth=1788.82, quote_age_seconds=607.64
- 1343228: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:5000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-12.37, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8244, profit_quality_score=0.5744
  top_book_depth=3676.47, nearby_book_depth=4889.31, quote_age_seconds=592.48
- 1345530: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:80000, action=selective_market, reasons=wide_spread
  net_edge_bps=1619.25, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9750, profit_quality_score=0.7658
  top_book_depth=27.10, nearby_book_depth=1009.65, quote_age_seconds=736.90
- 1345531: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:90000, action=watch_market, reasons=stale_quote, negative_edge, wide_spread
  net_edge_bps=-75.48, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=1.0000, profit_quality_score=0.3508
  top_book_depth=790.22, nearby_book_depth=3885.20, quote_age_seconds=68911.81
- 1393068: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:500000, action=watch_market, reasons=stale_quote, negative_edge, contract_price_too_low, thin_liquidity
  net_edge_bps=-20.00, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8143, profit_quality_score=0.5520
  top_book_depth=918.38, nearby_book_depth=11874.32, quote_age_seconds=3996.36
- 1393070: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:1000000, action=watch_market, reasons=negative_edge, contract_price_too_low, thin_liquidity
  net_edge_bps=-8.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8105, profit_quality_score=0.5813
  top_book_depth=12282.47, nearby_book_depth=15274.72, quote_age_seconds=704.30
- 573654: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2026-04-01:150, action=watch_market, reasons=stale_quote, contract_price_too_low, thin_liquidity
  net_edge_bps=3434.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8016, profit_quality_score=0.8695
  top_book_depth=31302.76, nearby_book_depth=33180.20, quote_age_seconds=944.49
- 573655: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2026-07-01:150, action=watch_market, reasons=stale_quote, contract_price_too_low, thin_liquidity
  net_edge_bps=3292.00, entry_cost_bps=30.00, spread_bps=60.00, liquidity_score=0.8181, profit_quality_score=0.8311
  top_book_depth=, nearby_book_depth=, quote_age_seconds=846.02
- 573656: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2027-01-01:150, action=selective_market, reasons=thin_liquidity
  net_edge_bps=2918.61, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8650, profit_quality_score=0.8272
  top_book_depth=672.94, nearby_book_depth=9241.20, quote_age_seconds=766.71
- 701486: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:200000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=67.37, entry_cost_bps=10.00, spread_bps=20.00, liquidity_score=0.8310, profit_quality_score=0.8000
  top_book_depth=383.89, nearby_book_depth=3926.93, quote_age_seconds=625.72
- 701487: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:190000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=113.25, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8409, profit_quality_score=0.8223
  top_book_depth=1412.89, nearby_book_depth=15990.32, quote_age_seconds=604.40
- 701488: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:180000, action=watch_market, reasons=negative_edge, wide_spread, thin_liquidity
  net_edge_bps=-7.28, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.8440, profit_quality_score=0.4335
  top_book_depth=7271.50, nearby_book_depth=19282.13, quote_age_seconds=681.64
- 701489: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:170000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=40.71, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8470, profit_quality_score=0.6655
  top_book_depth=2875.00, nearby_book_depth=12870.85, quote_age_seconds=684.10
- 701490: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:160000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=159.95, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8591, profit_quality_score=0.8260
  top_book_depth=5871.63, nearby_book_depth=22110.19, quote_age_seconds=607.88
- 701491: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:150000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=145.99, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8650, profit_quality_score=0.8272
  top_book_depth=55.00, nearby_book_depth=11136.70, quote_age_seconds=484.32
- 701492: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:140000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-57.93, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8650, profit_quality_score=0.4072
  top_book_depth=275.38, nearby_book_depth=34859.60, quote_age_seconds=684.50
- 701493: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:130000, action=selective_market, reasons=thin_liquidity
  net_edge_bps=2.61, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8824, profit_quality_score=0.5710
  top_book_depth=1234.52, nearby_book_depth=5817.91, quote_age_seconds=684.80
- 701494: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:120000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-63.64, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9045, profit_quality_score=0.4151
  top_book_depth=308.90, nearby_book_depth=3674.87, quote_age_seconds=706.61
- 701495: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:110000, action=watch_market, reasons=stale_quote, negative_edge, wide_spread, thin_liquidity
  net_edge_bps=-169.97, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9367, profit_quality_score=0.3382
  top_book_depth=720.25, nearby_book_depth=2171.22, quote_age_seconds=4049.42
- 701496: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:100000, action=watch_market, reasons=negative_edge
  net_edge_bps=-54.12, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9735, profit_quality_score=0.4289
  top_book_depth=48.87, nearby_book_depth=3244.52, quote_age_seconds=683.65
- 701501: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:55000, action=watch_market, reasons=contract_price_too_low, thin_liquidity
  net_edge_bps=1638.09, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9389, profit_quality_score=0.8220
  top_book_depth=495.67, nearby_book_depth=3830.67, quote_age_seconds=720.94
- 701502: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:45000, action=selective_market, reasons=wide_spread
  net_edge_bps=979.67, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9996, profit_quality_score=0.7708
  top_book_depth=409.64, nearby_book_depth=1129.33, quote_age_seconds=395.97
- 701503: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:35000, action=tradable_market, reasons=none
  net_edge_bps=420.67, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9518, profit_quality_score=0.8570
  top_book_depth=1631.36, nearby_book_depth=3117.74, quote_age_seconds=687.91
- 701504: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:25000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=72.40, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8824, profit_quality_score=0.7371
  top_book_depth=192.74, nearby_book_depth=10579.24, quote_age_seconds=682.55
