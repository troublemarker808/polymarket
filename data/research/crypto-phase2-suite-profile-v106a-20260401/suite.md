# Crypto Phase 2 Suite

- generated_at: 2026-04-01T15:09:40.019552+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-profile-v106a-20260401\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-profile-v106a-20260401\replay-unfiltered
- signals_generated: 45
- submitted_orders: 33
- submitted_notional: 131.777605
- events_recorded: 1964
- today_pnl: -0.365927
- total_equity: 24.634073
- status: completed
- maker_fill_rate: 0.0606
- taker_fill_rate: 0.0000
- expiration_rate: 0.7576
- stop_out_rate: 1.0000
- average_trade_pnl: -0.069334
- average_signal_edge_bps: 520.4052
- average_adverse_fill_bps: 113.8945
- expected_edge_capture_bps: 406.5107
- edge_capture_ratio: 0.7811
- average_trade_expected_edge_bps: 781.0532
- average_trade_execution_drag_bps: 90.3823
- average_trade_realized_pnl_bps: -59.2213
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.208003
- closed_trade_count: 3
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.069334
- average_submitted_notional: 3.993261
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.6667
- exit_family_balance_score: 0.7333
- small_bucket_pnl_per_notional: -0.001578
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000021", "market_id": "701496", "net_pnl": -0.130057, "abs_loss": 0.130057, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_yes", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_reach_short_shadow|sell_yes", "closed_at": "2026-03-27T12:36:33.256000+00:00"}, {"intent_id": "intent-00000015", "market_id": "701503", "net_pnl": -0.069946, "abs_loss": 0.069946, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T12:35:58.595000+00:00"}, {"intent_id": "intent-00000040", "market_id": "701503", "net_pnl": -0.008, "abs_loss": 0.008, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T12:41:32.552000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "701496", "total_abs_loss": 0.130057, "loss_count": 1}, {"market_id": "701503", "total_abs_loss": 0.077946, "loss_count": 2}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_reach_short_shadow|sell_yes", "total_abs_loss": 0.130057, "loss_count": 1}, {"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.077946, "loss_count": 2}]

### filtered

- output_dir: data\research\crypto-phase2-suite-profile-v106a-20260401\replay-filtered
- signals_generated: 10
- submitted_orders: 10
- submitted_notional: 39.885714
- events_recorded: 1910
- today_pnl: -0.287981
- total_equity: 24.712019
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.130057
- average_signal_edge_bps: 501.9379
- average_adverse_fill_bps: 144.1497
- expected_edge_capture_bps: 357.7882
- edge_capture_ratio: 0.7128
- average_trade_expected_edge_bps: 560.0039
- average_trade_execution_drag_bps: 137.3057
- average_trade_realized_pnl_bps: -83.8442
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.130057
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.130057
- average_submitted_notional: 3.988571
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.003261
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000010", "market_id": "701496", "net_pnl": -0.130057, "abs_loss": 0.130057, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_yes", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_reach_short_shadow|sell_yes", "closed_at": "2026-03-27T12:36:33.256000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "701496", "total_abs_loss": 0.130057, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_reach_short_shadow|sell_yes", "total_abs_loss": 0.130057, "loss_count": 1}]

## Delta

- signals_delta: -35
- orders_delta: -23
- pnl_delta: 0.077946

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, top3_loss_concentration_above_ceiling, pnl_per_notional_not_positive
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
