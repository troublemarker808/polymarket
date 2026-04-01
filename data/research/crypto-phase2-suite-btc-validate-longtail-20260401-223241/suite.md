# Crypto Phase 2 Suite

- generated_at: 2026-04-01T14:33:48.442792+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-validate-longtail-20260401-223241\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-validate-longtail-20260401-223241\replay-unfiltered
- signals_generated: 11
- submitted_orders: 11
- submitted_notional: 54.822596
- events_recorded: 2009
- today_pnl: -0.086825
- total_equity: 999.913175
- status: completed
- maker_fill_rate: 0.0909
- taker_fill_rate: 0.0000
- expiration_rate: 0.6364
- stop_out_rate: 1.0000
- average_trade_pnl: -0.043413
- average_signal_edge_bps: 934.2375
- average_adverse_fill_bps: 66.7796
- expected_edge_capture_bps: 867.4579
- edge_capture_ratio: 0.9285
- average_trade_expected_edge_bps: 917.7669
- average_trade_execution_drag_bps: 68.5149
- average_trade_realized_pnl_bps: -44.1142
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.086825
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.043413
- average_submitted_notional: 4.983872
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.001584
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000007", "market_id": "1339768", "net_pnl": -0.084325, "abs_loss": 0.084325, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:38:52.830000+00:00"}, {"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.0025, "abs_loss": 0.0025, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:35:52.792000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339768", "total_abs_loss": 0.084325, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.0025, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.086825, "loss_count": 2}]

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-validate-longtail-20260401-223241\replay-filtered
- signals_generated: 10
- submitted_orders: 9
- submitted_notional: 44.822596
- events_recorded: 2005
- today_pnl: -0.086825
- total_equity: 999.913175
- status: completed
- maker_fill_rate: 0.2222
- taker_fill_rate: 0.0000
- expiration_rate: 0.5556
- stop_out_rate: 1.0000
- average_trade_pnl: -0.043413
- average_signal_edge_bps: 928.1592
- average_adverse_fill_bps: 60.0138
- expected_edge_capture_bps: 868.1454
- edge_capture_ratio: 0.9353
- average_trade_expected_edge_bps: 909.0622
- average_trade_execution_drag_bps: 54.8119
- average_trade_realized_pnl_bps: -35.2913
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.086825
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.043413
- average_submitted_notional: 4.980288
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.001937
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000006", "market_id": "1339768", "net_pnl": -0.084325, "abs_loss": 0.084325, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:38:52.830000+00:00"}, {"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.0025, "abs_loss": 0.0025, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:35:52.792000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339768", "total_abs_loss": 0.084325, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.0025, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.086825, "loss_count": 2}]

## Delta

- signals_delta: -1
- orders_delta: -2
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
