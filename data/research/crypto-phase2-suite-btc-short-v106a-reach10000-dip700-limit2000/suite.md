# Crypto Phase 2 Suite

- generated_at: 2026-04-01T10:09:50.532513+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- selection_output_dir: data\research\crypto-phase2-suite-btc-short-v106a-reach10000-dip700-limit2000\selection
- blocked_series_keys: when-will-bitcoin-hit-150k

## Replays

### unfiltered

- output_dir: data\research\crypto-phase2-suite-btc-short-v106a-reach10000-dip700-limit2000\replay-unfiltered
- signals_generated: 23
- submitted_orders: 20
- submitted_notional: 79.823993
- events_recorded: 1881
- today_pnl: -0.709825
- total_equity: 24.290175
- status: completed
- maker_fill_rate: 0.0500
- taker_fill_rate: 0.0000
- expiration_rate: 0.5500
- stop_out_rate: 1.0000
- average_trade_pnl: -0.103827
- average_signal_edge_bps: 852.9871
- average_adverse_fill_bps: 188.5156
- expected_edge_capture_bps: 664.4715
- edge_capture_ratio: 0.7790
- average_trade_expected_edge_bps: 1014.7585
- average_trade_execution_drag_bps: 153.0862
- average_trade_realized_pnl_bps: -66.6698
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.207655
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.103827
- average_submitted_notional: 3.991200
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.002601
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

### filtered

- output_dir: data\research\crypto-phase2-suite-btc-short-v106a-reach10000-dip700-limit2000\replay-filtered
- signals_generated: 15
- submitted_orders: 15
- submitted_notional: 59.823993
- events_recorded: 1994
- today_pnl: -0.279147
- total_equity: 24.720853
- status: completed
- maker_fill_rate: 0.0000
- taker_fill_rate: 0.0000
- expiration_rate: 0.6000
- stop_out_rate: 1.0000
- average_trade_pnl: -0.103827
- average_signal_edge_bps: 434.4168
- average_adverse_fill_bps: 140.1992
- expected_edge_capture_bps: 294.2176
- edge_capture_ratio: 0.6773
- average_trade_expected_edge_bps: 472.9584
- average_trade_execution_drag_bps: 125.1567
- average_trade_realized_pnl_bps: -106.6717
- average_barrier_observed_gap_bps: 1845.7977
- average_surface_observed_gap_bps: 112.5000
- average_fusion_observed_gap_bps: 668.4625
- average_barrier_surface_disagreement_bps: 1822.6589
- closed_trade_net_pnl: -0.207655
- closed_trade_count: 2
- winning_trade_rate: 0.0000
- average_win_trade_pnl: 0.000000
- average_loss_trade_pnl: -0.103827
- average_submitted_notional: 3.988266
- large_notional_share: 0.0000
- dominant_exit_reason: adverse_fill_reversal
- stop_loss_exit_share: 0.0000
- passive_cleanup_exit_share: 0.5000
- exit_family_balance_score: 0.8000
- small_bucket_pnl_per_notional: -0.003471
- medium_bucket_pnl_per_notional: 0.000000
- large_bucket_pnl_per_notional: 0.000000
- execution_feedback_bias: more_passive

## Delta

- signals_delta: -8
- orders_delta: -5
- pnl_delta: 0.430678

## Final Scorecard

- recommended_action: review
- readiness_score: 0.7500
- execution_quality: fragile
- evidence_status: ready
- promotion_decision: review
- promotion_stage_label: paper available
- promotion_blocking_reasons: insufficient_closed_trade_count, pnl_per_notional_not_positive
- profit_focus: exit
- selection_quality_score: 0.7000
- pricing_quality_score: 0.5800
- execution_quality_score: 0.4300
- exit_quality_score: 0.0100
- sizing_quality_score: 0.7700
- selection_loss: 0.3000
- pricing_loss: 0.4200
- execution_loss: 0.5700
- exit_loss: 0.9900
- sizing_loss: 0.2300
- total_profit_loss: 2.5100
- tuning_priority: exit
