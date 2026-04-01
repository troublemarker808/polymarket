# Crypto Phase 2 Suite

- generated_at: 2026-04-01T07:21:57.829204+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v97b-no-taker-hold12-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v97b-no-taker-hold12-limit2000\replay-unfiltered
- signals_generated: 25
- submitted_orders: 22
- submitted_notional: 87.453931
- events_recorded: 2003
- today_pnl: -0.616977
- total_equity: 24.383023
- status: completed
- maker_fill_rate: 0.0455
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.152244
- average_signal_edge_bps: 1085.9036
- average_adverse_fill_bps: 205.3210
- expected_edge_capture_bps: 880.5825
- edge_capture_ratio: 0.8109
- average_trade_expected_edge_bps: 1147.9039
- average_trade_execution_drag_bps: 173.7598
- average_trade_realized_pnl_bps: -158.8841
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.608977
- closed_trade_count: 4
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.152244
- average_submitted_notional: 3.975179
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.7500
- exit_family_balance_score: 0.7000
- small_bucket_pnl_per_notional: -0.006963
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v97b-no-taker-hold12-limit2000\replay-filtered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 39.881713
- events_recorded: 2019
- today_pnl: -0.150050
- total_equity: 24.849950
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.075025
- average_signal_edge_bps: 642.1408
- average_adverse_fill_bps: 94.8884
- expected_edge_capture_bps: 547.2524
- edge_capture_ratio: 0.8522
- average_trade_expected_edge_bps: 632.6844
- average_trade_execution_drag_bps: 94.4828
- average_trade_realized_pnl_bps: -95.3857
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.150050
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.075025
- average_submitted_notional: 3.988171
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.003762
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -15
- orders_delta: -12
- pnl_delta: 0.466927

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
