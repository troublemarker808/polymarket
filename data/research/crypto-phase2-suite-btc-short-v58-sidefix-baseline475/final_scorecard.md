# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- filtered_orders: 8
- filtered_signals: 8
- filtered_pnl: -0.561013
- filtered_status: completed
- filter_order_delta: -8
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
- observed_execution_loss_ratio: 0.3055
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive

## Profit Components

- selection_quality_score: 0.7000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.5300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.7700
- average_signal_edge_bps: 604.7461
- average_adverse_fill_bps: 194.0373
- expected_edge_capture_bps: 410.7089
- edge_capture_ratio: 0.6791
- average_trade_expected_edge_bps: 601.8203
- average_trade_execution_drag_bps: 183.8783
- average_trade_realized_pnl_bps: -70.7665
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.136970
- average_submitted_notional: 3.984848
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: -0.004297
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- submitted_notional: 31.878788
- pnl_per_notional: -0.004297

## Profit Loss Decomposition

- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9100
- sizing_loss: 0.2300
- total_profit_loss: 2.3300

- tuning_priority: exit

## Tuning Actions

- tighten aging/stale exit thresholds so weak positions recycle earlier
- lower max_holding_multiplier for presets with repeated negative closed trades
- design the next variant to also address secondary loss in execution instead of retuning exit in isolation
- keep execution-loss on watch even if another component is currently weaker

## Reasons

- filtered replay pnl is negative
- selection filter removed more orders than it stabilized
- selection filter still blocks runtime ladder families
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: runtime still blocks ladder families, filter removes more orders than it preserves
- pricing: negative filtered pnl, barrier and surface models disagree too much
- execution: maker fill rate is weak versus expiration, recent execution feedback prefers more passive routing, fills give up too much edge versus mid-price, trade-level execution drag remains too high
- exit: negative pnl per submitted order, closed trades are repeatedly stopping out, exits fail to convert enough positions into positive closes, losing exits are materially larger than winning exits, exit path is not preserving positive close quality, trade-level realized pnl stays negative after execution and exit effects
- sizing: average closed-trade pnl is negative, deployed notional is not producing positive net capture
