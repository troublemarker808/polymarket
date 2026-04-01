# Crypto Phase 2 Suite

- generated_at: 2026-04-01T20:10:19.848689+00:00
- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_wide_window_v1.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-wide-m16-finalsweep-passiveexit-20260402\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-wide-m16-finalsweep-passiveexit-20260402\replay-unfiltered
- signals_generated: 17
- submitted_orders: 17
- submitted_notional: 45.500000
- events_recorded: 87
- today_pnl: -0.492500
- total_equity: 24.507500
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4118
- stop_out_rate: 1.0000
- average_trade_pnl: -0.083700
- average_signal_edge_bps: 1290.8333
- average_adverse_fill_bps: 200.5091
- expected_edge_capture_bps: 1090.3241
- edge_capture_ratio: 0.8447
- average_trade_expected_edge_bps: 1290.8333
- average_trade_execution_drag_bps: 200.5091
- average_trade_realized_pnl_bps: -180.1715
- average_barrier_observed_gap_bps: 1069.0943
- average_surface_observed_gap_bps: 224.0625
- average_fusion_observed_gap_bps: 426.5412
- average_barrier_surface_disagreement_bps: 1047.5590
- closed_trade_net_pnl: -0.334800
- closed_trade_count: 4
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.083700
- average_submitted_notional: 2.676471
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.007358
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000016", "market_id": "1345531", "net_pnl": -0.1108, "abs_loss": 0.1108, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|maker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-28T12:29:59.672000+00:00"}, {"intent_id": "intent-00000015", "market_id": "1345530", "net_pnl": -0.107, "abs_loss": 0.107, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|maker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-28T12:29:59.672000+00:00"}, {"intent_id": "intent-00000014", "market_id": "701502", "net_pnl": -0.0599, "abs_loss": 0.0599, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|maker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-28T12:29:54.672000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1345531", "total_abs_loss": 0.1108, "loss_count": 1}, {"market_id": "1345530", "total_abs_loss": 0.107, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.0599, "loss_count": 1}, {"market_id": "1339767", "total_abs_loss": 0.0571, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|maker|btc_reach_short_shadow|sell_no", "total_abs_loss": 0.2178, "loss_count": 2}, {"signature": "exit|maker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.117, "loss_count": 2}]

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-wide-m16-finalsweep-passiveexit-20260402\replay-filtered
- signals_generated: 17
- submitted_orders: 17
- submitted_notional: 45.500000
- events_recorded: 87
- today_pnl: -0.492500
- total_equity: 24.507500
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4118
- stop_out_rate: 1.0000
- average_trade_pnl: -0.083700
- average_signal_edge_bps: 1290.8333
- average_adverse_fill_bps: 200.5091
- expected_edge_capture_bps: 1090.3241
- edge_capture_ratio: 0.8447
- average_trade_expected_edge_bps: 1290.8333
- average_trade_execution_drag_bps: 200.5091
- average_trade_realized_pnl_bps: -180.1715
- average_barrier_observed_gap_bps: 1069.0943
- average_surface_observed_gap_bps: 224.0625
- average_fusion_observed_gap_bps: 426.5412
- average_barrier_surface_disagreement_bps: 1047.5590
- closed_trade_net_pnl: -0.334800
- closed_trade_count: 4
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.083700
- average_submitted_notional: 2.676471
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.007358
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000016", "market_id": "1345531", "net_pnl": -0.1108, "abs_loss": 0.1108, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|maker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-28T12:29:59.672000+00:00"}, {"intent_id": "intent-00000015", "market_id": "1345530", "net_pnl": -0.107, "abs_loss": 0.107, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "btc_reach_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|maker|btc_reach_short_shadow|sell_no", "closed_at": "2026-03-28T12:29:59.672000+00:00"}, {"intent_id": "intent-00000014", "market_id": "701502", "net_pnl": -0.0599, "abs_loss": 0.0599, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|maker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-28T12:29:54.672000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1345531", "total_abs_loss": 0.1108, "loss_count": 1}, {"market_id": "1345530", "total_abs_loss": 0.107, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.0599, "loss_count": 1}, {"market_id": "1339767", "total_abs_loss": 0.0571, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|maker|btc_reach_short_shadow|sell_no", "total_abs_loss": 0.2178, "loss_count": 2}, {"signature": "exit|maker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.117, "loss_count": 2}]

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
- dominant_route_stage_blocker: route_adverse_fill_too_high
- next_constrained_action: reduce taker adverse-fill drag first by tightening premium caps and fallback taker escalation rules.
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: top3_loss_concentration_above_ceiling, pnl_per_notional_not_positive
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
