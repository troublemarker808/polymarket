# Crypto Phase 2 Final Scorecard

- recommended_action: review
- readiness_score: 0.7000
- execution_quality: fragile
- evidence_status: ready
- route_stage_acceptance_decision: review
- route_stage_failed_stages: route_conversion_quality, close_out_quality, profitability_tail_risk
- dominant_route_stage_blocker: route_adverse_fill_too_high
- next_constrained_action: reduce maker-expiry loops and stabilize route conversion before increasing activity.
- filtered_orders: 8
- filtered_signals: 8
- filtered_pnl: -0.281244
- filtered_status: completed
- filter_order_delta: 0
- profit_focus: exit
- secondary_profit_focus: execution
- loss_ranking: exit, execution, pricing, sizing, selection
- blocked_series_keys: none

## BTC Promotion Gate

- promotion_decision: review
- promotion_stage_label: paper available
- promotion_min_closed_trades: 3
- promotion_min_edge_capture_ratio: 0.3500
- promotion_max_execution_loss_ratio: 0.6500
- promotion_min_pnl_per_notional: 0.000000
- observed_execution_loss_ratio: 0.1149
- promotion_max_single_loss_pnl: -0.200000
- promotion_max_top3_loss_concentration_ratio: 0.7500
- observed_max_single_loss_pnl: -0.111802
- observed_top3_loss_concentration_ratio: 1.0000
- promotion_blocking_reasons: insufficient_closed_trade_count, top3_loss_concentration_above_ceiling, pnl_per_notional_not_positive

## Route Stage Gates

- scan_quality: pass
- scan_quality_blockers: none
- selection_pass_through: pass
- selection_pass_through_blockers: none
- route_conversion_quality: review
- route_conversion_quality_blockers: route_adverse_fill_too_high
- close_out_quality: review
- close_out_quality_blockers: close_out_insufficient_closed_trade_density, close_out_stop_out_pressure, close_out_negative_realized_pnl_bps, close_out_cleanup_dominance
- profitability_tail_risk: review
- profitability_tail_risk_blockers: profitability_non_positive_pnl_per_notional, tail_loss_top3_concentration_breach, tail_loss_top1_concentration_breach, tail_loss_market_concentration_breach, tail_loss_signature_concentration_breach

## Profit Components

- selection_quality_score: 1.0000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.5300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- average_signal_edge_bps: 1179.8918
- average_adverse_fill_bps: 134.2975
- expected_edge_capture_bps: 1045.5943
- edge_capture_ratio: 0.8862
- average_trade_expected_edge_bps: 1128.2750
- average_trade_execution_drag_bps: 129.6383
- average_trade_realized_pnl_bps: -106.8709
- average_barrier_observed_gap_bps: 3346.7983
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 1171.3794
- average_barrier_surface_disagreement_bps: 3346.7983
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.096622
- average_submitted_notional: 3.860666
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: -0.006257
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- submitted_notional: 30.885326
- pnl_per_notional: -0.006257

## Profit Loss Decomposition

- selection_loss: 0.0000
- pricing_loss: 0.4200
- execution_loss: 0.4700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.1100

- tuning_priority: exit

## Tuning Actions

- tighten aging/stale exit thresholds so weak positions recycle earlier
- lower max_holding_multiplier for presets with repeated negative closed trades
- design the next variant to also address secondary loss in execution instead of retuning exit in isolation
- keep execution-loss on watch even if another component is currently weaker

## Top Loss Attribution

- top_loss_trades: [{"intent_id": "intent-00000006", "market_id": "1339767", "net_pnl": -0.111802, "abs_loss": 0.111802, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T15:16:21.317000+00:00"}, {"intent_id": "intent-00000008", "market_id": "1339768", "net_pnl": -0.081443, "abs_loss": 0.081443, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "btc_dip_short_shadow", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|btc_dip_short_shadow|sell_no", "closed_at": "2026-03-27T15:17:21.627000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1339767", "total_abs_loss": 0.111802, "loss_count": 1}, {"market_id": "1339768", "total_abs_loss": 0.081443, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|taker|btc_dip_short_shadow|sell_no", "total_abs_loss": 0.193244, "loss_count": 2}]

## Reasons

- filtered replay pnl is negative
- route stage blocked: route_conversion_quality (route_adverse_fill_too_high)
- route stage blocked: close_out_quality (close_out_insufficient_closed_trade_density, close_out_stop_out_pressure, close_out_negative_realized_pnl_bps, close_out_cleanup_dominance)
- route stage blocked: profitability_tail_risk (profitability_non_positive_pnl_per_notional, tail_loss_top3_concentration_breach, tail_loss_top1_concentration_breach, tail_loss_market_concentration_breach, tail_loss_signature_concentration_breach)
- promotion gate blocked: insufficient_closed_trade_count
- promotion gate blocked: top3_loss_concentration_above_ceiling
- promotion gate blocked: pnl_per_notional_not_positive

## Component Reasons

- selection: selection stable
- pricing: negative filtered pnl, barrier and surface models disagree too much
- execution: maker fill rate is weak versus expiration, recent execution feedback prefers more passive routing, fills give up too much edge versus mid-price, trade-level execution drag remains too high
- exit: negative pnl per submitted order, closed trades are repeatedly stopping out, exits fail to convert enough positions into positive closes, losing exits are materially larger than winning exits, exit path is not preserving positive close quality, too many closes rely on aging or stale cleanup exits, trade-level realized pnl stays negative after execution and exit effects
- sizing: average closed-trade pnl is negative, deployed notional is not producing positive net capture
