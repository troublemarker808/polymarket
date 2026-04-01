# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:00:29.478638+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v57-grid-d00_s000_c000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v57-grid-d00_s000_c000\replay-unfiltered
- signals_generated: 16
- submitted_orders: 16
- submitted_notional: 63.878788
- events_recorded: 485
- today_pnl: -0.722859
- total_equity: 24.277141
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.136970
- average_signal_edge_bps: 851.2242
- average_adverse_fill_bps: 199.5709
- expected_edge_capture_bps: 651.6533
- edge_capture_ratio: 0.7655
- average_trade_expected_edge_bps: 768.8441
- average_trade_execution_drag_bps: 189.3103
- average_trade_realized_pnl_bps: -58.9721
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.136970
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.992424
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.002144
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v57-grid-d00_s000_c000\replay-filtered
- signals_generated: 8
- submitted_orders: 8
- submitted_notional: 31.878788
- events_recorded: 475
- today_pnl: -0.561013
- total_equity: 24.438987
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3750
- stop_out_rate: 1.0000
- average_trade_pnl: -0.136970
- average_signal_edge_bps: 604.7461
- average_adverse_fill_bps: 194.0373
- expected_edge_capture_bps: 410.7089
- edge_capture_ratio: 0.6791
- average_trade_expected_edge_bps: 601.8203
- average_trade_execution_drag_bps: 183.8783
- average_trade_realized_pnl_bps: -70.7665
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.136970
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.984848
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.004297
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -8
- orders_delta: -8
- pnl_delta: 0.161846

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
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9100
- sizing_loss: 0.2300
- total_profit_loss: 2.3300
- tuning_priority: exit
