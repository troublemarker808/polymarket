# Autoresearch Report

- generated_at: 2026-03-28T10:27:11.608353+00:00
- classification: alpha-bound
- score: 0.0000
- metrics_path: data\research\fixed-window-phase2-eth-v33\holdout\baseline.metrics.json
- event_path: data\research\fixed-window-phase2-eth-v33\holdout\baseline.events.jsonl
- state_path: 

## Objective

- Improve closed-trade quality and downside behavior on the existing opportunity set.

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

- Tighten surface entries: strategy.surface.min_edge_bps, strategy.surface.max_curve_mispricing_bps
  rationale: Alpha-bound runs need a cleaner opportunity set before changing safety behavior.
  expected_effect: Fewer low-quality entries and better per-trade expectancy.
- Tune surface exits and stop-loss: strategy.surface.exit_edge_bps, strategy.surface.stop_loss_bps
  rationale: Closed-trade quality is already observable, so exits are the highest-leverage local control.
  expected_effect: Improved closed-trade PnL and downside containment.
- Tune maker inventory skew: strategy.maker.inventory_skew_strength
  rationale: Inventory pressure often leaks alpha through slow exits and overexposure to one side.
  expected_effect: Cleaner inventory normalization and less forced-loss behavior.

## Next Follow-Ups

- Build train/validation/holdout replay windows around the strategy that produced the losing closed trades.
- Compare alpha candidates with the repo-local score first, then with replay/backtest confirmation.
- Do not widen scope beyond one strategy until closed-trade quality improves on validation windows.