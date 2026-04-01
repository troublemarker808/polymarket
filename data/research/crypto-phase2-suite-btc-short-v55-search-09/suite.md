# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:50:48.873898+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v55-search-09\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v55-search-09\replay-unfiltered
- signals_generated: 22
- submitted_orders: 21
- submitted_notional: 83.724942
- events_recorded: 514
- today_pnl: -0.443540
- total_equity: 24.556460
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6190
- stop_out_rate: 1.0000
- average_trade_pnl: -0.153254
- average_signal_edge_bps: 1044.3518
- average_adverse_fill_bps: 196.0815
- expected_edge_capture_bps: 848.2703
- edge_capture_ratio: 0.8122
- average_trade_expected_edge_bps: 936.6892
- average_trade_execution_drag_bps: 192.8223
- average_trade_realized_pnl_bps: -159.1032
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.306508
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.153254
- average_submitted_notional: 3.986902
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.003661
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v55-search-09\replay-filtered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 39.878788
- events_recorded: 494
- today_pnl: -0.274002
- total_equity: 24.725998
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.7000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.136970
- average_signal_edge_bps: 400.6669
- average_adverse_fill_bps: 176.0355
- expected_edge_capture_bps: 224.6314
- edge_capture_ratio: 0.5606
- average_trade_expected_edge_bps: 436.8395
- average_trade_execution_drag_bps: 177.3182
- average_trade_realized_pnl_bps: -117.9442
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.136970
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.987879
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.003435
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -12
- orders_delta: -11
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
