# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:46:07.447030+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v52_edge140_taker400_size4\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v52_edge140_taker400_size4\replay-unfiltered
- signals_generated: 18
- submitted_orders: 18
- submitted_notional: 71.508725
- events_recorded: 509
- today_pnl: -0.675324
- total_equity: 24.324676
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.179431
- average_signal_edge_bps: 1145.8840
- average_adverse_fill_bps: 222.5464
- expected_edge_capture_bps: 923.3376
- edge_capture_ratio: 0.8058
- average_trade_expected_edge_bps: 1078.9229
- average_trade_execution_drag_bps: 222.8096
- average_trade_realized_pnl_bps: -201.3307
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.538292
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.179431
- average_submitted_notional: 3.972707
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.007528
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v52_edge140_taker400_size4\replay-filtered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 39.662572
- events_recorded: 495
- today_pnl: -0.505786
- total_equity: 24.494214
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.184377
- average_signal_edge_bps: 827.9444
- average_adverse_fill_bps: 226.3506
- expected_edge_capture_bps: 601.5939
- edge_capture_ratio: 0.7266
- average_trade_expected_edge_bps: 835.9066
- average_trade_execution_drag_bps: 225.5020
- average_trade_realized_pnl_bps: -193.5263
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.368753
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.184377
- average_submitted_notional: 3.966257
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.009297
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -8
- orders_delta: -8
- pnl_delta: 0.169538

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
- exit_quality_score: 0.0900
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.5700
- exit_loss: 0.9100
- sizing_loss: 0.2300
- total_profit_loss: 2.4300
- tuning_priority: exit
