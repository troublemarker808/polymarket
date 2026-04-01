# Crypto Market Selection Report

- generated_at: 2026-04-01T05:46:25.691191+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v34.20260328.jsonl
- barrier_steepness: 1.65
- fusion_barrier_weight: 0.35
- fusion_surface_weight: 0.65

## Series Reports

### when-will-bitcoin-hit-150k

- underlying: BTC
- event_family: reach
- market_count: 3
- runtime_actionable_market_count: 0
- positive_net_edge_count: 3
- mean_net_edge_bps: 3189.33
- median_net_edge_bps: 3214.25
- mean_entry_cost_bps: 43.33
- min_liquidity_score: 0.8010
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.8108
- selection_rank: 1
- recommended_action: watch_only
- reasons: thin_liquidity, no_runtime_actionable_markets

### what-price-will-bitcoin-hit-before-2027

- underlying: BTC
- event_family: dip
- market_count: 27
- runtime_actionable_market_count: 5
- positive_net_edge_count: 16
- mean_net_edge_bps: 261.21
- median_net_edge_bps: 41.75
- mean_entry_cost_bps: 53.33
- min_liquidity_score: 0.8105
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.6465
- selection_rank: 2
- recommended_action: selective_only
- reasons: thin_liquidity

## Market Rows

- 1057883: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:250000, action=watch_market, reasons=thin_top_book, thin_liquidity
  net_edge_bps=134.50, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8275, profit_quality_score=0.8747
  top_book_depth=11.02, nearby_book_depth=2754.97, quote_age_seconds=0.00
- 1057916: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:15000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=41.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8458, profit_quality_score=0.7230
  top_book_depth=42.80, nearby_book_depth=503.39, quote_age_seconds=0.00
- 1339767: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:50000, action=selective_market, reasons=wide_runtime_spread, wide_spread
  net_edge_bps=1276.90, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9808, profit_quality_score=0.7670
  top_book_depth=647.44, nearby_book_depth=1605.45, quote_age_seconds=18.86
- 1339768: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:40000, action=selective_market, reasons=wide_runtime_spread, wide_spread
  net_edge_bps=632.56, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9880, profit_quality_score=0.7684
  top_book_depth=557.82, nearby_book_depth=6703.36, quote_age_seconds=0.00
- 1339769: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:30000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=218.62, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9149, profit_quality_score=0.8171
  top_book_depth=1643.64, nearby_book_depth=3199.40, quote_age_seconds=0.00
- 1343219: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:20000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-48.48, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8531, profit_quality_score=0.4088
  top_book_depth=206.48, nearby_book_depth=3904.73, quote_age_seconds=0.00
- 1343220: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:10000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-6.26, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8307, profit_quality_score=0.5919
  top_book_depth=184.52, nearby_book_depth=2072.22, quote_age_seconds=0.00
- 1343228: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:5000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-20.19, entry_cost_bps=10.00, spread_bps=20.00, liquidity_score=0.8247, profit_quality_score=0.5453
  top_book_depth=943.01, nearby_book_depth=2480.00, quote_age_seconds=0.00
- 1345530: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:80000, action=selective_market, reasons=wide_spread, thin_top_book
  net_edge_bps=1684.29, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9750, profit_quality_score=0.7658
  top_book_depth=6.45, nearby_book_depth=2913.81, quote_age_seconds=27.69
- 1345531: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:90000, action=watch_market, reasons=negative_edge, wide_runtime_spread, wide_spread
  net_edge_bps=-158.79, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9984, profit_quality_score=0.3505
  top_book_depth=30.00, nearby_book_depth=2647.68, quote_age_seconds=0.00
- 1393068: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:500000, action=watch_market, reasons=negative_edge, contract_price_too_low, thin_liquidity
  net_edge_bps=-20.00, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8143, profit_quality_score=0.5520
  top_book_depth=4055.46, nearby_book_depth=17866.82, quote_age_seconds=0.00
- 1393070: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:1000000, action=watch_market, reasons=negative_edge, contract_price_too_low, thin_liquidity
  net_edge_bps=-8.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8105, profit_quality_score=0.5813
  top_book_depth=9923.12, nearby_book_depth=12706.41, quote_age_seconds=0.00
- 573654: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2026-04-01:150, action=watch_market, reasons=stale_quote, contract_price_too_low, thin_liquidity
  net_edge_bps=3434.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8010, profit_quality_score=0.8694
  top_book_depth=28973.09, nearby_book_depth=33454.80, quote_age_seconds=670.37
- 573655: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2026-07-01:150, action=watch_market, reasons=contract_price_too_low, thin_top_book, thin_nearby_depth, thin_liquidity
  net_edge_bps=3214.25, entry_cost_bps=75.00, spread_bps=150.00, liquidity_score=0.8159, profit_quality_score=0.7557
  top_book_depth=10.00, nearby_book_depth=30.00, quote_age_seconds=0.00
- 573656: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2027-01-01:150, action=watch_market, reasons=thin_liquidity
  net_edge_bps=2918.98, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8650, profit_quality_score=0.8072
  top_book_depth=727.75, nearby_book_depth=9230.01, quote_age_seconds=0.00
- 701486: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:200000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=102.37, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8325, profit_quality_score=0.8757
  top_book_depth=499.09, nearby_book_depth=1619.35, quote_age_seconds=0.00
- 701487: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:190000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=105.13, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8409, profit_quality_score=0.8023
  top_book_depth=4549.04, nearby_book_depth=17639.90, quote_age_seconds=0.00
- 701488: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:180000, action=watch_market, reasons=negative_edge, wide_spread, thin_liquidity
  net_edge_bps=-7.10, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.8440, profit_quality_score=0.4340
  top_book_depth=6856.90, nearby_book_depth=29269.82, quote_age_seconds=0.00
- 701489: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:170000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=40.97, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8470, profit_quality_score=0.6461
  top_book_depth=8050.22, nearby_book_depth=12778.88, quote_age_seconds=0.00
- 701490: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:160000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=192.79, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8591, profit_quality_score=0.8060
  top_book_depth=5252.84, nearby_book_depth=22958.05, quote_age_seconds=0.00
- 701491: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:150000, action=watch_market, reasons=thin_top_book, thin_liquidity
  net_edge_bps=13.95, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8591, profit_quality_score=0.5765
  top_book_depth=10.00, nearby_book_depth=18586.54, quote_age_seconds=0.00
- 701492: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:140000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=75.16, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8709, profit_quality_score=0.7421
  top_book_depth=244.74, nearby_book_depth=23846.25, quote_age_seconds=26.43
- 701493: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:130000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-29.16, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8824, profit_quality_score=0.4662
  top_book_depth=1194.14, nearby_book_depth=4711.64, quote_age_seconds=0.00
- 701494: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:120000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-62.82, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9045, profit_quality_score=0.4151
  top_book_depth=408.90, nearby_book_depth=3840.80, quote_age_seconds=44.83
- 701495: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:110000, action=watch_market, reasons=negative_edge, wide_runtime_spread, wide_spread, thin_liquidity
  net_edge_bps=-152.88, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9367, profit_quality_score=0.3382
  top_book_depth=959.27, nearby_book_depth=2513.79, quote_age_seconds=0.00
- 701496: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:100000, action=watch_market, reasons=negative_edge, wide_runtime_spread, wide_spread
  net_edge_bps=-170.90, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9719, profit_quality_score=0.3452
  top_book_depth=59.38, nearby_book_depth=2144.23, quote_age_seconds=8.71
- 701501: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:55000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=1638.86, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9389, profit_quality_score=0.8220
  top_book_depth=1884.57, nearby_book_depth=5295.42, quote_age_seconds=0.00
- 701502: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:45000, action=selective_market, reasons=wide_runtime_spread, wide_spread
  net_edge_bps=1050.52, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9984, profit_quality_score=0.7705
  top_book_depth=11.36, nearby_book_depth=1550.97, quote_age_seconds=0.00
- 701503: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:35000, action=tradable_market, reasons=none
  net_edge_bps=421.47, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9518, profit_quality_score=0.8570
  top_book_depth=10.00, nearby_book_depth=842.74, quote_age_seconds=0.00
- 701504: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:25000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=108.09, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8881, profit_quality_score=0.8118
  top_book_depth=5176.20, nearby_book_depth=24569.91, quote_age_seconds=0.00
