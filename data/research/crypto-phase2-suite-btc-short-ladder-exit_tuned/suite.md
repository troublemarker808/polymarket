# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:37:31.193453+00:00
- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-ladder-exit_tuned\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-ladder-exit_tuned\replay-unfiltered
- signals_generated: 1
- submitted_orders: 1
- submitted_notional: 5.000000
- events_recorded: 22
- today_pnl: -0.110000
- total_equity: 24.890000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1026.8929
- average_adverse_fill_bps: 121.2121
- expected_edge_capture_bps: 905.6807
- edge_capture_ratio: 0.8820
- average_trade_expected_edge_bps: 1026.8929
- average_trade_execution_drag_bps: 121.2121
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 3346.7983
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1171.3794
- average_barrier_surface_disagreement_bps: 3346.7983
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 5.000000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: stable

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-ladder-exit_tuned\replay-filtered
- signals_generated: 1
- submitted_orders: 1
- submitted_notional: 5.000000
- events_recorded: 22
- today_pnl: -0.110000
- total_equity: 24.890000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1026.8929
- average_adverse_fill_bps: 121.2121
- expected_edge_capture_bps: 905.6807
- edge_capture_ratio: 0.8820
- average_trade_expected_edge_bps: 1026.8929
- average_trade_execution_drag_bps: 121.2121
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 3346.7983
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1171.3794
- average_barrier_surface_disagreement_bps: 3346.7983
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 5.000000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: stable

## Delta

- signals_delta: 0
- orders_delta: 0
- pnl_delta: 0.000000

## Final Scorecard

- recommended_action: review
- readiness_score: 0.9000
- execution_quality: stable
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: execution
- selection_quality_score: 1.0000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.7300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- selection_loss: 0.0000
- pricing_loss: 0.1200
- execution_loss: 0.2700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.4700
- tuning_priority: execution
