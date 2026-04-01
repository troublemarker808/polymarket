# Crypto Maturity Problem Checklist

Last updated: 2026-04-02

This checklist is the control document for the crypto module.

Rules for execution:

1. Only one problem can be `in_progress` at a time.
2. Do not start the next problem until the current one has:
   - a precise root cause
   - a bounded code change
   - targeted tests
   - replay or paper evidence that the problem is actually resolved
3. Do not do global tuning while a problem is still open.

## Problem List

### P1. BTC Reach `watch_only` Is Not Enforced In Runtime

Status: `completed`

Observed behavior:

- `BTC reach / what-price-will-bitcoin-hit-before-2027` shows some positive static net-edge rung candidates.
- Real execution evidence shows `signal -> submit -> expiry` with `0 fill`.
- Research correctly downgrades this family to `watch_only`.
- Replay and paper still only hard-block `skip_series`, so the `watch_only` conclusion is not yet fully enforced.

Root cause:

- `selection.py` exposes `watch_only` only as a report classification.
- `crypto.phase2` replay and paper context builders only consume `recommended_skip_series_keys(...)`.

Bounded fix:

- Add a runtime-facing helper that blocks both `skip_series` and `watch_only`.
- Use that helper in `crypto.phase2` replay and continuous paper context building.
- Keep the static `skip_series` helper for reporting and analysis.

Primary code targets:

- `src/pm_bot/strategies/crypto/phase1/selection.py`
- `src/pm_bot/strategies/crypto/phase2/replay.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/strategies/crypto/phase2/suite.py`

Acceptance criteria:

- A `watch_only` family appears in `blocked_series_keys` for replay and paper context.
- `BTC reach` filtered replay produces `0` signals because it is blocked, not because of later execution behavior.
- Regression tests cover the new runtime-blocking helper and replay/paper wiring.

Resolution evidence:

- `src/pm_bot/strategies/crypto/phase1/selection.py`
- `src/pm_bot/strategies/crypto/phase2/replay.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/runtime/paper_session.py`
- `src/pm_bot/cli.py`
- Verified replay artifact:
  - `data/research/phase2-replay-btc-reach-watchonly-verified/metrics.json`
  - `signals_generated = 0`
  - `submitted_orders = 0`
- Targeted regression:
  - `27 passed`

### P2. Family-Specific Market Selection Is Still Too Coarse

Status: `completed`

Observed behavior:

- Runtime selection previously only had `blocked_series_keys`.
- Once a family was considered risky, the only choices were "allow the whole series" or "block the whole series".
- This was too coarse for `BTC reach`, where execution evidence showed one bad rung (`701495`) repeatedly expiring, while other rungs still had actionable behavior.

Root cause:

- `selection.py` aggregated execution evidence to the series level, but not to the individual market/rung level.
- `crypto.phase2` strategy and runtime context had no `blocked_market_ids` path.

Bounded fix:

- Extend selection overlay down to the market level.
- Mark individual markets with `execution_no_fill` when they show `signal -> submit -> expiry` and `0 fill`.
- Add runtime-facing `blocked_market_ids`.
- Make `crypto.phase2` skip blocked markets before entry, while keeping the rest of the family available.

Primary code targets:

- `src/pm_bot/strategies/crypto/phase1/selection.py`
- `src/pm_bot/strategies/crypto/phase2/strategy.py`
- `src/pm_bot/strategies/crypto/phase2/replay.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`

Acceptance criteria:

- Selection report identifies the toxic rung by market id.
- Runtime context includes `blocked_market_ids`.
- Replay no longer emits entry signals on `701495`.
- Another rung in the same `BTC reach` family can still pass if not blocked.

Resolution evidence:

- `701495` is marked with `execution_no_fill` in:
  - `data/research/selection-overlay-phase2-v35-btc-reach-marketfilter/report.json`
- Verified replay artifact:
  - `data/research/phase2-replay-btc-reach-marketfilter-verified/metrics.json`
  - `signals_generated = 2`
  - `submitted_orders = 2`
- Verified events:
  - `data/research/phase2-replay-btc-reach-marketfilter-verified/events.jsonl`
  - signals route to `1339768`
  - no signal is generated for `701495`
- Targeted regression:
  - `38 passed`

### P3. Fair Value Still Measures Pricing Better Than Tradeability

Status: `pending`

Problem:

- Some ladders show thin positive net edge that does not survive real execution conditions.

Goal:

- Add stronger tradeability constraints to family-specific pricing and selection.

### P4. Runtime Execution Feedback Does Not Yet Change Family Policy

Status: `pending`

Problem:

- The system records expiries, fills, and poor routes, but that evidence is not yet strong enough to suppress later activity by family.

Goal:

- Promote execution evidence into runtime family state and adaptive gating.

### P5. Portfolio-Level Crypto Risk Is Still Too Flat

Status: `pending`

Problem:

- Risk is still dominated by account-level and single-position rules.

Goal:

- Add underlying-level and ladder-level exposure aggregation before promotion beyond paper.

### P6. BTC Promotion Decision Still Relies On Manual Interpretation

Status: `completed`

Observed behavior:

- Phase2 suite produced rich metrics, but promotion decisions still required manual reading and ad-hoc interpretation.
- Operator workflows lacked a stable machine-readable BTC go/no-go field.

Root cause:

- Final scorecard emphasized descriptive diagnostics but did not enforce explicit BTC promotion thresholds and stage labels.
- Autoresearch and CLI outputs did not consistently carry promotion gate payloads.

Bounded fix:

- Add a BTC promotion gate in phase2 final scorecard with explicit `proceed/review/pause` decision.
- Encode gate thresholds and observed values in scorecard JSON fields.
- Surface promotion gate payload in suite markdown, final report CLI output, and autoresearch when scorecard is provided.

Primary code targets:

- `src/pm_bot/strategies/crypto/phase2/final_report.py`
- `src/pm_bot/strategies/crypto/phase2/suite.py`
- `src/pm_bot/research/autoresearch.py`
- `src/pm_bot/cli.py`

Acceptance criteria:

- Final scorecard JSON includes machine-readable promotion decision, stage label, blocking reasons, thresholds, and observed values for:
  - execution-loss ratio
  - max single-loss bound
  - top-3 loss concentration ratio
- Gate semantics satisfy:
  - `pause` when runtime status is halted.
  - `review` when evidence is insufficient, profitability/edge-capture thresholds are not met, or tail-loss gates fail.
  - `proceed` only when all BTC gate thresholds pass.
- CLI final report output includes promotion decision fields.
- Final scorecard additionally includes route-stage acceptance fields and stage-level blockers:
  - `route_stage_acceptance_decision`
  - `route_stage_failed_stages`
  - `route_stage_statuses`
  - `route_stage_blockers`

Resolution evidence:

- Unit tests:
  - `tests/unit/strategies/test_crypto_phase2_final_report.py`
  - `tests/unit/strategies/test_crypto_phase2_suite.py`
  - `tests/unit/research/test_autoresearch.py`
- Integration test:
  - `tests/integration/test_cli_research.py::test_cli_crypto_phase2_final_report_prints_btc_promotion_gate_payload`
- Route-stage gate coverage:
  - `tests/unit/strategies/test_crypto_phase2_final_report.py`
  - `tests/unit/strategies/test_crypto_phase2_suite.py`
  - `tests/unit/research/test_autoresearch.py`
- Protocol comparability baseline lock:
  - `src/pm_bot/research/autoresearch.py` now emits `window_set_id`, `variant_id`, `evidence_tier`
  - mixed-window comparison blockers are now machine-evaluable via `evaluate_report_comparability(...)`

### P7. BTC Closed-Loop Route Still Fails Deterministic Acceptance

Status: `in_progress`

Observed behavior:

- Fixed-window BTC suite still returns `recommended_action=review`.
- Dominant blocker is stable: `route_adverse_fill_too_high`.
- Close-out and tail-risk are now better attributed but still failing:
  - `close_out_insufficient_closed_trade_density`
  - `close_out_stop_out_pressure`
  - `close_out_negative_realized_pnl_bps`
  - `close_out_cleanup_dominance`
  - `tail_loss_top3_concentration_breach`
  - `tail_loss_top1_concentration_breach`
  - `tail_loss_market_concentration_breach`
  - `tail_loss_signature_concentration_breach`

Root cause:

- Execution conversion drag (adverse fill) remains the first-order loss source.
- Current close-outs are dominated by passive cleanup/time-stop behavior with negative realized outcomes.
- Losses remain concentrated in one BTC dip signature bucket.

Latest verification note (2026-04-02):

- After tightening taker-entry tolerance in profile and forcing more passive time-stop handling, adverse-fill blocker was removed on the same fixed window.
- Dominant blocker shifted to `route_maker_expire_dominance` with `0` closed trades.
- Conclusion: current phase has moved from "adverse-fill dominated loss" to "maker conversion starvation"; still not promotion-ready.
- Controlled probe-conversion path has now been implemented and verified in replay diagnostics:
  - probe eligibility/activation fields are emitted and observed on the same fixed window.
  - after adding a probe notional floor tied to market `min_order_size`, probe taker signals are now executable submissions.
  - current stage outcome is still `review`, but `closed_trade_count` moved from `0` to `1` on `u8f`.
- Latest root-cause refinement:
  - conversion starvation has been partially addressed, but the blocker shifted back to adverse-fill drag:
    - `dominant_route_stage_blocker=route_adverse_fill_too_high`
    - `average_adverse_fill_bps=147.6341`
    - closed-trade net pnl remains negative.

Bounded next fix:

- Prioritize route conversion containment before further alpha expansion:
  - tighten fallback taker escalation and premium caps
  - tighten maker repost loop and no-fill suppression on fragile signatures
- Add explicit pending-order replacement path for probe-taker conversion so activated probes can become executable submissions.
- Keep probe execution floor, then tighten probe premium/net-edge thresholds to reduce adverse-fill drag while preserving minimal conversion.
- Keep close-out quality guard and attribution blockers as hard evidence gates.
- Require comparable replay windows and deterministic blocker-to-action mapping in each iteration.

Primary code targets (already landed for attribution + verdict packaging):

- `src/pm_bot/strategies/crypto/phase2/final_report.py`
- `src/pm_bot/strategies/crypto/phase2/strategy.py`
- `src/pm_bot/strategies/crypto/phase2/management.py`
- `src/pm_bot/research/autoresearch.py`

Current evidence bundle:

- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u4`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u5`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u6`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8b`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8c`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8d`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8e`
- `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u8f`
- comparability report:
  - `data/research/crypto-phase2-suite-btc-closure-progress-20260402-u6/autoresearch_compare.md`
