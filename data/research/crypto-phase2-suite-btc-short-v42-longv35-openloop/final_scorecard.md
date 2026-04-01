# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.9000
- execution_quality: stable
- evidence_status: ready
- filtered_orders: 3
- filtered_signals: 12
- filtered_pnl: -0.451561
- filtered_status: completed
- filter_order_delta: 0
- profit_focus: execution
- secondary_profit_focus: selection
- loss_ranking: execution, selection, pricing, sizing, exit
- blocked_series_keys: when-will-bitcoin-hit-150k

## BTC Promotion Gate

- promotion_decision: review
- promotion_stage_label: paper available
- promotion_min_closed_trades: 3
- promotion_min_edge_capture_ratio: 0.3500
- promotion_max_execution_loss_ratio: 0.6500
- promotion_min_pnl_per_notional: 0.000000
- observed_execution_loss_ratio: 0.2527
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive

## Profit Components

- selection_quality_score: 0.8000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.5300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- average_signal_edge_bps: 1036.1944
- average_adverse_fill_bps: 255.7007
- expected_edge_capture_bps: 780.4937
- edge_capture_ratio: 0.7532
- average_trade_expected_edge_bps: 954.8388
- average_trade_execution_drag_bps: 241.2978
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1862.3949
- average_surface_observed_gap_bps: 111.1667
- average_fusion_observed_gap_bps: 674.6581
- average_barrier_surface_disagreement_bps: 1850.9094
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 5.000000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- submitted_notional: 15.000000
- pnl_per_notional: 0.000000

## Profit Loss Decomposition

- selection_loss: 0.2000
- pricing_loss: 0.1200
- execution_loss: 0.4700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.8700

- tuning_priority: execution

## Tuning Actions

- lower taker_urgency_threshold for families that miss too many fills
- design the next variant to also address secondary loss in selection instead of retuning execution in isolation

## Reasons

- selection filter still blocks runtime ladder families
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: runtime still blocks ladder families
- pricing: barrier and surface models disagree too much
- execution: maker fill rate is weak versus expiration, moderate signal-to-order capture ratio, fills give up too much edge versus mid-price, trade-level execution drag remains too high
- exit: exit stable
- sizing: deployed notional is not producing positive net capture
