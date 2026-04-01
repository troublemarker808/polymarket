# Crypto Phase 2 Suite

- generated_at: 2026-04-01T15:07:49.160076+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-preset-package-btc-20260401-230126\pricing_realization_gap_guard\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-preset-package-btc-20260401-230126\pricing_realization_gap_guard\replay-unfiltered
- signals_generated: 13
- submitted_orders: 13
- submitted_notional: 64.901961
- events_recorded: 2012
- today_pnl: -0.002500
- total_equity: 999.997500
- status: completed
- maker_fill_rate: 0.1538
- taker_fill_rate: 0.0000
- expiration_rate: 0.7692
- stop_out_rate: 1.0000
- average_trade_pnl: -0.002500
- average_signal_edge_bps: 1143.0512
- average_adverse_fill_bps: 50.0883
- expected_edge_capture_bps: 1092.9629
- edge_capture_ratio: 0.9562
- average_trade_expected_edge_bps: 1688.9672
- average_trade_execution_drag_bps: 34.6865
- average_trade_realized_pnl_bps: -1.6667
- average_barrier_observed_gap_bps: 1850.1336
- average_surface_observed_gap_bps: 110.8333
- average_fusion_observed_gap_bps: 669.9801
- average_barrier_surface_disagreement_bps: 1826.9948
- closed_trade_net_pnl: -0.002500
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.002500
- average_submitted_notional: 4.992459
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.000039
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.0025, "abs_loss": 0.0025, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:35:52.792000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "701502", "total_abs_loss": 0.0025, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.0025, "loss_count": 1}]

### filtered

- output_dir: data\research\crypto-phase2-preset-package-btc-20260401-230126\pricing_realization_gap_guard\replay-filtered
- signals_generated: 11
- submitted_orders: 11
- submitted_notional: 54.822596
- events_recorded: 2005
- today_pnl: -0.086825
- total_equity: 999.913175
- status: completed
- maker_fill_rate: 0.1818
- taker_fill_rate: 0.0000
- expiration_rate: 0.5455
- stop_out_rate: 1.0000
- average_trade_pnl: -0.043413
- average_signal_edge_bps: 928.1599
- average_adverse_fill_bps: 60.0138
- expected_edge_capture_bps: 868.1461
- edge_capture_ratio: 0.9353
- average_trade_expected_edge_bps: 909.0630
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
- top_loss_trades: [{"intent_id": "intent-00000009", "market_id": "1339768", "net_pnl": -0.084325, "abs_loss": 0.084325, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:40:27.835000+00:00"}, {"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.0025, "abs_loss": 0.0025, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:35:52.792000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339768", "total_abs_loss": 0.084325, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.0025, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.086825, "loss_count": 2}]

## Delta

- signals_delta: -2
- orders_delta: -2
- pnl_delta: -0.084325

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
- pricing_quality_score: 0.4300
- execution_quality_score: 0.4300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.5700
- execution_loss: 0.5700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.6600
- tuning_priority: exit
