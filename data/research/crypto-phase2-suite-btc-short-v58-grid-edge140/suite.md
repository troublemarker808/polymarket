# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:16:12.248288+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v58-grid-edge140\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v58-grid-edge140\replay-unfiltered
- signals_generated: 19
- submitted_orders: 19
- submitted_notional: 75.453931
- events_recorded: 510
- today_pnl: -0.746009
- total_equity: 24.253991
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4211
- stop_out_rate: 1.0000
- average_trade_pnl: -0.152244
- average_signal_edge_bps: 1071.0943
- average_adverse_fill_bps: 206.9803
- expected_edge_capture_bps: 864.1140
- edge_capture_ratio: 0.8068
- average_trade_expected_edge_bps: 951.1792
- average_trade_execution_drag_bps: 193.0665
- average_trade_realized_pnl_bps: -176.5379
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.608977
- closed_trade_count: 4
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.152244
- average_submitted_notional: 3.971260
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.7500
- exit_family_balance_score: 0.7000
- small_bucket_pnl_per_notional: -0.008071
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v58-grid-edge140\replay-filtered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 39.607777
- events_recorded: 494
- today_pnl: -0.576471
- total_equity: 24.423529
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.146479
- average_signal_edge_bps: 771.8518
- average_adverse_fill_bps: 202.5560
- expected_edge_capture_bps: 569.2957
- edge_capture_ratio: 0.7376
- average_trade_expected_edge_bps: 741.0979
- average_trade_execution_drag_bps: 186.4916
- average_trade_realized_pnl_bps: -163.8796
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.439438
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.146479
- average_submitted_notional: 3.960778
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.011095
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -9
- orders_delta: -9
- pnl_delta: 0.169538

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: pnl_per_notional_not_positive
- profit_focus: exit
- selection_quality_score: 0.7000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.5300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7000
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9900
- sizing_loss: 0.3000
- total_profit_loss: 2.4800
- tuning_priority: exit
