# Fixed Window Experiment Report

- generated_at: 2026-03-28T12:18:13.350789+00:00
- mode: replay
- snapshot_path: data\research\family-export-phase2-v34-btc-reach\snapshots.jsonl
- output_dir: data\research\fixed-window-phase2-v34-btc-reach-v2
- baseline_classification: capacity-bound
- validation_winner: baseline
- promoted_winner: baseline
- decision_reason: No non-baseline candidate beat the baseline on validation promotion score.

## Objective

- Increase useful submissions and fills per fixed safety budget by reducing low-value signal generation before daily limits and concurrency gates saturate.

## Dataset Split

- train: 32 snapshots (2026-03-28T10:29:35.400000+00:00 -> 2026-03-28T10:32:41.753000+00:00)
- validation: 10 snapshots (2026-03-28T10:32:44.811000+00:00 -> 2026-03-28T10:32:51.056000+00:00)
- holdout: 12 snapshots (2026-03-28T10:32:51.140000+00:00 -> 2026-03-28T10:33:07.211000+00:00)

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

- baseline: none
  rationale: Unmodified config baseline for the captured fixed window.
- phase2_resolution_edge_plus15: strategy.phase2.resolution_maker_min_edge_bps=165.0
  rationale: Tighten long-horizon phase2 entries when closed-trade quality, not fill scarcity, is the problem.
- phase2_maker_edge_plus10: strategy.phase2.maker_min_edge_bps=110.0
  rationale: Trim marginal phase2 entries before widening any execution route.
- phase2_taker_premium_minus25: strategy.phase2.taker_max_entry_premium_bps=75.0
  rationale: Reduce phase2 taker aggressiveness when alpha quality is the issue.

## Train

- baseline: score=0.0000, promotion_score=0.0000, classification=capacity-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\baseline\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\baseline\autoresearch.md
- phase2_maker_edge_plus10: score=0.0000, promotion_score=0.0000, classification=capacity-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-maker-edge-plus10\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-maker-edge-plus10\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-maker-edge-plus10\autoresearch.md
  overrides: strategy.phase2.maker_min_edge_bps=110.0
- phase2_resolution_edge_plus15: score=0.0000, promotion_score=0.0000, classification=capacity-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-resolution-edge-plus15\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-resolution-edge-plus15\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-resolution-edge-plus15\autoresearch.md
  overrides: strategy.phase2.resolution_maker_min_edge_bps=165.0
- phase2_taker_premium_minus25: score=0.0000, promotion_score=0.0000, classification=capacity-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-taker-premium-minus25\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-taker-premium-minus25\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\train\phase2-taker-premium-minus25\autoresearch.md
  overrides: strategy.phase2.taker_max_entry_premium_bps=75.0

## Validation

- baseline: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\baseline\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\baseline\autoresearch.md
- phase2_maker_edge_plus10: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\phase2-maker-edge-plus10\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\phase2-maker-edge-plus10\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\phase2-maker-edge-plus10\autoresearch.md
  overrides: strategy.phase2.maker_min_edge_bps=110.0
- phase2_resolution_edge_plus15: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\phase2-resolution-edge-plus15\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\phase2-resolution-edge-plus15\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\validation\phase2-resolution-edge-plus15\autoresearch.md
  overrides: strategy.phase2.resolution_maker_min_edge_bps=165.0

## Holdout

- baseline: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v2\holdout\baseline\metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v2\holdout\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v2\holdout\baseline\autoresearch.md