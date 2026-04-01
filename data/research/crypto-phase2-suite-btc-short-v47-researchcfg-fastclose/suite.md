# Crypto Phase 2 Suite

- generated_at: 2026-03-31T21:44:52.307535+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v35.20260328.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v47-researchcfg-fastclose\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v47-researchcfg-fastclose\replay-unfiltered
- signals_generated: 17
- submitted_orders: 8
- submitted_notional: 39.537422
- events_recorded: 499
- today_pnl: -0.672943
- total_equity: 24.327057
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.2500
- stop_out_rate: 1.0000
- average_trade_pnl: -0.250826
- average_signal_edge_bps: 1478.3426
- average_adverse_fill_bps: 242.6104
- expected_edge_capture_bps: 1235.7322
- edge_capture_ratio: 0.8359
- average_trade_expected_edge_bps: 1374.9227
- average_trade_execution_drag_bps: 242.3949
- average_trade_realized_pnl_bps: -211.0965
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.501653
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.250826
- average_submitted_notional: 4.942178
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.012688
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v47-researchcfg-fastclose\replay-filtered
- signals_generated: 10
- submitted_orders: 5
- submitted_notional: 24.729730
- events_recorded: 489
- today_pnl: -0.539513
- total_equity: 24.460487
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.2000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.289730
- average_signal_edge_bps: 1114.9071
- average_adverse_fill_bps: 241.8723
- expected_edge_capture_bps: 873.0347
- edge_capture_ratio: 0.7831
- average_trade_expected_edge_bps: 980.8154
- average_trade_execution_drag_bps: 217.2303
- average_trade_realized_pnl_bps: -153.4498
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_net_pnl: -0.289730
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.289730
- average_submitted_notional: 4.945946
- large_notional_share: 0.0000
- dominant_exit_reason: exit
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.011716
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -7
- orders_delta: -3
- pnl_delta: 0.133430

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
- execution_quality_score: 0.6300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.6500
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.3700
- exit_loss: 0.9100
- sizing_loss: 0.3500
- total_profit_loss: 2.3500
- tuning_priority: exit
