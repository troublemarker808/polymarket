# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.8000
- execution_quality: stable
- evidence_status: ready
- operator_verdict: review_required
- operator_summary: Primary blocker is adverse fill; execution conversion still loses too much edge.
- route_stage_acceptance_decision: review
- route_stage_failed_stages: route_conversion_quality, close_out_quality, profitability_tail_risk
- dominant_route_stage_blocker: route_adverse_fill_too_high
- next_constrained_action: reduce taker adverse-fill drag first by tightening premium caps and fallback taker escalation rules.
- filtered_orders: 2
- filtered_signals: 2
- filtered_pnl: -0.160400
- filtered_status: completed
- filter_order_delta: 0
- profit_focus: execution
- secondary_profit_focus: pricing
- loss_ranking: execution, pricing, sizing, exit, selection
- blocked_series_keys: none

## BTC Promotion Gate

- promotion_decision: review
- promotion_stage_label: paper available
- promotion_min_closed_trades: 3
- promotion_min_edge_capture_ratio: 0.3500
- promotion_max_execution_loss_ratio: 0.6500
- promotion_min_pnl_per_notional: 0.000000
- observed_execution_loss_ratio: 0.1035
- promotion_max_single_loss_pnl: -0.200000
- promotion_max_top3_loss_concentration_ratio: 0.7500
- observed_max_single_loss_pnl: 0.000000
- observed_top3_loss_concentration_ratio: 0.0000
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive

## Route Stage Gates

- scan_quality: pass
- scan_quality_blockers: none
- selection_pass_through: pass
- selection_pass_through_blockers: none
- route_conversion_quality: review
- route_conversion_quality_blockers: route_adverse_fill_too_high
- close_out_quality: blocked
- close_out_quality_blockers: close_out_no_closed_trades
- profitability_tail_risk: review
- profitability_tail_risk_blockers: profitability_non_positive_pnl_per_notional

## Profit Components

- selection_quality_score: 1.0000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.7300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- average_signal_edge_bps: 1934.2505
- average_adverse_fill_bps: 200.2540
- expected_edge_capture_bps: 1733.9965
- edge_capture_ratio: 0.8965
- average_trade_expected_edge_bps: 1934.2505
- average_trade_execution_drag_bps: 200.2540
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 676.7261
- average_surface_observed_gap_bps: 421.4286
- average_fusion_observed_gap_bps: 322.0822
- average_barrier_surface_disagreement_bps: 637.5026
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 2.600000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- submitted_notional: 5.200000
- pnl_per_notional: 0.000000

## Profit Loss Decomposition

- selection_loss: 0.0000
- pricing_loss: 0.1200
- execution_loss: 0.2700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.4700

- tuning_priority: execution

## Tuning Actions

- lower taker_urgency_threshold for families that miss too many fills

## Top Loss Attribution

- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Reasons

- route stage blocked: route_conversion_quality (route_adverse_fill_too_high)
- route stage blocked: close_out_quality (close_out_no_closed_trades)
- route stage blocked: profitability_tail_risk (profitability_non_positive_pnl_per_notional)
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: selection stable
- pricing: barrier and surface models disagree too much
- execution: fills give up too much edge versus mid-price, trade-level execution drag remains too high
- exit: exit stable
- sizing: deployed notional is not producing positive net capture
