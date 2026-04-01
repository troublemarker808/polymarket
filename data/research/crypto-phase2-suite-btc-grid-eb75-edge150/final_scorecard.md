# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- filtered_orders: 2
- filtered_signals: 2
- filtered_pnl: -0.171212
- filtered_status: completed
- filter_order_delta: -2
- profit_focus: exit
- secondary_profit_focus: pricing
- loss_ranking: exit, pricing, execution, sizing, selection
- blocked_series_keys: none

## BTC Promotion Gate

- promotion_decision: review
- promotion_stage_label: paper available
- promotion_min_closed_trades: 3
- promotion_min_edge_capture_ratio: 0.3500
- promotion_max_execution_loss_ratio: 0.6500
- promotion_min_pnl_per_notional: 0.000000
- observed_execution_loss_ratio: 0.5129
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive

## Profit Components

- selection_quality_score: 0.9000
- pricing_quality_score: 0.3300
- execution_quality_score: 0.6300
- exit_quality_score: 0.0900
- sizing_quality_score: 0.6500
- average_signal_edge_bps: 338.9243
- average_adverse_fill_bps: 173.8462
- expected_edge_capture_bps: 165.0781
- edge_capture_ratio: 0.4871
- average_trade_expected_edge_bps: 338.9243
- average_trade_execution_drag_bps: 173.8462
- average_trade_realized_pnl_bps: -176.9163
- average_barrier_observed_gap_bps: 539.6441
- average_surface_observed_gap_bps: 208.4375
- average_fusion_observed_gap_bps: 231.6627
- average_barrier_surface_disagreement_bps: 518.1088
- closed_trade_count: 1
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.171212
- average_submitted_notional: 4.924242
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 1.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.017385
- large_bucket_pnl_per_notional: 0.000000
- submitted_notional: 9.848485
- pnl_per_notional: -0.017385

## Profit Loss Decomposition

- selection_loss: 0.1000
- pricing_loss: 0.6700
- execution_loss: 0.3700
- exit_loss: 0.9100
- sizing_loss: 0.3500
- total_profit_loss: 2.4000

- tuning_priority: exit

## Tuning Actions

- tighten aging/stale exit thresholds so weak positions recycle earlier
- lower max_holding_multiplier for presets with repeated negative closed trades
- design the next variant to also address secondary loss in pricing instead of retuning exit in isolation
- keep execution-loss on watch even if another component is currently weaker

## Reasons

- filtered replay pnl is negative
- selection filter removed more orders than it stabilized
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: filter removes more orders than it preserves
- pricing: negative filtered pnl, selection currently loses pnl versus unfiltered replay, modeled edge decays before it becomes realized pnl, barrier and surface models disagree too much
- execution: recent execution feedback prefers more passive routing, fills give up too much edge versus mid-price, trade-level execution drag remains too high
- exit: negative pnl per submitted order, closed trades are repeatedly stopping out, exits fail to convert enough positions into positive closes, losing exits are materially larger than winning exits, exit path is not preserving positive close quality, trade-level realized pnl stays negative after execution and exit effects
- sizing: average closed-trade pnl is negative, sizing loses too much pnl per unit of deployed notional, medium notional bucket underperforms small clips
