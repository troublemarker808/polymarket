# Crypto Market Selection Report

- generated_at: 2026-04-01T06:06:18.283273+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
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
- mean_net_edge_bps: 3237.93
- median_net_edge_bps: 3360.00
- mean_entry_cost_bps: 21.67
- min_liquidity_score: 0.8010
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.8469
- selection_rank: 1
- recommended_action: watch_only
- reasons: thin_liquidity, no_runtime_actionable_markets

### what-price-will-bitcoin-hit-before-2027

- underlying: BTC
- event_family: dip
- market_count: 27
- runtime_actionable_market_count: 5
- positive_net_edge_count: 16
- mean_net_edge_bps: 246.89
- median_net_edge_bps: 41.82
- mean_entry_cost_bps: 60.74
- min_liquidity_score: 0.8105
- signal_count: 0
- submitted_order_count: 0
- filled_order_count: 0
- expired_order_count: 0
- profit_quality_score: 0.6345
- selection_rank: 2
- recommended_action: selective_only
- reasons: thin_liquidity

## Market Rows

- 1057883: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:250000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=141.00, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8275, profit_quality_score=0.8747
  top_book_depth=1948.74, nearby_book_depth=4411.59, quote_age_seconds=156.90
- 1057916: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:15000, action=watch_market, reasons=stale_quote, thin_liquidity
  net_edge_bps=41.82, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8455, profit_quality_score=0.7231
  top_book_depth=13.89, nearby_book_depth=174.46, quote_age_seconds=189.74
- 1339767: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:50000, action=selective_market, reasons=wide_runtime_spread, wide_spread
  net_edge_bps=1277.01, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9808, profit_quality_score=0.7670
  top_book_depth=574.35, nearby_book_depth=1522.36, quote_age_seconds=109.36
- 1339768: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:40000, action=selective_market, reasons=wide_runtime_spread, wide_spread
  net_edge_bps=632.67, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9880, profit_quality_score=0.7684
  top_book_depth=557.82, nearby_book_depth=6703.36, quote_age_seconds=0.00
- 1339769: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:30000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=218.72, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9149, profit_quality_score=0.8171
  top_book_depth=2830.28, nearby_book_depth=4396.04, quote_age_seconds=145.65
- 1343219: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:20000, action=watch_market, reasons=negative_edge, wide_runtime_spread, wide_spread, thin_liquidity
  net_edge_bps=-130.89, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.8561, profit_quality_score=0.3221
  top_book_depth=3002.41, nearby_book_depth=6636.71, quote_age_seconds=168.00
- 1343220: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:10000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-6.20, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8307, profit_quality_score=0.5921
  top_book_depth=168.15, nearby_book_depth=1856.80, quote_age_seconds=160.60
- 1343228: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:5000, action=watch_market, reasons=stale_quote, negative_edge, thin_liquidity
  net_edge_bps=-13.14, entry_cost_bps=10.00, spread_bps=20.00, liquidity_score=0.8260, profit_quality_score=0.5643
  top_book_depth=212.31, nearby_book_depth=4837.77, quote_age_seconds=189.78
- 1345530: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:80000, action=selective_market, reasons=wide_spread
  net_edge_bps=1584.30, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9780, profit_quality_score=0.7664
  top_book_depth=15.00, nearby_book_depth=496.16, quote_age_seconds=116.88
- 1345531: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:90000, action=watch_market, reasons=negative_edge, wide_runtime_spread, wide_spread
  net_edge_bps=-109.98, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9984, profit_quality_score=0.3505
  top_book_depth=15.00, nearby_book_depth=2527.69, quote_age_seconds=117.04
- 1393068: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:500000, action=watch_market, reasons=negative_edge, contract_price_too_low, thin_liquidity
  net_edge_bps=-20.00, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8143, profit_quality_score=0.5520
  top_book_depth=3436.33, nearby_book_depth=17448.19, quote_age_seconds=156.44
- 1393070: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:1000000, action=watch_market, reasons=negative_edge, contract_price_too_low, thin_liquidity
  net_edge_bps=-8.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8105, profit_quality_score=0.5813
  top_book_depth=9476.79, nearby_book_depth=12235.08, quote_age_seconds=140.33
- 573654: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2026-04-01:150, action=watch_market, reasons=stale_quote, contract_price_too_low, thin_liquidity
  net_edge_bps=3434.75, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8010, profit_quality_score=0.8694
  top_book_depth=28973.09, nearby_book_depth=33454.80, quote_age_seconds=662.11
- 573655: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2026-07-01:150, action=watch_market, reasons=contract_price_too_low, thin_nearby_depth, thin_liquidity
  net_edge_bps=3360.00, entry_cost_bps=10.00, spread_bps=20.00, liquidity_score=0.8159, profit_quality_score=0.8640
  top_book_depth=17.90, nearby_book_depth=46.34, quote_age_seconds=101.74
- 573656: series_key=when-will-bitcoin-hit-150k, instrument_key=BTC:reach:2027-01-01:150, action=watch_market, reasons=thin_liquidity
  net_edge_bps=2919.03, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8650, profit_quality_score=0.8072
  top_book_depth=727.75, nearby_book_depth=9289.01, quote_age_seconds=0.00
- 701486: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:200000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=82.37, entry_cost_bps=5.00, spread_bps=10.00, liquidity_score=0.8313, profit_quality_score=0.8284
  top_book_depth=274.74, nearby_book_depth=2331.86, quote_age_seconds=160.60
- 701487: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:190000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=111.63, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8409, profit_quality_score=0.8023
  top_book_depth=4547.97, nearby_book_depth=17638.83, quote_age_seconds=13.65
- 701488: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:180000, action=watch_market, reasons=negative_edge, wide_spread, thin_liquidity
  net_edge_bps=-7.07, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.8440, profit_quality_score=0.4341
  top_book_depth=6855.83, nearby_book_depth=29269.82, quote_age_seconds=0.00
- 701489: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:170000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=41.00, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8470, profit_quality_score=0.6462
  top_book_depth=8049.14, nearby_book_depth=12860.80, quote_age_seconds=0.00
- 701490: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:160000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=192.84, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8591, profit_quality_score=0.8060
  top_book_depth=5251.74, nearby_book_depth=22956.95, quote_age_seconds=0.00
- 701491: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:150000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=14.01, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8591, profit_quality_score=0.5767
  top_book_depth=588.99, nearby_book_depth=18605.44, quote_age_seconds=0.00
- 701492: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:140000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=75.24, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8709, profit_quality_score=0.7423
  top_book_depth=243.61, nearby_book_depth=23944.12, quote_age_seconds=111.79
- 701493: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:130000, action=watch_market, reasons=negative_edge, thin_liquidity
  net_edge_bps=-45.31, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8824, profit_quality_score=0.4231
  top_book_depth=1194.14, nearby_book_depth=4716.64, quote_age_seconds=127.86
- 701494: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:120000, action=watch_market, reasons=negative_edge, wide_spread, thin_liquidity
  net_edge_bps=-128.96, entry_cost_bps=100.00, spread_bps=200.00, liquidity_score=0.9071, profit_quality_score=0.3323
  top_book_depth=3132.99, nearby_book_depth=4990.57, quote_age_seconds=110.02
- 701495: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:110000, action=watch_market, reasons=stale_quote, negative_edge, wide_runtime_spread, wide_spread, thin_liquidity
  net_edge_bps=-202.76, entry_cost_bps=150.00, spread_bps=300.00, liquidity_score=0.9389, profit_quality_score=0.2553
  top_book_depth=959.27, nearby_book_depth=2505.09, quote_age_seconds=228.06
- 701496: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:reach:2027-01-01:100000, action=watch_market, reasons=negative_edge
  net_edge_bps=-92.95, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9703, profit_quality_score=0.4282
  top_book_depth=86.66, nearby_book_depth=1413.54, quote_age_seconds=115.48
- 701501: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:55000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=1603.96, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9389, profit_quality_score=0.8220
  top_book_depth=98.00, nearby_book_depth=3525.82, quote_age_seconds=76.64
- 701502: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:45000, action=selective_market, reasons=wide_runtime_spread, wide_spread
  net_edge_bps=885.64, entry_cost_bps=200.00, spread_bps=400.00, liquidity_score=0.9975, profit_quality_score=0.6870
  top_book_depth=649.86, nearby_book_depth=4521.74, quote_age_seconds=149.08
- 701503: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:35000, action=tradable_market, reasons=none
  net_edge_bps=421.58, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.9518, profit_quality_score=0.8570
  top_book_depth=10.00, nearby_book_depth=1521.30, quote_age_seconds=68.27
- 701504: series_key=what-price-will-bitcoin-hit-before-2027, instrument_key=BTC:dip:2027-01-01:25000, action=watch_market, reasons=thin_liquidity
  net_edge_bps=108.18, entry_cost_bps=50.00, spread_bps=100.00, liquidity_score=0.8881, profit_quality_score=0.8118
  top_book_depth=4013.40, nearby_book_depth=24456.04, quote_age_seconds=132.63
