# Crypto Phase 2 Suite

- generated_at: 2026-04-01T20:55:41.467254+00:00
- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_wide_window_v1.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-rootfix-20260402-r2\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-rootfix-20260402-r2\replay-unfiltered
- signals_generated: 9
- submitted_orders: 9
- submitted_notional: 32.300000
- events_recorded: 64
- today_pnl: -0.102150
- total_equity: 24.897850
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.7778
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1210.0942
- average_adverse_fill_bps: 125.9880
- expected_edge_capture_bps: 1084.1061
- edge_capture_ratio: 0.8959
- average_trade_expected_edge_bps: 1210.0942
- average_trade_execution_drag_bps: 125.9880
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1069.0943
- average_surface_observed_gap_bps: 224.0625
- average_fusion_observed_gap_bps: 426.5412
- average_barrier_surface_disagreement_bps: 1047.5590
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 3.588889
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_aggressive
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-rootfix-20260402-r2\replay-filtered
- signals_generated: 9
- submitted_orders: 9
- submitted_notional: 32.300000
- events_recorded: 64
- today_pnl: -0.102150
- total_equity: 24.897850
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.7778
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 1210.0942
- average_adverse_fill_bps: 125.9880
- expected_edge_capture_bps: 1084.1061
- edge_capture_ratio: 0.8959
- average_trade_expected_edge_bps: 1210.0942
- average_trade_execution_drag_bps: 125.9880
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 1069.0943
- average_surface_observed_gap_bps: 224.0625
- average_fusion_observed_gap_bps: 426.5412
- average_barrier_surface_disagreement_bps: 1047.5590
- closed_trade_net_pnl: 0.000000
- closed_trade_count: 0
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: 0.000000
- average_submitted_notional: 3.588889
- large_notional_share: 0.0000
- dominant_exit_reason: none
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.0000
- exit_family_balance_score: 0.0000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_aggressive
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Delta

- signals_delta: 0
- orders_delta: 0
- pnl_delta: 0.000000

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8000
- execution_quality: stable
- evidence_status: ready
- route_stage_acceptance_decision: review
- route_stage_failed_stages: route_conversion_quality, close_out_quality, profitability_tail_risk
- dominant_route_stage_blocker: route_adverse_fill_too_high
- next_constrained_action: reduce taker adverse-fill drag first by tightening premium caps and fallback taker escalation rules.
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: execution
- selection_quality_score: 1.0000
- pricing_quality_score: 0.8800
- execution_quality_score: 0.5300
- exit_quality_score: 1.0000
- sizing_quality_score: 0.9200
- selection_loss: 0.0000
- pricing_loss: 0.1200
- execution_loss: 0.4700
- exit_loss: 0.0000
- sizing_loss: 0.0800
- total_profit_loss: 0.6700
- tuning_priority: execution
