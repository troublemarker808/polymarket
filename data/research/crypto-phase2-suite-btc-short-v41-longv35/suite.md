# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:40:36.986140+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v41-longv35\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v41-longv35\replay-unfiltered
- signals_generated: 2
- submitted_orders: 2
- submitted_notional: 10.000000
- events_recorded: 54
- today_pnl: -0.280270
- total_equity: 24.719730
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1277.0072
- average_adverse_fill_bps: 298.3333
- expected_edge_capture_bps: 978.6739
- edge_capture_ratio: 0.7664
- average_trade_expected_edge_bps: 1277.0072
- average_trade_execution_drag_bps: 298.3333
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1022.8931
- average_surface_observed_gap_bps: 123.5185
- average_fusion_observed_gap_bps: 383.3681
- average_barrier_surface_disagreement_bps: 1010.1314
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

- output_dir: data\research\crypto-phase2-suite-btc-short-v41-longv35\replay-filtered
- signals_generated: 1
- submitted_orders: 1
- submitted_notional: 5.000000
- events_recorded: 52
- today_pnl: -0.161515
- total_equity: 24.838485
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 605.7994
- average_adverse_fill_bps: 174.1538
- expected_edge_capture_bps: 431.6456
- edge_capture_ratio: 0.7125
- average_trade_expected_edge_bps: 605.7994
- average_trade_execution_drag_bps: 174.1538
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1022.8931
- average_surface_observed_gap_bps: 123.5185
- average_fusion_observed_gap_bps: 383.3681
- average_barrier_surface_disagreement_bps: 1010.1314
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

- signals_delta: -1
- orders_delta: -1
- pnl_delta: 0.118755

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: selection
- selection_quality_score: 0.7000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.7300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- selection_loss: 0.3000
- pricing_loss: 0.1200
- execution_loss: 0.2700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.7700
- tuning_priority: selection
