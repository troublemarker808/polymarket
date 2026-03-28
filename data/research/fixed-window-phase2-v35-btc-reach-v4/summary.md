# Fixed Window Experiment Report

- generated_at: 2026-03-28T12:47:20.172929+00:00
- mode: replay
- snapshot_path: data\research\family-export-phase2-v35-btc-reach\snapshots.jsonl
- output_dir: data\research\fixed-window-phase2-v35-btc-reach-v4
- baseline_classification: execution-bound
- validation_winner: baseline
- promoted_winner: baseline
- decision_reason: No non-baseline candidate beat the baseline on validation promotion score.

## Objective

- Increase fill quality and completed trade count for approved orders without changing account-level risk caps.

## Dataset Split

- train: 30 snapshots (2026-03-28T12:27:40.101000+00:00 -> 2026-03-28T12:29:54+00:00)
- validation: 10 snapshots (2026-03-28T12:29:58.077000+00:00 -> 2026-03-28T12:30:13.806000+00:00)
- holdout: 10 snapshots (2026-03-28T12:30:13.808000+00:00 -> 2026-03-28T12:30:16.867000+00:00)

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

- baseline: none
  rationale: Unmodified config baseline for the captured fixed window.
- phase2_resolution_ttl_plus45: strategy.phase2.resolution_maker_quote_ttl_seconds=90, strategy.phase2.entry_repost_cooldown_seconds=45.0
  rationale: Let long-horizon maker quotes rest longer before expiring, while backing off slightly after a miss.
- phase2_resolution_edge_minus25_ttl_plus45: strategy.phase2.resolution_maker_min_edge_bps=125.0, strategy.phase2.resolution_maker_quote_ttl_seconds=90
  rationale: Probe whether the family is under-trading thin but still positive resolution edges that need more time on the book.
- phase2_maker_aggr_plus025_ttl_plus15: strategy.phase2.maker_aggressiveness=1.25, strategy.phase2.maker_quote_ttl_seconds=75
  rationale: Make passive quotes one notch more aggressive while keeping them non-crossing and letting them rest slightly longer.

## Train

- phase2_resolution_edge_minus25_ttl_plus45: score=0.0000, promotion_score=6.0000, classification=execution-bound, useful_submissions=2, submission_coverage=1.0000, submitted=2, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-resolution-edge-minus25-ttl-plus45\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-resolution-edge-minus25-ttl-plus45\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-resolution-edge-minus25-ttl-plus45\autoresearch.md
  overrides: strategy.phase2.resolution_maker_min_edge_bps=125.0, strategy.phase2.resolution_maker_quote_ttl_seconds=90
- phase2_resolution_ttl_plus45: score=0.0000, promotion_score=3.0000, classification=execution-bound, useful_submissions=1, submission_coverage=1.0000, submitted=1, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-resolution-ttl-plus45\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-resolution-ttl-plus45\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-resolution-ttl-plus45\autoresearch.md
  overrides: strategy.phase2.resolution_maker_quote_ttl_seconds=90, strategy.phase2.entry_repost_cooldown_seconds=45.0
- baseline: score=-6.0000, promotion_score=-6.0000, classification=execution-bound, useful_submissions=0, submission_coverage=1.0000, submitted=1, filled=0, expired=1, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=1.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\baseline\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\baseline\autoresearch.md
- phase2_maker_aggr_plus025_ttl_plus15: score=-6.0000, promotion_score=-6.0000, classification=execution-bound, useful_submissions=0, submission_coverage=1.0000, submitted=1, filled=0, expired=1, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=1.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-maker-aggr-plus025-ttl-plus15\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-maker-aggr-plus025-ttl-plus15\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\train\phase2-maker-aggr-plus025-ttl-plus15\autoresearch.md
  overrides: strategy.phase2.maker_aggressiveness=1.25, strategy.phase2.maker_quote_ttl_seconds=75

## Validation

- baseline: score=0.0000, promotion_score=6.0000, classification=execution-bound, useful_submissions=2, submission_coverage=1.0000, submitted=2, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\baseline\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\baseline\autoresearch.md
- phase2_resolution_edge_minus25_ttl_plus45: score=0.0000, promotion_score=6.0000, classification=execution-bound, useful_submissions=2, submission_coverage=1.0000, submitted=2, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\phase2-resolution-edge-minus25-ttl-plus45\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\phase2-resolution-edge-minus25-ttl-plus45\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\phase2-resolution-edge-minus25-ttl-plus45\autoresearch.md
  overrides: strategy.phase2.resolution_maker_min_edge_bps=125.0, strategy.phase2.resolution_maker_quote_ttl_seconds=90
- phase2_resolution_ttl_plus45: score=0.0000, promotion_score=6.0000, classification=execution-bound, useful_submissions=2, submission_coverage=1.0000, submitted=2, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\phase2-resolution-ttl-plus45\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\phase2-resolution-ttl-plus45\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\validation\phase2-resolution-ttl-plus45\autoresearch.md
  overrides: strategy.phase2.resolution_maker_quote_ttl_seconds=90, strategy.phase2.entry_repost_cooldown_seconds=45.0

## Holdout

- baseline: score=0.0000, promotion_score=3.0000, classification=execution-bound, useful_submissions=1, submission_coverage=1.0000, submitted=1, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v35-btc-reach-v4\holdout\baseline\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v35-btc-reach-v4\holdout\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v35-btc-reach-v4\holdout\baseline\autoresearch.md