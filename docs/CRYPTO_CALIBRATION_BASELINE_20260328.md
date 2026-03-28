# Crypto Calibration Baseline 2026-03-28

## 1. Baseline Classification

Current calibration baseline: `alpha-bound`

Why:

- on the real ETH runtime ladder window at
  `2026-03-27T15:14:21Z` to `2026-03-27T15:21:59Z`,
  both baseline and `crypto.phase2` produced `0` signals and `0` orders
  using:
  - `tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl`
  - `data/research/phase2_compare/baseline-eth-runtime/metrics.json`
  - `data/research/phase2_compare/phase2-eth-runtime/metrics.json`
- the fused fair values on that runtime-derived ETH dip ladder stayed well
  below the observed market mids:
  - `701552`: observed `0.72`, fair `0.4390`, net edge `-2594.64bps`
  - `701553`: observed `0.27`, fair `0.1593`, net edge `-892.28bps`
  - `701554`: observed `0.205`, fair `0.1120`, net edge `-815.41bps`
  - source: `data/research/phase2_compare/phase2-eth-runtime/fair_values.jsonl`
- execution plumbing is no longer the primary blocker because the synthetic
  compare fixture on `2026-03-28` completed a full profitable entry-to-exit
  path under `crypto.phase2`:
  - `data/research/phase2_compare/phase2-compare/events.jsonl`
  - `data/research/phase2_compare/phase2-compare/metrics.json`

Top failure mechanisms:

1. The current barrier model is too conservative on real ETH dip ladders.
2. The current barrier/surface fusion is preserving that conservative bias
   instead of correcting it.
3. As a result, the execution layer is starved of candidates on real runtime
   windows.

## 2. Rewritten Objective

Do not optimize for raw paper PnL yet.

The immediate objective is:

`Increase repricing-aligned positive-net-edge coverage on fixed crypto ladder windows without relaxing fixed safety controls.`

This means:

- reward markets where model edge direction matches later repricing direction
- reward positive net-edge candidates
- penalize broad negative-net-edge saturation
- keep risk controls and runtime survival settings fixed

## 3. Locked Parameter List

These are frozen for calibration round 1:

- `starting_equity`
- `max_daily_drawdown_pct`
- `max_consecutive_losses`
- `max_open_orders`
- `daily_order_soft_limit`
- `daily_order_hard_limit`
- `paper_place_latency_ms`
- `paper_cancel_latency_ms`
- `paper_taker_slippage_bps`

## 4. Tunable Parameter Whitelist

Only these parameters are in scope for round 1 calibration:

- `barrier_distance_coefficient`
- `barrier_probability_floor`
- `barrier_probability_ceiling`
- `fusion_barrier_weight`
- `fusion_surface_weight`
- `min_net_edge_bps`
- `maker_min_edge_bps`

Round 1 priority:

1. `barrier_distance_coefficient`
2. `fusion_barrier_weight`
3. `fusion_surface_weight`

## 5. Score Formula

Round 1 score:

`score = (40 * sign_alignment_rate) + (8 * positive_net_edge_count) - (0.02 * mean_abs_gap_bps) - (0.03 * max(-mean_net_edge_bps, 0))`

Interpretation:

- reward sign alignment between model edge and later repricing
- reward positive net-edge opportunities
- penalize large fair/observed gaps
- penalize broadly negative net-edge datasets

## 6. Dataset Split

Initial fixed split:

- `train`
  - `tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl`
- `validation`
  - `tests/fixtures/crypto_phase2/compare_snapshots.jsonl`
- `holdout`
  - `tests/fixtures/crypto_phase1/ladder_snapshots.jsonl`

This split is intentionally narrow. It is good enough to start calibration
infrastructure, but it is not large enough for promotion decisions.

## 7. Experiment Matrix

First round experiment matrix:

1. Lower barrier steepness from the current `2.4` coefficient.
2. Reduce barrier dominance in fusion from `0.65 / 0.35`.
3. Re-run calibration report on the fixed split.
4. Reject any candidate that:
   - lowers sign alignment
   - creates positive-net-edge candidates only on synthetic data
   - worsens holdout score

## 8. Next Three Experiments

1. Tune `barrier_distance_coefficient` over a narrow range around the current
   value and compare train/validation/holdout scores.
2. Tune fusion weights so the surface term can counteract conservative barrier
   output on real dip ladders.
3. Expand the fixed dataset family with one BTC runtime ladder window and one
   ETH reach runtime ladder window before any promotion attempt.
