# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:47:25.154947+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v73-longtail-base\selection
- blocked_series_keys: when-will-bitcoin-hit-150k, what-price-will-bitcoin-hit-before-2027

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v73-longtail-base\replay-unfiltered
- signals_generated: 18
- submitted_orders: 17
- submitted_notional: 67.804022
- events_recorded: 508
- today_pnl: -0.365871
- total_equity: 24.634129
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5882
- stop_out_rate: 1.0000
- average_trade_pnl: -0.081195
- average_signal_edge_bps: 752.2754
- average_adverse_fill_bps: 118.0566
- expected_edge_capture_bps: 634.2187
- edge_capture_ratio: 0.8431
- average_trade_expected_edge_bps: 739.4371
- average_trade_execution_drag_bps: 111.3274
- average_trade_realized_pnl_bps: -88.6449
- average_barrier_observed_gap_bps: 1847.4582
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 669.0437
- average_barrier_surface_disagreement_bps: 1824.3194
- closed_trade_net_pnl: -0.243586
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.081195
- average_submitted_notional: 3.988472
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.003592
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v73-longtail-base\replay-filtered
- signals_generated: 9
- submitted_orders: 9
- submitted_notional: 35.858076
- events_recorded: 492
- today_pnl: -0.295925
- total_equity: 24.704075
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4444
- stop_out_rate: 1.0000
- average_trade_pnl: -0.086820
- average_signal_edge_bps: 829.5331
- average_adverse_fill_bps: 126.2108
- expected_edge_capture_bps: 703.3223
- edge_capture_ratio: 0.8479
- average_trade_expected_edge_bps: 848.1094
- average_trade_execution_drag_bps: 120.6474
- average_trade_realized_pnl_bps: -88.5797
- average_barrier_observed_gap_bps: 1847.4582
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 669.0437
- average_barrier_surface_disagreement_bps: 1824.3194
- closed_trade_net_pnl: -0.173640
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.086820
- average_submitted_notional: 3.984231
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.004842
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -9
- orders_delta: -8
- pnl_delta: 0.069946

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
