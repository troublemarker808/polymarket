# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:37:35.179131+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v65d-prem350-rep140-baseline475\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v65d-prem350-rep140-baseline475\replay-unfiltered
- signals_generated: 20
- submitted_orders: 19
- submitted_notional: 75.945205
- events_recorded: 512
- today_pnl: -0.070685
- total_equity: 24.929315
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.7895
- stop_out_rate: 1.0000
- average_trade_pnl: -0.070685
- average_signal_edge_bps: 504.0763
- average_adverse_fill_bps: 88.9655
- expected_edge_capture_bps: 415.1107
- edge_capture_ratio: 0.8235
- average_trade_expected_edge_bps: 504.0763
- average_trade_execution_drag_bps: 88.9655
- average_trade_realized_pnl_bps: -89.7629
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.070685
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.070685
- average_submitted_notional: 3.997116
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.000931
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v65d-prem350-rep140-baseline475\replay-filtered
- signals_generated: 11
- submitted_orders: 10
- submitted_notional: 39.945205
- events_recorded: 496
- today_pnl: -0.070685
- total_equity: 24.929315
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.8000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.070685
- average_signal_edge_bps: 504.0763
- average_adverse_fill_bps: 88.9655
- expected_edge_capture_bps: 415.1107
- edge_capture_ratio: 0.8235
- average_trade_expected_edge_bps: 504.0763
- average_trade_execution_drag_bps: 88.9655
- average_trade_realized_pnl_bps: -89.7629
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.070685
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.070685
- average_submitted_notional: 3.994521
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.001770
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -9
- orders_delta: -9
- pnl_delta: 0.000000

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
