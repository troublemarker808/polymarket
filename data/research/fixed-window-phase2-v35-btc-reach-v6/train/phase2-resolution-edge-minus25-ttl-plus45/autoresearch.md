# Autoresearch Report

- generated_at: 2026-03-28T12:52:33.469308+00:00
- classification: execution-bound
- score: 0.0000
- metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v6\train\phase2-resolution-edge-minus25-ttl-plus45\engine.metrics.json
- event_path: data\research\fixed-window-phase2-v35-btc-reach-v6\train\phase2-resolution-edge-minus25-ttl-plus45\events.jsonl
- state_path: 

## Objective

- Increase fill quality and completed trade count for approved orders without changing account-level risk caps.

## Baseline

- signals_generated: 2
- orders_submitted: 2
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
- strategy.phase2.maker_aggressiveness
- strategy.phase2.high_edge_taker_min_edge_bps
- strategy.phase2.high_edge_taker_max_spread_bps
- strategy.phase2.taker_max_entry_premium_bps
- strategy.phase2.maker_quote_ttl_seconds
- strategy.phase2.resolution_maker_quote_ttl_seconds
- strategy.phase2.entry_repost_cooldown_seconds
- strategy.phase2.exit_edge_bps
- strategy.phase2.min_holding_seconds_before_exit
- strategy.phase2.adverse_fill_exit_bps
- strategy.phase2.adverse_fill_max_remaining_edge_bps

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

- Adjust maker quote lifetime and spread together: strategy.maker.quote_ttl_seconds, strategy.maker.min_spread_bps
  rationale: Execution-bound runs usually need a better balance between quote persistence and adverse-selection risk.
  expected_effect: Higher fill rate with lower expiry churn.
- Tune market-local failure cooldown: strategy.maker.failure_cooldown_seconds, strategy.maker.min_requote_edge_improvement_bps, strategy.maker.failure_reentry_edge_improvement_bps
  rationale: Once execution is the bottleneck, recently expired or replaced markets need a local pause instead of a strategy-wide brake.
  expected_effect: Better fill opportunity coverage outside churn-heavy markets.
- Tune maker inventory skew: strategy.maker.inventory_skew_strength
  rationale: Inventory skew changes whether fills accumulate into positions that can be exited cleanly.
  expected_effect: Less inventory drag and better exit quality.

## Next Follow-Ups

- Replay deterministic book windows that contain expiries and compare fill-rate changes across narrow TTL/spread moves.
- Track maker versus taker fill-source mix per candidate, not just aggregate fill rate.
- Reject any candidate that raises fill rate only by worsening avg_fill_price_vs_mid_bps materially.