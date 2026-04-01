# Crypto Phase 2 Suite

- generated_at: 2026-04-01T17:06:14.278152+00:00
- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-profile-v118a-btc-short-20260402-unit2-partial\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-profile-v118a-btc-short-20260402-unit2-partial\replay-unfiltered
- signals_generated: 8
- submitted_orders: 8
- submitted_notional: 30.885326
- events_recorded: 37
- today_pnl: -0.281244
- total_equity: 24.718756
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3750
- stop_out_rate: 1.0000
- average_trade_pnl: -0.096622
- average_signal_edge_bps: 1179.8918
- average_adverse_fill_bps: 134.2975
- expected_edge_capture_bps: 1045.5943
- edge_capture_ratio: 0.8862
- average_trade_expected_edge_bps: 1128.2750
- average_trade_execution_drag_bps: 129.6383
- average_trade_realized_pnl_bps: -106.8709
- average_barrier_observed_gap_bps: 3346.7983
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1171.3794
- average_barrier_surface_disagreement_bps: 3346.7983
- closed_trade_net_pnl: -0.193244
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.096622
- average_submitted_notional: 3.860666
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.006257
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000006", "market_id": "1339767", "net_pnl": -0.111802, "abs_loss": 0.111802, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T15:16:21.317000+00:00"}, {"intent_id": "intent-00000008", "market_id": "1339768", "net_pnl": -0.081443, "abs_loss": 0.081443, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T15:17:21.627000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339767", "total_abs_loss": 0.111802, "loss_count": 1}, {"market_id": "1339768", "total_abs_loss": 0.081443, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.193244, "loss_count": 2}]

### filtered

- output_dir: data\research\crypto-phase2-suite-profile-v118a-btc-short-20260402-unit2-partial\replay-filtered
- signals_generated: 8
- submitted_orders: 8
- submitted_notional: 30.885326
- events_recorded: 37
- today_pnl: -0.281244
- total_equity: 24.718756
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3750
- stop_out_rate: 1.0000
- average_trade_pnl: -0.096622
- average_signal_edge_bps: 1179.8918
- average_adverse_fill_bps: 134.2975
- expected_edge_capture_bps: 1045.5943
- edge_capture_ratio: 0.8862
- average_trade_expected_edge_bps: 1128.2750
- average_trade_execution_drag_bps: 129.6383
- average_trade_realized_pnl_bps: -106.8709
- average_barrier_observed_gap_bps: 3346.7983
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1171.3794
- average_barrier_surface_disagreement_bps: 3346.7983
- closed_trade_net_pnl: -0.193244
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.096622
- average_submitted_notional: 3.860666
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.006257
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000006", "market_id": "1339767", "net_pnl": -0.111802, "abs_loss": 0.111802, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T15:16:21.317000+00:00"}, {"intent_id": "intent-00000008", "market_id": "1339768", "net_pnl": -0.081443, "abs_loss": 0.081443, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T15:17:21.627000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339767", "total_abs_loss": 0.111802, "loss_count": 1}, {"market_id": "1339768", "total_abs_loss": 0.081443, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.193244, "loss_count": 2}]

## Delta

- signals_delta: 0
- orders_delta: 0
- pnl_delta: 0.000000

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7000
- execution_quality: fragile
- evidence_status: ready
- route_stage_acceptance_decision: review
- route_stage_failed_stages: route_conversion_quality, close_out_quality, profitability_tail_risk
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, top3_loss_concentration_above_ceiling, pnl_per_notional_not_positive
- profit_focus: exit
- selection_quality_score: 1.0000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.5300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.0000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.1100
- tuning_priority: exit
