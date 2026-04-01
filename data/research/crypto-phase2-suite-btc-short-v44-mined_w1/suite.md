# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:42:01.923465+00:00
- snapshot_path: data\research\mined-windows-phase2-v35-btc-reach\window-01.snapshots.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v44-mined_w1\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v44-mined_w1\replay-unfiltered
- signals_generated: 4
- submitted_orders: 2
- submitted_notional: 10.000000
- events_recorded: 24
- today_pnl: 0.000000
- total_equity: 25.000000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 0.0000
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 0.0000
- edge_capture_ratio: 0.0000
- average_trade_expected_edge_bps: 0.0000
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 462.8055
- average_surface_observed_gap_bps: 260.0000
- average_fusion_observed_gap_bps: 200.9819
- average_barrier_surface_disagreement_bps: 543.7173
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

- output_dir: data\research\crypto-phase2-suite-btc-short-v44-mined_w1\replay-filtered
- signals_generated: 2
- submitted_orders: 2
- submitted_notional: 9.926470
- events_recorded: 25
- today_pnl: -0.093382
- total_equity: 24.906618
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.093382
- average_signal_edge_bps: 644.2022
- average_adverse_fill_bps: 94.0741
- expected_edge_capture_bps: 550.1281
- edge_capture_ratio: 0.8540
- average_trade_expected_edge_bps: 644.2022
- average_trade_execution_drag_bps: 94.0741
- average_trade_realized_pnl_bps: -94.9661
- average_barrier_observed_gap_bps: 462.8055
- average_surface_observed_gap_bps: 260.0000
- average_fusion_observed_gap_bps: 200.9819
- average_barrier_surface_disagreement_bps: 543.7173
- closed_trade_net_pnl: -0.093382
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.093382
- average_submitted_notional: 4.963235
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.009407
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -2
- orders_delta: 0
- pnl_delta: -0.093382

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8000
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: exit
- selection_quality_score: 1.0000
- pricing_quality_score: 0.4300
- execution_quality_score: 0.6300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.7200
- selection_loss: 0.0000
- pricing_loss: 0.5700
- execution_loss: 0.3700
- exit_loss: 0.9100
- sizing_loss: 0.2800
- total_profit_loss: 2.1300
- tuning_priority: exit
