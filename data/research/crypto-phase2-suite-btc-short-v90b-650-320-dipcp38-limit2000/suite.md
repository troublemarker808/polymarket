# Crypto Phase 2 Suite

- generated_at: 2026-04-01T07:00:14.233357+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v90b-650-320-dipcp38-limit2000\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v90b-650-320-dipcp38-limit2000\replay-unfiltered
- signals_generated: 28
- submitted_orders: 24
- submitted_notional: 95.670147
- events_recorded: 2010
- today_pnl: -0.385193
- total_equity: 24.614807
- status: completed
- maker_fill_rate: 0.0417
- taker_fill_rate: 0.0000
- expiration_rate: 0.5833
- stop_out_rate: 1.0000
- average_trade_pnl: -0.125731
- average_signal_edge_bps: 982.9088
- average_adverse_fill_bps: 178.0047
- expected_edge_capture_bps: 804.9041
- edge_capture_ratio: 0.8189
- average_trade_expected_edge_bps: 1076.2531
- average_trade_execution_drag_bps: 142.7553
- average_trade_realized_pnl_bps: -121.8802
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.377193
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.125731
- average_submitted_notional: 3.986256
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.003943
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v90b-650-320-dipcp38-limit2000\replay-filtered
- signals_generated: 13
- submitted_orders: 12
- submitted_notional: 47.823993
- events_recorded: 1988
- today_pnl: -0.215655
- total_equity: 24.784345
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5833
- stop_out_rate: 1.0000
- average_trade_pnl: -0.103827
- average_signal_edge_bps: 427.8740
- average_adverse_fill_bps: 153.1274
- expected_edge_capture_bps: 274.7466
- edge_capture_ratio: 0.6421
- average_trade_expected_edge_bps: 463.7342
- average_trade_execution_drag_bps: 141.9771
- average_trade_realized_pnl_bps: -106.6717
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.207655
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.103827
- average_submitted_notional: 3.985333
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.004342
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -15
- orders_delta: -12
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
- selection_quality_score: 0.9000
- pricing_quality_score: 0.4800
- execution_quality_score: 0.4300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.1000
- pricing_loss: 0.5200
- execution_loss: 0.5700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.4100
- tuning_priority: exit
