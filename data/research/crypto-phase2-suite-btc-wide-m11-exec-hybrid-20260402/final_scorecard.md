# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.8000
- execution_quality: stable
- evidence_status: ready
- operator_verdict: review_required
- operator_summary: Primary blocker is maker expiry dominance; conversion loop remains unstable.
- route_stage_acceptance_decision: review
- route_stage_failed_stages: route_conversion_quality, close_out_quality, profitability_tail_risk
- dominant_route_stage_blocker: route_maker_expire_dominance
- next_constrained_action: reduce maker expiry loops via stricter repost/cooldown policy before expanding order flow.
- filtered_orders: 10
- filtered_signals: 11
- filtered_pnl: 0.000000
- filtered_status: completed
- filter_order_delta: 0
- profit_focus: pricing
- secondary_profit_focus: sizing
- loss_ranking: pricing, sizing, execution, exit, selection
- blocked_series_keys: none

## BTC Promotion Gate

- promotion_decision: review
- promotion_stage_label: paper available
- promotion_min_closed_trades: 3
- promotion_min_edge_capture_ratio: 0.3500
- promotion_max_execution_loss_ratio: 0.6500
- promotion_min_pnl_per_notional: 0.000000
- observed_execution_loss_ratio: 0.0000
- promotion_max_single_loss_pnl: -0.200000
- promotion_max_top3_loss_concentration_ratio: 0.7500
- observed_max_single_loss_pnl: 0.000000
- observed_top3_loss_concentration_ratio: 0.0000
- promotion_blocking_reasons: insufficient_closed_trade_count, edge_capture_ratio_below_floor, pnl_per_notional_not_positive

## Route Stage Gates

- scan_quality: pass
- scan_quality_blockers: none
- selection_pass_through: pass
- selection_pass_through_blockers: none
- route_conversion_quality: review
- route_conversion_quality_blockers: route_maker_expire_dominance
- close_out_quality: blocked
- close_out_quality_blockers: close_out_no_closed_trades
- profitability_tail_risk: review
- profitability_tail_risk_blockers: profitability_non_positive_pnl_per_notional

## Profit Components

- selection_quality_score: 1.0000
- pricing_quality_score: 0.3100
- execution_quality_score: 0.8000
- exit_quality_score: 1.0000
- sizing_quality_score: 0.7700
- average_signal_edge_bps: 0.0000
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 0.0000
- edge_capture_ratio: 0.0000
- average_trade_expected_edge_bps: 0.0000
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1069.0943
- average_surface_observed_gap_bps: 224.0625
- average_fusion_observed_gap_bps: 426.5412
- average_barrier_surface_disagreement_bps: 1047.5590
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 4.000000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- submitted_notional: 40.000000
- pnl_per_notional: 0.000000

## Profit Loss Decomposition

- selection_loss: 0.0000
- pricing_loss: 0.6900
- execution_loss: 0.2000
- exit_loss: 0.0000
- sizing_loss: 0.2300
- total_profit_loss: 1.1200

- tuning_priority: pricing

## Tuning Actions

- re-run phase1 calibration against the locked baseline before widening execution thresholds
- compare filtered versus unfiltered pnl by family to isolate mispriced ladders
- design the next variant to also address secondary loss in sizing instead of retuning pricing in isolation

## Top Loss Attribution

- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Reasons

- route stage blocked: route_conversion_quality (route_maker_expire_dominance)
- route stage blocked: close_out_quality (close_out_no_closed_trades)
- route stage blocked: profitability_tail_risk (profitability_non_positive_pnl_per_notional)
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: edge_capture_ratio_below_floor
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: selection stable
- pricing: flat filtered pnl, filled trades do not preserve positive modeled edge, captured edge is too small versus modeled edge, fused fair values remain far from observed pricing without enough realized capture, barrier and surface models disagree too much
- execution: maker quotes expire before filling
- exit: exit stable
- sizing: captured pnl per order is too small, deployed notional is not producing positive net capture
