# Mature-Version Gap Plan

Last updated: 2026-03-29

## 1. Purpose

This document turns the current repo review into one bounded execution plan:

- clarify what "mature version" means for this repository
- state the biggest gaps between current state and that target
- define the order in which those gaps should be closed
- prevent the project from mixing research growth, live risk, and UI polish into one blurry stream

This is a control document, not a brainstorming note.

## 2. Recommended Target

Do **not** define the next mature version as:

- sports + crypto + weather all mature at the same time
- broad live rollout
- full operator product with polished GUI

That target is too wide for the repo's current stage.

Recommended target for the next mature version:

`crypto-only mature foundation`

Meaning:

- crypto has a trustworthy replay -> paper -> sync-shadow -> micro-live promotion path
- risk protections are real, not just config declarations
- runtime evidence is stable enough to justify promote / pause / rollback decisions
- operator artifacts are clear enough for non-technical use

Sports and weather stay in research/replay stage until crypto reaches this bar.

## 3. Current Stage Assessment

### Overall repo

Current overall stage:

- architecture-complete foundation
- broad paper/replay tooling
- not yet mature

Best current stage label for the whole repo:

- `paper available`

Not acceptable labels yet:

- `shadow available`
- `small live available`
- `production-ready`

### Crypto

Current crypto stage:

- strong research and paper scaffold
- execution-stable enough for further hardening
- still missing real runtime protections and promotion governance

Best current stage label:

- `paper available, preparing for shadow / small-live validation`

### Sports and weather

Current sports/weather stage:

- research and replay direction exists
- mature-roadmap documents exist
- promotion path is not the bottleneck because the strategy maturity itself is not there yet

Best current stage label:

- `research / replay available`

## 4. Hard Truths

These are the most important current truths and should stay explicit.

1. The repo is not a toy. Structure, runtime modules, replay tooling, and tests are already substantial.
2. The repo is also not mature. Good structure is not the same thing as promotion readiness.
3. The next bottleneck is not adding more categories. It is making crypto risk, evidence, and promotion logic trustworthy.
4. A risk rule that exists only in config is not a real protection.
5. A profile that validates as `ready=true` is not enough to call the runtime ready for real-money validation.

## 5. Not In Scope Right Now

These items were considered and intentionally deferred.

- mature sports live rollout
  - reason: sports still needs narrower alpha proof before execution promotion matters
- mature weather live rollout
  - reason: weather still needs stronger settlement and distribution maturity first
- full GUI product redesign
  - reason: operator surface matters, but the main problem is still runtime trustworthiness
- broad multi-board orchestration
  - reason: one mature board is more valuable than three half-ready boards
- large parameter search while hard safety gaps remain open
  - reason: tuning on top of untrusted runtime behavior produces false confidence

## 6. Gap List

## P0. Real Protection Gaps

These are stop-the-line gaps. Do not call the system mature until all are closed.

### P0.1 Risk config is richer than runtime enforcement

Problem:

- some risk settings exist in config and docs but are not fully wired into halt or approval behavior

Examples:

- `risk.kill_switch_on_stale_data_seconds`
- `risk.halt_on_data_source_failure`
- `trading.max_notional_per_market`
- `trading.max_notional_per_category`

Why this matters:

- the operator may believe a protection exists when it does not actually stop or block anything

Primary code targets:

- `src/pm_bot/risk/manager.py`
- `src/pm_bot/runtime/live_session.py`
- `src/pm_bot/runtime/paper_session.py`
- `src/pm_bot/core/settings.py`

Acceptance:

- stale-data and repeated data-source failure can halt the runtime when configured to do so
- per-market and per-category notional caps are enforced in order approval
- runtime artifacts show which protection fired and why

### P0.2 Repo output contracts are drifting

Problem:

- test baselines are no longer fully aligned with emitted events and dashboard lines

Observed evidence:

- `pytest` currently fails on replay baseline output and dashboard contract expectations

Why this matters:

- research artifacts stop being trustworthy the moment output shape changes without baseline control

Primary code targets:

- `tests/fixtures/replay_baseline/expected.events.jsonl`
- `tests/unit/research/test_replay_baseline.py`
- `tests/unit/runtime/test_dashboard.py`
- event emitters and dashboard serializers that changed shape

Acceptance:

- full pytest is green again
- replay and dashboard contract changes are intentional and documented

### P0.3 Validation tooling is incomplete on a fresh environment

Problem:

- repo defines `mypy` and `ruff`, but this environment could not run either because they were not installed

Why this matters:

- a mature repo should have one obvious path to run the full validation set

Primary code targets:

- `pyproject.toml`
- validation / setup docs
- optional local helper scripts if needed

Acceptance:

- one documented command path exists for tests + lint + type-check
- fresh operator or contributor setup does not silently skip static gates

## P1. Crypto Paper Maturity Gaps

These are the next bottlenecks after P0.

### P1.1 Window quality is still too weak

Problem:

- many crypto runtime windows are low-information
- zero-activity or low-fill windows make later tuning noisy

Why this matters:

- without eventful windows, the system cannot tell "no alpha" from "dead market window"

Primary code and doc targets:

- `src/pm_bot/research/window_mining.py`
- `src/pm_bot/research/experiments.py`
- `src/pm_bot/research/autoresearch.py`
- `docs/CRYPTO_MODULE_REMAINING_GAPS.md`

Acceptance:

- long paper captures can be mined into eventful train / validation windows
- replay reports clearly separate dead windows from tradable windows

### P1.2 Runtime selection is better, but still not mature policy

Problem:

- crypto runtime selection has improved, especially around blocked series and blocked markets
- it is still not a full runtime tradability policy

What is still missing:

- stronger family-specific rules
- better spread and depth filters
- stale quote / stale trade quality gates
- dynamic quarantine rules from runtime evidence

Primary code targets:

- `src/pm_bot/strategies/crypto/phase1/selection.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/strategies/crypto/phase2/strategy.py`

Acceptance:

- runtime opportunity set is smaller, cleaner, and explicitly explained
- market-family block / allow reasons appear in operator-facing artifacts

### P1.3 Fair-value calibration is usable, not final

Problem:

- current calibration and selection work are meaningful
- they still do not justify calling the pricing layer mature

Why this matters:

- mature promotion requires stable BTC / ETH family-specific calibration, not just one promising round

Primary code and doc targets:

- `src/pm_bot/strategies/crypto/phase1/calibration.py`
- `src/pm_bot/strategies/crypto/phase1/pricing.py`
- `src/pm_bot/strategies/crypto/phase1/fusion.py`
- `docs/CRYPTO_CALIBRATION_*.md`

Acceptance:

- one locked calibration baseline exists
- BTC and ETH validation windows both pass the same baseline sanity bar

### P1.4 Execution feedback is recorded more than it is used

Problem:

- runtime records fills, expiries, and route outcomes
- that evidence still does not sufficiently change later route or suppression behavior

Primary code targets:

- `src/pm_bot/strategies/crypto/phase2/execution.py`
- `src/pm_bot/strategies/crypto/phase2/management.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/runtime/paper_session.py`

Acceptance:

- repeated bad maker behavior changes later maker policy
- repeated bad taker behavior changes later taker policy
- operator artifacts can explain that adaptation

## P2. Promotion-Path Gaps

These gaps block trustworthy shadow and small-live progression.

### P2.1 Portfolio risk is still too flat

Problem:

- current controls are mostly account-level, order-count-level, and single-position-level
- crypto ladders need underlying-level and strip-level aggregation

Primary code targets:

- `src/pm_bot/risk/manager.py`
- crypto-specific helpers under `src/pm_bot/strategies/crypto/phase2/`

Acceptance:

- BTC / ETH exposure is visible at runtime
- one ladder family cannot silently dominate category risk

### P2.2 Small-live baseline is an observation profile, not a mature live gate

Problem:

- current small-live profile is useful for evidence collection
- it should not be confused with a mature promotion profile

Why this matters:

- its relaxed halt thresholds are acceptable for baseline sampling, but not for calling the system mature

Primary doc targets:

- `docs/SMALL_LIVE_BASELINE.md`
- `docs/SYNC_NORMAL_SHADOW_MODE.md`

Acceptance:

- there is an explicit promotion checklist between sync-shadow and small-live
- baseline live profiles and promotion live profiles are clearly separated

### P2.3 Operator alerting is still mostly local state and logs

Problem:

- data failures and recoveries are recorded
- external alerting and escalation are still weak

Primary code targets:

- `src/pm_bot/risk/manager.py`
- `src/pm_bot/runtime/live_session.py`
- `src/pm_bot/runtime/paper_session.py`

Acceptance:

- repeated runtime degradation can surface a clear operator alert
- severe repeated failure can escalate to halt when configured

## P3. Operator Product Gaps

These are important, but they come after runtime trust.

### P3.1 Operator surface is still CLI-first

Problem:

- the current operator experience is mainly command-line plus text artifacts

Why this matters:

- this repo serves non-technical usage patterns, so maturity eventually requires a clearer control surface

Primary code targets:

- `src/pm_bot/cli.py`
- runtime dashboard and artifact surface
- later dedicated UI/control-console work

Acceptance:

- an operator can understand state, risk, last decision, and required action without reading raw code or raw event logs

## 7. Closure Order

This is the recommended sequence. Do not reorder casually.

### Phase A. Restore truthfulness

Goal:

- make the repo say only what it can really prove

Tasks:

1. close P0.2 output-contract drift
2. close P0.1 real-protection wiring
3. close P0.3 validation-tooling path

Exit gate:

- full repo validation is green
- declared risk rules are actually executable

### Phase B. Make crypto paper evidence trustworthy

Goal:

- ensure crypto paper results can be used for real go / no-go decisions

Tasks:

1. close P1.1 eventful window mining
2. close P1.2 runtime selection maturity
3. close P1.3 fair-value baseline lock
4. close P1.4 execution feedback loop

Exit gate:

- crypto paper evidence is not dominated by dead windows
- opportunity set and suppression rules are explainable
- calibration baseline is stable

### Phase C. Make promotion logic trustworthy

Goal:

- move from "interesting paper system" to "controlled promotion path"

Tasks:

1. close P2.1 portfolio crypto risk
2. close P2.2 promotion checklist between paper / sync-shadow / small-live
3. close P2.3 alerting and escalation

Exit gate:

- crypto can be called `small-range real-environment validation ready`
- but only for crypto, not for the full multi-board repo

### Phase D. Improve operator usability

Goal:

- make the system operable by the intended non-technical owner

Tasks:

1. close P3.1 operator-facing state and control improvements
2. only after that, consider broader console work

Exit gate:

- the user can understand and operate the system through a controlled surface, not raw engineering internals

## 8. Recommended Build Strategy

There are three plausible paths.

### Option A. Crypto-first maturity

Time:

- fastest path to one trustworthy mature subsystem

Cost:

- lowest coordination cost

Stability:

- highest, because scope stays narrow

Expandability:

- strong, because later boards can reuse a proven promotion model

### Option B. Parallel maturity across crypto, sports, weather

Time:

- looks fast on paper, slows down in practice

Cost:

- highest

Stability:

- weakest, because evidence and risk policy stay fragmented

Expandability:

- poor, because three immature paths are harder to govern than one mature path

### Option C. UI/control-console first

Time:

- medium

Cost:

- medium

Stability:

- weak, because better presentation does not fix missing protections

Expandability:

- only useful after runtime trust improves

Recommendation:

- choose Option A, crypto-first maturity

Reason:

- it closes the real risk gap first, creates one mature template, and avoids turning the repo into three parallel half-finished systems

## 9. Immediate Next Build Queue

This is the recommended short queue from today.

1. restore green validation by fixing replay/dashboard contract drift
2. wire stale-data and data-source-failure settings into real halt behavior
3. wire per-market and per-category notional caps into actual order approval
4. define and document the crypto promotion checklist from paper -> sync-shadow -> small-live baseline
5. continue crypto window mining and calibration only after the first four items are closed

## 10. Success Definition For The Next Mature Version

The next mature version is achieved only when all are true:

- crypto runtime protections are real and test-backed
- repo validation is green and repeatable
- crypto paper artifacts are stable enough to guide promotion
- sync-shadow and small-live baseline paths are controlled and evidence-based
- operator-facing evidence is understandable without code reading

If those are not all true, the repo should still be described as:

- architecture-complete
- paper-capable
- improving
- not yet mature

