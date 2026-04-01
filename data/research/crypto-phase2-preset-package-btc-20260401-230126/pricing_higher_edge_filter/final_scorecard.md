# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- filtered_orders: 9
- filtered_signals: 10
- filtered_pnl: -0.086825
- filtered_status: completed
- filter_order_delta: -2
- profit_focus: exit
- secondary_profit_focus: execution
- loss_ranking: exit, execution, pricing, selection, sizing
- blocked_series_keys: when-will-bitcoin-hit-150k

## BTC Promotion Gate

- promotion_decision: review
- promotion_stage_label: paper available
- promotion_min_closed_trades: 3
- promotion_min_edge_capture_ratio: 0.3500
- promotion_max_execution_loss_ratio: 0.6500
- promotion_min_pnl_per_notional: 0.000000
- observed_execution_loss_ratio: 0.0603
- promotion_max_single_loss_pnl: -0.200000
- promotion_max_top3_loss_concentration_ratio: 0.7500
- observed_max_single_loss_pnl: -0.084325
- observed_top3_loss_concentration_ratio: 1.0000
- promotion_blocking_reasons: insufficient_closed_trade_count, top3_loss_concentration_above_ceiling, pnl_per_notional_not_positive

## Profit Components

- selection_quality_score: 0.7000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.5300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
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
- submitted_notional: 44.822596
- pnl_per_notional: -0.001937

## Profit Loss Decomposition

- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.4100

- tuning_priority: exit

## Tuning Actions

- tighten aging/stale exit thresholds so weak positions recycle earlier
- lower max_holding_multiplier for presets with repeated negative closed trades
- design the next variant to also address secondary loss in execution instead of retuning exit in isolation
- keep execution-loss on watch even if another component is currently weaker

## Top Loss Attribution

- top_loss_trades: [{"intent_id": "intent-00000006", "market_id": "1339768", "net_pnl": -0.084325, "abs_loss": 0.084325, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:38:52.830000+00:00"}, {"intent_id": "intent-00000002", "market_id": "701502", "net_pnl": -0.0025, "abs_loss": 0.0025, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:35:52.792000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339768", "total_abs_loss": 0.084325, "loss_count": 1}, {"market_id": "701502", "total_abs_loss": 0.0025, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.086825, "loss_count": 2}]

## Reasons

- filtered replay pnl is negative
- selection filter removed more orders than it stabilized
- selection filter still blocks runtime ladder families
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: top3_loss_concentration_above_ceiling
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: runtime still blocks ladder families, filter removes more orders than it preserves
- pricing: negative filtered pnl, barrier and surface models disagree too much
- execution: maker fill rate is weak versus expiration, recent execution feedback prefers more passive routing, fills give up too much edge versus mid-price, trade-level execution drag remains too high
- exit: negative pnl per submitted order, closed trades are repeatedly stopping out, exits fail to convert enough positions into positive closes, losing exits are materially larger than winning exits, exit path is not preserving positive close quality, too many closes rely on aging or stale cleanup exits, trade-level realized pnl stays negative after execution and exit effects
- sizing: average closed-trade pnl is negative, deployed notional is not producing positive net capture
