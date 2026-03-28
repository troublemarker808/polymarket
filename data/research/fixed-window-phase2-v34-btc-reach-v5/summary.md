# Fixed Window Experiment Report

- generated_at: 2026-03-28T12:29:03.863581+00:00
- mode: replay
- snapshot_path: data\research\family-export-phase2-v34-btc-reach\snapshots.jsonl
- output_dir: data\research\fixed-window-phase2-v34-btc-reach-v5
- baseline_classification: execution-bound
- validation_winner: baseline
- promoted_winner: baseline
- decision_reason: No non-baseline candidate beat the baseline on validation promotion score.

## Objective

- Increase fill quality and completed trade count for approved orders without changing account-level risk caps.

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
- phase2_high_edge_taker_minus50_spread_plus200_premium_plus75: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0
  rationale: Allow genuinely high-edge phase2 signals to cross a still-bounded spread/premium budget instead of stalling one tick below the offer.
- phase2_high_edge_taker_relax_adverse_fill_gate: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0, strategy.phase2.adverse_fill_max_remaining_edge_bps=100.0
  rationale: Keep the aggressive entry path, but avoid treating still-large remaining edge as an immediate adverse-fill exit signal.
- phase2_high_edge_taker_hold_15s: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0, strategy.phase2.min_holding_seconds_before_exit=15.0
  rationale: Probe whether the aggressive entry only becomes bad because exit re-evaluates too quickly on the next snapshot.

## Train

- phase2_high_edge_taker_minus50_spread_plus200_premium_plus75: score=11.7804, promotion_score=17.7804, classification=alpha-bound, useful_submissions=2, submission_coverage=1.0000, submitted=2, filled=2, expired=0, canceled=0, rejected=0, fill_rate=1.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-minus50-spread-plus200-premium-plus75\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-minus50-spread-plus200-premium-plus75\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-minus50-spread-plus200-premium-plus75\autoresearch.md
  overrides: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0
- phase2_high_edge_taker_relax_adverse_fill_gate: score=11.7804, promotion_score=17.7804, classification=alpha-bound, useful_submissions=2, submission_coverage=1.0000, submitted=2, filled=2, expired=0, canceled=0, rejected=0, fill_rate=1.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-relax-adverse-fill-gate\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-relax-adverse-fill-gate\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-relax-adverse-fill-gate\autoresearch.md
  overrides: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0, strategy.phase2.adverse_fill_max_remaining_edge_bps=100.0
- phase2_high_edge_taker_hold_15s: score=2.2836, promotion_score=5.2836, classification=execution-bound, useful_submissions=1, submission_coverage=1.0000, submitted=1, filled=1, expired=0, canceled=0, rejected=0, fill_rate=1.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-hold-15s\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-hold-15s\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\phase2-high-edge-taker-hold-15s\autoresearch.md
  overrides: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0, strategy.phase2.min_holding_seconds_before_exit=15.0
- baseline: score=0.0000, promotion_score=3.0000, classification=execution-bound, useful_submissions=1, submission_coverage=1.0000, submitted=1, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\baseline\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\train\baseline\autoresearch.md

## Validation

- baseline: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\baseline\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\baseline\autoresearch.md
- phase2_high_edge_taker_minus50_spread_plus200_premium_plus75: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\phase2-high-edge-taker-minus50-spread-plus200-premium-plus75\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\phase2-high-edge-taker-minus50-spread-plus200-premium-plus75\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\phase2-high-edge-taker-minus50-spread-plus200-premium-plus75\autoresearch.md
  overrides: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0
- phase2_high_edge_taker_relax_adverse_fill_gate: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\phase2-high-edge-taker-relax-adverse-fill-gate\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\phase2-high-edge-taker-relax-adverse-fill-gate\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\validation\phase2-high-edge-taker-relax-adverse-fill-gate\autoresearch.md
  overrides: strategy.phase2.high_edge_taker_min_edge_bps=150.0, strategy.phase2.high_edge_taker_max_spread_bps=300.0, strategy.phase2.taker_max_entry_premium_bps=175.0, strategy.phase2.adverse_fill_max_remaining_edge_bps=100.0

## Holdout

- baseline: score=0.0000, promotion_score=0.0000, classification=alpha-bound, useful_submissions=0, submission_coverage=0.0000, submitted=0, filled=0, expired=0, canceled=0, rejected=0, fill_rate=0.0000, cancel_rate=0.0000
  metrics_path: data\research\fixed-window-phase2-v34-btc-reach-v5\holdout\baseline\engine.metrics.json
  event_path: data\research\fixed-window-phase2-v34-btc-reach-v5\holdout\baseline\events.jsonl
  autoresearch_path: data\research\fixed-window-phase2-v34-btc-reach-v5\holdout\baseline\autoresearch.md