# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:46:26.744240+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v34.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v73-longv34-profit\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v73-longv34-profit\replay-unfiltered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 40.000000
- events_recorded: 211
- today_pnl: -0.546040
- total_equity: 24.453960
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1140.2528
- average_adverse_fill_bps: 200.1255
- expected_edge_capture_bps: 940.1273
- edge_capture_ratio: 0.8245
- average_trade_expected_edge_bps: 935.8508
- average_trade_execution_drag_bps: 183.9204
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1860.7199
- average_surface_observed_gap_bps: 114.8333
- average_fusion_observed_gap_bps: 673.6853
- average_barrier_surface_disagreement_bps: 1847.5689
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
- execution_feedback_bias: more_aggressive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v73-longv34-profit\replay-filtered
- signals_generated: 5
- submitted_orders: 5
- submitted_notional: 20.000000
- events_recorded: 202
- today_pnl: -0.378040
- total_equity: 24.621960
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 749.9871
- average_adverse_fill_bps: 181.0553
- expected_edge_capture_bps: 568.9318
- edge_capture_ratio: 0.7586
- average_trade_expected_edge_bps: 701.5148
- average_trade_execution_drag_bps: 170.3973
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1860.7199
- average_surface_observed_gap_bps: 114.8333
- average_fusion_observed_gap_bps: 673.6853
- average_barrier_surface_disagreement_bps: 1847.5689
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

## Delta

- signals_delta: -5
- orders_delta: -5
- pnl_delta: 0.168000

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: execution
- selection_quality_score: 0.7000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.6300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- selection_loss: 0.3000
- pricing_loss: 0.1200
- execution_loss: 0.3700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.8700
- tuning_priority: execution
