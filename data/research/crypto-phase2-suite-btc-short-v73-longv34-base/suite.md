# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:46:25.293779+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v34.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v73-longv34-base\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v73-longv34-base\replay-unfiltered
- signals_generated: 11
- submitted_orders: 11
- submitted_notional: 43.783784
- events_recorded: 214
- today_pnl: -0.777823
- total_equity: 24.222177
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4545
- stop_out_rate: 1.0000
- average_trade_pnl: -0.231784
- average_signal_edge_bps: 1249.7855
- average_adverse_fill_bps: 236.4893
- expected_edge_capture_bps: 1013.2963
- edge_capture_ratio: 0.8108
- average_trade_expected_edge_bps: 1102.0322
- average_trade_execution_drag_bps: 221.8729
- average_trade_realized_pnl_bps: -102.2998
- average_barrier_observed_gap_bps: 1860.7199
- average_surface_observed_gap_bps: 114.8333
- average_fusion_observed_gap_bps: 673.6853
- average_barrier_surface_disagreement_bps: 1847.5689
- closed_trade_net_pnl: -0.231784
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.231784
- average_submitted_notional: 3.980344
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.005294
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v73-longv34-base\replay-filtered
- signals_generated: 6
- submitted_orders: 6
- submitted_notional: 23.783784
- events_recorded: 205
- today_pnl: -0.609823
- total_equity: 24.390177
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.1667
- stop_out_rate: 1.0000
- average_trade_pnl: -0.231784
- average_signal_edge_bps: 1101.7903
- average_adverse_fill_bps: 241.0536
- expected_edge_capture_bps: 860.7367
- edge_capture_ratio: 0.7812
- average_trade_expected_edge_bps: 994.6669
- average_trade_execution_drag_bps: 221.3495
- average_trade_realized_pnl_bps: -122.7598
- average_barrier_observed_gap_bps: 1860.7199
- average_surface_observed_gap_bps: 114.8333
- average_fusion_observed_gap_bps: 673.6853
- average_barrier_surface_disagreement_bps: 1847.5689
- closed_trade_net_pnl: -0.231784
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.231784
- average_submitted_notional: 3.963964
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.009745
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -5
- orders_delta: -5
- pnl_delta: 0.168000

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
- execution_quality_score: 0.6300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.3700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.3100
- tuning_priority: exit
