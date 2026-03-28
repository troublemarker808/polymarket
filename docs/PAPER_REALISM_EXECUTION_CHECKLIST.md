# Paper Realism Execution Checklist

## 1. Purpose

This document turns the "make paper closer to real PM trading" discussion into
an execution checklist that can be reviewed phase by phase.

Primary rule:

- code changes, tests, reports, and run commands should be prepared here first
- the final long-running paper or small-live execution is started by the user

This document is not a product roadmap. It is a working checklist for:

- tracking what changed
- deciding what still blocks trustable paper samples
- making it easy to inspect each diff before the next run

## 2. Current Boundary

Current repo status:

- paper now has continuous sessions, queue-aware matching, partial fills, fees,
  slippage, execution metrics, and runtime persistence
- paper is useful for execution diagnostics and sample acquisition
- paper is still not exchange-equal
- paper still needs paper-vs-live calibration before its samples can be treated
  as high-confidence evidence for promotion decisions

Important current rule:

- do not use paper PnL as promotion evidence until the execution realism items
  below are checked off

## 3. Global Gates Before Any New Long Run

All of the following should be true before starting a new "trust-building" run:

- [ ] execution integrity issues found in the previous review are fixed or
      explicitly waived
- [ ] targeted unit tests for affected execution paths pass
- [ ] artifact paths for the next run are decided in advance
- [ ] the run command is written down and ready for the user to execute
- [ ] the expected review outputs are known before the run begins

Required artifact set for every meaningful run:

- `metrics.json`
- `events.jsonl`
- `state.json`
- `capture.jsonl`
- one short markdown summary or log note explaining what that run was meant to validate

## 4. Phase Checklist

### Phase 0: Paper Integrity

Objective:

- make sure paper is internally correct before asking whether it looks like live

Code areas:

- [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
- [paper_adapter.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_adapter.py)
- [position_ledger.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/position_ledger.py)
- [paper_sync.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_sync.py)
- [paper_metrics.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_metrics.py)
- [ws_client.py](/D:/dev/polymarket_bot2.0/src/pm_bot/adapters/polymarket/ws_client.py)

Checklist:

- [x] fix YES/NO token-side maker fill price mapping
- [x] stop replaying the same last-trade event across later snapshots
- [x] audit YES/NO token-side handling for all remaining execution paths:
      taker fill, mark price, mid-price comparison, close-trade accounting
- [x] add deterministic replay checks:
      same capture replayed twice must produce identical outputs
- [x] add event/state/metrics reconciliation checks for one fixed replay sample
- [x] document which fields are cumulative and which are deltas

Artifacts to produce:

- one integrity note in [SIMULATION_RESEARCH_LOG.md](/D:/dev/polymarket_bot2.0/docs/SIMULATION_RESEARCH_LOG.md)
- one fixed replay sample and expected outputs
- one field-semantics note in [PAPER_ARTIFACT_FIELD_SEMANTICS.md](/D:/dev/polymarket_bot2.0/docs/PAPER_ARTIFACT_FIELD_SEMANTICS.md)
- updated regression tests

Acceptance:

- no duplicate fill consumption
- no token-side price inversion bugs
- no unexplained mismatch between `events`, `state`, and `metrics`

Status:

- `completed`

### Phase 1: Small-Live Baseline

Objective:

- create the first real PM micro-order baseline that paper can be compared against

Code areas:

- [polymarket_live.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/polymarket_live.py)
- [live_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_session.py)
- [live_sync.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_sync.py)
- [metrics_report.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/metrics_report.py)

Checklist:

- [x] define the micro-order live profile:
      tiny size, crypto-only, explicit safety caps
- [x] make live output the same execution metrics schema as paper
- [x] make live emit comparable event logs
- [ ] store the first live baseline artifact set in `data/runtime`
- [x] document baseline assumptions and market window

Artifacts to produce:

- `live-calibration-baseline.metrics.json`
- `live-calibration-baseline.events.jsonl`
- `live-calibration-baseline.state.json`
- one baseline markdown note

Acceptance:

- paper and live are now comparable using the same metric names
- at least one real micro-order sample window exists

Status:

- `ready_for_first_operator_run`

### Phase 2: Fill/Cancel Calibration

Objective:

- make paper submit, fill, and expire in ratios that are directionally close to live

Code areas:

- [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
- [paper_metrics.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_metrics.py)
- [manager.py](/D:/dev/polymarket_bot2.0/src/pm_bot/risk/manager.py)

Checklist:

- [ ] compare paper vs live on `orders_submitted`
- [ ] compare paper vs live on `orders_filled`
- [ ] compare paper vs live on `orders_partially_filled`
- [ ] compare paper vs live on `orders_expired`
- [ ] compare paper vs live on `fill_rate`
- [ ] compare paper vs live on `cancel_rate`
- [ ] split the comparison by market, not only by run total

Artifacts to produce:

- one fill/cancel comparison report
- one per-market comparison table

Acceptance:

- paper no longer systematically overfills or underfills relative to live

Status:

- `not_started`

### Phase 3: Latency Calibration

Objective:

- make time-to-fill and cancel timing closer to live behavior

Code areas:

- [factory.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/factory.py)
- [paper_adapter.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_adapter.py)
- [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)

Checklist:

- [ ] replace fixed latency assumptions with calibrated distributions where needed
- [ ] separate place latency from cancel latency
- [ ] verify `avg_time_to_fill_ms` against live baseline
- [ ] verify that tail latency is not wildly more optimistic than live

Artifacts to produce:

- one latency calibration note
- updated execution config defaults or profile-level overrides

Acceptance:

- paper fill timing is explainably close to live, not just lucky on one run

Status:

- `not_started`

### Phase 4: Price Quality Calibration

Objective:

- make paper fill prices closer to real PM execution outcomes

Code areas:

- [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
- [position_ledger.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/position_ledger.py)
- [paper_metrics.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_metrics.py)

Checklist:

- [ ] compare paper vs live on `avg_fill_price_vs_mid_bps`
- [ ] split maker and taker paths
- [ ] split YES and NO token-side paths
- [ ] split thin-book vs thick-book conditions if enough data exists

Artifacts to produce:

- one price-quality comparison report
- one note explaining whether slippage is too optimistic or too pessimistic

Acceptance:

- paper price quality no longer shows a systematic optimistic bias

Status:

- `not_started`

### Phase 5: Queue Realism

Objective:

- make passive maker outcomes more believable under real contention

Code areas:

- [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
- [order_tracker.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/order_tracker.py)

Checklist:

- [ ] validate queue-ahead assumptions against live maker observations
- [ ] model front-of-queue depletion more realistically
- [ ] confirm how quote replacement should affect queue priority
- [ ] compare maker fill share between paper and live baseline

Artifacts to produce:

- one queue realism note
- one maker-only comparison report

Acceptance:

- maker fill share and maker time-to-fill stop diverging materially from live

Status:

- `not_started`

### Phase 6: Regime Segmentation

Objective:

- stop using one global execution realism assumption for all market states

Code areas:

- [market_universe.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/market_universe.py)
- [execution_sample strategy](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/execution_sample/strategy.py)
- execution config profiles under [configs/profiles](/D:/dev/polymarket_bot2.0/configs/profiles)

Checklist:

- [ ] define simple market regimes:
      active, inactive, thin-book, thick-book, fast-move, slow-move
- [ ] tag comparison samples by regime
- [ ] allow paper calibration parameters to vary by regime if needed

Artifacts to produce:

- one regime-definition note
- one regime-tagged calibration summary

Acceptance:

- paper realism can be discussed per market condition rather than only by global average

Status:

- `not_started`

### Phase 7: Sample Confidence Grading

Objective:

- decide which paper samples are safe to use for strategy tuning

Code areas:

- [paper_metrics.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_metrics.py)
- [autoresearch.py](/D:/dev/polymarket_bot2.0/src/pm_bot/research/autoresearch.py)

Checklist:

- [ ] define confidence labels:
      high, medium, low
- [ ] base the label on calibration quality, regime coverage, and known execution caveats
- [ ] emit run-level confidence summaries

Artifacts to produce:

- one sample-confidence report
- one short rule set explaining why a sample received its grade

Acceptance:

- future optimization work can exclude low-confidence paper samples by policy

Status:

- `not_started`

## 5. What Not To Do Yet

Do not do these before the earlier phases are completed:

- [ ] do not treat paper PnL as proof of live profitability
- [ ] do not widen notional just to get more activity
- [ ] do not optimize alpha off low-confidence paper samples
- [ ] do not promote from one good-looking paper day

## 6. Review Template For Each Change Batch

Use this template after every meaningful batch of changes:

- scope:
  list the files touched
- reason:
  explain which checklist item this batch addresses
- verification:
  list the tests run
- artifacts:
  list any new metrics, events, state, capture, or markdown files
- open risk:
  list what still prevents a "trust-building" run
- handoff:
  state whether the batch is ready for the user to run or still code-only

## 7. Run Handoff Rule

When a phase reaches "ready to validate by run", stop at this boundary:

- code changes are complete
- targeted tests pass
- expected output files are named
- exact run command is prepared
- operator note explains what success or failure looks like

At that point:

- the user runs the session
- post-run analysis is done against the fixed artifact set

## 8. Immediate Next Step

The next execution step should be:

- have the operator run the first fresh small-live baseline window with the prepared profile and artifact paths

Why this is next:

- the code handoff package for small-live is now prepared
- the live runner now stays up across clean stream endings
- the small-live profile now restores only session-scoped activity
- the next blocker is the absence of the first real micro-order artifact window
