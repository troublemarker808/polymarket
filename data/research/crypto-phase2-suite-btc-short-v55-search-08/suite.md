# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:50:46.070729+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v55-search-08\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v55-search-08\replay-unfiltered
- signals_generated: 23
- submitted_orders: 22
- submitted_notional: 88.000000
- events_recorded: 517
- today_pnl: 0.000000
- total_equity: 25.000000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.8182
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 0.0000
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 0.0000
- edge_capture_ratio: 0.0000
- average_trade_expected_edge_bps: 0.0000
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
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

- output_dir: data\research\crypto-phase2-suite-btc-short-v55-search-08\replay-filtered
- signals_generated: 11
- submitted_orders: 11
- submitted_notional: 44.000000
- events_recorded: 497
- today_pnl: 0.000000
- total_equity: 25.000000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 1.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 0.0000
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 0.0000
- edge_capture_ratio: 0.0000
- average_trade_expected_edge_bps: 0.0000
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
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

## Delta

- signals_delta: -12
- orders_delta: -11
- pnl_delta: 0.000000

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, edge_capture_ratio_below_floor, pnl_per_notional_not_positive
- profit_focus: pricing
- selection_quality_score: 0.7000
- pricing_quality_score: 0.3100
- execution_quality_score: 0.8000
- exit_quality_score: 1.0000
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.6900
- execution_loss: 0.2000
- exit_loss: 0.0000
- sizing_loss: 0.2300
- total_profit_loss: 1.4200
- tuning_priority: pricing
