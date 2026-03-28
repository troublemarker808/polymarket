# Unified Phase 1 Task Breakdown

## 1. Purpose

This document turns the Phase 1 sections of the crypto, sports, and weather
roadmaps into one concrete implementation checklist with suggested file landing
points.

This document covers only Phase 1 work:

- crypto alpha foundation
- sports pregame alpha foundation
- weather forecast probability foundation

It does **not** cover Phase 2 execution expansion, Phase 3 portfolio risk, or
Phase 4 operating maturity.

Acceptance summary:

- see `docs/PHASE1_ACCEPTANCE_SUMMARY.md`


## 2. Phase 1 Working Rules

1. Keep the current V1 strategies intact while Phase 1 research code is being
   built.
2. Put new board-specific Phase 1 logic under
   `src/pm_bot/strategies/<board>/phase1/`.
3. Put shared replay and artifact plumbing under `src/pm_bot/research/`.
4. Only add new shared dataclasses to `src/pm_bot/core/` if they are useful to
   at least two boards.
5. Every Phase 1 task must land with:
   - code
   - unit tests
   - at least one fixture set
   - replay artifact output
6. Do not start Phase 2 work for any board until that board passes its own
   Phase 1 exit criteria.


## 3. Recommended Execution Order

Build order across the three boards:

1. shared Phase 1 scaffolding
2. crypto Phase 1
3. sports Phase 1
4. weather Phase 1

Reason:

- crypto has the fastest feedback loop
- sports Phase 1 depends on cleaner event normalization discipline
- weather Phase 1 benefits from the replay and artifact conventions built for
  the first two boards


## 4. Shared File Landing Map

Use this as the default landing map unless later implementation proves a better
boundary.

### Shared code

- `src/pm_bot/core/research_types.py`
  - shared dataclasses for normalized market definitions, fair-value outputs,
    and attribution rows
- `src/pm_bot/research/phase1_runner.py`
  - common Phase 1 replay entry point and run orchestration
- `src/pm_bot/research/phase1_artifacts.py`
  - artifact writing helpers for summary, metrics, attribution, and per-trade
    outputs

### Shared config layout

- `configs/profiles/research-crypto-phase1-v1/`
- `configs/profiles/research-sports-phase1-v1/`
- `configs/profiles/research-weather-phase1-v1/`

Each profile directory should contain:

- `base.example.toml`
- board-specific example config:
  - `crypto.v1.example.toml`
  - `sports.v1.example.toml`
  - `weather.v1.example.toml`

### Shared artifacts and fixtures

- `data/research/phase1/crypto/`
- `data/research/phase1/sports/`
- `data/research/phase1/weather/`
- `tests/fixtures/crypto_phase1/`
- `tests/fixtures/sports_phase1/`
- `tests/fixtures/weather_phase1/`

### Shared tests

- `tests/unit/research/test_phase1_runner.py`
- `tests/unit/research/test_phase1_artifacts.py`
- `tests/integration/test_phase1_profiles.py`


## 5. Shared Phase 1 Tasks

These tasks should be completed once before board-specific Phase 1 work starts.

### P1-SHARED-01: Research Types

Goal:

- create a minimal shared type layer for Phase 1 research loops

Suggested file landing:

- `src/pm_bot/core/research_types.py`

Suggested contents:

- `NormalizedMarketDefinition`
- `FairValueEstimate`
- `NetEdgeEstimate`
- `ReplayAttributionRow`
- `Phase1RunSummary`

Tests:

- `tests/unit/core/test_research_types.py`

Done when:

- all three boards can import shared research dataclasses without touching
  board-specific strategy files


### P1-SHARED-02: Replay Runner

Goal:

- create a shared Phase 1 replay harness that wraps existing replay plumbing
  without forking the whole runtime

Suggested file landing:

- `src/pm_bot/research/phase1_runner.py`

Integration points:

- reuse `src/pm_bot/research/engine.py`
- reuse `src/pm_bot/research/replay.py`
- do not duplicate event-router setup logic

Tests:

- `tests/unit/research/test_phase1_runner.py`

Done when:

- one command path can run board-specific Phase 1 replay jobs and emit stable
  artifacts


### P1-SHARED-03: Artifact Writer

Goal:

- standardize how Phase 1 jobs write summaries, metrics, attribution, and
  replay outputs

Suggested file landing:

- `src/pm_bot/research/phase1_artifacts.py`

Artifact contract:

- `summary.md`
- `metrics.json`
- `fair_values.jsonl`
- `attribution.jsonl`

Tests:

- `tests/unit/research/test_phase1_artifacts.py`

Done when:

- crypto, sports, and weather Phase 1 jobs can all emit the same top-level
  artifact shape into `data/research/phase1/<board>/<run_id>/`


### P1-SHARED-04: Board-Scoped Research Profiles

Goal:

- create isolated config entry points for each board's Phase 1 work

Suggested file landing:

- `configs/profiles/research-crypto-phase1-v1/base.example.toml`
- `configs/profiles/research-crypto-phase1-v1/crypto.v1.example.toml`
- `configs/profiles/research-sports-phase1-v1/base.example.toml`
- `configs/profiles/research-sports-phase1-v1/sports.v1.example.toml`
- `configs/profiles/research-weather-phase1-v1/base.example.toml`
- `configs/profiles/research-weather-phase1-v1/weather.v1.example.toml`

Tests:

- `tests/integration/test_phase1_profiles.py`

Done when:

- each board can run Phase 1 research in isolation with no unrelated strategy
  enabled


## 6. Crypto Phase 1 Task Breakdown

Target scope:

- BTC yearly `dip / reach` ladders
- ETH yearly `dip / reach` ladders

Do not expand scope during Phase 1:

- no short-dated narrative markets
- no multi-underlying portfolio logic
- no production maker / taker routing work


### P1-CRYPTO-01: Ladder Scope and Market Normalization

Modules:

- `crypto_market_taxonomy`
- `crypto_market_normalizer`
- `crypto_series_builder`

Suggested file landing:

- `src/pm_bot/strategies/crypto/phase1/__init__.py`
- `src/pm_bot/strategies/crypto/phase1/models.py`
- `src/pm_bot/strategies/crypto/phase1/normalization.py`
- `src/pm_bot/strategies/crypto/phase1/series.py`

Tests:

- `tests/unit/strategies/test_crypto_phase1_normalization.py`
- `tests/unit/strategies/test_crypto_phase1_series.py`

Fixtures:

- `tests/fixtures/crypto_phase1/market_catalog.json`
- `tests/fixtures/crypto_phase1/ladder_snapshots.jsonl`

Done when:

- the same BTC or ETH event family always normalizes to the same structured
  definition
- all rungs in one ladder can be grouped deterministically
- unsupported crypto market families are rejected explicitly


### P1-CRYPTO-02: Underlying and Regime Inputs

Modules:

- `underlying_state_service`
- `volatility_regime_engine`
- `time_decay_engine`

Suggested file landing:

- `src/pm_bot/strategies/crypto/phase1/inputs.py`

Tests:

- `tests/unit/strategies/test_crypto_phase1_inputs.py`

Fixtures:

- `tests/fixtures/crypto_phase1/underlying_state.json`

Done when:

- the pricing layer can request spot, realized vol, distance-to-barrier, and
  time-to-expiry from one consistent input object


### P1-CRYPTO-03: Fair Value and Curve Logic

Modules:

- `barrier_probability_model`
- `surface_consistency_model`
- `cross_anchor_model`
- `fair_value_fusion`

Suggested file landing:

- `src/pm_bot/strategies/crypto/phase1/pricing.py`
- `src/pm_bot/strategies/crypto/phase1/fusion.py`

Tests:

- `tests/unit/strategies/test_crypto_phase1_pricing.py`
- `tests/unit/strategies/test_crypto_phase1_fusion.py`

Fixtures:

- `tests/fixtures/crypto_phase1/fair_value_cases.json`

Done when:

- each ladder rung can produce `fair_probability`
- the full strip can be shape-checked together
- fused fair values are stable enough for replay


### P1-CRYPTO-04: Net Edge, Replay, and Attribution

Modules:

- `net_edge_calculator`
- `crypto_replay_lab`
- `pnl_attribution_engine`

Suggested file landing:

- `src/pm_bot/strategies/crypto/phase1/edge.py`
- `src/pm_bot/strategies/crypto/phase1/replay.py`
- `src/pm_bot/strategies/crypto/phase1/attribution.py`

Tests:

- `tests/unit/strategies/test_crypto_phase1_edge.py`
- `tests/unit/strategies/test_crypto_phase1_replay.py`
- `tests/unit/strategies/test_crypto_phase1_attribution.py`

Artifacts:

- `data/research/phase1/crypto/<run_id>/summary.md`
- `data/research/phase1/crypto/<run_id>/metrics.json`
- `data/research/phase1/crypto/<run_id>/fair_values.jsonl`
- `data/research/phase1/crypto/<run_id>/attribution.jsonl`

Done when:

- replay can show raw edge vs net edge
- attribution can split prediction error from execution drag
- at least one BTC or ETH ladder subset can be ranked by replay quality


## 7. Sports Phase 1 Task Breakdown

Target scope:

- one league only
- one market family only
- pregame only

Recommended first target:

- NBA pregame moneyline

Do not expand scope during Phase 1:

- no live state ingestion
- no totals or spreads
- no multi-league modeling


### P1-SPORTS-01: Event Scope and Market Normalization

Modules:

- `sports_market_taxonomy`
- `sports_market_normalizer`
- `event_schedule_builder`

Suggested file landing:

- `src/pm_bot/strategies/sports/phase1/__init__.py`
- `src/pm_bot/strategies/sports/phase1/models.py`
- `src/pm_bot/strategies/sports/phase1/normalization.py`

Tests:

- `tests/unit/strategies/test_sports_phase1_normalization.py`

Fixtures:

- `tests/fixtures/sports_phase1/nba_market_catalog.json`
- `tests/fixtures/sports_phase1/nba_pregame_snapshots.jsonl`

Done when:

- the same game always maps to one stable event definition
- all selected pregame moneyline markets map cleanly to league, teams, and
  start time
- unsupported sports markets are rejected explicitly


### P1-SPORTS-02: Pregame Feature and Anchor Pipeline

Modules:

- `pregame_feature_pipeline`
- `odds_anchor_engine`
- `injury_lineup_engine`
- `travel_rest_engine`

Suggested file landing:

- `src/pm_bot/strategies/sports/phase1/features.py`
- `src/pm_bot/strategies/sports/phase1/anchors.py`

Tests:

- `tests/unit/strategies/test_sports_phase1_features.py`
- `tests/unit/strategies/test_sports_phase1_anchors.py`

Fixtures:

- `tests/fixtures/sports_phase1/nba_feature_cases.json`

Done when:

- one pregame feature object exists for every supported event
- anchor probability and model adjustments are separated cleanly


### P1-SPORTS-03: Fair Value and Closing-Line Validation

Modules:

- `pregame_fair_value_model`
- `line_dislocation_model`
- `closing_line_lab`

Suggested file landing:

- `src/pm_bot/strategies/sports/phase1/pricing.py`
- `src/pm_bot/strategies/sports/phase1/validation.py`

Tests:

- `tests/unit/strategies/test_sports_phase1_pricing.py`
- `tests/unit/strategies/test_sports_phase1_validation.py`

Fixtures:

- `tests/fixtures/sports_phase1/closing_line_cases.json`

Done when:

- the model can emit `fair_probability` for the chosen pregame market family
- dislocations can be ranked
- CLV-style validation can be measured in replay


### P1-SPORTS-04: Replay and Attribution

Modules:

- `sports_replay_lab`
- `pnl_attribution_engine`

Suggested file landing:

- `src/pm_bot/strategies/sports/phase1/replay.py`
- `src/pm_bot/strategies/sports/phase1/attribution.py`

Tests:

- `tests/unit/strategies/test_sports_phase1_replay.py`
- `tests/unit/strategies/test_sports_phase1_attribution.py`

Artifacts:

- `data/research/phase1/sports/<run_id>/summary.md`
- `data/research/phase1/sports/<run_id>/metrics.json`
- `data/research/phase1/sports/<run_id>/fair_values.jsonl`
- `data/research/phase1/sports/<run_id>/attribution.jsonl`

Done when:

- replay can compare predicted edge to closing movement
- attribution can distinguish model error, timing error, and fill error
- one league and one pregame market family can be scored consistently


## 8. Weather Phase 1 Task Breakdown

Target scope:

- one repeatable location family
- one threshold market family
- one settlement source

Recommended first target:

- daily high-temperature threshold markets for a fixed city set

Do not expand scope during Phase 1:

- no rainfall / wind / snowfall expansion
- no multi-source settlement support
- no forecast-run execution routing work


### P1-WEATHER-01: Market, Location, and Settlement Normalization

Modules:

- `weather_market_taxonomy`
- `weather_market_normalizer`
- `location_mapping_service`
- `settlement_mapping_service`

Suggested file landing:

- `src/pm_bot/strategies/weather/phase1/__init__.py`
- `src/pm_bot/strategies/weather/phase1/models.py`
- `src/pm_bot/strategies/weather/phase1/normalization.py`
- `src/pm_bot/strategies/weather/phase1/settlement.py`

Tests:

- `tests/unit/strategies/test_weather_phase1_normalization.py`
- `tests/unit/strategies/test_weather_phase1_settlement.py`

Fixtures:

- `tests/fixtures/weather_phase1/market_catalog.json`
- `tests/fixtures/weather_phase1/location_mapping.json`

Done when:

- every supported weather market maps deterministically to location, threshold,
  date, and settlement source
- settlement ambiguity is reduced to explicit rejections or explicit mapping


### P1-WEATHER-02: Forecast Ingestion and Skill Correction

Modules:

- `forecast_run_calendar`
- `forecast_ingestor`
- `model_skill_store`
- `bias_correction_engine`

Suggested file landing:

- `src/pm_bot/strategies/weather/phase1/forecasts.py`
- `src/pm_bot/strategies/weather/phase1/skill.py`

Tests:

- `tests/unit/strategies/test_weather_phase1_forecasts.py`
- `tests/unit/strategies/test_weather_phase1_skill.py`

Fixtures:

- `tests/fixtures/weather_phase1/forecast_runs.json`
- `tests/fixtures/weather_phase1/model_skill_cases.json`

Done when:

- forecast runs can be loaded with clean timestamps and horizons
- historical skill and bias adjustments can be applied before pricing


### P1-WEATHER-03: Distribution, Threshold Pricing, and Fusion

Modules:

- `forecast_distribution_builder`
- `threshold_probability_model`
- `strip_consistency_model`
- `fair_value_fusion`

Suggested file landing:

- `src/pm_bot/strategies/weather/phase1/pricing.py`
- `src/pm_bot/strategies/weather/phase1/fusion.py`

Tests:

- `tests/unit/strategies/test_weather_phase1_pricing.py`
- `tests/unit/strategies/test_weather_phase1_fusion.py`

Fixtures:

- `tests/fixtures/weather_phase1/threshold_cases.json`

Done when:

- a full threshold probability can be computed from forecast inputs
- the threshold strip can be monotonicity-checked
- fused fair values are stable enough for replay


### P1-WEATHER-04: Replay and Attribution

Modules:

- `weather_replay_lab`
- `pnl_attribution_engine`

Suggested file landing:

- `src/pm_bot/strategies/weather/phase1/replay.py`
- `src/pm_bot/strategies/weather/phase1/attribution.py`

Tests:

- `tests/unit/strategies/test_weather_phase1_replay.py`
- `tests/unit/strategies/test_weather_phase1_attribution.py`

Artifacts:

- `data/research/phase1/weather/<run_id>/summary.md`
- `data/research/phase1/weather/<run_id>/metrics.json`
- `data/research/phase1/weather/<run_id>/fair_values.jsonl`
- `data/research/phase1/weather/<run_id>/attribution.jsonl`

Done when:

- replay can compare fair threshold probability to realized market behavior
- attribution can separate forecast error from settlement-mapping error
- one repeatable weather family can be scored cleanly


## 9. Cross-Board Exit Checklist

Do not call Phase 1 complete for a board until all are true:

- supported markets normalize deterministically
- fair values can be produced for the majority of in-scope markets
- replay artifacts are stable and auditable
- net edge can be measured
- attribution can explain wins and losses in board-native terms


## 10. Immediate Next Implementation Sequence

If implementation starts now, the first ten tasks should be:

1. `P1-SHARED-01`
2. `P1-SHARED-02`
3. `P1-SHARED-03`
4. `P1-SHARED-04`
5. `P1-CRYPTO-01`
6. `P1-CRYPTO-02`
7. `P1-CRYPTO-03`
8. `P1-CRYPTO-04`
9. `P1-SPORTS-01`
10. `P1-WEATHER-01`

After that, keep finishing one board at a time rather than partially building
all three in parallel.
