# Crypto Mature Roadmap

## 1. Purpose

This document turns the current crypto strategy direction into a phased
implementation roadmap so future work can be tracked against a stable target.

Scope of this roadmap:

- crypto only
- focused first on BTC / ETH price ladders
- replay-first, then paper, then shadow, then small live

This roadmap does **not** assume the current crypto strategies are already
mature. The current system is treated as a V1 scaffold:

- [`crypto.surface`](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/surface/strategy.py)
- [`crypto.maker`](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/maker/strategy.py)


## 2. End State

The mature crypto stack should be able to answer these questions clearly for
every trade:

1. What exact market family does this market belong to?
2. What is the fair probability and why?
3. Is the edge large enough **after** spread, slippage, and exit cost?
4. Should the order be maker, taker, or skipped?
5. What is the expected holding period and expected exit path?
6. How does this trade affect total BTC / ETH ladder exposure?
7. After the trade closes, was profit or loss driven by prediction, execution,
   or exit logic?


## 3. Trading Domain Focus

Do not try to mature all crypto market types at once.

Primary target for maturity:

- BTC yearly `dip / reach` ladder markets
- ETH yearly `dip / reach` ladder markets

Deferred until the ladder flow is mature:

- time-window direction markets
- single binary narrative markets
- volatility regime markets

Reason:

- ladders are the most structured
- ladders create repeatable replay samples
- ladders expose both pricing and execution problems quickly


## 4. Module Inventory

The full mature-state crypto roadmap uses these modules:

1. `crypto_market_taxonomy`
2. `crypto_market_normalizer`
3. `crypto_series_builder`
4. `underlying_state_service`
5. `volatility_regime_engine`
6. `time_decay_engine`
7. `barrier_probability_model`
8. `surface_consistency_model`
9. `cross_anchor_model`
10. `fair_value_fusion`
11. `signal_classifier`
12. `net_edge_calculator`
13. `trade_eligibility_filter`
14. `execution_router`
15. `order_construction_engine`
16. `execution_feedback_loop`
17. `position_intent_tracker`
18. `exit_engine`
19. `reentry_control`
20. `crypto_exposure_aggregator`
21. `series_risk_manager`
22. `regime_kill_switch`
23. `crypto_replay_lab`
24. `pnl_attribution_engine`
25. `strategy_scorecard`
26. `crypto_strategy_config_registry`
27. `promotion_pipeline`


## 5. Phase Structure

The roadmap is intentionally phased. Do not build all 27 modules in one linear
pass before validating edge.

Phase order:

1. Prove alpha exists
2. Prove alpha can be traded
3. Prove the strategy can run as a portfolio
4. Prove it can be operated and promoted


## 6. Phase 1: Alpha Foundation

### Goal

Build the smallest complete research loop that can answer:

`Do BTC / ETH ladder markets contain repeatable, net-positive pricing edge?`

Detailed Phase 1 task breakdown and file landing:

- [`PHASE1_TASK_BREAKDOWN.md`](/D:/dev/polymarket_bot2.0/docs/PHASE1_TASK_BREAKDOWN.md)

### Modules

1. `crypto_market_taxonomy`
2. `crypto_market_normalizer`
3. `crypto_series_builder`
4. `underlying_state_service`
5. `volatility_regime_engine`
6. `time_decay_engine`
7. `barrier_probability_model`
8. `surface_consistency_model`
9. `cross_anchor_model`
10. `fair_value_fusion`
11. `net_edge_calculator`
12. `crypto_replay_lab`
13. `pnl_attribution_engine`

### Responsibilities

`crypto_market_taxonomy`

- classify market family from metadata
- reject unsupported crypto market types explicitly

`crypto_market_normalizer`

- extract underlying, direction, barrier, expiry, event family
- normalize `yes/no` token mapping
- produce a deterministic structured market definition

`crypto_series_builder`

- group all ladder markets into a full strip
- ensure same underlying + expiry + event family are linked

`underlying_state_service`

- provide spot, returns, realized vol, distance-to-barrier
- expose a standard snapshot of BTC / ETH state

`volatility_regime_engine`

- label low / normal / high vol environments
- estimate sigma and jump-risk proxy

`time_decay_engine`

- compute time to expiry
- map raw expiry into an effective trading horizon

`barrier_probability_model`

- estimate fair probability of hitting each ladder barrier
- use underlying distance, volatility, and remaining time

`surface_consistency_model`

- fit a smooth fair curve across the whole strip
- identify local and global shape violations

`cross_anchor_model`

- compare ladder pricing to external anchors
- adjust for option-like move expectations or other external regimes

`fair_value_fusion`

- combine barrier, curve-fit, and external-anchor views
- emit final `fair_probability`, `confidence`, `half_life`

`net_edge_calculator`

- convert raw mispricing into net tradable edge
- subtract entry spread, exit spread, slippage, and adverse-selection budget

`crypto_replay_lab`

- replay historical sessions deterministically
- output signal-by-signal research artifacts

`pnl_attribution_engine`

- split expected alpha vs realized alpha
- isolate prediction error from execution error

### Deliverables

- stable ladder market normalization
- fair probability for BTC / ETH ladders
- replay reports with expected vs realized edge
- attribution per trade and per market family

### Exit Criteria

Do not leave Phase 1 until all are true:

- the system can replay ladder markets end to end
- fair probability can be computed for the majority of target ladder markets
- edge can be measured in net terms, not raw terms
- replay results identify at least one repeatable tradable subset
- attribution can explain why wins and losses happened

### Key Risk

You may learn that the current ladder idea has weak edge after transaction
frictions. That is acceptable. The point of Phase 1 is to find out early.


## 7. Phase 2: Execution Maturity

### Goal

Answer:

`If edge exists, can the system capture it without giving it away in execution?`

### Modules

1. `signal_classifier`
2. `trade_eligibility_filter`
3. `execution_router`
4. `order_construction_engine`
5. `position_intent_tracker`
6. `exit_engine`
7. `reentry_control`
8. `execution_feedback_loop`

### Responsibilities

`signal_classifier`

- classify opportunities as:
  - `resolution_edge`
  - `repricing_edge`
  - `liquidity_edge`
  - `no_trade`

`trade_eligibility_filter`

- reject trades with insufficient confidence
- reject trades with insufficient net edge
- reject trades with poor market quality

`execution_router`

- choose maker, taker, or skip
- route based on spread, half-life, expected exit cost, and urgency

`order_construction_engine`

- build actual order shape
- handle quote price, slicing, ttl, passive-first rules, taker override rules

`position_intent_tracker`

- store why a position was opened
- record signal type, expected holding period, expected exit mode

`exit_engine`

- manage exits through:
  - fair value reached
  - thesis invalidated
  - time stop
  - risk-forced exit

`reentry_control`

- prevent repeated stop-out loops
- support cooldowns and quarantine after repeated failures

`execution_feedback_loop`

- learn from fill quality
- update maker / taker preference using realized fill outcomes

### Deliverables

- explicit maker / taker routing policy
- position-level trade intent storage
- board-aware exit rules
- repeated-loss and reentry controls

### Exit Criteria

- the system can explain why each trade was maker, taker, or skipped
- stop-loss or loss-cluster loops are blocked
- execution reports show whether alpha is being lost at entry or exit
- repeated expiration patterns are visible and actionable

### Key Risk

Execution may destroy the alpha even if pricing is good. This phase exists to
measure that directly.


## 8. Phase 3: Portfolio and Risk Maturity

### Goal

Answer:

`Can the crypto strategy run as a portfolio instead of as isolated single trades?`

### Modules

1. `crypto_exposure_aggregator`
2. `series_risk_manager`
3. `regime_kill_switch`

### Responsibilities

`crypto_exposure_aggregator`

- aggregate exposure by:
  - underlying
  - direction
  - expiry bucket
  - ladder family

`series_risk_manager`

- manage one-sided strip concentration
- cap correlated ladder exposure
- prevent the same thesis from appearing diversified when it is not

`regime_kill_switch`

- shrink or halt strategy under:
  - extreme volatility
  - spread blowout
  - bad fill regime
  - degraded data

### Deliverables

- ladder-level exposure dashboard
- underlying-level crypto exposure limits
- extreme-regime protection rules

### Exit Criteria

- exposure can be measured at ladder and underlying level
- the system can cap correlated risk before a cluster of markets fails together
- regime transitions produce predictable strategy shrinkage behavior


## 9. Phase 4: Operating Maturity

### Goal

Answer:

`Is the crypto strategy stable enough to score, configure, and promote over time?`

### Modules

1. `strategy_scorecard`
2. `crypto_strategy_config_registry`
3. `promotion_pipeline`

### Responsibilities

`strategy_scorecard`

- score performance by:
  - market family
  - underlying
  - signal type
  - execution mode

`crypto_strategy_config_registry`

- manage per-family configs cleanly
- avoid using one global parameter set for all crypto market types

`promotion_pipeline`

- move strategy through:
  - replay
  - paper
  - shadow
  - small live
  - scaled live

### Deliverables

- stable per-family config organization
- scorecard for promote / pause / retire decisions
- promotion checklist for each deployment stage

### Exit Criteria

- the strategy can be promoted or rolled back using clear evidence
- configs are family-specific and versioned
- performance review is repeatable and not anecdotal


## 10. Recommended Build Order

This is the recommended execution order across all phases.

### Now

1. `crypto_market_taxonomy`
2. `crypto_market_normalizer`
3. `crypto_series_builder`
4. `underlying_state_service`
5. `volatility_regime_engine`
6. `time_decay_engine`
7. `barrier_probability_model`
8. `surface_consistency_model`
9. `cross_anchor_model`
10. `fair_value_fusion`
11. `net_edge_calculator`
12. `crypto_replay_lab`
13. `pnl_attribution_engine`

### After alpha is proven

14. `signal_classifier`
15. `trade_eligibility_filter`
16. `execution_router`
17. `order_construction_engine`
18. `position_intent_tracker`
19. `exit_engine`
20. `reentry_control`
21. `execution_feedback_loop`

### After execution quality is proven

22. `crypto_exposure_aggregator`
23. `series_risk_manager`
24. `regime_kill_switch`

### After portfolio behavior is stable

25. `strategy_scorecard`
26. `crypto_strategy_config_registry`
27. `promotion_pipeline`


## 11. Progress Tracking Template

Use the checklist below to track implementation.

### Phase 1

- [ ] `crypto_market_taxonomy`
- [ ] `crypto_market_normalizer`
- [ ] `crypto_series_builder`
- [ ] `underlying_state_service`
- [ ] `volatility_regime_engine`
- [ ] `time_decay_engine`
- [ ] `barrier_probability_model`
- [ ] `surface_consistency_model`
- [ ] `cross_anchor_model`
- [ ] `fair_value_fusion`
- [ ] `net_edge_calculator`
- [ ] `crypto_replay_lab`
- [ ] `pnl_attribution_engine`

### Phase 2

- [ ] `signal_classifier`
- [ ] `trade_eligibility_filter`
- [ ] `execution_router`
- [ ] `order_construction_engine`
- [ ] `position_intent_tracker`
- [ ] `exit_engine`
- [ ] `reentry_control`
- [ ] `execution_feedback_loop`

### Phase 3

- [ ] `crypto_exposure_aggregator`
- [ ] `series_risk_manager`
- [ ] `regime_kill_switch`

### Phase 4

- [ ] `strategy_scorecard`
- [ ] `crypto_strategy_config_registry`
- [ ] `promotion_pipeline`


## 12. Decisions That Must Stay Explicit

These decisions should never remain implicit while the roadmap is executed:

- What exact crypto market family is in scope right now?
- What exact fair probability formula is being used right now?
- What exact conditions allow taker orders?
- What exact conditions force exit?
- What exact replay evidence is required before promotion?

If those answers are vague, the roadmap is drifting.


## 13. Immediate Next Step

The first concrete implementation milestone should be:

`Build a research-complete BTC / ETH ladder pricing loop`

That milestone includes:

- deterministic ladder normalization
- ladder grouping
- barrier fair probability
- curve consistency fit
- fused fair probability
- net edge output
- replay attribution

Until that milestone exists, do not spend major effort on production
promotion, scaling, or broad market coverage.
