# Crypto Phase 2 Suite

- generated_at: 2026-04-01T15:11:41.886756+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.overnight.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-profile-v108a-overnight-20260401\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-profile-v108a-overnight-20260401\replay-unfiltered
- signals_generated: 409
- submitted_orders: 80
- submitted_notional: 320.880000
- events_recorded: 2489
- today_pnl: 0.784160
- total_equity: 25.784160
- status: completed
- maker_fill_rate: 0.1500
- taker_fill_rate: 0.0000
- expiration_rate: 0.7000
- stop_out_rate: 0.0833
- average_trade_pnl: 0.065347
- average_signal_edge_bps: 375.4362
- average_adverse_fill_bps: 63.6054
- expected_edge_capture_bps: 311.8308
- edge_capture_ratio: 0.8306
- average_trade_expected_edge_bps: 375.4362
- average_trade_execution_drag_bps: 63.6054
- average_trade_realized_pnl_bps: 81.8303
- average_barrier_observed_gap_bps: 2060.4054
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 721.1419
- average_barrier_surface_disagreement_bps: 2060.4054
- closed_trade_net_pnl: 0.784160
- closed_trade_count: 12
- winning_trade_rate: 0.9167
- average_win_trade_pnl: 0.072000
- average_loss_trade_pnl: -0.007840
- average_submitted_notional: 4.011000
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.002444
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_aggressive
- top_loss_trades: [{"intent_id": "intent-00000054", "market_id": "1345531", "net_pnl": -0.00784, "abs_loss": 0.00784, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|taker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-26T22:52:54.761000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1345531", "total_abs_loss": 0.00784, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_reach_short_shadow|sell_no", "total_abs_loss": 0.00784, "loss_count": 1}]

### filtered

- output_dir: data\research\crypto-phase2-suite-profile-v108a-overnight-20260401\replay-filtered
- signals_generated: 7
- submitted_orders: 6
- submitted_notional: 24.000000
- events_recorded: 2013
- today_pnl: 0.000000
- total_equity: 25.000000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 1.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 0.0000
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 0.0000
- edge_capture_ratio: 0.0000
- average_trade_expected_edge_bps: 0.0000
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 2060.4054
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 721.1419
- average_barrier_surface_disagreement_bps: 2060.4054
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 4.000000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_aggressive
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Delta

- signals_delta: -402
- orders_delta: -74
- pnl_delta: -0.784160

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, edge_capture_ratio_below_floor, pnl_per_notional_not_positive
- profit_focus: pricing
- selection_quality_score: 0.9000
- pricing_quality_score: 0.1600
- execution_quality_score: 0.8000
- exit_quality_score: 1.0000
- sizing_quality_score: 0.7700
- selection_loss: 0.1000
- pricing_loss: 0.8400
- execution_loss: 0.2000
- exit_loss: 0.0000
- sizing_loss: 0.2300
- total_profit_loss: 1.3700
- tuning_priority: pricing
