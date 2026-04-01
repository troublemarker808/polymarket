# Crypto Phase 2 Suite

- generated_at: 2026-04-01T06:06:17.832806+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v75a-profit-escalate-a1-cap590-baseline475\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v75a-profit-escalate-a1-cap590-baseline475\replay-unfiltered
- signals_generated: 22
- submitted_orders: 21
- submitted_notional: 83.670147
- events_recorded: 514
- today_pnl: -0.514225
- total_equity: 24.485775
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5238
- stop_out_rate: 1.0000
- average_trade_pnl: -0.125731
- average_signal_edge_bps: 962.5975
- average_adverse_fill_bps: 179.8727
- expected_edge_capture_bps: 782.7247
- edge_capture_ratio: 0.8131
- average_trade_expected_edge_bps: 813.0855
- average_trade_execution_drag_bps: 163.1489
- average_trade_realized_pnl_bps: -139.2917
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.377193
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.125731
- average_submitted_notional: 3.984293
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.004508
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v75a-profit-escalate-a1-cap590-baseline475\replay-filtered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 39.823993
- events_recorded: 494
- today_pnl: -0.344687
- total_equity: 24.655313
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.103827
- average_signal_edge_bps: 427.8740
- average_adverse_fill_bps: 153.1274
- expected_edge_capture_bps: 274.7466
- edge_capture_ratio: 0.6421
- average_trade_expected_edge_bps: 463.7342
- average_trade_execution_drag_bps: 141.9771
- average_trade_realized_pnl_bps: -106.6717
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.207655
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.103827
- average_submitted_notional: 3.982399
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.005214
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -12
- orders_delta: -11
- pnl_delta: 0.169538

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
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.5200
- execution_loss: 0.5700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.6100
- tuning_priority: exit
