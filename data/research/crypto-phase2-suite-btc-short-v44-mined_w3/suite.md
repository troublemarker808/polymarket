# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:42:02.045942+00:00
- snapshot_path: data\research\mined-windows-phase2-v35-btc-reach\window-03.snapshots.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v44-mined_w3\selection
- blocked_series_keys: what-price-will-bitcoin-hit-before-2027

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v44-mined_w3\replay-unfiltered
- signals_generated: 1
- submitted_orders: 1
- submitted_notional: 5.000000
- events_recorded: 17
- today_pnl: -0.204805
- total_equity: 24.795195
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 690.9884
- average_adverse_fill_bps: 219.0728
- expected_edge_capture_bps: 471.9155
- edge_capture_ratio: 0.6830
- average_trade_expected_edge_bps: 690.9884
- average_trade_execution_drag_bps: 219.0728
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 501.7566
- average_surface_observed_gap_bps: 1300.0000
- average_fusion_observed_gap_bps: 830.3736
- average_barrier_surface_disagreement_bps: 1341.7898
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

- output_dir: data\research\crypto-phase2-suite-btc-short-v44-mined_w3\replay-filtered
- signals_generated: 0
- submitted_orders: 0
- submitted_notional: 0.000000
- events_recorded: 20
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
- average_barrier_observed_gap_bps: 501.7566
- average_surface_observed_gap_bps: 1300.0000
- average_fusion_observed_gap_bps: 830.3736
- average_barrier_surface_disagreement_bps: 1341.7898
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 0.000000
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

- signals_delta: -1
- orders_delta: -1
- pnl_delta: 0.204805

## Final Scorecard

- recommended_action: review
- readiness_score: 0.4500
- execution_quality: fragile
- evidence_status: thin
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, edge_capture_ratio_below_floor, pnl_per_notional_not_positive
- profit_focus: selection
- selection_quality_score: 0.1500
- pricing_quality_score: 0.3100
- execution_quality_score: 0.8000
- exit_quality_score: 1.0000
- sizing_quality_score: 1.0000
- selection_loss: 0.8500
- pricing_loss: 0.6900
- execution_loss: 0.2000
- exit_loss: 0.0000
- sizing_loss: 0.0000
- total_profit_loss: 1.7400
- tuning_priority: selection
