# Crypto Phase 2 Suite

- generated_at: 2026-04-01T07:27:20.896081+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v98b-reach30-dip35-takermin350-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v98b-reach30-dip35-takermin350-limit2000\replay-unfiltered
- signals_generated: 35
- submitted_orders: 29
- submitted_notional: 115.508725
- events_recorded: 2022
- today_pnl: -0.546292
- total_equity: 24.453708
- status: completed
- maker_fill_rate: 0.0345
- taker_fill_rate: 0.0000
- expiration_rate: 0.6552
- stop_out_rate: 1.0000
- average_trade_pnl: -0.179431
- average_signal_edge_bps: 1161.9510
- average_adverse_fill_bps: 220.5292
- expected_edge_capture_bps: 941.4218
- edge_capture_ratio: 0.8102
- average_trade_expected_edge_bps: 1308.8609
- average_trade_execution_drag_bps: 194.9584
- average_trade_realized_pnl_bps: -176.1644
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.538292
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.179431
- average_submitted_notional: 3.983059
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.004660
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v98b-reach30-dip35-takermin350-limit2000\replay-filtered
- signals_generated: 16
- submitted_orders: 16
- submitted_notional: 63.815296
- events_recorded: 2031
- today_pnl: -0.216335
- total_equity: 24.783665
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6875
- stop_out_rate: 1.0000
- average_trade_pnl: -0.108167
- average_signal_edge_bps: 484.1132
- average_adverse_fill_bps: 148.4615
- expected_edge_capture_bps: 335.6517
- edge_capture_ratio: 0.6933
- average_trade_expected_edge_bps: 550.1083
- average_trade_execution_drag_bps: 136.9231
- average_trade_realized_pnl_bps: -138.9624
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

- signals_delta: -19
- orders_delta: -13
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
