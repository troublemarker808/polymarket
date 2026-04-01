# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:31:32.588095+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v60c-scaleout-ts80-af100-baseline475\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v60c-scaleout-ts80-af100-baseline475\replay-unfiltered
- signals_generated: 32
- submitted_orders: 18
- submitted_notional: 69.982738
- events_recorded: 507
- today_pnl: -0.735067
- total_equity: 24.264933
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4444
- stop_out_rate: 1.0000
- average_trade_pnl: -0.152676
- average_signal_edge_bps: 1063.6692
- average_adverse_fill_bps: 212.0869
- expected_edge_capture_bps: 851.5823
- edge_capture_ratio: 0.8006
- average_trade_expected_edge_bps: 996.7545
- average_trade_execution_drag_bps: 206.0963
- average_trade_realized_pnl_bps: -176.1644
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.458027
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.152676
- average_submitted_notional: 3.887930
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.006545
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v60c-scaleout-ts80-af100-baseline475\replay-filtered
- signals_generated: 21
- submitted_orders: 9
- submitted_notional: 34.905815
- events_recorded: 491
- today_pnl: -0.567067
- total_equity: 24.432933
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3333
- stop_out_rate: 1.0000
- average_trade_pnl: -0.161198
- average_signal_edge_bps: 758.2249
- average_adverse_fill_bps: 210.0783
- expected_edge_capture_bps: 548.1466
- edge_capture_ratio: 0.7229
- average_trade_expected_edge_bps: 766.8515
- average_trade_execution_drag_bps: 202.7689
- average_trade_realized_pnl_bps: -161.2719
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.322397
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.161198
- average_submitted_notional: 3.878424
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.009236
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -11
- orders_delta: -9
- pnl_delta: 0.168000

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
- execution_quality_score: 0.4300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.5700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.5100
- tuning_priority: exit
