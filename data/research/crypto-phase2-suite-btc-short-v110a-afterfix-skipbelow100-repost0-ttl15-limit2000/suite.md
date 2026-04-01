# Crypto Phase 2 Suite

- generated_at: 2026-04-01T10:42:25.695793+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v110a-afterfix-skipbelow100-repost0-ttl15-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v110a-afterfix-skipbelow100-repost0-ttl15-limit2000\replay-unfiltered
- signals_generated: 26
- submitted_orders: 23
- submitted_notional: 91.499669
- events_recorded: 1953
- today_pnl: -0.609285
- total_equity: 24.390715
- status: completed
- maker_fill_rate: 0.0435
- taker_fill_rate: 0.0000
- expiration_rate: 0.5652
- stop_out_rate: 1.0000
- average_trade_pnl: -0.146479
- average_signal_edge_bps: 953.5851
- average_adverse_fill_bps: 203.3131
- expected_edge_capture_bps: 750.2720
- edge_capture_ratio: 0.7868
- average_trade_expected_edge_bps: 1078.8973
- average_trade_execution_drag_bps: 169.1013
- average_trade_realized_pnl_bps: -127.4619
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.439438
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.146479
- average_submitted_notional: 3.978246
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.004803
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v110a-afterfix-skipbelow100-repost0-ttl15-limit2000\replay-filtered
- signals_generated: 17
- submitted_orders: 17
- submitted_notional: 67.760501
- events_recorded: 2032
- today_pnl: -0.287020
- total_equity: 24.712980
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5882
- stop_out_rate: 1.0000
- average_trade_pnl: -0.095673
- average_signal_edge_bps: 488.6806
- average_adverse_fill_bps: 134.8495
- expected_edge_capture_bps: 353.8310
- edge_capture_ratio: 0.7241
- average_trade_expected_edge_bps: 534.7643
- average_trade_execution_drag_bps: 120.9372
- average_trade_realized_pnl_bps: -122.5626
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.287020
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.095673
- average_submitted_notional: 3.985912
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.004236
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -9
- orders_delta: -6
- pnl_delta: 0.322265

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
