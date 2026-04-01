---
title: fix: BTC Stage-Gate Closure Execution Checklist
type: fix
status: active
date: 2026-04-02
origin: docs/plans/2026-04-01-003-feat-btc-route-acceptance-closure-plan.md
---

# fix: BTC Stage-Gate Closure Execution Checklist

## Overview

This plan is a concrete execution checklist for one objective:

- Move BTC route from repeated `review` to stable stage-gate pass in replay/paper evidence.

The plan only targets BTC and only addresses currently failing stages:

- `route_conversion_quality`
- `close_out_quality`
- `profitability_tail_risk`

## Problem Frame

Current scorecard evidence shows a repeatable structural mismatch:

- modeled edge is present, but realized trade outcomes remain negative
- maker route conversion is weak in key windows (expiry pressure)
- closed trades are too few and too loss-concentrated to pass promotion gates

So the execution goal is not "more orders". It is:

- controlled conversion
- controlled close-out
- controlled tail loss

## Requirements Trace

- R1. Scope remains BTC-only.
- R2. Keep hard risk controls authoritative (no bypass).
- R3. Improve route conversion quality without global taker unlock.
- R4. Increase close-out evidence density (closed trades) while reducing stop-out pressure.
- R5. Make profitability and tail-risk pass together, not separately.
- R6. Keep all blockers machine-readable in scorecard/autoresearch outputs.
- R7. Maintain correct maturity language (replay/paper/shadow only).

## Scope Boundaries

In scope:

- BTC phase2 execution/exit/sizing behavior
- stage-gate oriented diagnostics and acceptance evidence
- controlled experiment loop with bounded parameter moves

Out of scope:

- non-BTC underlyings
- full strategy rewrite
- live-money enablement
- broad architecture migration

## Key Technical Decisions

- Decision 1: Use stage-gate-first optimization.
  - Rationale: aggregate metrics hide where the route fails.

- Decision 2: Prioritize exit containment before more aggressive entry conversion.
  - Rationale: current blockers are loss concentration and poor close quality.

- Decision 3: Run bounded experiment matrix with small deltas and fixed windows.
  - Rationale: avoid overfitting and avoid mixed-cause result interpretation.

- Decision 4: Keep family-specific controls (`reach` vs `dip`) independent.
  - Rationale: failure modes differ and should not be collapsed into one knob set.

## Execution Checklist (Ordered)

- [x] Step 0: Freeze Baseline and Validation Windows
- [x] Step 1: Exit Containment Hardening (Escalated Lineage)
- [x] Step 2: Route Conversion Stabilization (No Global Aggression)
- [x] Step 3: Sizing De-risk for Negative-PnL Families
- [x] Step 4: Bounded Experiment Matrix and Score Ranking
- [x] Step 5: Gate Validation, Artifact Lock, and Promotion Readiness Review

## Implementation Units

- [x] **Unit 0: Baseline Freeze and Experiment Protocol Lock**

Goal:

- Ensure every subsequent run is comparable and reproducible.

Requirements:

- R1, R6, R7

Dependencies:

- None

Files:

- Modify: `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- Modify: `docs/plans/2026-04-01-003-feat-btc-route-acceptance-closure-plan.md`
- Modify: `src/pm_bot/research/autoresearch.py` (protocol fields only)
- Test: `tests/unit/research/test_autoresearch.py`

Approach:

- Lock one BTC fixed-window set for train/validation/holdout.
- Emit run metadata fields in reports (`window_set_id`, `variant_id`, `evidence_tier`).
- Reject candidate comparisons when window sets differ.

Test scenarios:

- Happy path: same window set yields comparable reports.
- Edge case: missing window metadata returns explicit blocker.
- Error path: mixed window sets are marked invalid for ranking.

Verification outcome:

- Later tuning decisions are based on apples-to-apples evidence.

- [x] **Unit 1: Exit Containment Hardening for Escalated Entries**

Goal:

- Reduce single-loss breach and top-loss concentration without collapsing fill viability.

Requirements:

- R2, R4, R5

Dependencies:

- Unit 0

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/config_registry.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`

Approach:

- Tighten adverse reversal and holding multiplier only for escalated lineage.
- Add per-family exit containment overrides.
- Keep default-off compatibility for unrelated profiles.

Test scenarios:

- Happy path: escalated entries exit earlier under adverse drift.
- Edge case: non-escalated entries preserve baseline exit behavior.
- Error path: lineage ambiguity falls back to conservative default.

Verification outcome:

- Tail-loss gates improve without route-wide behavior regression.

- [x] **Unit 2: Route Conversion Stabilization with Family-Specific Cooldown**

Goal:

- Improve conversion quality without triggering global taker overreach.

Requirements:

- R2, R3, R5

Dependencies:

- Unit 1

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/execution.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/config_registry.py`
- Test: `tests/unit/strategies/test_crypto_phase2_execution.py`
- Test: `tests/unit/strategies/test_crypto_phase2_runtime_context.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`

Approach:

- Keep selective taker path, but add family-local no-fill cooldown and retry budget.
- Prevent repeated maker expiry loops on the same market family in short windows.
- Preserve strict spread/net-edge guards for escalations.

Test scenarios:

- Happy path: chronic no-fill windows switch route in bounded manner.
- Edge case: healthy maker windows do not get unnecessary taker escalation.
- Error path: missing no-fill counters do not crash and keep safe fallback.

Verification outcome:

- `route_conversion_quality` stage no longer fails due to repeated expiry dominance.

- [x] **Unit 3: Sizing De-risk and Notional Efficiency Guards**

Goal:

- Stop negative notional deployment from amplifying losses while evidence is still thin.

Requirements:

- R2, R4, R5

Dependencies:

- Unit 2

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/config_registry.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`

Approach:

- Add family-level size throttles tied to short-window PnL efficiency.
- Prevent larger clips from scaling when `pnl_per_notional <= 0`.
- Surface explicit size-throttle reasons in diagnostics and scorecard.

Test scenarios:

- Happy path: negative family bucket scales down notional.
- Edge case: positive bucket is not over-throttled.
- Error path: missing bucket stats triggers safe low-size fallback.

Verification outcome:

- `profitability_tail_risk` stage improves without hiding losses.

- [x] **Unit 4: Bounded Experiment Matrix and Deterministic Ranking**

Goal:

- Replace ad-hoc tuning with deterministic small-step experimentation.

Requirements:

- R3, R5, R6

Dependencies:

- Unit 3

Files:

- Modify: `src/pm_bot/research/autoresearch.py`
- Modify: `src/pm_bot/cli.py`
- Modify: `docs/ideation/2026-04-01-btc-profit-line-ideation.md` (result log section only)
- Test: `tests/unit/research/test_autoresearch.py`
- Test: `tests/integration/test_cli_research.py`

Approach:

- Define bounded variant matrix (max 3-5 variants per loop).
- Rank by stage-gate priority first, then profitability.
- Reject variants automatically when evidence is thin or incomparable.

Test scenarios:

- Happy path: ranking picks variant with better stage-gate pass profile.
- Edge case: tie on stage-gate falls back to profitability metric.
- Error path: missing required evidence fields marks candidate invalid.

Verification outcome:

- Every loop produces a reproducible winner and explicit reject reasons.

- [x] **Unit 5: Gate Validation and Promotion Readiness Packaging**

Goal:

- Produce operator-facing closure evidence that explains pass/fail by stage.

Requirements:

- R6, R7

Dependencies:

- Unit 4

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/suite.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Modify: `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- Test: `tests/unit/strategies/test_crypto_phase2_suite.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`

Approach:

- Add final operator section: stage gate summary + next constrained action.
- Separate "pass with caution" vs "review" with explicit blockers.
- Keep promotion language bounded to paper/shadow maturity.

Test scenarios:

- Happy path: stage gates pass and decision reaches `proceed`.
- Edge case: one stage fails and output gives single dominant blocker.
- Error path: partial scorecard still emits deterministic fallback decision.

Verification outcome:

- Operator can answer "why not promoted" and "what to fix next" in one artifact.

## Experiment Operating Rules

- Use fixed windows for one full loop (no mid-loop window changes).
- One loop addresses one dominant stage blocker only.
- Parameter delta per loop stays small and bounded.
- Do not widen notional while `pnl_per_notional <= 0`.
- Do not enable global taker unlock.

## Acceptance Criteria (Route-to-Acceptance)

A candidate loop is considered pass-ready for next maturity step only when all hold:

- `route_conversion_quality` is `pass` or stable `review` without hard blocker
- `close_out_quality` has non-zero closed trades and no repeated stop-out dominance
- `profitability_tail_risk` has positive `pnl_per_notional` and no single-loss breach
- promotion gate does not include `insufficient_closed_trade_count`
- stage blocker list is shorter than baseline and points to one remaining bottleneck at most

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Overfitting to one short window | fixed train/validation/holdout and mandatory holdout check |
| Exit tightening kills conversion | evaluate conversion and close-out together, not in isolation |
| Too many knobs at once | bounded matrix, max 3-5 variants per loop |
| Thin sample false confidence | minimum closed-trade evidence gate before ranking |
| Silent report drift | contract tests for scorecard/autoresearch fields |

## Deliverables

- Updated BTC config/profile variants with bounded rationale
- Suite artifacts per loop (`suite.json`, `suite.md`, `final_scorecard.json`, `final_scorecard.md`)
- Autoresearch comparison report with deterministic winner/reject list
- Updated maturity checklist with current stage and explicit blockers

## Execution Status (2026-04-02)

- Unit 0 delivered:
  - `autoresearch` now carries protocol metadata fields: `window_set_id`, `variant_id`, `evidence_tier`.
  - added report-level comparability checker that blocks mixed-window evidence comparisons.
  - added unit tests for protocol metadata resolution and mixed-window blocking.
- Unit 1 delivered:
  - added family-specific escalated-entry tail-guard policy overrides for `reach` and `dip`.
  - exit containment can now be enabled/disabled by family and override guard thresholds per family.
  - added strategy tests for `reach` family enable and `dip` family disable behavior.
- Unit 2 delivered:
  - added family-level entry cooldown controls (`entry_family_cooldown_seconds`, `entry_family_cooldown_seconds_reach`, `entry_family_cooldown_seconds_dip`).
  - runtime now blocks repeated short-window entry attempts on the same family via `entry_family_activity_lock_active`.
  - added strategy tests covering same-family block and cross-family non-block behavior.
  - replay check on current profile remains unchanged because cooldown defaults to safe-off unless explicitly configured.
- Unit 3 delivered:
  - added family-level PnL/notional sizing haircut controls and runtime diagnostics.
  - profitability stage now emits sizing blockers for large-bucket underperformance / large-notional inefficiency.
  - added strategy and final-report tests validating sizing guard behavior.
- Unit 4 delivered:
  - added deterministic candidate ranking in `autoresearch` with explicit comparability gate.
  - added `autoresearch-compare` CLI command to rank candidate bundles.
  - candidate comparison now rejects mixed evidence windows/tier and surfaces blockers explicitly.
- Unit 5 delivered:
  - final scorecard now emits `dominant_route_stage_blocker` and `next_constrained_action`.
  - suite markdown/json now includes these operator-facing closure fields.
  - tests updated for final report, suite contract, and CLI ranking path.

## Stage Label

Current intended stage after this plan:

- `replay or backtest usable` -> `paper evidence stable`

This plan does not target live or real-money readiness.

## Sources & References

- `docs/plans/2026-04-01-003-feat-btc-route-acceptance-closure-plan.md`
- `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- `src/pm_bot/strategies/crypto/phase2/final_report.py`
- `src/pm_bot/strategies/crypto/phase2/suite.py`
- `src/pm_bot/research/autoresearch.py`
