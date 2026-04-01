# Crypto Phase 2 Auto Experiments

- experiment_family: exit
- winner: baseline
- winner_reason: baseline remains the strongest current preset
- promotion_decision: keep_baseline
- promotion_target: baseline
- promotion_reason: baseline remains the strongest current working preset

## Baseline

- readiness_score: 0.7500
- total_profit_loss: 2.4100
- filtered_pnl: -0.086825
- recommended_action: review
- average_loss_trade_pnl: -0.043413
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 54.8119
- average_trade_realized_pnl_bps: -35.2913
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 2
- targeted_loss_improvement: 0.0000

## Candidates

### exit_faster_recycle

- focus: exit
- secondary_focus: execution
- loss_ranking: exit, execution, pricing, selection, sizing
- readiness_score: 0.7500
- total_profit_loss: 2.4100
- filtered_pnl: -0.187316
- recommended_action: review
- tuning_priority: exit
- average_loss_trade_pnl: -0.093658
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 118.7599
- average_trade_realized_pnl_bps: -95.4154
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 2
- targeted_loss_improvement: 0.0000
- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_faster_recycle

### exit_tighter_stale_cleanup

- focus: exit
- secondary_focus: execution
- loss_ranking: exit, execution, pricing, selection, sizing
- readiness_score: 0.7500
- total_profit_loss: 2.4100
- filtered_pnl: -0.086825
- recommended_action: review
- tuning_priority: exit
- average_loss_trade_pnl: -0.043413
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 54.8119
- average_trade_realized_pnl_bps: -35.2913
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 2
- targeted_loss_improvement: 0.0000
- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_tighter_stale_cleanup

### exit_execution_recycle

- focus: exit+execution
- secondary_focus: execution
- loss_ranking: exit, execution, pricing, selection, sizing
- readiness_score: 0.7500
- total_profit_loss: 2.4100
- filtered_pnl: -0.187316
- recommended_action: review
- tuning_priority: exit
- average_loss_trade_pnl: -0.093658
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 118.7599
- average_trade_realized_pnl_bps: -95.4154
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 2
- targeted_loss_improvement: 0.0000
- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_execution_recycle

### exit_loss_asymmetry_guard

- focus: exit
- secondary_focus: execution
- loss_ranking: exit, execution, pricing, selection, sizing
- readiness_score: 0.7500
- total_profit_loss: 2.4100
- filtered_pnl: -0.187316
- recommended_action: review
- tuning_priority: exit
- average_loss_trade_pnl: -0.093658
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 118.7599
- average_trade_realized_pnl_bps: -95.4154
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 2
- targeted_loss_improvement: 0.0000
- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_loss_asymmetry_guard

### exit_passive_cleanup_guard

- focus: exit
- secondary_focus: execution
- loss_ranking: exit, execution, pricing, selection, sizing
- readiness_score: 0.7500
- total_profit_loss: 2.4100
- filtered_pnl: -0.086825
- recommended_action: review
- tuning_priority: exit
- average_loss_trade_pnl: -0.043413
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 54.8119
- average_trade_realized_pnl_bps: -35.2913
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 2
- targeted_loss_improvement: 0.0000
- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_passive_cleanup_guard

### exit_smaller_clip_guard

- focus: exit
- secondary_focus: pricing
- loss_ranking: exit, pricing, execution, sizing, selection
- readiness_score: 0.8000
- total_profit_loss: 2.4600
- filtered_pnl: -0.073802
- recommended_action: review
- tuning_priority: exit
- average_loss_trade_pnl: -0.036901
- large_notional_share: 0.0000
- average_trade_execution_drag_bps: 54.8119
- average_trade_realized_pnl_bps: -35.2913
- exit_family_balance_score: 0.6000
- large_bucket_pnl_per_notional: 0.000000
- target_alignment_score: 1
- targeted_loss_improvement: -0.0685
- output_dir: data\research\crypto-phase2-autoexp-btc-exit-20260401-223419\exit_smaller_clip_guard
