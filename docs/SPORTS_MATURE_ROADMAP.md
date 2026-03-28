# Sports Mature Roadmap

## 1. Purpose

This document defines the phased maturity roadmap for the sports trading stack.
It turns the current sports strategy direction into a concrete execution plan
that can be tracked over time.

Current sports starting points:

- [`sports.anchor`](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/anchor/strategy.py)
- [`sports.live`](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/live/strategy.py)

Scope of this roadmap:

- sports only
- pregame first, live second
- one league and one market family first
- replay-first, then paper, then shadow, then small live


## 2. End State

The mature sports stack should be able to answer these questions clearly for
every trade:

1. What sport, league, and market family does this market belong to?
2. Is this a pregame trade or a live trade?
3. What is the fair probability and which inputs moved it?
4. Is the edge real after spread, slippage, and stale-feed risk?
5. Should the order be maker, taker, or skipped?
6. What event state invalidates the trade?
7. How much total risk is already tied to this game, team, and league?
8. After the trade closes, was PnL driven by prediction quality, execution, or
   delayed data?


## 3. Trading Domain Focus

Do not mature all sports markets at once.

Primary target for maturity:

- one league only
- one market family only
- start with pregame moneyline markets

Recommended initial target:

- NBA pregame moneyline

Deferred until the first target is mature:

- live moneyline
- totals
- spreads
- player props
- multi-league support

Reason:

- pregame is easier to validate than live
- one league reduces hidden data-quality differences
- moneyline is the cleanest first sports probability problem


## 4. Module Inventory

The full mature-state sports roadmap uses these modules:

1. `sports_market_taxonomy`
2. `sports_market_normalizer`
3. `event_schedule_builder`
4. `pregame_feature_pipeline`
5. `odds_anchor_engine`
6. `injury_lineup_engine`
7. `travel_rest_engine`
8. `pregame_fair_value_model`
9. `line_dislocation_model`
10. `closing_line_lab`
11. `live_state_ingestor`
12. `state_transition_model`
13. `stale_feed_guard`
14. `live_fair_value_fusion`
15. `signal_classifier`
16. `net_edge_calculator`
17. `trade_eligibility_filter`
18. `execution_router`
19. `order_construction_engine`
20. `position_intent_tracker`
21. `exit_engine`
22. `reentry_control`
23. `sport_exposure_aggregator`
24. `event_risk_manager`
25. `sports_replay_lab`
26. `pnl_attribution_engine`
27. `strategy_scorecard`
28. `sports_strategy_config_registry`
29. `promotion_pipeline`


## 5. Phase Structure

The sports roadmap is phased. Do not build live execution machinery before the
pregame edge is proven.

Phase order:

1. Prove pregame alpha exists
2. Prove pregame alpha can be traded
3. Extend to live with stale-feed discipline
4. Prove the strategy can be operated and promoted


## 6. Phase 1: Pregame Alpha Foundation

### Goal

Build the smallest complete research loop that can answer:

`Does one sports league and one sports market family contain repeatable, net-positive pregame edge?`

Detailed Phase 1 task breakdown and file landing:

- [`PHASE1_TASK_BREAKDOWN.md`](/D:/dev/polymarket_bot2.0/docs/PHASE1_TASK_BREAKDOWN.md)

### Modules

1. `sports_market_taxonomy`
2. `sports_market_normalizer`
3. `event_schedule_builder`
4. `pregame_feature_pipeline`
5. `odds_anchor_engine`
6. `injury_lineup_engine`
7. `travel_rest_engine`
8. `pregame_fair_value_model`
9. `line_dislocation_model`
10. `closing_line_lab`
11. `sports_replay_lab`
12. `pnl_attribution_engine`

### Responsibilities

`sports_market_taxonomy`

- classify sport, league, and market family
- reject unsupported sports market types explicitly

`sports_market_normalizer`

- normalize teams, start time, market side, and resolution rules
- standardize mapping from market metadata to a deterministic event definition

`event_schedule_builder`

- build a stable event object around game start, teams, and league
- map multiple markets to the same sporting event

`pregame_feature_pipeline`

- assemble pregame model inputs
- examples:
  - market odds
  - public consensus
  - home / away
  - team strength
  - recent form
  - likely starters

`odds_anchor_engine`

- treat the sharpest available market odds as an anchor
- convert odds to a clean implied baseline probability

`injury_lineup_engine`

- model the effect of injuries, scratches, and lineup changes
- quantify when news is strong enough to move fair probability

`travel_rest_engine`

- model fatigue, back-to-back, altitude, travel, and rest asymmetry

`pregame_fair_value_model`

- produce fair probability for the chosen market family
- explicitly separate anchor probability from model adjustment

`line_dislocation_model`

- measure how far the market is from fair
- score both raw edge and context-adjusted edge

`closing_line_lab`

- track whether the market moves toward or away from your fair estimate
- measure CLV-like validation

`sports_replay_lab`

- replay historical pregame snapshots and news updates
- produce research-grade outputs

`pnl_attribution_engine`

- separate prediction error from execution error
- record when loss came from bad model, bad timing, or bad fill

### Deliverables

- stable event normalization for one league
- one reliable pregame fair-value model
- research reports showing expected edge vs closing movement
- attribution per event and per trade

### Exit Criteria

Do not leave Phase 1 until all are true:

- one league and one market family replay cleanly end to end
- fair probability exists for the majority of replayed events
- CLV-like validation can be measured
- replay identifies at least one repeatable tradable subset
- attribution clearly explains wins and losses


## 7. Phase 2: Pregame Execution Maturity

### Goal

Answer:

`If pregame edge exists, can it be captured without giving it away in execution?`

### Modules

1. `signal_classifier`
2. `net_edge_calculator`
3. `trade_eligibility_filter`
4. `execution_router`
5. `order_construction_engine`
6. `position_intent_tracker`
7. `exit_engine`
8. `reentry_control`

### Responsibilities

`signal_classifier`

- classify signals by confidence and expected horizon
- distinguish between:
  - strong pregame dislocation
  - weak pregame dislocation
  - no-trade

`net_edge_calculator`

- convert raw edge into net edge after:
  - spread
  - expected exit cost
  - slippage
  - execution delay budget

`trade_eligibility_filter`

- reject low-confidence trades
- reject thin or stale markets
- reject edges that do not survive friction

`execution_router`

- choose maker, taker, or skip
- route based on urgency and expected line movement

`order_construction_engine`

- construct order price, size, and ttl
- support passive-first behavior for slower-moving pregame opportunities

`position_intent_tracker`

- store the reason a pregame trade exists
- record expected pregame holding horizon and intended exit condition

`exit_engine`

- exit when:
  - price converges to fair
  - pregame thesis is invalidated
  - game is close enough to start that edge no longer matters

`reentry_control`

- prevent repetitive re-entry after failed fills or failed exits

### Deliverables

- net-edge gating for pregame trades
- maker / taker selection policy
- explicit pregame exit rules

### Exit Criteria

- the system can explain why each order was maker, taker, or skipped
- repeated failed re-entry loops are blocked
- execution reports show whether alpha survives actual fills


## 8. Phase 3: Live Sports Expansion

### Goal

Answer:

`Can a live sports strategy operate only when data freshness is strong enough to justify trading?`

### Modules

1. `live_state_ingestor`
2. `state_transition_model`
3. `stale_feed_guard`
4. `live_fair_value_fusion`

### Responsibilities

`live_state_ingestor`

- ingest score, clock, possession-like state, timeout state, penalties, and
  official game status

`state_transition_model`

- estimate fair probability from live state
- model how the next state updates expected win probability

`stale_feed_guard`

- reject trades if live state is stale relative to market state
- treat data freshness as a first-order trading constraint

`live_fair_value_fusion`

- fuse live model, market odds, and state confidence into one fair value

### Deliverables

- live fair probability for one sport and one live market family
- explicit stale-feed rejection rules

### Exit Criteria

- live state freshness can be measured on every decision
- the system can reject live trades when the data is not fresh enough
- live replay proves that stale-state rejection avoids bad trades


## 9. Phase 4: Portfolio and Operating Maturity

### Goal

Answer:

`Can the sports strategy be scored, controlled, and promoted as a stable subsystem?`

### Modules

1. `sport_exposure_aggregator`
2. `event_risk_manager`
3. `strategy_scorecard`
4. `sports_strategy_config_registry`
5. `promotion_pipeline`

### Responsibilities

`sport_exposure_aggregator`

- aggregate risk by event, team, league, and market family

`event_risk_manager`

- cap over-concentration in one game or one correlated thesis

`strategy_scorecard`

- score by league, market family, execution mode, and time bucket

`sports_strategy_config_registry`

- keep per-league and per-market-family configuration separate

`promotion_pipeline`

- move the strategy through:
  - replay
  - paper
  - shadow
  - small live
  - scaled live

### Deliverables

- game-level and league-level risk tracking
- per-family configuration discipline
- promotion criteria based on evidence rather than intuition

### Exit Criteria

- event-level concentration is visible and controllable
- strategy performance can be compared by sport and market family
- promotion and rollback can be justified with repeatable evidence


## 10. Recommended Build Order

### Now

1. `sports_market_taxonomy`
2. `sports_market_normalizer`
3. `event_schedule_builder`
4. `pregame_feature_pipeline`
5. `odds_anchor_engine`
6. `injury_lineup_engine`
7. `travel_rest_engine`
8. `pregame_fair_value_model`
9. `line_dislocation_model`
10. `closing_line_lab`
11. `sports_replay_lab`
12. `pnl_attribution_engine`

### After pregame alpha is proven

13. `signal_classifier`
14. `net_edge_calculator`
15. `trade_eligibility_filter`
16. `execution_router`
17. `order_construction_engine`
18. `position_intent_tracker`
19. `exit_engine`
20. `reentry_control`

### After pregame execution is stable

21. `live_state_ingestor`
22. `state_transition_model`
23. `stale_feed_guard`
24. `live_fair_value_fusion`

### After live discipline is proven

25. `sport_exposure_aggregator`
26. `event_risk_manager`
27. `strategy_scorecard`
28. `sports_strategy_config_registry`
29. `promotion_pipeline`


## 11. Progress Tracking Template

### Phase 1

- [ ] `sports_market_taxonomy`
- [ ] `sports_market_normalizer`
- [ ] `event_schedule_builder`
- [ ] `pregame_feature_pipeline`
- [ ] `odds_anchor_engine`
- [ ] `injury_lineup_engine`
- [ ] `travel_rest_engine`
- [ ] `pregame_fair_value_model`
- [ ] `line_dislocation_model`
- [ ] `closing_line_lab`
- [ ] `sports_replay_lab`
- [ ] `pnl_attribution_engine`

### Phase 2

- [ ] `signal_classifier`
- [ ] `net_edge_calculator`
- [ ] `trade_eligibility_filter`
- [ ] `execution_router`
- [ ] `order_construction_engine`
- [ ] `position_intent_tracker`
- [ ] `exit_engine`
- [ ] `reentry_control`

### Phase 3

- [ ] `live_state_ingestor`
- [ ] `state_transition_model`
- [ ] `stale_feed_guard`
- [ ] `live_fair_value_fusion`

### Phase 4

- [ ] `sport_exposure_aggregator`
- [ ] `event_risk_manager`
- [ ] `strategy_scorecard`
- [ ] `sports_strategy_config_registry`
- [ ] `promotion_pipeline`


## 12. Decisions That Must Stay Explicit

- Which league is in scope right now?
- Which sports market family is in scope right now?
- Is the strategy pregame-only or live-enabled right now?
- What exact data freshness threshold is required for live trading?
- What exact replay evidence is required before promotion?

If those answers become vague, the roadmap is drifting.


## 13. Immediate Next Step

The first concrete milestone should be:

`Build a research-complete pregame moneyline loop for one league`

That milestone includes:

- deterministic event normalization
- pregame feature pipeline
- odds anchor plus model adjustment
- fair probability
- line dislocation scoring
- replay validation
- CLV-style review
- attribution

Until that milestone exists, do not spend major effort on multi-league live
trading.
