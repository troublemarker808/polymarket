# Autoresearch Report

- generated_at: 2026-03-28T10:24:31.624220+00:00
- classification: capacity-bound
- score: 0.0000
- metrics_path: data\research\fixed-window-phase2-eth-v32\train\baseline.metrics.json
- event_path: data\research\fixed-window-phase2-eth-v32\train\baseline.events.jsonl
- state_path: 

## Objective

- Increase useful submissions and fills per fixed safety budget by reducing low-value signal generation before daily limits and concurrency gates saturate.

## Baseline

- signals_generated: 0
- orders_submitted: 0
- orders_rejected: 0
- orders_filled: 0
- orders_partially_filled: 0
- orders_expired: 0
- trades_closed: 0
- fill_rate: 0.0000
- cancel_rate: 0.0000
- avg_fill_price_vs_mid_bps: 0.00
- capacity_bound_rejection_ratio: 0.0000
- closed_trade_net_pnl: 0.000000

## Dominant Rejection Reasons

- none

## Fill Sources

- none

## Locked Parameters

- polymarket.allow_live_orders
- trading.live_allowed_categories
- trading.max_notional_per_market
- trading.max_notional_per_category
- trading.max_concurrent_positions
- trading.max_positions_per_market
- trading.daily_order_soft_limit
- trading.daily_order_hard_limit
- risk.max_daily_drawdown_pct
- risk.max_consecutive_losses
- risk.max_open_orders
- risk.kill_switch_on_stale_data_seconds
- risk.manual_resume_required
- risk.halt_on_data_source_failure
- polymarket.post_only_live_orders
- polymarket.private_key_env
- polymarket.api_key_env
- polymarket.api_secret_env
- polymarket.api_passphrase_env
- polymarket.funder_env

## Tunable Whitelist

- strategy.maker.min_spread_bps
- strategy.maker.inventory_skew_strength
- strategy.maker.quote_ttl_seconds
- strategy.maker.global_cooldown_seconds
- strategy.maker.market_cooldown_seconds
- strategy.maker.failure_cooldown_seconds
- strategy.maker.min_requote_edge_improvement_bps
- strategy.maker.failure_reentry_edge_improvement_bps
- risk.open_order_replacement_min_edge_improvement_bps
- strategy.surface.min_edge_bps
- strategy.surface.max_curve_mispricing_bps
- strategy.surface.exit_edge_bps
- strategy.surface.stop_loss_bps
- strategy.phase2.maker_min_edge_bps
- strategy.phase2.resolution_maker_min_edge_bps
- strategy.phase2.high_edge_taker_min_edge_bps
- strategy.phase2.high_edge_taker_max_spread_bps
- strategy.phase2.taker_max_entry_premium_bps
- strategy.phase2.maker_quote_ttl_seconds
- strategy.phase2.resolution_maker_quote_ttl_seconds
- strategy.phase2.entry_repost_cooldown_seconds

## Score Formula

```text
score =
  + 8.0 * closed_trade_net_pnl
  + 3.0 * trades_closed
  + 10.0 * fill_rate
  - 6.0 * cancel_rate
  - 8.0 * rejected_ratio
  - 10.0 * capacity_bound_rejection_ratio
  - 3.0 * market_data_failures
  - 0.05 * abs(avg_fill_price_vs_mid_bps)
```

## Experiment Matrix

- Tighten maker spread floor: strategy.maker.min_spread_bps
  rationale: Maker dominates signal volume and is burning the fixed order budget on low-selectivity opportunities.
  expected_effect: Lower signal pressure and fewer hard-limit rejects before the first useful fills.
- Throttle failed markets before global churn: strategy.maker.failure_cooldown_seconds, strategy.maker.min_requote_edge_improvement_bps, strategy.maker.failure_reentry_edge_improvement_bps
  rationale: Capacity-bound runs usually need maker to stop revisiting the same recently failed market unless the next quote is materially better.
  expected_effect: Lower repeated intent pressure on churn-heavy markets without suppressing the rest of the book.
- Lengthen maker quote lifetime: strategy.maker.quote_ttl_seconds
  rationale: Recent paper runs show high expiry counts relative to fills, which suggests quotes are churning faster than they convert.
  expected_effect: Fewer expiries and better chance that submitted quotes survive long enough to fill.

## Next Follow-Ups

- Build a score wrapper that penalizes capacity-bound rejection ratio directly on timestamped paper-session artifacts.
- Split fixed windows by day and compare signal-to-submission efficiency before and after maker selectivity changes.
- Only move to replay/backtest after useful submissions rise without touching hard limits.