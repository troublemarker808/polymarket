# Optimization Plan

Last updated: 2026-03-25

## 1. Current Baseline

This plan is based on the latest repo-local paper artifacts:

- [autoresearch report](/D:/dev/polymarket_bot2.0/data/runtime/paper-overnight-20260325-042240-autoresearch.md)
- [health report](/D:/dev/polymarket_bot2.0/data/runtime/paper-overnight-20260325-042240-health.md)
- [metrics](/D:/dev/polymarket_bot2.0/data/runtime/paper-overnight-20260325-042240-metrics.json)
- [events](/D:/dev/polymarket_bot2.0/data/runtime/paper-overnight-20260325-042240-events.jsonl)

Baseline classification:

- `capacity-bound`

Key observed facts from the current run:

- signals are extremely high relative to submissions
- most rejected orders are blocked by daily order limits, not signal review
- maker behavior produces very few completed executions
- fills that do occur are taker-only
- one losing closed trade is not enough evidence to optimize alpha yet

The practical interpretation is:

- the system is spending its fixed safety budget on too many low-value entry attempts
- current paper output is not yet a good optimization target for alpha tuning

## 2. Top Problems

### Problem A: the runtime saturates the safety budget before it learns anything useful

Evidence:

- rejection reasons are dominated by `daily order hard limit reached`
- secondary rejection reason is `max concurrent positions reached`
- current root cause is upstream selectivity, not downstream execution plumbing

Relevant files:

- [manager.py](/D:/dev/polymarket_bot2.0/src/pm_bot/risk/manager.py)
- [event_router.py](/D:/dev/polymarket_bot2.0/src/pm_bot/orchestrator/event_router.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/maker/strategy.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/surface/strategy.py)

### Problem B: per-strategy maker TTL is configured but not actually honored

Evidence:

- `strategy.maker.quote_ttl_seconds` exists in config and strategy config
- expiry still uses global `trading.default_quote_ttl_seconds`
- `OrderIntent` has no per-order TTL field

Relevant files:

- [crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/crypto.v1.example.toml)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/maker/strategy.py)
- [types.py](/D:/dev/polymarket_bot2.0/src/pm_bot/core/types.py)
- [engine.py](/D:/dev/polymarket_bot2.0/src/pm_bot/research/engine.py)
- [paper_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_session.py)

### Problem C: strategy timestamps use wall-clock time instead of market time

Evidence:

- strategies build `generated_at` from `datetime.now(...)`
- replay and paper semantics should use `snapshot.timestamp`

Impact:

- TTL behavior is less reproducible than it should be
- fill-age and daily-rollover metrics are polluted by runtime clock

Relevant files:

- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/maker/strategy.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/surface/strategy.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/anchor/strategy.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/live/strategy.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/ensemble/strategy.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/threshold/strategy.py)

### Problem D: long-running supervisor health is stale unless refreshed manually

Evidence:

- the supervisor only runs health refresh after the paper session process exits
- continuous sessions do not exit during normal long-running operation

Relevant files:

- [run-paper-supervisor.ps1](/D:/dev/polymarket_bot2.0/scripts/run-paper-supervisor.ps1)
- [check-paper-health.ps1](/D:/dev/polymarket_bot2.0/scripts/check-paper-health.ps1)

## 3. Optimization Objective

The optimization target for the next round is not "maximize PnL."

The correct objective is:

> Increase useful submissions and fills per fixed safety budget by reducing low-value signal generation before daily limits and concurrency gates saturate.

This implies three immediate rules:

1. Do not raise global hard limits to make the metrics look better.
2. Do not optimize alpha until the run stops being capacity-bound.
3. Prefer improvements that reduce rejection pressure while preserving or increasing useful fills.

## 4. Locked Safety Boundary

These stay fixed during optimization:

- `polymarket.allow_live_orders`
- `trading.live_allowed_categories`
- `trading.max_notional_per_market`
- `trading.max_notional_per_category`
- `trading.max_concurrent_positions`
- `trading.max_positions_per_market`
- `trading.daily_order_soft_limit`
- `trading.daily_order_hard_limit`
- `risk.max_daily_drawdown_pct`
- `risk.max_consecutive_losses`
- `risk.max_open_orders`
- `risk.kill_switch_on_stale_data_seconds`
- `risk.manual_resume_required`
- `risk.halt_on_data_source_failure`
- signer, wallet, API, RPC, and funder settings

## 5. Tunable Scope

Only tune crypto strategy-local parameters in the next round:

- `strategy.maker.min_spread_bps`
- `strategy.maker.inventory_skew_strength`
- `strategy.maker.quote_ttl_seconds`
- `strategy.surface.min_edge_bps`
- `strategy.surface.max_curve_mispricing_bps`
- `strategy.surface.exit_edge_bps`
- `strategy.surface.stop_loss_bps`

Do not tune more than 1 to 3 of them in the same round.

## 6. Optimization Strategy

### Phase 0: correctness fixes before search

These are required before trusting any search loop.

#### 0.1 Use snapshot time for all generated signals

Change:

- replace wall-clock `generated_at=datetime.now(...)` with `generated_at=snapshot.timestamp`

Why:

- makes replay and paper deterministic
- makes TTL and fill-age stats meaningful

Acceptance:

- replaying the same snapshot set twice produces identical order timestamps

#### 0.2 Add per-order TTL support

Change:

- extend [types.py](/D:/dev/polymarket_bot2.0/src/pm_bot/core/types.py) so `OrderIntent` can carry a quote TTL override
- have maker strategy attach `quote_ttl_seconds`
- use that TTL in paper and research expiry paths instead of only the global default

Why:

- current `quote_ttl_seconds` tuning is mostly inert
- optimization cannot target maker persistence until this is wired through

Acceptance:

- changing `strategy.maker.quote_ttl_seconds` changes actual paper expiry behavior

#### 0.3 Refresh health during continuous runs

Change:

- add periodic health refresh to [run-paper-supervisor.ps1](/D:/dev/polymarket_bot2.0/scripts/run-paper-supervisor.ps1), independent of process exit

Why:

- operators need current health while the session is still running

Acceptance:

- `paper-health.latest.md` updates during long-running sessions without manual intervention

### Phase 1: stop wasting the order budget

This is the highest-value optimization phase.

#### 1.1 Reduce maker signal pressure before risk review

Implementation options:

- raise `strategy.maker.min_spread_bps`
- add a strategy-local cooldown after one recent rejection or one recent submission in the same market
- add a strategy-local "only emit if edge improves materially versus last emitted quote" rule

Recommendation:

- implement edge-improvement gating and market-local cooldown before widening parameter search

Why:

- current maker strategy can emit a fresh best candidate on every snapshot
- risk manager then becomes the main throttle, which is too late

Acceptance:

- submission rate improves materially without changing hard limits
- rejection ratio drops sharply

#### 1.2 Make surface consume budget only on higher-conviction setups

Implementation options:

- raise `strategy.surface.min_edge_bps`
- narrow `strategy.surface.max_curve_mispricing_bps`
- add a market-level cooldown after recent entry rejection

Recommendation:

- start with `min_edge_bps`

Why:

- surface is not the dominant spammer, but it still shares the same global budget

Acceptance:

- surface submissions remain rare and higher quality

### Phase 2: improve execution quality after capacity pressure drops

Only start this after Phase 1.

#### 2.1 Make maker TTL real and then tune it

Once per-order TTL is wired:

- compare `quote_ttl_seconds` values such as `10`, `20`, and `30`
- measure changes in:
  - `orders_expired`
  - `fill_rate`
  - maker/taker fill share

Success signal:

- expiries fall faster than adverse-selection costs rise

#### 2.2 Re-evaluate maker spread floor

Tune `strategy.maker.min_spread_bps` after Phase 1 gating exists.

Goal:

- reduce low-value quotes
- preserve the best fill opportunities

Success signal:

- fewer rejected/expired attempts
- same or better useful fills per day

### Phase 3: only then optimize alpha

Do not treat one losing trade as an alpha verdict.

When there are enough filled and closed trades:

- tune `strategy.surface.exit_edge_bps`
- tune `strategy.surface.stop_loss_bps`
- tune `strategy.surface.max_curve_mispricing_bps`

Goal:

- improve closed-trade quality, not just signal count

Acceptance:

- better closed-trade net PnL on validation windows
- no regression in rejection profile or fill quality

## 7. Search and Scoring Loop

Use the repo-local autoresearch tooling first:

- [autoresearch.py](/D:/dev/polymarket_bot2.0/src/pm_bot/research/autoresearch.py)
- [cli.py](/D:/dev/polymarket_bot2.0/src/pm_bot/cli.py)

### Score

Current repo-local score:

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

Interpretation:

- this intentionally punishes capacity-bound runs harder than low-PnL runs
- that is correct for the current state of the system

### Artifact flow

For every candidate:

1. run timestamped paper artifacts
2. refresh health
3. generate autoresearch report
4. compare against the baseline report and metrics
5. reject any candidate that improves only by starving activity or by hiding behind capacity saturation

## 8. Dataset Plan

### Train

- short timestamped paper sessions used for quick iteration
- purpose: detect rejection-pressure improvements and execution behavior changes

### Validation

- overnight paper sessions on fixed config candidates
- purpose: confirm capacity improvements persist outside short windows

### Holdout

- replay or backtest windows once fixed datasets are available
- purpose: validate alpha and exit logic after capacity/execution fixes are complete

Rule:

- do not tune on holdout

## 9. Exact Next Experiment Matrix

Order matters.

### Round 1: correctness

1. snapshot-time signals
2. per-order maker TTL wiring
3. periodic supervisor health refresh

Expected outcome:

- better measurement fidelity, not necessarily better PnL

### Round 2: capacity reduction

1. add maker market-local cooldown
2. add maker quote-improvement threshold
3. raise maker `min_spread_bps` in a narrow band

Expected outcome:

- lower `capacity_bound_rejection_ratio`
- more useful submissions per day

### Round 3: secondary selectivity

1. raise surface `min_edge_bps`
2. optionally narrow `max_curve_mispricing_bps`

Expected outcome:

- surface consumes less scarce capacity on weak opportunities

### Round 4: execution tuning

1. compare maker TTL values
2. compare maker spread floor values
3. inspect maker/taker fill-source mix

Expected outcome:

- lower expiry ratio
- better fill quality

### Round 5: alpha tuning

Only start once:

- capacity-bound status is gone
- there are enough filled and closed trades to compare meaningfully

## 10. Acceptance Gates

The system is ready to move from capacity work to execution work when:

- capacity-bound rejection ratio is no longer dominant
- `orders_submitted` is materially larger than the current baseline without changing hard limits
- useful fills increase
- health remains clean

The system is ready to move from execution work to alpha work when:

- maker TTL and spread tuning actually affect results
- expiry behavior is interpretable
- closed trades are no longer statistically trivial

The system is ready for promotion-style evaluation when:

- tests pass
- validation windows repeat
- holdout does not regress
- no safety boundary worsens

## 11. Immediate Coding Checklist

Implement in this order:

1. signal timestamp fix
2. per-order TTL plumbing
3. supervisor health refresh during continuous runs
4. maker local throttling and quote-improvement gating
5. candidate-run helper or script for timestamped experiment outputs

## 12. What Not To Do

- do not increase `daily_order_hard_limit` to hide the current problem
- do not optimize surface exits before the runtime stops being capacity-bound
- do not use raw PnL from one or two trades as the main objective
- do not treat `strategy.maker.quote_ttl_seconds` as tunable until it is actually wired through
- do not trust replay/paper timing until strategy timestamps use `snapshot.timestamp`
