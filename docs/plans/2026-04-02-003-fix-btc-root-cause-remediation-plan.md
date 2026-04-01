---
title: fix: BTC Root-Cause Remediation for Profitability Acceptance
type: fix
status: active
date: 2026-04-02
origin: audit-btc-profitability-root-cause-2026-04-02
---

# fix: BTC Root-Cause Remediation for Profitability Acceptance

## Overview

This plan addresses the root-cause failures identified in the BTC audit, not another parameter-only tuning round.

Primary objective:

- Repair the BTC strategy-execution-risk-feedback loop so profitability acceptance is evaluated on truthful, stage-aligned evidence.

This remains a replay/paper plan and does not enable live trading.

## Problem Frame

Current BTC line fails acceptance because loop signals are polluted or incomplete:

- Negative closes are mapped as stop-loss in replay/runtime reentry state updates.
- Execution feedback treats all negative closes as stop-outs, forcing passive bias amplification.
- `trade.closed` payload lacks `close_reason` and route lineage, so attribution uses weak proxies.
- Repricing fallback repeatedly drifts into maker-expiry loops.
- Time-stop behavior and exit routing do not preserve close quality under fragile conversion.
- Gate outputs are deterministic but not causally faithful to root cause.

Result: repeated retuning cycles without stable acceptance progress.

## Requirements Trace

- R1. Preserve truth of close semantics end-to-end (`close_reason` must remain explicit and loss-sign cannot substitute reason class).
- R2. Reentry and quarantine logic must use actual exit reason taxonomy, not pnl sign proxies.
- R3. Execution feedback must separate true stop-outs from generic negative closes.
- R4. `trade.closed` artifacts must include enough context for attribution and route diagnostics.
- R5. Entry-route fallback logic must avoid uncontrolled maker-expiry dead loops.
- R6. Exit path (especially time-stop and cleanup) must prioritize bounded-loss conversion quality.
- R7. Scorecard blockers must map to truthful causes and produce constrained next actions.
- R8. Acceptance must be validated on fixed BTC replay windows with comparable protocol metadata.

## Scope Boundaries

In scope:

- BTC phase2 strategy/management/replay/runtime context loop
- paper sync and close event payload enrichment
- final scorecard blocker semantics and constrained action mapping
- targeted tests and replay evidence for acceptance decision

Out of scope:

- non-BTC expansion
- live mode enablement
- wallet/real-fund execution
- broad architectural rewrite unrelated to the audited failure chain

## Sources & References

- Audit evidence:
  - `data/research/crypto-phase2-suite-btc-wide-m20-slip5-m16style-20260402/final_scorecard.json`
  - `data/research/crypto-phase2-suite-btc-wide-m20-slip5-m16style-20260402/suite.json`
  - `data/research/crypto-phase2-suite-btc-wide-m20-slip5-m16style-20260402/selection/report.json`
- Existing closure plan baseline:
  - `docs/plans/2026-04-02-002-feat-btc-closed-loop-readiness-plan.md`
- Root-cause code loci:
  - `src/pm_bot/strategies/crypto/phase2/replay.py`
  - `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
  - `src/pm_bot/strategies/crypto/phase2/management.py`
  - `src/pm_bot/strategies/crypto/phase2/execution.py`
  - `src/pm_bot/strategies/crypto/phase2/strategy.py`
  - `src/pm_bot/runtime/paper_sync.py`
  - `src/pm_bot/execution/position_ledger.py`
  - `src/pm_bot/runtime/state.py`

## Key Technical Decisions

- Decision 1: Treat event-truthfulness as a hard dependency before optimization.
  - Rationale: if close reason and route lineage are missing or substituted, any tuning is directionally unreliable.

- Decision 2: Decouple reason class from pnl sign in all feedback loops.
  - Rationale: negative pnl can come from time-stop/cleanup execution drag; conflating them with stop-loss poisons controls.

- Decision 3: Repair fallback conversion as bounded state machine behavior.
  - Rationale: uncontrolled maker fallback loops create starvation; broad taker unlock creates adverse-fill regression.

- Decision 4: Keep acceptance gate strict but causal.
  - Rationale: passing by metric gaming is forbidden; blocker semantics must reflect real failure mechanism.

## Execution Checklist (Ordered)

- [ ] Step 0: Lock baseline evidence and acceptance contract for this remediation cycle
- [ ] Step 1: Repair close event schema and propagation truthfulness
- [ ] Step 2: Fix replay/runtime reentry reason mapping logic
- [ ] Step 3: Refactor close-out and stop-out metrics to remove pnl-sign aliasing
- [ ] Step 4: Rebuild route feedback policy on clean metrics
- [ ] Step 5: Rework repricing fallback and time-stop conversion controls
- [ ] Step 6: Align scorecard blockers with repaired semantics
- [ ] Step 7: Run fixed-window replay verification and produce go/no-go evidence

## Implementation Units

- [ ] **Unit 0: Baseline Lock and Acceptance Contract**

Goal:

- Freeze one comparable BTC evidence baseline and explicit acceptance thresholds for this remediation run.

Requirements:

- R8

Dependencies:

- None

Files:

- Modify: `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- Modify: `docs/plans/2026-04-02-003-fix-btc-root-cause-remediation-plan.md`

Approach:

- Record baseline artifact paths and threshold values used for pass/review decisions.
- Define pass contract for this cycle: required stage statuses, minimum closed trades, non-negative `pnl_per_notional`, and concentration ceiling.

Test scenarios:

- Happy path: baseline metadata and thresholds are fully specified and machine-readable.
- Error path: missing baseline metadata blocks remediation completion claim.

Acceptance:

- Remediation cycle has one canonical baseline and one canonical acceptance contract.

- [ ] **Unit 1: Close Event Schema Truthfulness**

Goal:

- Ensure `trade.closed` carries reason and route lineage needed for attribution and controls.

Requirements:

- R1, R4

Dependencies:

- Unit 0

Files:

- Modify: `src/pm_bot/runtime/state.py`
- Modify: `src/pm_bot/execution/position_ledger.py`
- Modify: `src/pm_bot/runtime/paper_sync.py`
- Modify: `src/pm_bot/runtime/live_session.py`
- Test: `tests/unit/execution/test_position_ledger.py`
- Test: `tests/unit/runtime/test_paper_sync.py`
- Test: `tests/unit/runtime/test_live_session.py`

Approach:

- Extend closed-trade model with `close_reason`, `entry_route`, `exit_route`, and optional diagnostics lineage fields.
- Propagate those fields from strategy decision path to closed-trade event payloads for paper/live parity.
- Keep backward compatibility by safe defaults when old events are read.

Test scenarios:

- Happy path: closed trade event includes reason and route lineage.
- Edge case: legacy event without new fields is still readable with conservative defaults.
- Error path: missing reason at close-generation time emits explicit fallback reason code and warning.

Acceptance:

- `trade.closed` payload is no longer reason/route-null in replay artifacts for new runs.

- [ ] **Unit 2: Reentry Mapping Repair**

Goal:

- Remove `negative pnl => stop_loss` substitution in runtime/replay reentry state updates.

Requirements:

- R1, R2

Dependencies:

- Unit 1

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/replay.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Test: `tests/unit/strategies/test_crypto_phase2_replay.py`
- Test: `tests/unit/strategies/test_crypto_phase2_runtime_context.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`

Approach:

- Drive reentry updates from explicit close reason taxonomy (`stop_loss`, `adverse_fill_reversal`, `time_stop`, `aging_exit`, `stale_position_cleanup`, etc.).
- Count stop-out only for reason classes that are true stop-out families.
- Keep quarantine behavior unchanged for true stop-out classes.

Test scenarios:

- Happy path: stop-loss close increments stop-out count and cooldown.
- Edge case: negative `time_stop` close does not increment stop-out count.
- Error path: unknown close reason falls back to neutral/non-stop-out classification and logs issue.

Acceptance:

- Reentry/quarantine behavior follows reason taxonomy, not pnl sign.

- [ ] **Unit 3: Close-Out Metric Refactor**

Goal:

- Split close quality metrics into distinct channels so route and exit controls get non-confounded feedback.

Requirements:

- R3, R6

Dependencies:

- Unit 2

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`

Approach:

- Introduce separate metrics: `true_stop_out_rate`, `negative_close_rate`, `time_stop_negative_rate`, `cleanup_negative_rate`.
- Update stage blockers so each blocker maps to one specific metric family.
- Keep old fields only as compatibility aliases if needed, marked deprecated.

Test scenarios:

- Happy path: mixed close reasons produce distinct metric values.
- Edge case: all negative closes from cleanup raise cleanup blocker without stop-out blocker.
- Error path: insufficient samples produce explicit density blocker, not silent pass.

Acceptance:

- Close-out diagnostics can distinguish strategy miss, execution drag, and cleanup pressure.

- [ ] **Unit 4: Execution Feedback Policy Decoupling**

Goal:

- Prevent passive-bias self-reinforcement caused by mislabeled stop-out pressure.

Requirements:

- R3, R5

Dependencies:

- Unit 3

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/execution.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Test: `tests/unit/strategies/test_crypto_phase2_execution.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`

Approach:

- Recompute route bias inputs using decoupled metrics from Unit 3.
- Add guardrails to prevent single metric spikes from forcing global passive mode.
- Preserve deterministic route bias outputs with explicit reason tags.

Test scenarios:

- Happy path: true stop-out spike changes bias with clear rationale.
- Edge case: negative cleanup spike alone does not force same bias as stop-out spike.
- Error path: missing feedback samples uses stable neutral bias.

Acceptance:

- Route bias changes only when causal metrics support it.

- [ ] **Unit 5: Repricing Fallback and Time-Stop Conversion Rewrite**

Goal:

- Break maker-expiry dead loops while avoiding broad adverse-fill regression.

Requirements:

- R5, R6

Dependencies:

- Unit 4

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/execution.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/config_registry.py`
- Modify: `configs/profiles/v118a-repricing-escalation/crypto.v1.example.toml`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`
- Test: `tests/unit/strategies/test_crypto_phase2_execution.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`

Approach:

- Convert repricing fallback into bounded state machine: maker attempt budget -> constrained probe taker -> bounded escalation -> cooldown.
- Tighten time-stop exit policy by reason-aware IOC activation under specific adverse-fill/expiry contexts.
- Remove over-wide `time_stop` tolerance behavior for BTC remediation profile while preserving explicit caps.

Test scenarios:

- Happy path: repeated no-fill sequence exits dead loop through bounded conversion path.
- Edge case: healthy maker market remains maker-preferred and avoids unnecessary taker escalation.
- Error path: escalation budget exhausted triggers cooldown instead of uncontrolled retries.

Acceptance:

- `route_maker_expire_dominance` and `route_adverse_fill_too_high` are both reduced without opening uncontrolled risk.

- [ ] **Unit 6: Scorecard Semantics Alignment**

Goal:

- Ensure route/close/profit blockers and next actions are causally faithful after metric and schema repairs.

Requirements:

- R7

Dependencies:

- Unit 5

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/suite.py`
- Modify: `src/pm_bot/research/autoresearch.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`
- Test: `tests/unit/strategies/test_crypto_phase2_suite.py`
- Test: `tests/unit/research/test_autoresearch.py`

Approach:

- Update blocker derivation to consume new close/route metrics and enriched close event fields.
- Re-rank constrained actions to point to root-cause domain (schema, feedback, conversion, exit) rather than generic retuning.
- Preserve deterministic decision outputs.

Test scenarios:

- Happy path: blocker/action pair points to actual dominant failure.
- Edge case: dual-stage failure yields stable dominant blocker and explicit secondary blocker list.
- Error path: partial data produces conservative `review` with explicit missing-field reason.

Acceptance:

- Scorecard explanation aligns with repaired control logic and event truthfulness.

- [ ] **Unit 7: Fixed-Window Verification and Go/No-Go**

Goal:

- Validate whether remediation passes profitability acceptance under comparable BTC evidence windows.

Requirements:

- R8

Dependencies:

- Unit 6

Files:

- Modify: `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- Generate: `data/research/crypto-phase2-suite-btc-rootfix-*/`
- Test: `tests/integration/test_cli_research.py`

Approach:

- Run replay bundle on fixed windows with locked protocol metadata.
- Compare against baseline from Unit 0.
- Produce explicit go/no-go with blocker deltas and residual risks.

Test scenarios:

- Happy path: profitability and concentration gates pass with sufficient close sample density.
- Edge case: one gate remains blocked but dominant blocker shifts to narrower, non-circular issue.
- Error path: protocol mismatch invalidates conclusion and blocks promotion.

Acceptance:

- Final artifact states one of:
  - `Go (paper stage acceptance)` with all threshold evidence, or
  - `No-Go` with bounded residual blockers and non-circular next actions.

## System-Wide Impact

- Runtime event contract changes impact replay consumers, scorecard generation, and research ranking ingestion.
- Closed-trade schema enrichment impacts any parser expecting old payload shape.
- Feedback policy changes alter route behavior and therefore order mix; risk controls remain authoritative.

## Risk Register

- Risk: schema change breaks historical artifact readers.
  - Mitigation: backward-compatible defaults and migration-safe parsing tests.

- Risk: decoupled metrics reduce sensitivity to genuine deterioration.
  - Mitigation: keep true-stop-out and adverse-fill thresholds explicit and tested.

- Risk: conversion rewrite improves fills but worsens slippage.
  - Mitigation: enforce bounded escalation budgets and premium caps; verify adverse-fill metrics jointly.

- Risk: acceptance appears improved via sample distortion.
  - Mitigation: require minimum close density and fixed-window comparability lock.

## Verification Strategy

- Unit-level: run targeted tests for each modified module listed per unit.
- Integration-level: run `tests/integration/test_cli_research.py` scenarios covering suite + scorecard generation.
- Evidence-level: generate one baseline-compatible replay bundle and compare blocker deltas.

Global acceptance gate for this plan:

- `pnl_per_notional >= 0`
- top3 loss concentration <= configured ceiling
- no dominant circular blocker oscillation between maker-expiry dead loop and adverse-fill overload
- close event payload includes reason/route lineage for newly generated runs

## Deliverables

- Repaired BTC close-event schema and propagation path
- Repaired reentry/feedback logic without pnl-sign reason aliasing
- Updated conversion/exit control behavior for repricing fallback and time-stop
- Updated scorecard semantics with causal blocker mapping
- Fixed-window replay evidence bundle and explicit go/no-go result

## Definition of Done

This remediation plan is complete when all are true:

- Every audited root-cause item is resolved with code-level and test-level evidence.
- BTC acceptance verdict is based on truthful, non-confounded loop signals.
- Final go/no-go is explicit, reproducible, and stage-accurate (`replay`/`paper`).
- If still no-go, remaining blockers are new bounded issues rather than repeated aliasing/feedback defects.

## Execution Status (2026-04-02)

- Completed:
  - Unit 1 core path: `trade.closed` now carries `close_reason`, `entry_route`, and `execution_route` from runtime close events.
  - Unit 2 core path: replay/runtime reentry mapping now prefers explicit close reason taxonomy (`stop_loss`, `adverse_fill_reversal`) instead of unconditional loss-sign mapping.
  - Unit 3 core path: execution/close-out stop-out accounting now prioritizes reason taxonomy and only falls back to loss-sign for legacy events missing reason fields.
  - Unit 4 partial: route-feedback stop-out computation aligned with repaired reason semantics.
  - Cross-runtime parity patch: sync shadow `order.submitted` payload now mirrors rationale/route metadata fields.
- Verification passed:
  - Targeted and integration regression subset: `201 passed, 15 deselected`.
- Acceptance runs executed:
  - `data/research/crypto-phase2-suite-btc-rootfix-20260402-r1`
  - `data/research/crypto-phase2-suite-btc-rootfix-20260402-r2`
- Current gate state:
  - Still `review` (not yet acceptance-ready).
  - Dominant blocker remains route conversion quality (`route_adverse_fill_too_high`), with strict-profile variant additionally exposing close-sample starvation (`close_out_no_closed_trades`).
