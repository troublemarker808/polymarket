# Weather Mature Roadmap

## 1. Purpose

This document defines the phased maturity roadmap for the weather trading stack.
It turns the current weather strategy direction into a concrete execution plan
that can be tracked over time.

Current weather starting points:

- [`weather.ensemble`](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/ensemble/strategy.py)
- [`weather.threshold`](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/threshold/strategy.py)

Scope of this roadmap:

- weather only
- one location family and one weather event family first
- forecast-distribution-first, then execution maturity
- replay-first, then paper, then shadow, then small live


## 2. End State

The mature weather stack should be able to answer these questions clearly for
every trade:

1. What weather event family does this market belong to?
2. Which location, station, and official settlement source apply?
3. What is the forecast distribution, not just the mean forecast?
4. What is the fair probability of crossing the settlement threshold?
5. How much of that edge survives spread, slippage, and settlement ambiguity?
6. Is the market moving because of a new forecast run or because of noise?
7. How much correlated exposure already exists for this location or weather
   system?
8. After the trade closes, was PnL driven by forecast quality, execution, or
   settlement mapping error?


## 3. Trading Domain Focus

Do not try to mature all weather markets at once.

Primary target for maturity:

- one repeatable location family
- one threshold market family
- one official settlement source

Recommended initial target:

- daily high-temperature threshold markets for a fixed set of cities

Deferred until the first target is mature:

- rainfall totals
- snowfall
- wind events
- hurricane path / regional events
- multi-source settlement families

Reason:

- daily threshold weather markets are highly repeatable
- settlement rules are easier to normalize
- model skill can be measured over many repeated samples


## 4. Module Inventory

The full mature-state weather roadmap uses these modules:

1. `weather_market_taxonomy`
2. `weather_market_normalizer`
3. `location_mapping_service`
4. `forecast_run_calendar`
5. `forecast_ingestor`
6. `model_skill_store`
7. `bias_correction_engine`
8. `forecast_distribution_builder`
9. `threshold_probability_model`
10. `strip_consistency_model`
11. `settlement_mapping_service`
12. `fair_value_fusion`
13. `signal_classifier`
14. `net_edge_calculator`
15. `trade_eligibility_filter`
16. `execution_router`
17. `order_construction_engine`
18. `position_intent_tracker`
19. `exit_engine`
20. `reentry_control`
21. `geo_exposure_aggregator`
22. `weather_system_risk_manager`
23. `run_event_router`
24. `weather_replay_lab`
25. `pnl_attribution_engine`
26. `strategy_scorecard`
27. `weather_strategy_config_registry`
28. `promotion_pipeline`


## 5. Phase Structure

The weather roadmap is phased. Do not optimize execution before the weather
probability engine and settlement mapping are reliable.

Phase order:

1. Prove forecast-to-threshold alpha exists
2. Prove alpha can be traded around forecast runs
3. Prove correlated weather-system risk can be controlled
4. Prove the strategy can be operated and promoted


## 6. Phase 1: Forecast Probability Foundation

### Goal

Build the smallest complete research loop that can answer:

`Do repeated weather threshold markets contain repeatable, net-positive edge after forecast and settlement mapping are handled correctly?`

Detailed Phase 1 task breakdown and file landing:

- [`PHASE1_TASK_BREAKDOWN.md`](/D:/dev/polymarket_bot2.0/docs/PHASE1_TASK_BREAKDOWN.md)

### Modules

1. `weather_market_taxonomy`
2. `weather_market_normalizer`
3. `location_mapping_service`
4. `forecast_run_calendar`
5. `forecast_ingestor`
6. `model_skill_store`
7. `bias_correction_engine`
8. `forecast_distribution_builder`
9. `threshold_probability_model`
10. `strip_consistency_model`
11. `settlement_mapping_service`
12. `fair_value_fusion`
13. `weather_replay_lab`
14. `pnl_attribution_engine`

### Responsibilities

`weather_market_taxonomy`

- classify weather event family
- reject unsupported weather market types explicitly

`weather_market_normalizer`

- normalize location, threshold, event date, and market direction
- produce a deterministic structured market definition

`location_mapping_service`

- map market location names to actual forecast and settlement points
- handle station aliases and geography normalization

`forecast_run_calendar`

- track official model run times
- expose forecast release schedule as a first-class object

`forecast_ingestor`

- ingest model forecasts and related weather inputs
- keep run timestamps and horizon metadata clean

`model_skill_store`

- maintain historical model accuracy by:
  - location
  - season
  - lead time
  - event family

`bias_correction_engine`

- correct known forecast bias patterns
- avoid treating raw model output as directly tradable probability

`forecast_distribution_builder`

- turn forecast inputs into a full probability distribution
- not just a point estimate

`threshold_probability_model`

- calculate settlement probability for the chosen threshold event
- map distribution to `fair_yes_probability`

`strip_consistency_model`

- fit and validate the entire threshold strip
- enforce monotonic structure and detect local dislocations

`settlement_mapping_service`

- map the market to its actual official measurement source
- reduce false alpha caused by misunderstood settlement rules

`fair_value_fusion`

- fuse corrected forecast distribution, strip shape, and settlement mapping
- emit final `fair_probability`, `confidence`, `half_life`

`weather_replay_lab`

- replay historical forecast runs and market snapshots
- produce research-grade validation artifacts

`pnl_attribution_engine`

- separate prediction error, execution error, and settlement-mapping error

### Deliverables

- normalized threshold weather market definitions
- location and settlement mapping
- forecast distribution to threshold probability pipeline
- replay reports with expected vs realized edge
- attribution per market family and location cluster

### Exit Criteria

Do not leave Phase 1 until all are true:

- one weather market family replays cleanly end to end
- settlement mapping is deterministic and auditable
- fair probability exists for the majority of replayed target markets
- replay identifies at least one repeatable tradable subset
- attribution can distinguish forecast error from settlement misunderstanding


## 7. Phase 2: Forecast-Run Execution Maturity

### Goal

Answer:

`If weather edge exists, can it be captured around forecast-run events without bleeding it away in execution?`

### Modules

1. `signal_classifier`
2. `net_edge_calculator`
3. `trade_eligibility_filter`
4. `run_event_router`
5. `execution_router`
6. `order_construction_engine`
7. `position_intent_tracker`
8. `exit_engine`
9. `reentry_control`

### Responsibilities

`signal_classifier`

- classify trades by forecast-run event type and signal strength
- distinguish:
  - new-information repricing
  - slow mispricing
  - no-trade

`net_edge_calculator`

- convert raw forecast edge into net edge after:
  - spread
  - expected exit cost
  - forecast-update decay
  - execution drag

`trade_eligibility_filter`

- reject trades with poor net edge
- reject ambiguous settlement cases
- reject stale or incomplete forecast-state markets

`run_event_router`

- decide whether a new forecast run should trigger trading
- distinguish true information events from routine market noise

`execution_router`

- choose maker, taker, or skip
- route based on urgency after a forecast update

`order_construction_engine`

- construct order price, size, and ttl around forecast-run timing

`position_intent_tracker`

- record whether the trade expects:
  - immediate repricing
  - slow convergence
  - hold toward settlement

`exit_engine`

- exit when:
  - edge is consumed
  - newer forecast invalidates the thesis
  - settlement approaches and informational edge disappears

`reentry_control`

- prevent re-entry loops after failed run-event trades

### Deliverables

- run-aware routing policy
- net-edge gating for weather trades
- explicit exit logic tied to forecast updates

### Exit Criteria

- the system can explain which forecast run triggered each trade
- maker / taker routing is tied to information urgency
- repeated failed re-entry patterns are blocked
- execution reports show whether forecast alpha survives fills


## 8. Phase 3: Correlation and Weather-System Risk

### Goal

Answer:

`Can the weather strategy control correlated exposure across cities and weather systems?`

### Modules

1. `geo_exposure_aggregator`
2. `weather_system_risk_manager`

### Responsibilities

`geo_exposure_aggregator`

- aggregate exposure by:
  - city
  - region
  - forecast horizon
  - event family

`weather_system_risk_manager`

- identify when multiple markets are really one underlying weather-system bet
- cap concentration across correlated geographies

### Deliverables

- geography-level exposure dashboard
- event-family and weather-system concentration limits

### Exit Criteria

- risk can be measured by geography and event family
- the system can detect when multiple markets share one weather-system thesis
- correlated losses can be traced to a risk bucket instead of isolated markets


## 9. Phase 4: Operating Maturity

### Goal

Answer:

`Can the weather strategy be scored, configured, and promoted as a stable subsystem?`

### Modules

1. `strategy_scorecard`
2. `weather_strategy_config_registry`
3. `promotion_pipeline`

### Responsibilities

`strategy_scorecard`

- score by:
  - location
  - event family
  - forecast horizon
  - execution mode
  - forecast-run cohort

`weather_strategy_config_registry`

- keep per-location-family and per-event-family configuration separate

`promotion_pipeline`

- move the strategy through:
  - replay
  - paper
  - shadow
  - small live
  - scaled live

### Deliverables

- per-location and per-family scorecards
- versioned weather-specific config structure
- evidence-based promotion criteria

### Exit Criteria

- strategy performance can be reviewed by location and event family
- configuration is not one-size-fits-all
- promotion and rollback decisions are repeatable


## 10. Recommended Build Order

### Now

1. `weather_market_taxonomy`
2. `weather_market_normalizer`
3. `location_mapping_service`
4. `forecast_run_calendar`
5. `forecast_ingestor`
6. `model_skill_store`
7. `bias_correction_engine`
8. `forecast_distribution_builder`
9. `threshold_probability_model`
10. `strip_consistency_model`
11. `settlement_mapping_service`
12. `fair_value_fusion`
13. `weather_replay_lab`
14. `pnl_attribution_engine`

### After alpha is proven

15. `signal_classifier`
16. `net_edge_calculator`
17. `trade_eligibility_filter`
18. `run_event_router`
19. `execution_router`
20. `order_construction_engine`
21. `position_intent_tracker`
22. `exit_engine`
23. `reentry_control`

### After execution quality is proven

24. `geo_exposure_aggregator`
25. `weather_system_risk_manager`

### After portfolio behavior is stable

26. `strategy_scorecard`
27. `weather_strategy_config_registry`
28. `promotion_pipeline`


## 11. Progress Tracking Template

### Phase 1

- [ ] `weather_market_taxonomy`
- [ ] `weather_market_normalizer`
- [ ] `location_mapping_service`
- [ ] `forecast_run_calendar`
- [ ] `forecast_ingestor`
- [ ] `model_skill_store`
- [ ] `bias_correction_engine`
- [ ] `forecast_distribution_builder`
- [ ] `threshold_probability_model`
- [ ] `strip_consistency_model`
- [ ] `settlement_mapping_service`
- [ ] `fair_value_fusion`
- [ ] `weather_replay_lab`
- [ ] `pnl_attribution_engine`

### Phase 2

- [ ] `signal_classifier`
- [ ] `net_edge_calculator`
- [ ] `trade_eligibility_filter`
- [ ] `run_event_router`
- [ ] `execution_router`
- [ ] `order_construction_engine`
- [ ] `position_intent_tracker`
- [ ] `exit_engine`
- [ ] `reentry_control`

### Phase 3

- [ ] `geo_exposure_aggregator`
- [ ] `weather_system_risk_manager`

### Phase 4

- [ ] `strategy_scorecard`
- [ ] `weather_strategy_config_registry`
- [ ] `promotion_pipeline`


## 12. Decisions That Must Stay Explicit

- Which weather event family is in scope right now?
- Which location set is in scope right now?
- Which station or official settlement source is authoritative right now?
- Which forecast runs are tradable right now?
- What exact replay evidence is required before promotion?

If those answers become vague, the roadmap is drifting.


## 13. Immediate Next Step

The first concrete milestone should be:

`Build a research-complete threshold probability loop for one repeated weather market family`

That milestone includes:

- deterministic market normalization
- location and settlement mapping
- forecast-run ingestion
- bias-corrected forecast distribution
- threshold probability
- strip consistency validation
- replay attribution

Until that milestone exists, do not spend major effort on broad weather-market
coverage or operational scaling.
