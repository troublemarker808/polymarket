# Crypto Phase 2 Suite

- generated_at: 2026-04-01T15:09:40.047786+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-profile-v112a-20260401\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-profile-v112a-20260401\replay-unfiltered
- signals_generated: 55
- submitted_orders: 44
- submitted_notional: 175.297130
- events_recorded: 2084
- today_pnl: -0.675664
- total_equity: 24.324336
- status: completed
- maker_fill_rate: 0.0682
- taker_fill_rate: 0.0000
- expiration_rate: 0.6364
- stop_out_rate: 1.0000
- average_trade_pnl: -0.085425
- average_signal_edge_bps: 915.6118
- average_adverse_fill_bps: 116.9162
- expected_edge_capture_bps: 798.6955
- edge_capture_ratio: 0.8723
- average_trade_expected_edge_bps: 954.0818
- average_trade_execution_drag_bps: 98.7949
- average_trade_realized_pnl_bps: -95.7338
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.597977
- closed_trade_count: 7
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.085425
- average_submitted_notional: 3.984026
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.8571
- exit_family_balance_score: 0.6571
- small_bucket_pnl_per_notional: -0.003411
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000028", "market_id": "1345530", "net_pnl": -0.13697, "abs_loss": 0.13697, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|taker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-27T12:37:11.431000+00:00"}, {"intent_id": "intent-00000025", "market_id": "701496", "net_pnl": -0.130057, "abs_loss": 0.130057, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_yes", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_reach_short_shadow|sell_yes", "closed_at": "2026-03-27T12:36:33.256000+00:00"}, {"intent_id": "intent-00000014", "market_id": "701502", "net_pnl": -0.094275, "abs_loss": 0.094275, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T12:35:39.483000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339768", "total_abs_loss": 0.15873, "loss_count": 2}, {"market_id": "1345530", "total_abs_loss": 0.13697, "loss_count": 1}, {"market_id": "701496", "total_abs_loss": 0.130057, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.094275, "loss_count": 1}, {"market_id": "701503", "total_abs_loss": 0.077946, "loss_count": 2}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.330951, "loss_count": 5}, {"signature": "exit|taker|btc_reach_short_shadow|sell_no", "total_abs_loss": 0.13697, "loss_count": 1}, {"signature": "exit|taker|btc_reach_short_shadow|sell_yes", "total_abs_loss": 0.130057, "loss_count": 1}]

### filtered

- output_dir: data\research\crypto-phase2-suite-profile-v112a-20260401\replay-filtered
- signals_generated: 25
- submitted_orders: 21
- submitted_notional: 83.559085
- events_recorded: 2034
- today_pnl: -0.520031
- total_equity: 24.479969
- status: completed
- maker_fill_rate: 0.0476
- taker_fill_rate: 0.0000
- expiration_rate: 0.5238
- stop_out_rate: 1.0000
- average_trade_pnl: -0.104006
- average_signal_edge_bps: 1005.8012
- average_adverse_fill_bps: 134.4150
- expected_edge_capture_bps: 871.3863
- edge_capture_ratio: 0.8664
- average_trade_expected_edge_bps: 952.3497
- average_trade_execution_drag_bps: 119.5970
- average_trade_realized_pnl_bps: -121.2841
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.520031
- closed_trade_count: 5
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.104006
- average_submitted_notional: 3.979004
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.8000
- exit_family_balance_score: 0.6800
- small_bucket_pnl_per_notional: -0.006224
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000017", "market_id": "1345530", "net_pnl": -0.13697, "abs_loss": 0.13697, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|taker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-27T12:37:11.431000+00:00"}, {"intent_id": "intent-00000014", "market_id": "701496", "net_pnl": -0.130057, "abs_loss": 0.130057, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_yes", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_reach_short_shadow|sell_yes", "closed_at": "2026-03-27T12:36:33.256000+00:00"}, {"intent_id": "intent-00000009", "market_id": "701502", "net_pnl": -0.094275, "abs_loss": 0.094275, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T12:35:39.483000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339768", "total_abs_loss": 0.15873, "loss_count": 2}, {"market_id": "1345530", "total_abs_loss": 0.13697, "loss_count": 1}, {"market_id": "701496", "total_abs_loss": 0.130057, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.094275, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.253005, "loss_count": 3}, {"signature": "exit|taker|btc_reach_short_shadow|sell_no", "total_abs_loss": 0.13697, "loss_count": 1}, {"signature": "exit|taker|btc_reach_short_shadow|sell_yes", "total_abs_loss": 0.130057, "loss_count": 1}]

## Delta

- signals_delta: -30
- orders_delta: -23
- pnl_delta: 0.155632

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
