---
title: BTC Phase2 Tail-Loss Gates and Fragile-Closer Sizing
date: 2026-04-01
category: logic-errors
module: crypto-phase2-btc-line
problem_type: logic_error
component: service_object
symptoms:
  - BTC line replay needed repeated manual interpretation to decide proceed/review/pause.
  - Large single losing trades and concentrated top-loss tails were not explicit gate blockers.
  - Entry notional did not downsize when recent close behavior showed repeated expiry/cancel pressure.
root_cause: logic_error
resolution_type: code_fix
severity: high
related_components:
  - testing_framework
  - tooling
tags:
  - btc
  - phase2
  - promotion-gate
  - tail-risk
  - notional-sizing
  - replay
---

# BTC Phase2 Tail-Loss Gates and Fragile-Closer Sizing

## Problem
BTC Phase2 had good descriptive diagnostics, but go/no-go promotion still depended on humans reading tables. At the same time, entry notional did not react to market-level close fragility, so tail losses could recur before operators intervened.

## Symptoms
- `promotion_decision` existed but lacked hard blockers for single-trade loss breach and top-3 loss concentration.
- Replay iteration required repeated manual judgment when PnL looked acceptable but tail shape was unsafe.
- Markets with repeated `order.expired` and stale-cancel patterns could continue receiving unchanged entry size.

## What Didn't Work
- Repeated profile parameter tuning alone (edge/TTL/spread) did not reliably suppress tail-risk concentration.
- Relying on scorecard narrative fields without machine-readable tail constraints caused ambiguous promotion outcomes.
- Only using generic execution quality feedback failed to penalize market-specific fragile closer behavior.

## Solution
Implemented two bounded controls on the BTC line.

1. Promotion gate tail-risk constraints in final scorecard:
- Added thresholds and observed metrics:
  - `promotion_max_single_loss_pnl` / `observed_max_single_loss_pnl`
  - `promotion_max_top3_loss_concentration_ratio` / `observed_top3_loss_concentration_ratio`
- Added explicit blockers:
  - `single_loss_breach`
  - `top3_loss_concentration_above_ceiling`
- Wired fields through final scorecard markdown/json and autoresearch promotion summary.

Key files:
- `src/pm_bot/strategies/crypto/phase2/final_report.py`
- `src/pm_bot/strategies/crypto/phase2/suite.py`
- `src/pm_bot/research/autoresearch.py`

2. Fragile-closer entry notional haircut in Phase2 strategy:
- Added optional config-gated market-level multiplier based on recent close-efficiency evidence:
  - sample = `order.expired` + close events in lookback
  - expired ratio above threshold => shrink notional toward configurable minimum multiplier
  - insufficient sample => fallback multiplier `1.0`
- Exposed diagnostics for operator traceability:
  - status, multiplier, sample_count, expired_count, closed_count, threshold

Key files:
- `src/pm_bot/strategies/crypto/phase2/strategy.py`
- `src/pm_bot/strategies/crypto/phase2/config_registry.py`

3. Validation additions:
- Unit tests for single-loss breach and top-3 concentration gate behavior.
- Unit tests for fragile-closer haircut applied vs insufficient-sample fallback.
- CLI integration test asserting new promotion fields are present in stdout and `final_scorecard.json`.

Key tests:
- `tests/unit/strategies/test_crypto_phase2_final_report.py`
- `tests/unit/strategies/test_crypto_phase2_strategy.py`
- `tests/unit/research/test_autoresearch.py`
- `tests/integration/test_cli_research.py`

## Why This Works
The failure mode was not missing data but missing enforceable decision logic on tail-risk shape. By codifying tail constraints as gate blockers, promotion output becomes deterministic (`proceed/review/pause`) instead of narrative-dependent. By adding fragile-closer notional haircut, markets with repeated close inefficiency receive immediate size reduction before full strategy-wide changes, reducing downside concentration without globally disabling BTC opportunities.

## Prevention
- Keep promotion gates machine-readable and stage-accurate; avoid qualitative-only promotion statements.
- For any new risk metric added to scorecards, require synchronized wiring in:
  - final scorecard json/markdown
  - suite placeholder payload
  - autoresearch extractor
  - CLI integration assertion
- Require targeted tests for both:
  - gate failure path (`review`/`pause` blockers)
  - fallback path when evidence is insufficient (no accidental over-blocking)
- Treat market-level fragile-close evidence as local sizing control, not replacement for core risk authority boundaries.

## Related Issues
- `docs/plans/2026-04-01-002-feat-btc-loss-replacement-plan.md`
- `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md` (P6 context and acceptance wording)
