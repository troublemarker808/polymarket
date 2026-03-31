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
