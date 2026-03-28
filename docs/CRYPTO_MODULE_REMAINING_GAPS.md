# Crypto Module Remaining Gaps 2026-03-28

## 1. Current Status

The crypto module is now beyond prototype stage.

It already has:

- Phase 1 pricing and calibration research
- Phase 2 execution policy
- replay and suite entrypoints
- continuous paper wiring
- ladder-series selection
- file-backed runtime underlying-state context
- bounded paper-session cleanup with no dangling positions or pending orders

It is not yet mature.

The current bottlenecks are no longer basic plumbing. They are mostly:

- eventful window discovery
- runtime market selection depth
- final fair-value calibration
- runtime execution feedback
- portfolio-level crypto risk aggregation

## 2. Remaining Gaps By Priority

### P0. Eventful Window Mining

Why it is now first:

- bounded paper and replay runs are operationally stable
- the latest ETH and BTC fixed-window experiments classify as `alpha-bound`
- current baseline windows often produce `0` useful submissions, so execution tuning is no longer the best next lever

What is missing:

- mining eventful windows from longer paper-session captures
- separating fill-bearing windows from dead windows before fixed-window experiments
- promoting mined windows into train/validation/holdout sets
- standardizing ETH and BTC window families so one overpriced yearly strip does not dominate calibration

Primary file targets:

- `src/pm_bot/research/window_mining.py`
- `src/pm_bot/research/autoresearch.py`
- `src/pm_bot/research/experiments.py`
- `docs/CRYPTO_PHASE2_EXECUTION_HARDENING_20260328.md`

Expected effect:

- higher-signal replay windows
- clearer attribution between "no alpha" and "execution too conservative"
- less wasted tuning on dead windows

Acceptance criteria:

- latest long crypto captures can be mined into fill-bearing fixed windows
- fixed-window reports distinguish mined windows from low-information baselines
- at least one promoted window contains non-zero useful submissions before more execution tuning

### P1. Runtime Market Selection

Why it is still open:

- the ladder filter exists
- but it is still closer to research gating than a full runtime selection layer

What is missing:

- family-specific selection rules for BTC vs ETH ladders
- spread/depth quality gates
- stale-quote and stale-trade guards
- dynamic runtime blocklists for toxic series
- stricter separation of "research-valid" vs "runtime-tradable"

Primary file targets:

- `src/pm_bot/strategies/crypto/phase1/selection.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/strategies/crypto/phase2/strategy.py`

Expected effect:

- fewer low-value runtime signals
- cleaner opportunity set
- lower order churn on structurally bad ladders

Acceptance criteria:

- runtime can skip bad series before signal generation
- BTC and ETH ladders can be filtered differently
- market quality reasons are visible in artifacts

### P1. Fair-Value Final Calibration

Why it is still open:

- current baseline is usable
- but it is not final across BTC/ETH, dip/reach, and expiry structure
- the current zero-activity windows suggest the pricing stack is still overly conservative on the remaining ladders

What is missing:

- larger runtime sample sets
- family-specific calibration buckets
- repricing calibration, not only static fair-value gap checks
- promotion of the best calibration set into an official locked baseline

Primary file targets:

- `src/pm_bot/strategies/crypto/phase1/calibration.py`
- `src/pm_bot/strategies/crypto/phase1/pricing.py`
- `src/pm_bot/strategies/crypto/phase1/fusion.py`
- `docs/CRYPTO_CALIBRATION_*.md`

Expected effect:

- fewer false negatives on windows that actually contain repricing
- better separation between tradable and overpriced strips
- more stable net-edge distribution

Acceptance criteria:

- locked calibration baseline documented
- ETH and BTC validation windows both pass baseline sanity checks
- calibration reports stop oscillating around obviously inconsistent candidates

### P2. Runtime Execution Feedback

Why it is still open:

- current metrics tell us what happened
- they do not yet feed back strongly enough into route selection or suppression

What is missing:

- route-quality scoring by market family
- taker shortfall analysis by signal type
- maker non-fill clustering by series
- adaptive downgrade from taker to maker or skip
- adaptive quarantine after repeated low-quality fills

Primary file targets:

- `src/pm_bot/strategies/crypto/phase2/management.py`
- `src/pm_bot/strategies/crypto/phase2/execution.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/runtime/paper_session.py`

Expected effect:

- fewer low-quality repeat entries
- cleaner route choice under real paper conditions
- lower execution drag without widening risk

Acceptance criteria:

- runtime can explain why a route was selected or suppressed
- repeated poor fills alter later routing behavior
- repeated non-fills alter later maker aggressiveness or suppression

### P3. Portfolio and Ladder Risk Aggregation

Why it is still open:

- current controls are still dominated by single-position and global account rules
- crypto ladders need underlying-level and strip-level aggregation

What is missing:

- underlying exposure aggregation
- ladder one-sided exposure limits
- expiry bucket exposure caps
- regime-aware kill switches
- correlated-position budgeting

Primary file targets:

- `src/pm_bot/risk/manager.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- new crypto-specific risk helpers under `src/pm_bot/strategies/crypto/phase2/`

Expected effect:

- better control of correlated crypto risk
- fewer hidden ladder concentration problems
- cleaner promotion path toward shadow/live

Acceptance criteria:

- BTC/ETH exposure is visible at runtime
- one ladder cannot silently dominate category risk
- regime contraction can reduce activity automatically

## 3. Concrete Next Build Order

Recommended sequence:

1. mine eventful windows from longer captures
2. deepen runtime market selection
3. finalize fair-value calibration baseline
4. add runtime execution feedback
5. add portfolio and ladder aggregation

This order is intentional:

- bounded paper and replay are already stable enough to move the bottleneck forward
- window mining and selection determine whether there is any tradable alpha to expose
- calibration finalization is more reliable after window quality improves
- execution feedback matters most once non-empty opportunities exist
- portfolio aggregation matters most once per-trade behavior is trustworthy

## 4. What Is Not A Priority Right Now

These are not the main blockers anymore:

- CLI entrypoints
- replay artifact generation
- paper wiring
- time-in-force propagation
- basic ladder-series blocking
- same-snapshot exit safety

Those pieces are already present and working well enough to move the bottleneck forward.

## 5. Current Definition Of "Mature Enough"

The crypto module should be considered mature enough for the next promotion step only when:

- entry does not create obvious toxic fills by construction
- runtime selection filters structurally bad ladders before they create churn
- calibration baseline is documented and stable across BTC and ETH families
- mined windows prove there is non-zero useful activity under the current fair-value stack
- BTC/ETH ladder exposure is aggregated at runtime

Until then, the module is best described as:

- operational in research and paper
- execution-stable
- still opportunity-sparse on current runtime windows
- not yet promotion-ready
