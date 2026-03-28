# Paper-Live Bias Assessment (2026-03-27)

## Purpose

This report is the formal paper-vs-live bias judgment using the existing real-money
micro-order artifacts collected on 2026-03-27.

The goal is not to judge profitability. The goal is to judge whether the current
paper runtime is directionally close enough to the real PM execution path to be
trusted as a calibration source.

## Artifact Scope

### Excluded Invalid Live Runs

These runs are excluded from the formal judgment because they were polluted by
known execution/runtime bugs:

- `live-baseline-20260327-024441`
  - invalid signature failure
- `live-baseline-20260327-025308`
  - exchange-side minimum / submit rejection path before containment
- `live-baseline-20260327-025736`
  - duplicate fill accounting across reconnects
- `live-baseline-20260327-032215`
  - historical user-stream contamination
- `live-baseline-20260327-032849`
  - live oversell / synthetic complement accounting bug

### Valid Live Artifacts Used

- Clean stable live baseline:
  - [live-calibration-baseline.metrics.live-baseline-20260327-034752.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.metrics.live-baseline-20260327-034752.json)
  - [live-calibration-baseline.events.live-baseline-20260327-034752.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.events.live-baseline-20260327-034752.jsonl)
- New paired live run after the first calibration pass:
  - [live-calibration-baseline.metrics.live-baseline-20260327-045459.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.metrics.live-baseline-20260327-045459.json)
  - [live-calibration-baseline.events.live-baseline-20260327-045459.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.events.live-baseline-20260327-045459.jsonl)
  - [live-calibration-baseline.state.live-baseline-20260327-045459.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.state.live-baseline-20260327-045459.json)

### Paper Artifact Used

- First calibrated paper run launched in parallel with the new live run:
  - [analysis-paper-session-metrics.paper-baseline-20260327-045459.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.paper-baseline-20260327-045459.json)
  - [analysis-paper-session-events.paper-baseline-20260327-045459.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.paper-baseline-20260327-045459.jsonl)

## Baseline Classification

The current problem is `execution-bound`.

This is not an alpha judgment. The dominant mismatch is still between paper and
live execution behavior:

- fill probability
- cancel probability
- maker vs taker composition
- exchange-side rejection handling

The paired live run also shows a secondary `capacity-bound` contamination because
rejects from concurrency and balance / allowance constraints materially affected the
live sample.

## Pass Criteria

Paper is considered "directionally aligned" only if all of the following are true
on a comparable window:

- `fill_rate` gap is within `10` percentage points
- `cancel_rate` gap is within `10` percentage points
- `avg_time_to_fill_ms` gap is within `25%`
- `maker_fill_share` and `taker_fill_share` stay in the same regime
- `avg_fill_price_vs_mid_bps` does not show unstable sign flips across valid live windows

## Formal Judgment

Status: `FAIL`

The current calibrated paper runtime is still not close enough to real execution to
be treated as a trustworthy standalone predictor of live behavior.

It is useful as a calibration target and debugging surface, but not yet accurate
enough to conclude "paper looks fine, so live should behave similarly."

## Core Evidence

### 1. Paper still overfills badly

Paired run comparison:

- live `fill_rate = 0.3721`
- paper `fill_rate = 0.9286`
- gap `+55.65` percentage points in favor of paper

Clean live reference:

- clean live `fill_rate = 0.4487`

Interpretation:

- paper still turns too many signals into fills
- live still loses many more intents to cancels, partials, and exchange-side failure

### 2. Paper still underestimates cancel pressure

Paired run comparison:

- live `cancel_rate = 0.8140`
- paper `cancel_rate = 0.0714`
- gap `-74.25` percentage points

Clean live reference:

- clean live `cancel_rate = 0.8333`

Interpretation:

- the real path remains cancellation-heavy
- paper still behaves as if orders survive to fill far more often than they really do

### 3. Paper still invents maker behavior that live does not show

Paired run comparison:

- live `maker_fill_share = 0.0`
- paper `maker_fill_share = 0.2173`

Event-level evidence:

- live fill-source histogram in `045459`: `taker = 41`, `maker = 0`
- paper fill-source histogram in `045459`: `taker = 26`, `maker = 5`

Interpretation:

- the execution sample strategy is still effectively all-taker in live
- paper is still awarding passive fills that do not appear in the real baseline

### 4. Live rejection modes are still missing from paper

Paired live rejection histogram:

- `max concurrent positions reached = 9`
- `not enough balance / allowance = 17`

Paired paper rejection histogram:

- `max concurrent positions reached = 13`
- no balance / allowance path exists

Interpretation:

- paper does not model exchange-side balance / allowance depletion or late account-state races
- this makes paper materially more forgiving than live even after the first calibration pass

### 5. Price realism is not yet stable enough to trust

Paired run comparison:

- live `avg_fill_price_vs_mid_bps = 145.78`
- paper `avg_fill_price_vs_mid_bps = 53.48`
- paper looks `92.30` bps better than live

But against the clean live baseline:

- clean live `avg_fill_price_vs_mid_bps = 21.30`
- paper `avg_fill_price_vs_mid_bps = 53.48`
- paper looks `32.18` bps worse than clean live

Interpretation:

- direction is unstable across valid live windows
- price-quality realism is not yet calibrated well enough to declare "matched"

## Metrics Table

| Metric | Clean Live `034752` | Paired Live `045459` | Paired Paper `045459` |
| --- | ---: | ---: | ---: |
| orders_submitted | 78 | 43 | 28 |
| orders_rejected | 5 | 26 | 13 |
| orders_filled | 35 | 16 | 26 |
| orders_partially_filled | 42 | 25 | 5 |
| orders_canceled | 65 | 35 | 0 |
| trades_closed | 38 | 20 | 15 |
| fill_rate | 0.4487 | 0.3721 | 0.9286 |
| cancel_rate | 0.8333 | 0.8140 | 0.0714 |
| avg_time_to_fill_ms | 11966.23 | 8270.75 | 5110.85 |
| avg_fill_price_vs_mid_bps | 21.30 | 145.78 | 53.48 |
| maker_fill_share | 0.0000 | 0.0000 | 0.2173 |
| taker_fill_share | 1.0000 | 1.0000 | 0.7827 |

## Practical Meaning

The paper runtime is no longer failing because of obvious bookkeeping bugs, but it
is still too optimistic about whether an intent will become a fill and too
optimistic about whether that fill can happen without a cancel-heavy live path.

The implication is straightforward:

- if paper looks only mildly bad, live may still be materially worse
- if paper looks good, that is still not enough evidence for live promotion

Current paper can be used for:

- debugging execution logic
- collecting synthetic samples
- testing whether a calibration change moves the right metric in the right direction

Current paper cannot yet be used for:

- trusting apparent profitability
- trusting fill density
- trusting maker behavior
- treating paper/live drift as "small enough"

## Highest-Value Follow-Up Calibration Targets

1. Remove false paper maker fills for `crypto.execution_sample` calibration windows.
2. Add a paper-side model for live rejection pressure from balance / allowance and
   concurrency exhaustion.
3. Re-run a new paired window after those two changes and judge again against the
   same pass criteria.
