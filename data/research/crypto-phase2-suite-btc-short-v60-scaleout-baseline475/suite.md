# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:29:59.011341+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v60-scaleout-baseline475\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v60-scaleout-baseline475\replay-unfiltered
- signals_generated: 37
- submitted_orders: 17
- submitted_notional: 61.314969
- events_recorded: 503
- today_pnl: -0.722731
- total_equity: 24.277269
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4706
- stop_out_rate: 1.0000
- average_trade_pnl: -0.100331
- average_signal_edge_bps: 1174.9780
- average_adverse_fill_bps: 214.8420
- expected_edge_capture_bps: 960.1360
- edge_capture_ratio: 0.8172
- average_trade_expected_edge_bps: 1128.8553
- average_trade_execution_drag_bps: 210.7474
- average_trade_realized_pnl_bps: -150.7832
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.200661
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.100331
- average_submitted_notional: 3.606763
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.003273
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v60-scaleout-baseline475\replay-filtered
- signals_generated: 27
- submitted_orders: 7
- submitted_notional: 25.891892
- events_recorded: 486
- today_pnl: -0.557039
- total_equity: 24.442961
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.2857
- stop_out_rate: 1.0000
- average_trade_pnl: -0.115892
- average_signal_edge_bps: 897.6174
- average_adverse_fill_bps: 214.0585
- expected_edge_capture_bps: 683.5589
- edge_capture_ratio: 0.7615
- average_trade_expected_edge_bps: 905.8120
- average_trade_execution_drag_bps: 208.6150
- average_trade_realized_pnl_bps: -122.7598
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.115892
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.115892
- average_submitted_notional: 3.698842
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.004476
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -10
- orders_delta: -10
- pnl_delta: 0.165692

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
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.4100
- tuning_priority: exit
