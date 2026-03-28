# Crypto Phase 2 Execution Hardening 2026-03-28

## Baseline Classification

`execution-bound`

The long paper window before this change showed:

- `signals_generated = 9`
- `orders_submitted = 9`
- `orders_filled = 1`
- `orders_expired = 6`
- `trades_closed = 0`
- one toxic fill on `573654`
- unrealized PnL `-2.5025`

Artifacts used:

- `data/runtime/phase2-paper-metrics.long.20260328.json`
- `data/runtime/phase2-paper-runtime-state.long.20260328.json`
- `data/runtime/phase2-paper-events.long.20260328.jsonl`

The dominant failure mechanisms were:

1. maker pricing could cross a one-tick spread and become an unintended taker fill
2. ultra-tail contracts such as `0.002` and `0.032` were still considered tradable
3. stop-loss logic was purely bps-based, so one tick in a coarse market could force an immediate bad exit

## Rewritten Objective

Do not optimize for raw signal count.

Optimize for:

- fewer toxic fills
- fewer ultra-tail entries
- lower forced-loss exit risk
- lower expired-order churn without increasing taker toxicity

## Locked Parameters

These remain outside this round:

- account-level risk caps
- daily order limits
- notional caps
- live/paper mode switches
- market-selection baseline weights

## Tunable Whitelist Used In This Round

- `min_contract_price`
- maker non-crossing quote logic
- `stop_loss_min_ticks`

## Score Formula For This Round

This round used a qualitative safety-first score:

- reward: reduction in toxic fills and open toxic loss
- reward: lower expired-order churn when it comes from tail filtering
- penalty: any new taker fill with poor `avg_fill_price_vs_mid_bps`
- penalty: any immediate stop-loss exit caused by coarse ticks

## Dataset Split

- train/observe: continuous paper window using `run-paper-crypto-phase2-session`
- underlying-state input: `tests/fixtures/crypto_phase2/runtime_underlying_states.json`
- baseline run:
  - `data/runtime/phase2-paper-metrics.long.20260328.json`
- candidate run:
  - `data/runtime/phase2-paper-metrics.long.v2.20260328.json`

## Code Changes

- `src/pm_bot/strategies/crypto/phase2/execution.py`
- `src/pm_bot/strategies/crypto/phase2/management.py`
- `src/pm_bot/strategies/crypto/phase2/strategy.py`
- `configs/profiles/research-crypto-phase2-v1/crypto.v1.example.toml`
- `configs/profiles/paper-crypto-phase2-v1/crypto.v1.example.toml`

Main changes:

1. maker entry quotes now refuse to cross a one-tick spread
2. contracts below `min_contract_price = 0.05` are rejected
3. stop-loss is now tick-aware via `stop_loss_min_ticks = 2`

## Before vs After

Before:

- `signals_generated = 9`
- `orders_submitted = 9`
- `orders_filled = 1`
- `orders_expired = 6`
- `fill_rate = 0.1111`
- `avg_fill_price_vs_mid_bps = 3340.00`
- unrealized PnL `-2.5025`

After:

- `signals_generated = 3`
- `orders_submitted = 3`
- `orders_filled = 0`
- `orders_expired = 2`
- `fill_rate = 0.0000`
- `avg_fill_price_vs_mid_bps = 0.00`
- unrealized PnL `0.0`

Candidate artifacts:

- `data/runtime/phase2-paper-metrics.long.v2.20260328.json`
- `data/runtime/phase2-paper-runtime-state.long.v2.20260328.json`
- `data/runtime/phase2-paper-events.long.v2.20260328.jsonl`

## Interpretation

This round successfully removed the known toxic execution pattern.

It did not yet solve the deeper activity problem:

- the strategy is now safer
- but also much more passive
- remaining signals still tend to rest without filling

## Dominant Runtime Rejection / Loss Pattern

There were no strategy-level rejections in either run.

The dominant failure pattern was execution-side:

- resting orders with low fill probability
- tail entry quality problems before the hardening round

## Next 3 Highest-Value Follow-Up Experiments

1. maker depth calibration
   - vary how far inside the spread `crypto.phase2` quotes after the non-cross guard
2. urgency threshold calibration
   - tighten when taker routing is allowed for repricing signals
3. market-family selection refinement
   - isolate which yearly ladder families generate persistent but low-quality resting orders
