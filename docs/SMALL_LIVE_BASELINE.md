# Small-Live Baseline

## Purpose

This profile is the first real-money micro-order baseline used to compare paper
execution against real PM execution.

It exists to answer one question:

- do paper execution artifacts behave directionally like real fills, cancels,
  and close events under tiny notional and strict safety caps?

This is not a promotion profile and not a profitability profile.

## Code Boundary

The code needed before the first small-live baseline window is now prepared:

- live now writes paper-comparable `metrics`, `events`, and `state` artifacts
- live emits standardized `order.filled`, `order.partially_filled`,
  `order.canceled`, `order.rejected`, and `trade.closed` events
- the dedicated micro-order profile is in
  [configs/profiles/small-live-baseline-v1](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1)

The actual live run is started by the operator, not by Codex.

## Profile Intent

Profile:

- [base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/base.example.toml)
- [crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/crypto.v1.example.toml)

Safety intent:

- live mode
- crypto only
- `default_order_notional = 1.1`
- `max_notional_per_market = 1.1`
- `max_notional_per_category = 3.3`
- `max_concurrent_positions = 3`
- `daily_order_hard_limit = 120`
- `max_daily_drawdown_pct = 40.0`
- `max_consecutive_losses = 40`
- `live_recovery_scope = "session"`

Sampling intent:

- use `crypto.execution_sample`
- keep the market universe narrow and liquid
- treat each baseline run as a fresh session-scoped window instead of replaying the
  full account history into local artifacts
- keep sample collection alive longer by widening halt thresholds without increasing
  single-order notional or concurrency
- collect comparable fill/cancel/latency/price-quality evidence before later
  paper calibration phases

Runtime bug fixes now baked into the profile handoff:

- live supervision now reconnects when the market/user streams end cleanly
  before a stop condition is reached
- second-stage small-live recovery now only restores trades and open orders
  created during the current run session
- live startup now probes balance/allowance and resolves the viable
  `signature_type` instead of blindly trusting the config default
- exchange-side submit rejections are recorded as `order.rejected` instead of
  crashing the entire live session

## Artifact Contract

The first small-live baseline window should produce:

- `state.json`
- `events.jsonl`
- `metrics.json`
- one short markdown operator note that records the run id, market window, and
  any notable exchange-side anomalies

Recommended artifact names:

- `data/runtime/live-calibration-baseline.state.<run>.json`
- `data/runtime/live-calibration-baseline.events.<run>.jsonl`
- `data/runtime/live-calibration-baseline.metrics.<run>.json`
- `data/runtime/live-calibration-baseline.note.<run>.md`

## Ready-To-Run Checks

Before the operator starts the first run:

- validate the profile with `validate-config`
- validate live credentials and readiness with `validate-live-config`
- decide the fixed artifact paths in advance
- decide the intended market window and stop condition in advance

## First Review Questions

After the first real micro-order baseline window, review:

- how many orders were submitted vs filled
- how many were partial vs full fills
- whether cancels were acknowledged cleanly
- whether close events and PnL closed-trade accounting look sane
- how live `fill_rate`, `cancel_rate`, `avg_time_to_fill_ms`,
  `avg_fill_price_vs_mid_bps`, `maker_fill_share`, and `taker_fill_share`
  compare against paper
