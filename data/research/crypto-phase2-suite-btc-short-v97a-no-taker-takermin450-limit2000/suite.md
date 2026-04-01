# Crypto Phase 2 Suite

- generated_at: 2026-04-01T07:21:57.830474+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v97a-no-taker-takermin450-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v97a-no-taker-takermin450-limit2000\replay-unfiltered
- signals_generated: 37
- submitted_orders: 28
- submitted_notional: 111.566445
- events_recorded: 2059
- today_pnl: -0.480687
- total_equity: 24.519313
- status: completed
- maker_fill_rate: 0.0357
- taker_fill_rate: 0.0000
- expiration_rate: 0.7143
- stop_out_rate: 1.0000
- average_trade_pnl: -0.160229
- average_signal_edge_bps: 1439.5419
- average_adverse_fill_bps: 218.0259
- expected_edge_capture_bps: 1221.5160
- edge_capture_ratio: 0.8485
- average_trade_expected_edge_bps: 1526.1362
- average_trade_execution_drag_bps: 175.3875
- average_trade_realized_pnl_bps: -179.6428
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.480687
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.160229
- average_submitted_notional: 3.984516
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.004309
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v97a-no-taker-takermin450-limit2000\replay-filtered
- signals_generated: 11
- submitted_orders: 11
- submitted_notional: 43.936508
- events_recorded: 2021
- today_pnl: -0.079365
- total_equity: 24.920635
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.7273
- stop_out_rate: 1.0000
- average_trade_pnl: -0.079365
- average_signal_edge_bps: 761.2925
- average_adverse_fill_bps: 100.0000
- expected_edge_capture_bps: 661.2925
- edge_capture_ratio: 0.8686
- average_trade_expected_edge_bps: 761.2925
- average_trade_execution_drag_bps: 100.0000
- average_trade_realized_pnl_bps: -101.0085
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.079365
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.079365
- average_submitted_notional: 3.994228
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.001806
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -26
- orders_delta: -17
- pnl_delta: 0.401322

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: exit
- selection_quality_score: 0.7000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.4300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.5700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.5100
- tuning_priority: exit
