# Crypto Phase 2 Suite

- generated_at: 2026-04-01T05:09:27.628905+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v58-longtail-baseline-l10000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k, what-price-will-bitcoin-hit-before-2027

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v58-longtail-baseline-l10000\replay-unfiltered
- signals_generated: 88
- submitted_orders: 48
- submitted_notional: 191.885714
- events_recorded: 9211
- today_pnl: -0.665727
- total_equity: 24.334273
- status: completed
- maker_fill_rate: 0.0417
- taker_fill_rate: 0.0000
- expiration_rate: 0.8750
- stop_out_rate: 1.0000
- average_trade_pnl: -0.130057
- average_signal_edge_bps: 821.1258
- average_adverse_fill_bps: 152.1683
- expected_edge_capture_bps: 668.9574
- edge_capture_ratio: 0.8147
- average_trade_expected_edge_bps: 1042.4439
- average_trade_execution_drag_bps: 106.7321
- average_trade_realized_pnl_bps: -41.9221
- average_barrier_observed_gap_bps: 1858.1823
- average_surface_observed_gap_bps: 118.3333
- average_fusion_observed_gap_bps: 674.4222
- average_barrier_surface_disagreement_bps: 1835.8765
- closed_trade_net_pnl: -0.130057
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.130057
- average_submitted_notional: 3.997619
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.000678
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v58-longtail-baseline-l10000\replay-filtered
- signals_generated: 9
- submitted_orders: 9
- submitted_notional: 35.885714
- events_recorded: 9645
- today_pnl: -0.287981
- total_equity: 24.712019
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.5556
- stop_out_rate: 1.0000
- average_trade_pnl: -0.130057
- average_signal_edge_bps: 501.9379
- average_adverse_fill_bps: 144.1497
- expected_edge_capture_bps: 357.7882
- edge_capture_ratio: 0.7128
- average_trade_expected_edge_bps: 560.0039
- average_trade_execution_drag_bps: 137.3057
- average_trade_realized_pnl_bps: -83.8442
- average_barrier_observed_gap_bps: 1858.1823
- average_surface_observed_gap_bps: 118.3333
- average_fusion_observed_gap_bps: 674.4222
- average_barrier_surface_disagreement_bps: 1835.8765
- closed_trade_net_pnl: -0.130057
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.130057
- average_submitted_notional: 3.987302
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.003624
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -79
- orders_delta: -39
- pnl_delta: 0.377746

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
- exit_quality_score: 0.0900
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.5700
- exit_loss: 0.9100
- sizing_loss: 0.2300
- total_profit_loss: 2.4300
- tuning_priority: exit
