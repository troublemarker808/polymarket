# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:45:46.119277+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v72d-profit-tsioc-off-scale85af85-baseline475\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v72d-profit-tsioc-off-scale85af85-baseline475\replay-unfiltered
- signals_generated: 25
- submitted_orders: 20
- submitted_notional: 78.548018
- events_recorded: 511
- today_pnl: -0.505181
- total_equity: 24.494819
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5500
- stop_out_rate: 1.0000
- average_trade_pnl: -0.140539
- average_signal_edge_bps: 965.6847
- average_adverse_fill_bps: 186.3124
- expected_edge_capture_bps: 779.3722
- edge_capture_ratio: 0.8071
- average_trade_expected_edge_bps: 850.8369
- average_trade_execution_drag_bps: 175.5358
- average_trade_realized_pnl_bps: -132.5860
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.281077
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.140539
- average_submitted_notional: 3.927401
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.003578
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v72d-profit-tsioc-off-scale85af85-baseline475\replay-filtered
- signals_generated: 11
- submitted_orders: 9
- submitted_notional: 35.278788
- events_recorded: 491
- today_pnl: -0.336796
- total_equity: 24.663204
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5556
- stop_out_rate: 1.0000
- average_trade_pnl: -0.136970
- average_signal_edge_bps: 403.8341
- average_adverse_fill_bps: 162.8673
- expected_edge_capture_bps: 240.9668
- edge_capture_ratio: 0.5967
- average_trade_expected_edge_bps: 433.0236
- average_trade_execution_drag_bps: 155.2645
- average_trade_realized_pnl_bps: -88.4582
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.136970
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.919865
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.003882
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -14
- orders_delta: -11
- pnl_delta: 0.168385

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
- pricing_quality_score: 0.4800
- execution_quality_score: 0.4300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.5200
- execution_loss: 0.5700
- exit_loss: 0.9100
- sizing_loss: 0.2300
- total_profit_loss: 2.5300
- tuning_priority: exit
