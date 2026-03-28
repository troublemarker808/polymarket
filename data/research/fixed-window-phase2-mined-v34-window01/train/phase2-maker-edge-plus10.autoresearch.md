# Autoresearch Report

- generated_at: 2026-03-28T10:33:44.546681+00:00
- classification: alpha-bound
- score: 0.0000
- metrics_path: data\research\fixed-window-phase2-mined-v34-window01\train\phase2-maker-edge-plus10.metrics.json
- event_path: data\research\fixed-window-phase2-mined-v34-window01\train\phase2-maker-edge-plus10.events.jsonl
- state_path: 

## Objective

- Find replay windows and ladder series with demonstrable tradable alpha before further execution tuning, because the current baseline produces no useful submissions.

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

- Mine eventful fixed windows: 
  rationale: Zero-activity alpha-bound runs should first isolate windows with fills, closes, or meaningful order lifecycle events before searching execution parameters.
  expected_effect: Higher-signal train/validation windows that can distinguish missing alpha from missing execution opportunities.
- Recalibrate ladder fair value: strategy.surface.min_edge_bps, strategy.surface.max_curve_mispricing_bps
  rationale: When no trades are even attempted, the likely bottleneck is fair-value conservatism or series selection, not exit plumbing.
  expected_effect: Restores a non-empty opportunity set on windows where repricing actually occurs.
- Tighten runtime market selection separately from pricing: strategy.phase2.maker_min_edge_bps, strategy.phase2.resolution_maker_min_edge_bps
  rationale: Selection should exclude structurally bad ladders without collapsing every runtime window to zero activity.
  expected_effect: Cleaner surviving ladders and clearer evidence about whether any family still contains alpha.

## Next Follow-Ups

- Run mine-fixed-windows on the latest long paper-session snapshot and event captures, then promote only fill-bearing windows into the fixed-window experiment set.
- Compare ETH and BTC ladders separately so overpriced yearly strips do not drown out shorter-lived repricing windows.
- Do not spend more iterations on maker TTL or taker premium until at least one replay window shows non-zero useful submissions under the current fair-value stack.