# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:41:34.298745+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v43-longv35-fastclose\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v43-longv35-fastclose\replay-unfiltered
- signals_generated: 22
- submitted_orders: 9
- submitted_notional: 44.537422
- events_recorded: 506
- today_pnl: -0.751436
- total_equity: 24.248564
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3333
- stop_out_rate: 1.0000
- average_trade_pnl: -0.250826
- average_signal_edge_bps: 1388.3186
- average_adverse_fill_bps: 229.5335
- expected_edge_capture_bps: 1158.7852
- edge_capture_ratio: 0.8347
- average_trade_expected_edge_bps: 1216.0315
- average_trade_execution_drag_bps: 216.8464
- average_trade_realized_pnl_bps: -175.9137
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.501653
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.250826
- average_submitted_notional: 4.948602
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.011264
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v43-longv35-fastclose\replay-filtered
- signals_generated: 9
- submitted_orders: 6
- submitted_notional: 29.729730
- events_recorded: 489
- today_pnl: -0.539513
- total_equity: 24.460487
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3333
- stop_out_rate: 1.0000
- average_trade_pnl: -0.289730
- average_signal_edge_bps: 1114.9071
- average_adverse_fill_bps: 241.8723
- expected_edge_capture_bps: 873.0347
- edge_capture_ratio: 0.7831
- average_trade_expected_edge_bps: 980.8154
- average_trade_execution_drag_bps: 217.2303
- average_trade_realized_pnl_bps: -153.4498
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.289730
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.289730
- average_submitted_notional: 4.954955
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.009745
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -13
- orders_delta: -3
- pnl_delta: 0.211923

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
- execution_quality_score: 0.5300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.7200
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9100
- sizing_loss: 0.2800
- total_profit_loss: 2.3800
- tuning_priority: exit
