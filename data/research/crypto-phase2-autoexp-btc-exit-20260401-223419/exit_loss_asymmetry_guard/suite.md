# Crypto Phase 2 Suite

- generated_at: 2026-04-01T14:39:42.101063+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_loss_asymmetry_guard\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_loss_asymmetry_guard\replay-unfiltered
- signals_generated: 9
- submitted_orders: 9
- submitted_notional: 44.822596
- events_recorded: 1987
- today_pnl: -0.187316
- total_equity: 999.812684
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.4444
- stop_out_rate: 1.0000
- average_trade_pnl: -0.093658
- average_signal_edge_bps: 943.2180
- average_adverse_fill_bps: 122.3136
- expected_edge_capture_bps: 820.9044
- edge_capture_ratio: 0.8703
- average_trade_expected_edge_bps: 925.8921
- average_trade_execution_drag_bps: 118.7599
- average_trade_realized_pnl_bps: -95.4154
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.187316
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.093658
- average_submitted_notional: 4.980288
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.004179
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.10299, "abs_loss": 0.10299, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:36:27.389000+00:00"}, {"intent_id": "intent-00000006", "market_id": "1339768", "net_pnl": -0.084325, "abs_loss": 0.084325, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:39:25+00:00"}]
- top_loss_market_breakdown: [{"market_id": "701502", "total_abs_loss": 0.10299, "loss_count": 1}, {"market_id": "1339768", "total_abs_loss": 0.084325, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.187316, "loss_count": 2}]

### filtered

- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_loss_asymmetry_guard\replay-filtered
- signals_generated: 8
- submitted_orders: 8
- submitted_notional: 39.822596
- events_recorded: 1981
- today_pnl: -0.187316
- total_equity: 999.812684
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.3750
- stop_out_rate: 1.0000
- average_trade_pnl: -0.093658
- average_signal_edge_bps: 943.2175
- average_adverse_fill_bps: 122.3136
- expected_edge_capture_bps: 820.9039
- edge_capture_ratio: 0.8703
- average_trade_expected_edge_bps: 925.8916
- average_trade_execution_drag_bps: 118.7599
- average_trade_realized_pnl_bps: -95.4154
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.187316
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.093658
- average_submitted_notional: 4.977824
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.004704
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.10299, "abs_loss": 0.10299, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:36:27.389000+00:00"}, {"intent_id": "intent-00000004", "market_id": "1339768", "net_pnl": -0.084325, "abs_loss": 0.084325, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:38:05.226000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "701502", "total_abs_loss": 0.10299, "loss_count": 1}, {"market_id": "1339768", "total_abs_loss": 0.084325, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.187316, "loss_count": 2}]

## Delta

- signals_delta: -1
- orders_delta: -1
- pnl_delta: 0.000000

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
- execution_quality_score: 0.5300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.4100
- tuning_priority: exit
