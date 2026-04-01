# Crypto Phase 2 Suite

- generated_at: 2026-04-01T14:42:35.199130+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.overnight.20260327.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-validate-overnight-20260401-224226\selection
- blocked_series_keys: none

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-validate-overnight-20260401-224226\replay-unfiltered
- signals_generated: 23
- submitted_orders: 23
- submitted_notional: 114.701961
- events_recorded: 2007
- today_pnl: -0.210340
- total_equity: 999.789660
- status: completed
- maker_fill_rate: 0.1304
- taker_fill_rate: 0.0000
- expiration_rate: 0.6522
- stop_out_rate: 1.0000
- average_trade_pnl: -0.052585
- average_signal_edge_bps: 554.1499
- average_adverse_fill_bps: 114.7825
- expected_edge_capture_bps: 439.3674
- edge_capture_ratio: 0.7929
- average_trade_expected_edge_bps: 556.7790
- average_trade_execution_drag_bps: 114.9675
- average_trade_realized_pnl_bps: -53.6745
- average_barrier_observed_gap_bps: 2060.4054
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 721.1419
- average_barrier_surface_disagreement_bps: 2060.4054
- closed_trade_net_pnl: -0.210340
- closed_trade_count: 4
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.052585
- average_submitted_notional: 4.987042
- large_notional_share: 0.0000
- dominant_exit_reason: time_stop
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 1.0000
- exit_family_balance_score: 0.6000
- small_bucket_pnl_per_notional: 0.000000
- medium_bucket_pnl_per_notional: -0.001834
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive
- top_loss_trades: [{"intent_id": "intent-00000023", "market_id": "701502", "net_pnl": -0.10299, "abs_loss": 0.10299, "signal_type": "exit", "execution_route": "taker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bullish", "signature": "exit|taker|default|sell_no", "closed_at": "2026-03-27T12:33:39+00:00"}, {"intent_id": "intent-00000014", "market_id": "1345531", "net_pnl": -0.10245, "abs_loss": 0.10245, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|maker|default|sell_no", "closed_at": "2026-03-26T23:00:41.393000+00:00"}, {"intent_id": "intent-00000008", "market_id": "1345531", "net_pnl": -0.00245, "abs_loss": 0.00245, "signal_type": "exit", "execution_route": "maker", "phase2_preset": "default", "side": "sell_no", "underlying_group_id": "crypto:btc", "thesis_group_id": "crypto:btc:bearish", "signature": "exit|maker|default|sell_no", "closed_at": "2026-03-26T22:20:02.775000+00:00"}]
- top_loss_market_breakdown: [{"market_id": "1345531", "total_abs_loss": 0.10735, "loss_count": 3}, {"market_id": "701502", "total_abs_loss": 0.10299, "loss_count": 1}]
- top_loss_signature_breakdown: [{"signature": "exit|maker|default|sell_no", "total_abs_loss": 0.10735, "loss_count": 3}, {"signature": "exit|taker|default|sell_no", "total_abs_loss": 0.10299, "loss_count": 1}]

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-validate-overnight-20260401-224226\replay-filtered
- signals_generated: 7
- submitted_orders: 7
- submitted_notional: 35.000000
- events_recorded: 2014
- today_pnl: 0.000000
- total_equity: 1000.000000
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 1.0000
- stop_out_rate: 0.0000
- average_trade_pnl: 0.000000
- average_signal_edge_bps: 0.0000
- average_adverse_fill_bps: 0.0000
- expected_edge_capture_bps: 0.0000
- edge_capture_ratio: 0.0000
- average_trade_expected_edge_bps: 0.0000
- average_trade_execution_drag_bps: 0.0000
- average_trade_realized_pnl_bps: 0.0000
- average_barrier_observed_gap_bps: 2060.4054
- average_surface_observed_gap_bps: 0.0000
- average_fusion_observed_gap_bps: 721.1419
- average_barrier_surface_disagreement_bps: 2060.4054
- closed_trade_net_pnl: 0.000000
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
- execution_feedback_bias: more_aggressive
- top_loss_trades: []
- top_loss_market_breakdown: []
- top_loss_signature_breakdown: []

## Delta

- signals_delta: -16
- orders_delta: -16
- pnl_delta: 0.210340

## Final Scorecard

- recommended_action: review
- readiness_score: 0.8500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, edge_capture_ratio_below_floor, pnl_per_notional_not_positive
- profit_focus: pricing
- selection_quality_score: 0.9000
- pricing_quality_score: 0.3100
- execution_quality_score: 0.8000
- exit_quality_score: 1.0000
- sizing_quality_score: 0.7700
- selection_loss: 0.1000
- pricing_loss: 0.6900
- execution_loss: 0.2000
- exit_loss: 0.0000
- sizing_loss: 0.2300
- total_profit_loss: 1.2200
- tuning_priority: pricing
