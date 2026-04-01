# Crypto Phase 2 Suite

- generated_at: 2026-04-01T10:05:55.221807+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v103a-after-underlyingfix-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v103a-after-underlyingfix-limit2000\replay-unfiltered
- signals_generated: 22
- submitted_orders: 19
- submitted_notional: 75.878788
- events_recorded: 1845
- today_pnl: -0.647140
- total_equity: 24.352860
- status: completed
- maker_fill_rate: 0.0526
- taker_fill_rate: 0.0000
- expiration_rate: 0.5789
- stop_out_rate: 1.0000
- average_trade_pnl: -0.136970
- average_signal_edge_bps: 876.1109
- average_adverse_fill_bps: 197.1683
- expected_edge_capture_bps: 678.9426
- edge_capture_ratio: 0.7750
- average_trade_expected_edge_bps: 1075.9273
- average_trade_execution_drag_bps: 162.2660
- average_trade_realized_pnl_bps: -50.5475
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.136970
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.993620
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.001805
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v103a-after-underlyingfix-limit2000\replay-filtered
- signals_generated: 13
- submitted_orders: 13
- submitted_notional: 51.878788
- events_recorded: 1957
- today_pnl: -0.216462
- total_equity: 24.783538
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6923
- stop_out_rate: 1.0000
- average_trade_pnl: -0.136970
- average_signal_edge_bps: 411.3026
- average_adverse_fill_bps: 148.0030
- expected_edge_capture_bps: 263.2997
- edge_capture_ratio: 0.6402
- average_trade_expected_edge_bps: 444.5538
- average_trade_execution_drag_bps: 134.2389
- average_trade_realized_pnl_bps: -88.4582
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.136970
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.990676
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.002640
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -9
- orders_delta: -6
- pnl_delta: 0.430678

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
