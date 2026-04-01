# Crypto Phase 2 Suite

- generated_at: 2026-04-01T16:34:10.129386+00:00
- snapshot_path: data\runtime\20260401-015839-btc-short-repricing-fallback-snapshots.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-profile-v118a-btc-short-20260402-unit4-defaultsafe\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-profile-v118a-btc-short-20260402-unit4-defaultsafe\replay-unfiltered
- signals_generated: 3
- submitted_orders: 3
- submitted_notional: 11.942857
- events_recorded: 8
- today_pnl: -0.238394
- total_equity: 24.761606
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1634.2838
- average_adverse_fill_bps: 160.0118
- expected_edge_capture_bps: 1474.2720
- edge_capture_ratio: 0.9021
- average_trade_expected_edge_bps: 1438.8631
- average_trade_execution_drag_bps: 161.2388
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 4582.4692
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1603.8642
- average_barrier_surface_disagreement_bps: 4582.4692
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 3.980952
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: stable
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

### filtered

- output_dir: data\research\crypto-phase2-suite-profile-v118a-btc-short-20260402-unit4-defaultsafe\replay-filtered
- signals_generated: 2
- submitted_orders: 2
- submitted_notional: 8.000000
- events_recorded: 11
- today_pnl: -0.116108
- total_equity: 24.883892
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 2072.5000
- average_adverse_fill_bps: 157.2603
- expected_edge_capture_bps: 1915.2397
- edge_capture_ratio: 0.9241
- average_trade_expected_edge_bps: 2072.5000
- average_trade_execution_drag_bps: 157.2603
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 4582.4692
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1603.8642
- average_barrier_surface_disagreement_bps: 4582.4692
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 4.000000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: stable
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Delta

- signals_delta: -1
- orders_delta: -1
- pnl_delta: 0.122286

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: execution
- selection_quality_score: 0.9000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.7300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- selection_loss: 0.1000
- pricing_loss: 0.1200
- execution_loss: 0.2700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.5700
- tuning_priority: execution
