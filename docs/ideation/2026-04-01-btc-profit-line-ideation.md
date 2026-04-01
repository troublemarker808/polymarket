---
date: 2026-04-01
topic: btc-profit-line
focus: strengthen BTC crypto line for profitability-first progression
---

# Ideation: BTC Profitability Path

## Codebase Context

- Current direction is explicitly crypto-first and BTC-focused through dedicated profiles:
  - `configs/profiles/sync-btc-short-shadow-v1`
  - `configs/profiles/sync-btc-shadow-v1`
  - `configs/profiles/paper-btc-short-shadow-v1`
- BTC-specific research documents show a recurring signal:
  - some BTC ladder families remain structurally overpriced
  - liquidity may be acceptable, but net edge is still negative in many strips
  - selection filters already block `skip_series` / `watch_only` scenarios in runtime paths
- Runtime already has meaningful controls:
  - series/market blocking and reasons
  - entry/exit cooldowns
  - no-fill attempt caps
  - maker/taker routing thresholds
  - execution-feedback summaries
- Remaining profitability bottlenecks are now mostly:
  - low density of truly tradable windows
  - static cost thresholds that lag market regime changes
  - execution feedback not yet converted into stronger adaptive policy
  - BTC profitability logic still mostly single-market centric rather than strip-structure aware

## Ranked Ideas

### 1. BTC Tradable-Window Miner + Auto Universe Scheduler
**Description:** Build a BTC-only window miner that scores each candidate window by actionable opportunity density (signal count, fill probability proxy, edge-after-cost distribution), then feeds only high-score windows into paper/shadow runs.
**Rationale:** Current docs repeatedly show dead windows and negative strips distorting tuning. Profitability improves faster when training/validation focuses on windows where edge can actually be converted.
**Downsides:** Needs careful anti-overfitting guardrails; weak scoring design can create selection bias.
**Confidence:** 94%
**Complexity:** Medium
**Status:** Unexplored

### 2. Family/Expiry Bias-Corrected Fair Value Layer (BTC)
**Description:** Add a residual bias-correction layer on top of current fair value for BTC families (dip/reach/above-below, short vs long expiry), learned from replay + paper error patterns.
**Rationale:** Existing BTC reports show persistent strip-level overpricing even after baseline calibration. A structured residual correction can reduce systematic false positives/false negatives faster than broad retuning.
**Downsides:** Requires strict out-of-sample validation; model drift risk if market regime shifts quickly.
**Confidence:** 90%
**Complexity:** High
**Status:** Unexplored

### 3. Edge-After-Cost Gate 2.0 (Dynamic, Regime-Aware)
**Description:** Replace static entry thresholds with dynamic thresholds driven by recent realized execution drag (premium, slippage, expiration loss) per BTC family and time bucket.
**Rationale:** Current execution route logic already computes relevant pieces, but gating is still mostly static. Profitability depends on trading only when expected edge survives current execution friction.
**Downsides:** If adaptation is too reactive, strategy may oscillate between over-trading and over-filtering.
**Confidence:** 92%
**Complexity:** Medium
**Status:** Unexplored

### 4. Contextual Route Learner (Maker/Taker Policy Upgrade)
**Description:** Upgrade route decision from threshold rules to a constrained contextual learner (bandit-style) that selects maker/taker/skip by market microstructure features and recent outcome feedback.
**Rationale:** Runtime already records fill and expiration outcomes; converting this into route policy learning is the shortest path to execution alpha without changing core market selection architecture.
**Downsides:** Requires strong safety constraints to avoid unstable exploration behavior.
**Confidence:** 86%
**Complexity:** High
**Status:** Unexplored

### 5. BTC Session Whitelist + Auto Pause/Resume
**Description:** Build a session-level profitability calendar that only allows BTC trading during historically favorable liquidity/edge-capture windows and auto-pauses low-quality sessions.
**Rationale:** Many crypto windows are low-information. Time-of-day/session filtering can improve PnL quality quickly with low architecture risk.
**Downsides:** Can miss sudden off-session opportunities; needs periodic recalibration.
**Confidence:** 83%
**Complexity:** Low
**Status:** Unexplored

### 6. Strip-Structure Relative-Value Mode (Adjacent Rung Spread)
**Description:** Add a BTC ladder relative-value mode that detects cross-rung inconsistencies (adjacent rung pricing slope anomalies) and trades structural normalization instead of pure directional bets.
**Rationale:** Current evidence indicates whole strips can be overpriced. Relative-value logic can harvest local mispricings even when directional edge is weak.
**Downsides:** Multi-leg coordination, inventory accounting, and risk controls become materially more complex.
**Confidence:** 74%
**Complexity:** High
**Status:** Unexplored

### 7. Profit-Weighted Sizing and Exposure Budgeting
**Description:** Move from mostly fixed notional to confidence-and-quality-weighted sizing, using edge capture ratio and recent per-family win quality as multipliers under hard BTC exposure caps.
**Rationale:** Same signal count can produce very different returns; sizing should emphasize high-quality contexts and automatically de-risk degraded regimes.
**Downsides:** Requires robust safeguards to prevent unintended leverage concentration.
**Confidence:** 88%
**Complexity:** Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Expand to ETH and multi-board simultaneously | Violates current BTC-only focus and increases noise. |
| 2 | Full front-end redesign first | Low direct impact on BTC alpha conversion. |
| 3 | Immediate large-notional live scaling | Premature before stronger profit-quality evidence. |
| 4 | Pure parameter brute-force sweep | Likely overfits dead windows and hides root causes. |
| 5 | Replace full strategy stack with new architecture | Blast radius too large for current stage goals. |
| 6 | Add many new external data vendors now | Increases complexity before proving current path profitability. |
| 7 | Remove conservative risk gates to boost trade count | Can raise losses faster than returns. |
| 8 | Backtest-only optimization cycle | Misses paper/shadow execution reality gap. |
| 9 | Ignore execution and focus only on fair value | Contradicts observed fill/expiry bottlenecks. |
| 10 | Treat all BTC families with one unified threshold | Ignores documented family-specific behavior differences. |
| 11 | Monthly-only manual tuning cadence | Too slow for current iteration needs. |
| 12 | One-shot “big model” replacement for all pricing | High risk and weak debuggability vs incremental layered upgrades. |

## Session Log

- 2026-04-01: Initial BTC-profit ideation - 27 candidates generated, 7 survived.
- 2026-04-01: Refinement pass (replace largest loss trade) - 18 candidates generated, 6 survived.

## Refinement Pass: Replace Largest Loss Trade

### 1. Counterfactual Entry Replacement Gate
**Description:** Before opening a BTC trade, score the current candidate against 1-2 best alternative markets in the same snapshot and only open if it is top-ranked by downside-adjusted expected value.
**Rationale:** Current bottleneck is a few repeated high-loss trades (not broad signal scarcity). Replacing bad entries with better contemporaneous alternatives is higher leverage than tuning exits on the same bad entry.
**Downsides:** Needs low-latency in-strategy scoring and careful tie-break logic to avoid over-filtering.
**Confidence:** 93%
**Complexity:** Medium
**Status:** Unexplored

### 2. Market-Level Probation With Graduated Reinstatement
**Description:** Add per-market probation states (`active -> probation -> quarantined`) using recent realized loss clusters and re-enable only after replay-validated recovery criteria.
**Rationale:** Existing cooldown/quarantine is broad; repeated offenders can still come back too quickly. A market-specific rehabilitation path directly targets recurring outliers like current top loss markets.
**Downsides:** If criteria are too strict, trade count can collapse.
**Confidence:** 91%
**Complexity:** Medium
**Status:** Unexplored

### 3. Family-Aware Trade Budget Router (Reach vs Dip)
**Description:** Allocate a dynamic per-family trade budget each run and force routing toward the family with better recent edge-capture quality instead of taking whichever signal appears first.
**Rationale:** Current losses cluster by family behavior. Budget routing improves replacement quality while preserving `closed>=3`.
**Downsides:** Misestimated family quality may temporarily suppress profitable opportunities.
**Confidence:** 87%
**Complexity:** Medium
**Status:** Unexplored

### 4. Exit Replay Micro-Policy (Per-Market Exit Mode Memory)
**Description:** Persist per-market exit outcomes (`IOC fill`, `passive expired`, `adverse reversal`) and choose initial exit mode from recent market-specific success profile.
**Rationale:** Existing global exit policy oscillates between preserving trade count and reducing slippage. Market-level memory can reduce repeated wrong first-exit choices.
**Downsides:** Adds state complexity and potential stale-policy risk across regime shifts.
**Confidence:** 84%
**Complexity:** Medium
**Status:** Unexplored

### 5. Notional Haircut for Fragile Closers
**Description:** Apply automatic size haircut on markets with poor close efficiency (high time-stop share + high passive expiry rate), while keeping full size on stable closers.
**Rationale:** If bad trades cannot be fully removed yet, shrinking their blast radius improves PnL distribution without losing all closures.
**Downsides:** May slow upside if market quality recovers quickly.
**Confidence:** 86%
**Complexity:** Low
**Status:** Unexplored

### 6. Replay-Driven “Do Not Re-Enter Same Signature” Filter
**Description:** Fingerprint high-loss entries by microstructure signature (spread band, depth, quote age, premium bucket) and block re-entry of matching signatures for a cooling horizon.
**Rationale:** Current logic blocks by market/time, but many losses repeat by condition pattern. Signature-level suppression targets root recurrence.
**Downsides:** Signature design can overfit if too granular.
**Confidence:** 82%
**Complexity:** High
**Status:** Unexplored

## Refinement Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Continue broad threshold sweeps only | Already plateaued across multiple runs, low incremental value. |
| 2 | Force all time-stop exits to IOC | Helps closure count but repeatedly worsens slippage on some markets. |
| 3 | Open selective taker globally | Reintroduced severe outlier losses in dip markets. |
| 4 | Remove reentry blocks to raise count | Increases repeated low-quality churn and tail risk. |
| 5 | Raise default notional to dilute fixed costs | Multiplies drawdown on current fragile entry set. |
| 6 | Merge reach/dip into one unified preset | Conflicts with observed family-specific behavior. |
| 7 | Purely extend passive TTL everywhere | Does not reliably improve filtered PnL and can reduce closure certainty. |
| 8 | Drop closed-trade count gate from evaluation | Hides stability risk rather than solving it. |
