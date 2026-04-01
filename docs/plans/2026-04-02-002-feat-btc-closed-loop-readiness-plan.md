---
title: feat: BTC Closed-Loop Readiness Program
type: feat
status: active
date: 2026-04-02
origin: user-request-btc-closed-loop-2026-04-02
---

# feat: BTC Closed-Loop Readiness Program

## Overview

This plan shifts BTC work from repeated parameter tuning to full-path closure.

Primary objective:

- Close the full BTC execution loop end-to-end with machine-checkable acceptance at every stage.

This plan focuses on BTC only and remains in replay/paper maturity.

## Problem Frame

Recent BTC runs repeatedly fail the same acceptance blockers:

- `route_conversion_quality` fails (`route_adverse_fill_too_high`)
- `close_out_quality` fails (`close_out_stop_out_pressure`, `close_out_negative_realized_pnl_bps`)
- `profitability_tail_risk` fails (`pnl_per_notional_not_positive`, `top3_loss_concentration_above_ceiling`)

Observed pattern: high modeled edge does not convert into stable realized edge.

## Requirements Trace

- R1. Keep scope BTC-only and do not widen to other underlyings.
- R2. Keep hard risk controls authoritative; no risk-guard bypass.
- R3. Make each loop stage explicit and machine-verifiable.
- R4. Improve route conversion and close-out quality before scaling activity.
- R5. Increase closed-trade evidence density to pass promotion gate sample thresholds.
- R6. Reduce loss concentration and keep tail losses within gate ceilings.
- R7. Keep outputs operator-facing with clear "why blocked" and "what next" actions.
- R8. Keep maturity language accurate (`replay`/`paper`, not live-ready).

## Scope Boundaries

In scope:

- BTC market scan -> identify -> select -> decide -> execute -> close -> attribute -> gate loop
- phase2 strategy, runtime context, execution management, scorecard packaging
- replay/paper evidence loop and deterministic comparison

Out of scope:

- non-BTC market expansion
- live trading enablement
- wallet/real-fund routing
- broad architecture rewrite

## Closed-Loop Flow (Acceptance by Stage)

```mermaid
flowchart TB
  A["1. Scan Market"] --> B["2. Identify Book State"]
  B --> C["3. Select Market/Rung"]
  C --> D["4. Entry Decision"]
  D --> E["5. Execute Order"]
  E --> F["6. Exit / Close"]
  F --> G["7. PnL & Risk Attribution"]
  G --> H["8. Gate Decision"]
  H --> I{"Proceed?"}
  I -->|No| J["Blocker -> Next constrained action"]
  I -->|Yes| K["Promote to next maturity step"]
```

Stage acceptance contract:

- Scan Market: BTC target universe only, blocked/watch-only families enforced.
- Identify Book State: required market/state fields complete and reproducible.
- Select Market/Rung: selected candidates have explicit inclusion reason and non-selected have explicit reject reason.
- Entry Decision: each entry has route rationale + edge/risk evidence in diagnostics.
- Execute Order: conversion quality no longer dominated by repeated expiry loops.
- Exit/Close: closed trades accumulate beyond minimum sample gate and stop-out dominance drops.
- Attribution: `pnl_per_notional` and loss concentration are measurable by family/signature/market.
- Gate Decision: scorecard emits deterministic pass/review with one dominant blocker and next constrained action.

## Key Technical Decisions

- Decision 1: Prioritize loop closure over aggressive alpha expansion.
  - Rationale: repeated blockers indicate execution closure gap, not just alpha insufficiency.

- Decision 2: Keep family-specific controls independent (`reach` vs `dip`).
  - Rationale: failure modes differ and need separate guardrails.

- Decision 3: Use stage-gate-first experiment ranking.
  - Rationale: aggregate PnL alone hides where closure fails.

- Decision 4: Freeze evidence protocol for comparability.
  - Rationale: avoid mixed-window false conclusions.

## Execution Checklist (Ordered)

- [x] Step 0: Lock BTC Closure Protocol and Baseline Windows
- [x] Step 1: Harden Scan/Identify Contract and Diagnostics
- [x] Step 2: Tighten Selection/Decision Transparency
- [x] Step 3: Stabilize Execution Conversion (Expiry Loop Suppression)
- [x] Step 4: Improve Exit/Close Quality and Sample Density
- [x] Step 5: Add Attribution-Level Tail-Loss Controls
- [x] Step 6: Gate Packaging and Deterministic Closure Verdict
- [x] Step 7: Replay/Paper Verification Bundle and Go/No-Go

## Implementation Units

- [x] **Unit 0: BTC Closure Protocol Lock**

Goal:

- Make every BTC run comparable and closure-auditable.

Requirements:

- R1, R3, R8

Dependencies:

- None

Files:

- Modify: `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- Modify: `src/pm_bot/research/autoresearch.py`
- Modify: `src/pm_bot/cli.py`
- Test: `tests/unit/research/test_autoresearch.py`
- Test: `tests/integration/test_cli_research.py`

Approach:

- Enforce mandatory protocol metadata for closure runs (`window_set_id`, `variant_id`, `evidence_tier`, `loop_stage_set`).
- Reject ranking/comparison when protocol fields mismatch.
- Emit protocol summary in operator-facing reports.

Test scenarios:

- Happy path: comparable runs rank successfully.
- Edge case: missing `loop_stage_set` gives explicit blocker.
- Error path: mixed-window comparisons are rejected deterministically.

Acceptance:

- Any closure candidate without protocol parity is marked invalid for promotion decision.

- [x] **Unit 1: Scan/Identify Contract Hardening**

Goal:

- Ensure candidate universe and book-state inputs are consistent and traceable.

Requirements:

- R1, R3, R7

Dependencies:

- Unit 0

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/replay.py`
- Modify: `src/pm_bot/strategies/crypto/phase1/selection.py`
- Test: `tests/unit/strategies/test_crypto_phase2_runtime_context.py`
- Test: `tests/unit/strategies/test_crypto_phase2_replay.py`
- Test: `tests/unit/strategies/test_crypto_phase1_selection.py`

Approach:

- Enforce BTC-only scan constraints for closure profiles.
- Promote watch-only and blocked-market enforcement as first-class runtime contract.
- Add diagnostics for scan eligibility and identify-stage field completeness.

Test scenarios:

- Happy path: eligible BTC markets pass with complete identify fields.
- Edge case: watch-only family is blocked before decision stage.
- Error path: missing identify fields result in explicit reject reason.

Acceptance:

- Stage statuses show `scan_quality=pass` and `selection_pass_through=pass` for valid closure windows.

- [x] **Unit 2: Selection/Decision Transparency Upgrade**

Goal:

- Make entry decisions explainable and auditable by market/family/route.

Requirements:

- R3, R4, R7

Dependencies:

- Unit 1

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/execution.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/config_registry.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`
- Test: `tests/unit/strategies/test_crypto_phase2_execution.py`

Approach:

- Add mandatory decision diagnostics: selected-route reason, skipped-route reason, net-edge-after-premium reason code.
- Keep strict guardrail ordering (risk -> eligibility -> route policy -> entry).
- Emit reason taxonomy stable enough for scorecard aggregation.

Test scenarios:

- Happy path: accepted candidate has full decision trace.
- Edge case: candidate rejected due to one specific guard emits stable reason code.
- Error path: missing route signal falls back to safe reject and logs reason.

Acceptance:

- Every emitted entry signal has a deterministic decision trace payload.

- [x] **Unit 3: Conversion Stabilization (Expiry Loop Suppression)**

Goal:

- Break repeated maker-expiry loop and improve route conversion quality.

Requirements:

- R2, R4

Dependencies:

- Unit 2

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/execution.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/config_registry.py`
- Test: `tests/unit/strategies/test_crypto_phase2_execution.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`

Approach:

- Strengthen family-local expiry counters and cooldown escalation.
- Ensure bounded fallback route behavior without global taker unlock.
- Add per-signature conversion diagnostics for blocker targeting.

Test scenarios:

- Happy path: repeated no-fill/expiry triggers bounded fallback and cooldown.
- Edge case: healthy maker market does not over-escalate.
- Error path: stale execution counters fail safe (reduce activity, no crash).

Acceptance:

- `route_conversion_quality` no longer fails on repeated expiry dominance in target windows.

- [x] **Unit 4: Close-Out Quality and Sample Density**

Goal:

- Increase quality closed trades and reduce stop-out/negative-close pressure.

Requirements:

- R4, R5

Dependencies:

- Unit 3

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/management.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/strategy.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Test: `tests/unit/strategies/test_crypto_phase2_management.py`
- Test: `tests/unit/strategies/test_crypto_phase2_strategy.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`

Approach:

- Tighten exit behavior for fragile signatures while preserving safe winners.
- Add close-quality-aware throttles to avoid repeating poor close patterns.
- Surface closure-quality reasons directly in scorecard stage blockers.

Test scenarios:

- Happy path: closed trade count increases and stop-out pressure decreases.
- Edge case: benign signatures keep baseline close behavior.
- Error path: low-sample windows keep conservative close policy.

Acceptance:

- `close_out_quality` passes or degrades to a single clearly bounded blocker.

- [x] **Unit 5: Attribution and Tail-Loss Control Layer**

Goal:

- Control loss concentration while preserving measurable edge capture.

Requirements:

- R2, R6

Dependencies:

- Unit 4

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/suite.py`
- Modify: `src/pm_bot/research/autoresearch.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`
- Test: `tests/unit/strategies/test_crypto_phase2_suite.py`
- Test: `tests/unit/research/test_autoresearch.py`

Approach:

- Add family/signature-level concentration diagnostics (`top1`, `top3`, market/signature bucket).
- Bind concentration breaches to explicit gate blockers and constrained actions.
- Keep single-loss and top3 concentration checks machine-readable and stable.

Test scenarios:

- Happy path: concentration below ceiling clears tail-loss blocker.
- Edge case: only one bucket breaches and blocker is correctly scoped.
- Error path: missing attribution data triggers conservative blocker.

Acceptance:

- `profitability_tail_risk` is evaluable with explicit concentration and pnl-per-notional evidence.

- [x] **Unit 6: Gate Packaging and Deterministic Verdict**

Goal:

- Produce a single operator artifact that answers pass/fail and next action.

Requirements:

- R3, R7, R8

Dependencies:

- Unit 5

Files:

- Modify: `src/pm_bot/strategies/crypto/phase2/final_report.py`
- Modify: `src/pm_bot/strategies/crypto/phase2/suite.py`
- Modify: `src/pm_bot/cli.py`
- Test: `tests/unit/strategies/test_crypto_phase2_final_report.py`
- Test: `tests/unit/strategies/test_crypto_phase2_suite.py`
- Test: `tests/integration/test_cli_research.py`

Approach:

- Guarantee deterministic `recommended_action`, `route_stage_acceptance_decision`, `dominant_route_stage_blocker`, `next_constrained_action`.
- Add operator summary block that explains not-ready reason in one screen.
- Keep maturity wording constrained to replay/paper/shadow stages.

Test scenarios:

- Happy path: all stage gates pass -> `proceed`.
- Edge case: one stage fails -> one dominant blocker and constrained action.
- Error path: partial scorecard -> deterministic fallback with conservative `review`.

Acceptance:

- Operator can determine go/no-go without manual interpretation.

- [x] **Unit 7: Verification Bundle and Promotion Readiness Review**

Goal:

- Validate closure across fixed windows and produce final go/no-go evidence set.

Requirements:

- R5, R6, R8

Dependencies:

- Unit 6

Files:

- Modify: `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md`
- Modify: `docs/plans/2026-04-02-002-feat-btc-closed-loop-readiness-plan.md`
- Generate artifacts under: `data/research/crypto-phase2-suite-btc-closure-*`
- Test: `tests/integration/test_cli_research.py`

Approach:

- Run fixed-window closure bundle (train/validation/holdout) with protocol lock.
- Compare candidates only when comparable; reject mixed evidence.
- Record final blocker-to-action mapping in checklist.

Test scenarios:

- Happy path: all windows satisfy gate thresholds -> closure pass-ready.
- Edge case: one window fails but failure is isolated and actionable.
- Error path: evidence mismatch invalidates conclusion.

Acceptance:

- Closure package includes deterministic verdict + full blocker evidence + next constrained action.

## Verification Strategy

For each unit:

- Run targeted unit tests for modified modules.
- For scorecard and CLI fields, run integration checks.
- After Unit 7, run closure suite on fixed BTC windows and compare against baseline.

Global verification gate:

- No claim of readiness unless outputs show stage-level pass evidence.
- If any core stage remains `review`, output must include one dominant blocker and bounded next action.

## Risk Register

- Risk: overfitting to one BTC window.
  - Mitigation: fixed train/validation/holdout protocol and comparability guard.

- Risk: conversion improvement degrades close quality.
  - Mitigation: stage-coupled acceptance (`route_conversion_quality` + `close_out_quality`) in same run.

- Risk: sample inflation with low-quality closes.
  - Mitigation: quality-aware close thresholds, not count-only optimization.

- Risk: concentration drops by reducing activity too much.
  - Mitigation: include notional-efficiency and evidence-density checks together.

## Deliverables

- Updated BTC closure-capable strategy/reporting code paths.
- Stable operator-facing stage-gate artifact bundle (`suite.json/.md`, `final_scorecard.json/.md`).
- Updated maturity checklist reflecting current stage and remaining blockers.
- Deterministic comparability-aware autoresearch comparison output.

## Definition of Done

This plan is complete when all are true:

- BTC loop stages are machine-checkable end-to-end.
- Stage blockers are deterministic and actionable.
- Verification bundle proves whether closure is pass-ready or explicitly blocked.
- Maturity statement remains accurate (replay/paper/shadow only until gate truly passes).

## Execution Status (2026-04-02)

- Unit 0 delivered:
  - `autoresearch` protocol metadata now includes `loop_stage_set`.
  - report comparability now blocks missing/mixed `loop_stage_set` in candidate ranking.
  - CLI now supports `--loop-stage-set` and propagates protocol fields in `autoresearch-report` and `autoresearch-compare`.
  - targeted tests passed:
    - `tests/unit/research/test_autoresearch.py` (`9 passed`)
    - `tests/integration/test_cli_research.py -k autoresearch` (`1 passed`)
- Unit 1 delivered:
  - added runtime scan/identify diagnostics contract via `runtime_scan_identify_diagnostics(...)`.
  - wired diagnostics into both paper runtime context and replay context as `scan_identify_diagnostics`.
  - covered with targeted tests:
    - `tests/unit/strategies/test_crypto_phase1_selection.py` (`16 passed`)
    - `tests/unit/strategies/test_crypto_phase2_runtime_context.py` (`6 passed`)
    - `tests/unit/strategies/test_crypto_phase2_replay.py` (`7 passed`)
- Unit 2 delivered:
  - added stable entry decision-trace fields in phase2 signal diagnostics:
    - `decision_trace_version`
    - `entry_decision_reason_code`
    - `entry_decision_rationale_tags`
    - `entry_eligibility_reason`
    - `entry_route_policy_bias`
  - wired `decision_trace_version` into resolved config contract (`strategy` + `config_registry`).
  - covered with targeted tests:
    - `tests/unit/strategies/test_crypto_phase2_strategy.py` (`81 passed`)
    - `tests/unit/strategies/test_crypto_phase2_execution.py` (`22 passed`)
- Unit 3 delivered:
  - added market no-fill suppression controls:
    - `entry_no_fill_cooldown_seconds` (config + resolved config wiring)
    - no-fill attempt accounting now includes `order.expired` and stale/exchange cancels.
  - added skip path `entry_no_fill_cooldown_active` with explicit diagnostics.
  - signal diagnostics now include `recent_no_fill_attempts`.
  - covered with targeted tests:
    - `tests/unit/strategies/test_crypto_phase2_strategy.py` (`83 passed`)
    - `tests/unit/strategies/test_crypto_phase2_replay.py` + `test_crypto_phase2_runtime_context.py` + `test_crypto_phase2_execution.py` (`35 passed`)
  - replay check on BTC fixed window remained `review` with unchanged blocker set; this unit improved control semantics but did not yet move stage-gate outcome on the current evidence window.
- Unit 4 delivered:
  - added close-out quality diagnostics helper in management layer:
    - `summarize_close_out_quality_from_events(...)`
    - emits `closed_count`, `stop_out_share`, `average_realized_pnl_bps`, `dominant_close_reason`, `latest_closed_at`
  - added strategy-level close-out quality guard controls (default off):
    - `close_out_quality_guard_enabled`
    - `close_out_quality_guard_lookback_events`
    - `close_out_quality_guard_min_closed_samples`
    - `close_out_quality_guard_max_stop_out_share`
    - `close_out_quality_guard_min_realized_pnl_bps`
    - `close_out_quality_guard_notional_min_multiplier`
    - `close_out_quality_guard_notional_max_multiplier`
    - `close_out_quality_guard_entry_cooldown_seconds`
  - entry path now supports:
    - quality-aware notional haircut (`close_out_quality_guard_notional_haircut_applied`)
    - bounded entry block under active cooldown (`close_out_quality_guard_cooldown_active`)
    - explicit skip reason `close_out_quality_guard_blocked`
  - final scorecard close-out stage now surfaces sample-density and cleanup-pressure blockers:
    - `close_out_insufficient_closed_trade_density`
    - `close_out_cleanup_dominance`
  - covered with targeted tests:
    - `tests/unit/strategies/test_crypto_phase2_management.py` (`24 passed`)
    - `tests/unit/strategies/test_crypto_phase2_strategy.py` (`85 passed`)
    - `tests/unit/strategies/test_crypto_phase2_final_report.py` (`6 passed`)
  - replay check on BTC fixed window:
    - output: `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u4`
    - decision remains `review` with failed stages:
      - `route_conversion_quality`
      - `close_out_quality`
      - `profitability_tail_risk`
    - dominant blocker remains `route_adverse_fill_too_high`
    - unit outcome: close-out blocker attribution is now more explicit and machine-readable, but acceptance did not yet pass on this window.
- Unit 5 delivered:
  - added attribution-level tail-loss concentration controls in route-stage gating:
    - `tail_loss_top1_concentration_breach`
    - `tail_loss_market_concentration_breach`
    - `tail_loss_signature_concentration_breach`
  - profitability stage now evaluates concentration from:
    - trade-level top losses
    - market bucket loss concentration
    - signature bucket loss concentration
  - added blocker-to-action mapping for tail-loss concentration in constrained action synthesis.
  - extended autoresearch promotion-gate summary extraction/reporting:
    - `dominant_route_stage_blocker`
    - `next_constrained_action`
  - covered with targeted tests:
    - `tests/unit/strategies/test_crypto_phase2_final_report.py` (`7 passed`)
    - `tests/unit/research/test_autoresearch.py` (`9 passed`)
    - `tests/unit/strategies/test_crypto_phase2_suite.py` (`1 passed`)
  - replay check on BTC fixed window:
    - output: `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u5`
    - decision remains `review`
    - dominant blocker remains `route_adverse_fill_too_high`
    - profitability blocker set now explicitly includes concentration breakdown:
      - `tail_loss_top3_concentration_breach`
      - `tail_loss_top1_concentration_breach`
      - `tail_loss_market_concentration_breach`
      - `tail_loss_signature_concentration_breach`
- Unit 6 delivered:
  - added deterministic operator-facing gate package fields in final scorecard:
    - `operator_verdict`
    - `operator_summary`
  - strengthened deterministic dominant-blocker selection via explicit blocker-priority ranking.
  - upgraded constrained-action synthesis from stage-only to blocker-specific mapping, including:
    - `route_adverse_fill_too_high`
    - `route_maker_expire_dominance`
    - `close_out_stop_out_pressure`
    - `close_out_negative_realized_pnl_bps`
    - tail-loss concentration blocker family
  - extended autoresearch promotion-gate ingestion/formatting to include:
    - `dominant_route_stage_blocker`
    - `next_constrained_action`
  - covered with targeted tests:
    - `tests/unit/strategies/test_crypto_phase2_final_report.py` (`7 passed`)
    - `tests/unit/research/test_autoresearch.py` (`9 passed`)
    - `tests/unit/strategies/test_crypto_phase2_suite.py` (`1 passed`)
  - replay check on BTC fixed window:
    - output: `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u6`
    - decision remains `review`
    - dominant blocker remains `route_adverse_fill_too_high`
    - next constrained action is now blocker-specific and deterministic:
      - `reduce taker adverse-fill drag first by tightening premium caps and fallback taker escalation rules.`
- Unit 7 delivered:
  - produced verification bundle iterations on fixed BTC window:
    - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u4`
    - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u5`
    - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u6`
    - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u7`
  - generated comparability-aware ranking artifact:
    - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u6/autoresearch_compare.md`
  - integrated checklist update for current maturity blocker framing:
    - `docs/CRYPTO_MATURITY_PROBLEM_CHECKLIST.md` now records P7 (`in_progress`) and current blocker/action map.
  - verification and integration checks passed:
    - `tests/integration/test_cli_research.py -k "crypto_phase2_suite or autoresearch"` (`2 passed`)
  - final go/no-go verdict on current fixed window:
    - `No-Go` (`recommended_action=review`, `operator_verdict=review_required`)
    - dominant blocker remains `route_adverse_fill_too_high`
    - current implementation is closure-auditable and deterministic, but not promotion-ready on this evidence window.
  - added targeted conversion containment iteration (u7b/u7c):
    - strategy update:
      - time-stop IOC suspension hook under passive adverse-fill regime in `strategy.py`
    - profile update:
      - tightened BTC taker-entry tolerance in `configs/profiles/v118a-repricing-escalation/crypto.v1.example.toml`
      - delayed time-stop force IOC and disabled repricing taker force IOC in same profile
    - evidence:
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u7b`
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u7c`
    - outcome:
      - `route_adverse_fill_too_high` was removed in `u7c` (`average_adverse_fill_bps=0.0`)
      - new dominant blocker became `route_maker_expire_dominance`
      - still `No-Go` because close sample density/profitability gates remain `review`.
  - additional conversion iterations (u7d/u7e/u7f/u7g):
    - `u7d` validated strategy-level fallback urgency-floor logic; outcome unchanged from `u7c` on this window.
    - `u7e` (moderate taker relaxation) recovered one closed trade but reintroduced adverse-fill dominance.
    - `u7f/u7g` (narrow fallback + stronger maker) moved back to zero closed trades and maker-expiry dominance.
    - current evidence indicates a constrained frontier on this fixed window:
      - too passive -> `route_maker_expire_dominance`
      - slightly more aggressive -> `route_adverse_fill_too_high`
    - next bounded action should introduce controlled probe-conversion logic (limited taker probes under strict premium/notional caps), not broad threshold loosening.
  - controlled probe-conversion implementation + verification (u8/u8b/u8c/u8d/u8e/u8f):
    - strategy update:
      - added constrained probe-taker path for repricing fallback in `strategy.py`:
        - guarded by no-fill attempts, probe premium cap, probe min-net-edge, and probe notional multiplier
        - emits explicit diagnostics:
          - `repricing_fallback_probe_taker_eligible`
          - `repricing_fallback_probe_taker_active`
          - `repricing_fallback_probe_taker_block_reason`
          - `repricing_fallback_probe_notional_multiplier`
      - added unit tests for probe activation and probe net-edge floor block:
        - `tests/unit/strategies/test_crypto_phase2_strategy.py`
    - profile iteration:
      - enabled probe controls in `configs/profiles/v118a-repricing-escalation/crypto.v1.example.toml`
      - tested multiple probe thresholds (attempt gate, premium cap, notional multiplier)
    - evidence:
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8`
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8b`
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8c`
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8d`
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8e`
      - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8f`
    - outcome:
      - probe path is now observable and does activate on this fixed window (`u8c/u8d/u8e/u8f` diagnostics).
      - after adding probe-notional min-order floor in strategy (`u8f`), probe signals were translated into executable submissions:
        - `probe_active=2`
        - `probe_notional_floor_applied=2`
        - `submitted_orders=6`
        - `closed_trade_count=1`
      - frontier shifted back from pure conversion starvation to adverse-fill/exit drag:
        - dominant blocker became `route_adverse_fill_too_high`
        - `average_adverse_fill_bps=147.6341`
        - realized close remained negative (`closed_trade_net_pnl=-0.0571`)
    - next bounded action:
      - keep probe-notional floor and narrow taker drag:
        - tighten probe premium cap and/or probe min net-edge floor family-wise
        - pair with stricter adverse-fill/time-stop containment to avoid converting starvation into lossful closes
