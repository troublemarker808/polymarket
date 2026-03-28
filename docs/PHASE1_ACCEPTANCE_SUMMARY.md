# Phase 1 Acceptance Summary

## 1. Scope

This document records the current acceptance state of the Phase 1 research
foundation across the three supported boards:

- crypto
- sports
- weather

It is intentionally short and operational. The goal is to answer:

1. what each board currently supports
2. what each board can now produce
3. what hard limits still remain before Phase 2 work starts


## 2. Unified Regression Status

Regression date:

- 2026-03-28

Command:

```powershell
python -m pytest tests\unit\core\test_research_types.py tests\unit\research\test_phase1_artifacts.py tests\unit\research\test_phase1_runner.py tests\integration\test_phase1_profiles.py tests\integration\test_cli_research.py tests\unit\test_cli.py tests\unit\strategies\test_crypto_phase1_normalization.py tests\unit\strategies\test_crypto_phase1_series.py tests\unit\strategies\test_crypto_phase1_inputs.py tests\unit\strategies\test_crypto_phase1_pricing.py tests\unit\strategies\test_crypto_phase1_fusion.py tests\unit\strategies\test_crypto_phase1_edge.py tests\unit\strategies\test_crypto_phase1_attribution.py tests\unit\strategies\test_crypto_phase1_replay.py tests\unit\strategies\test_sports_phase1_normalization.py tests\unit\strategies\test_sports_phase1_features.py tests\unit\strategies\test_sports_phase1_anchors.py tests\unit\strategies\test_sports_phase1_pricing.py tests\unit\strategies\test_sports_phase1_validation.py tests\unit\strategies\test_sports_phase1_attribution.py tests\unit\strategies\test_sports_phase1_replay.py tests\unit\strategies\test_weather_phase1_normalization.py tests\unit\strategies\test_weather_phase1_settlement.py tests\unit\strategies\test_weather_phase1_forecasts.py tests\unit\strategies\test_weather_phase1_skill.py tests\unit\strategies\test_weather_phase1_pricing.py tests\unit\strategies\test_weather_phase1_fusion.py tests\unit\strategies\test_weather_phase1_attribution.py tests\unit\strategies\test_weather_phase1_replay.py
```

Result:

- 56 tests passed
- shared Phase 1 scaffold passed
- crypto Phase 1 passed
- sports Phase 1 passed
- weather Phase 1 passed


## 3. Shared Phase 1 Foundation

Current shared support:

- common research dataclasses in `src/pm_bot/core/research_types.py`
- common replay harness in `src/pm_bot/research/phase1_runner.py`
- common artifact writer in `src/pm_bot/research/phase1_artifacts.py`
- board-scoped research profiles for crypto, sports, and weather
- CLI entry path for `phase1-replay`

Current shared outputs:

- `summary.md`
- `metrics.json`
- `fair_values.jsonl`
- `attribution.jsonl`

Current hard limits:

- this is still a research-only foundation, not a production execution layer
- Phase 1 outputs are stable for replay and inspection, not yet for automatic live promotion
- board-specific replay wrappers exist, but no cross-board orchestration job exists yet


## 4. Crypto Acceptance

Current supported scope:

- BTC yearly `dip / reach` ladders
- ETH yearly `dip / reach` ladders
- ladder normalization and deterministic strip grouping
- pricing inputs from underlying spot, volatility, and time-to-expiry
- barrier probability estimation
- surface consistency checks across the strip
- fused fair value generation
- net edge estimation
- replay and attribution output

Current outputs:

- normalized ladder market definitions
- ladder series objects
- pricing inputs and volatility regime labels
- per-market `fair_probability`, `confidence`, and `half_life_seconds`
- replay artifacts with net edge fields
- attribution rows that split predicted edge and execution drag

Current hard limits:

- only ladder-style crypto markets are supported
- no short-dated narrative markets
- no binary news/event crypto markets
- no maker/taker execution router in Phase 1
- no live position lifecycle or Phase 2 execution policy
- no ladder-level portfolio risk manager yet

Acceptance judgment:

- Phase 1 accepted as a research foundation for crypto
- crypto is the best candidate to enter Phase 2 first


## 5. Sports Acceptance

Current supported scope:

- NBA only
- pregame only
- moneyline only
- stable event normalization for one game definition
- pregame feature pipeline
- odds anchor selection
- injury, lineup, travel, and rest adjustments
- fair value and dislocation scoring
- closing-line review
- replay and attribution output

Current outputs:

- normalized event definitions and grouped schedules
- pregame feature objects per supported event
- anchor probability and adjustment decomposition
- per-market `fair_probability`, `confidence`, and edge measurements
- closing-line review rows
- replay artifacts and attribution rows

Current hard limits:

- no live markets
- no totals
- no spreads
- no multi-league support
- no independent sports data ingestion beyond the metadata and anchor assumptions already used in Phase 1
- no execution routing policy yet

Acceptance judgment:

- Phase 1 accepted as a narrow pregame research foundation
- sports should not enter live-style execution expansion before a stronger board-specific data layer exists


## 6. Weather Acceptance

Current supported scope:

- daily high-temperature threshold markets only
- fixed location mapping with explicit station mapping
- single settlement source mapping
- forecast run ingestion
- model skill loading
- bias correction
- forecast distribution building
- threshold probability estimation
- strip consistency checks across supported thresholds
- fair value fusion
- replay and attribution output

Current outputs:

- normalized weather market definitions
- explicit settlement mapping objects
- forecast run calendars
- bias-corrected forecast rows
- forecast distributions with weighted mean and sigma
- per-market `fair_probability`, `confidence`, and `half_life_seconds`
- replay artifacts and attribution rows

Current hard limits:

- only one weather family is supported: daily high-temperature thresholds
- location coverage is still explicitly whitelisted
- settlement support is still single-source
- no rainfall, wind, snowfall, hurricane, or path markets
- no forecast-run execution timing policy yet
- no production weather risk aggregation yet

Acceptance judgment:

- Phase 1 accepted as a weather probability research foundation
- weather should stay in research mode until location coverage and settlement mapping are broadened


## 7. Recommended Next Step

Recommended order after this acceptance checkpoint:

1. start Phase 2 with crypto only
2. keep sports and weather in Phase 1 refinement mode until broader data and market coverage are justified
3. treat this document as the boundary check before any Phase 2 execution work expands scope
