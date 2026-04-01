# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:37:03.144505+00:00
- snapshot_path: data\research\family-export-phase2-v35-btc-reach\snapshots.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-exp-base\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-exp-base\replay-unfiltered
- signals_generated: 5
- submitted_orders: 4
- submitted_notional: 20.000000
- events_recorded: 186
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
- average_barrier_observed_gap_bps: 539.6441
- average_surface_observed_gap_bps: 208.4375
- average_fusion_observed_gap_bps: 231.6627
- average_barrier_surface_disagreement_bps: 518.1088
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
- execution_feedback_bias: more_aggressive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-exp-base\replay-filtered
- signals_generated: 2
- submitted_orders: 2
- submitted_notional: 9.848485
- events_recorded: 181
- today_pnl: -0.171212
- total_equity: 24.828788
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.171212
- average_signal_edge_bps: 338.9243
- average_adverse_fill_bps: 173.8462
- expected_edge_capture_bps: 165.0781
- edge_capture_ratio: 0.4871
- average_trade_expected_edge_bps: 338.9243
- average_trade_execution_drag_bps: 173.8462
- average_trade_realized_pnl_bps: -176.9163
- average_barrier_observed_gap_bps: 539.6441
- average_surface_observed_gap_bps: 208.4375
- average_fusion_observed_gap_bps: 231.6627
- average_barrier_surface_disagreement_bps: 518.1088
- closed_trade_net_pnl: -0.171212
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.171212
- average_submitted_notional: 4.924242
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.017385
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -3
- orders_delta: -2
- pnl_delta: -0.171212

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: exit
- selection_quality_score: 0.9000
- pricing_quality_score: 0.3300
- execution_quality_score: 0.6300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.6500
- selection_loss: 0.1000
- pricing_loss: 0.6700
- execution_loss: 0.3700
- exit_loss: 0.9100
- sizing_loss: 0.3500
- total_profit_loss: 2.4000
- tuning_priority: exit
