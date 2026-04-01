# Crypto Phase 2 Suite

- generated_at: 2026-04-01T19:58:20.064627+00:00
- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_wide_window_v1_desc.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-wide-m8-desc-20260402\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-wide-m8-desc-20260402\replay-unfiltered
- signals_generated: 3
- submitted_orders: 3
- submitted_notional: 6.600000
- events_recorded: 24
- today_pnl: -0.279867
- total_equity: 24.720133
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1463.3701
- average_adverse_fill_bps: 337.7761
- expected_edge_capture_bps: 1125.5940
- edge_capture_ratio: 0.7692
- average_trade_expected_edge_bps: 1642.7531
- average_trade_execution_drag_bps: 285.3867
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 676.7261
- average_surface_observed_gap_bps: 421.4286
- average_fusion_observed_gap_bps: 322.0822
- average_barrier_surface_disagreement_bps: 637.5026
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 2.200000
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: stable
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-wide-m8-desc-20260402\replay-filtered
- signals_generated: 2
- submitted_orders: 2
- submitted_notional: 5.200000
- events_recorded: 51
- today_pnl: -0.160400
- total_equity: 24.839600
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
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
- closed_trade_net_pnl: 0.000000
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
- execution_feedback_bias: stable
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Delta

- signals_delta: -1
- orders_delta: -1
- pnl_delta: 0.119467

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- route_stage_acceptance_decision: review
- route_stage_failed_stages: selection_pass_through, route_conversion_quality, close_out_quality, profitability_tail_risk
- dominant_route_stage_blocker: route_adverse_fill_too_high
- next_constrained_action: reduce taker adverse-fill drag first by tightening premium caps and fallback taker escalation rules.
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: execution
- selection_quality_score: 0.9000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.7300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- selection_loss: 0.1000
- pricing_loss: 0.1200
- execution_loss: 0.2700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.5700
- tuning_priority: execution
