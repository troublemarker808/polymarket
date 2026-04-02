---
title: BTC Phase2 Probe Lineage Tail-Guard Gap
date: 2026-04-02
category: logic-errors
module: crypto-phase2-btc-line
problem_type: logic_error
component: service_object
symptoms:
  - Probe taker entries were filled, but exit diagnostics still showed escalated_entry_lineage=false.
  - Escalated tail-guard config was enabled but did not activate on the real losing BTC close path.
  - Replay stayed at review with close-out quality and profitability blockers even after multiple parameter-only tuning rounds.
root_cause: logic_error
resolution_type: code_fix
severity: high
related_components:
  - tooling
  - testing_framework
tags:
  - btc
  - phase2
  - probe
  - lineage
  - tail-guard
  - replay
---

# BTC Phase2 Probe Lineage Tail-Guard Gap

## Problem
BTC Phase2 already had probe and escalated-exit containment controls, but the real replay path still closed the key BTC probe position with `time_stop` loss because lineage recognition failed on the live event sequence.

## Symptoms
- Exit signal diagnostics on the losing BTC trade showed:
  - `escalated_entry_lineage=false`
  - `escalated_entry_tail_guard_active=false`
- The entry was actually a probe taker fill (`repricing_fallback_probe_taker_active=true`, `fill_source=taker`).
- Main suite outputs repeatedly stayed at `recommended_action=review` with blockers like `route_adverse_fill_too_high` and `pnl_per_notional_not_positive`.

## What Didn't Work
- Only tightening/loosening profile params (premium cap, notional multiplier, settlement passes) changed little because the protection path itself was not consistently activated.
- Enabling escalated-entry containment in config alone did not work when lineage inference failed in runtime context.
- Forcing passive exit route (`time_stop_force_ioc_for_repricing_taker=false`) changed execution route labels but did not remove core PnL blocker in filtered acceptance.

## Solution
Applied bounded strategy logic fixes so probe taker entries can reliably activate escalated tail-guard logic:

1. Broadened lineage source recognition to include probe taker diagnostics on submitted orders.
2. Added token-level filtering in lineage event scan to avoid false resets from other token close events in the same market.
3. Added fallback lineage recognition from buy-fill payload (`signal_type=repricing_edge` + `execution_route=taker`) when submitted-event context is truncated.
4. Added final intent-based fallback: if intent is `repricing_edge` and `entry_fill_source=taker`, treat lineage as escalated.

Key code changes:
- `src/pm_bot/strategies/crypto/phase2/strategy.py`
  - `_has_repricing_fallback_taker_escalation_lineage(...)`
  - `_exit_signals(...)` lineage fallback before tail-guard activation

Key tests added:
- `tests/unit/strategies/test_crypto_phase2_strategy.py`
  - `test_crypto_phase2_strategy_treats_probe_taker_as_escalated_lineage_for_tail_guard`
  - `test_crypto_phase2_strategy_lineage_ignores_other_token_closed_events`
  - `test_crypto_phase2_strategy_lineage_uses_buy_fill_fallback_when_submit_event_missing`
  - `test_crypto_phase2_strategy_lineage_falls_back_to_intent_for_repricing_taker_entry`

Validation evidence:
- Unit suite passed after updates (`98 passed`).
- Replay evidence in `.tmp/review-btc-v74-mainprofile7-intentlineage-20260402` showed the target exit now carries:
  - `escalated_entry_lineage=true`
  - `escalated_entry_tail_guard_active=true`

## Why This Works
The failure was not lack of risk config; it was lineage inference drift between design assumptions and real replay event shape. Tail-guard logic depends on lineage. Once lineage is reconstructed robustly from diagnostics, token-filtered events, fill payload, and intent fallback, the protective branch becomes reachable on the real BTC probe path instead of only in idealized test/event-order conditions.

## Prevention
- For any new execution-route feature, add at least one test for each lineage evidence source:
  - submitted-order diagnostics
  - filled-order fallback
  - intent fallback
- When runtime context uses a bounded recent-event window, never rely on a single event type as the only truth source for high-impact risk branches.
- Keep exit diagnostics fields (`escalated_entry_lineage`, `escalated_entry_tail_guard_active`) mandatory in replay review checklists so lineage regressions are caught early.
- Separate validation into:
  - logic activation checks (branch reached)
  - profitability checks (acceptance metrics)
  to avoid masking logic regressions with parameter noise.

## Related Issues
- `/docs/solutions/logic-errors/btc-phase2-tail-loss-gates-and-fragile-closer-sizing-2026-04-01.md` (moderate overlap: same BTC phase2 tail-risk area, different root-cause slice)
- `.tmp/review-btc-v74-mainprofile7-intentlineage-20260402`
- `.tmp/review-btc-v74-mainprofile8-passive-exit-20260402`
