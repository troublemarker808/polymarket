# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:10:18.244055+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.overnight.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v58-longtail-overnight\selection
- blocked_series_keys: what-price-will-bitcoin-hit-before-2027

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v58-longtail-overnight\replay-unfiltered
- signals_generated: 53
- submitted_orders: 45
- submitted_notional: 180.080000
- events_recorded: 3541
- today_pnl: 0.160000
- total_equity: 25.160000
- status: completed
- maker_fill_rate: 0.0667
- taker_fill_rate: 0.0000
- expiration_rate: 0.9556
- stop_out_rate: 0.0000
- average_trade_pnl: 0.160000
- average_signal_edge_bps: 355.2535
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 355.2535
- edge_capture_ratio: 1.0000
- average_trade_expected_edge_bps: 322.0343
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 130.7190
- average_barrier_observed_gap_bps: 2161.3520
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 756.4732
- average_barrier_surface_disagreement_bps: 2161.3520
- closed_trade_net_pnl: 0.160000
- closed_trade_count: 1
- winning_trade_rate: 1.0000
- average_win_trade_pnl: 0.160000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 4.001778
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000888
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_aggressive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v58-longtail-overnight\replay-filtered
- signals_generated: 4
- submitted_orders: 4
- submitted_notional: 16.000000
- events_recorded: 6286
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
- average_barrier_observed_gap_bps: 2161.3520
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 756.4732
- average_barrier_surface_disagreement_bps: 2161.3520
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

- signals_delta: -49
- orders_delta: -41
- pnl_delta: -0.160000

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
- pricing_quality_score: 0.1600
- execution_quality_score: 0.8000
- exit_quality_score: 1.0000
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.8400
- execution_loss: 0.2000
- exit_loss: 0.0000
- sizing_loss: 0.2300
- total_profit_loss: 1.5700
- tuning_priority: pricing
