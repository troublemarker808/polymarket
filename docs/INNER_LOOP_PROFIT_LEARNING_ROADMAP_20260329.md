# Inner-Loop Profit And Learning Roadmap

## 1. Purpose

This roadmap replaces the previous "maturity-first / operator-first" direction
as the primary development focus.

The repository has already reached:

- crypto final version
- sports final version
- weather final version
- unified multi-board ops maturity
- long-running operator automation stability

That means the next bottleneck is no longer outer operating structure.

The new bottleneck is the inner loop:

- can the system improve profitability?
- can the system learn from its own outcomes?
- can the best inner-loop methods be migrated from crypto to sports and weather?


## 2. Core Principle

The system should now develop from inside out.

Priority order:

1. profitability
2. learning
3. stability maintenance
4. outer operating polish

Interpretation:

- stability remains mandatory, but it is now a maintained boundary rather than
  the main development target
- operator tooling should only change when it directly supports profitability or
  learning
- new category expansion is not the current goal


## 3. New End State

The target is no longer just "a mature system."

The target is:

`a stable, profitable, self-improving trading system`

This means the repository should eventually be able to answer all of these:

1. Which opportunities actually create repeatable edge after execution costs?
2. Which parameter family or strategy family is currently the best performer?
3. Which losses were caused by prediction error, execution error, or exit error?
4. Which strategy configurations should be downgraded, quarantined, or promoted?
5. What exact learning signal should be used to improve the next run?


## 4. Main Route

The main route from now on is:

1. strengthen crypto profitability core
2. strengthen crypto learning core
3. migrate proven methods into sports
4. migrate proven methods into weather
5. only then revisit additional outer-layer expansion


## 5. Phase A: Crypto Profit Core

### Goal

Increase repeatable net edge capture in crypto without weakening safety
boundaries.

### Main Question

`Why is a candidate trade profitable or unprofitable after execution, exit, and sizing are included?`

### Focus Areas

1. selection quality
2. fair-value quality
3. execution quality
4. exit quality
5. sizing quality

### Required Work

#### A1. Selection quality scoring

The current crypto selection layer is mature enough to block weak markets, but
it is still more eligibility-oriented than profitability-oriented.

Next upgrades:

- add score-oriented ranking instead of only `actionable / watch_only / blocked`
- compute expected profit quality by market family, not just tradability
- expose which filters correlate with realized good or bad outcomes

Target files:

- [selection.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase1/selection.py)
- [suite.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/suite.py)
- [final_report.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/final_report.py)

#### A2. Fair-value error decomposition

The current calibration and baseline lock are strong enough for maturity, but
they still need to become profit-oriented.

Next upgrades:

- measure not just calibration score, but profit relevance of calibration error
- separate:
  - barrier-model miss
  - fusion miss
  - late repricing miss
  - bad selection despite good fair value
- compare family-specific errors across BTC/ETH dip/reach presets

Target files:

- [calibration.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase1/calibration.py)
- [baseline.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase1/baseline.py)
- [replay.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase1/replay.py)

#### A3. Execution profitability breakdown

Execution feedback exists, but it is still too compact.

Next upgrades:

- compute profit impact of:
  - maker expiry
  - maker adverse fill
  - taker urgency
  - delayed entry
  - delayed exit
- compare expected edge vs captured edge at the trade level
- summarize "alpha lost in execution" more directly

Target files:

- [management.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/management.py)
- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/strategy.py)
- [final_report.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/final_report.py)

#### A4. Exit and holding-period quality

Current exits are mature enough to operate, but not yet optimized for profit.

Next upgrades:

- compare:
  - thesis-complete exits
  - time-stop exits
  - stop-loss exits
  - adverse-fill exits
- identify which exit families preserve profit and which are cutting winners or
  letting losers persist too long
- make scorecards explicitly report exit-quality contribution

Target files:

- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/strategy.py)
- [models.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/models.py)

#### A5. Sizing quality

Current sizing is safe and feedback-aware, but still relatively coarse.

Next upgrades:

- scale notional by:
  - family confidence
  - selection score
  - execution quality regime
  - current loss cluster state
- shrink low-conviction trades before they consume budget
- explicitly compare captured edge per notional bucket

Target files:

- [strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/strategy.py)
- [config_registry.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/config_registry.py)


## 6. Phase B: Crypto Learning Core

### Goal

Turn result collection into real strategy learning.

### Main Question

`How does the system decide what should be promoted, downgraded, or retried next?`

### Required Work

#### B1. Versioned strategy comparison

The system needs a first-class way to compare:

- preset A vs preset B
- baseline vs candidate
- previous winner vs current winner

Needed outputs:

- stable per-run comparison artifact
- win/loss by metric family
- explicit recommendation:
  - promote
  - keep current
  - quarantine

#### B2. Automatic attribution for learning

Learning needs stronger attribution categories.

Add explicit categories such as:

- prediction_loss
- execution_loss
- exit_loss
- sizing_loss
- selection_loss

The point is not only reporting. The point is to decide which subsystem should
change next.

#### B3. Downgrade and quarantine logic

If a preset or family repeatedly underperforms, the system should be able to
say more than "review."

Add learning-facing states:

- stable
- candidate
- degraded
- quarantined

These should not immediately change live behavior automatically, but they
should drive the next research and promotion recommendations.

#### B4. Feedback-driven parameter updates

Execution feedback already changes routing behavior in-session.

The next layer is cross-run learning:

- repeated `more_aggressive` bias should trigger review of maker assumptions
- repeated stop-out clusters should trigger downgrade of sizing or edge policy
- repeated low-fill but high-score opportunities should trigger route or TTL review

Target files:

- [management.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/management.py)
- [suite.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/suite.py)
- [final_report.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/phase2/final_report.py)


## 7. Phase C: Migration Template For Sports And Weather

Sports and weather are not forgotten. They are deferred as migration targets,
not abandoned modules.

The rule is:

- do not independently invent a separate learning philosophy for each board
- first prove the method in crypto
- then port the useful method

### Sports migration targets

Port after crypto phases A and B are working:

- score-oriented selection ranking
- event-level profit attribution
- versioned scorecard comparison
- downgrade / quarantine state

Target areas:

- [phase1](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/phase1)
- [anchor](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/anchor)
- [live](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/sports/live)

### Weather migration targets

Port after crypto phases A and B are working:

- score-oriented run ranking
- settlement-quality vs profit-quality attribution
- versioned scorecard comparison
- downgrade / quarantine state

Target areas:

- [phase1](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/phase1)
- [threshold](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/threshold)
- [ensemble](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/weather/ensemble)


## 8. What To Stop Prioritizing

Until crypto phases A and B materially advance, do not prioritize:

- new module expansion
- broader outer-layer operator polish
- additional dashboard surface area
- more generic multi-board abstraction work
- cosmetic control-panel expansion

Those are allowed only if they directly support profitability analysis or
learning closure.


## 9. First Concrete Deliverables

The next concrete implementation sequence should be:

1. add crypto profit-oriented score decomposition
2. add crypto execution-loss and exit-loss attribution
3. add crypto preset / candidate comparison artifact
4. add crypto degrade / quarantine recommendation logic
5. only then migrate the same pattern into sports
6. only then migrate the same pattern into weather


## 10. Success Definition

This roadmap is succeeding only when all are true:

- crypto scorecards explain profit and loss in subsystem terms
- crypto can compare versions and recommend promote / keep / quarantine
- execution feedback changes next-run recommendations, not only current-run routing
- sports and weather have a clear migration queue based on crypto-proven methods
- outer-layer work no longer dominates the roadmap


## 11. Immediate Working Rule

For the next implementation rounds, every proposed task should be tested against
this question:

`Does this directly improve profitability, learning, or the migration of proven inner-loop methods?`

If not, it is not a primary task.
