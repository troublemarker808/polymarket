# Crypto Phase 2 Suite

- generated_at: 2026-04-01T09:40:40.427796+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v102a-reach30-dip35-timestop-ioc-adverse200-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v102a-reach30-dip35-timestop-ioc-adverse200-limit2000\replay-unfiltered
- signals_generated: 25
- submitted_orders: 22
- submitted_notional: 87.508725
- events_recorded: 1973
- today_pnl: -0.554292
- total_equity: 24.445708
- status: completed
- maker_fill_rate: 0.0455
- taker_fill_rate: 0.0000
- expiration_rate: 0.5455
- stop_out_rate: 1.0000
- average_trade_pnl: -0.179431
- average_signal_edge_bps: 1116.5339
- average_adverse_fill_bps: 212.4671
- expected_edge_capture_bps: 904.0668
- edge_capture_ratio: 0.8097
- average_trade_expected_edge_bps: 1210.2736
- average_trade_execution_drag_bps: 183.1967
- average_trade_realized_pnl_bps: -156.5906
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.538292
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.179431
- average_submitted_notional: 3.977669
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.006151
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v102a-reach30-dip35-timestop-ioc-adverse200-limit2000\replay-filtered
- signals_generated: 16
- submitted_orders: 16
- submitted_notional: 63.815295
- events_recorded: 1999
- today_pnl: -0.224335
- total_equity: 24.775665
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6875
- stop_out_rate: 1.0000
- average_trade_pnl: -0.108167
- average_signal_edge_bps: 476.0352
- average_adverse_fill_bps: 140.7942
- expected_edge_capture_bps: 335.2410
- edge_capture_ratio: 0.7042
- average_trade_expected_edge_bps: 524.4018
- average_trade_execution_drag_bps: 127.3592
- average_trade_realized_pnl_bps: -111.1699
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.216335
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.108167
- average_submitted_notional: 3.988456
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.003390
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -9
- orders_delta: -6
- pnl_delta: 0.329957

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
