---
date: 2026-04-01
topic: repo-maturity-gaps
focus: open-ended repo improvement scan
---

# Ideation: Repo Maturity Gap Closure

## Codebase Context

- Python trading system with layered modules (`adapters`, `strategies`, `execution`, `risk`, `runtime`, `research`), with `189` source files and `133` test files.
- Crypto-first maturity direction is already documented in [docs/MATURITY_GAP_PLAN_20260329.md](/D:/dev/polymarket_bot2.0/docs/MATURITY_GAP_PLAN_20260329.md), but several foundation quality gates are still open.
- Latest repository validation run (`python -m pm_bot validate-repo`) returned `620 passed / 3 failed`, with failures in:
  - replay baseline event contract matching
  - live recovery idempotency (processed trade IDs across restart)
  - crypto phase2 replay compare fixture expectations
- Linting is green (`ruff`), but strict typing still has drift (`mypy src` reports 4 errors in crypto strategy modules).
- Operator tooling remains mostly CLI/text-artefact based (`src/pm_bot/cli.py` is 2713 lines), while intended users are non-technical operators.
- Known issue docs still identify missing external alert escalation, even though local runtime alert objects exist.

## Ranked Ideas

### 1. Contract-Truth Pipeline for Runtime Artifacts
**Description:** Introduce explicit schema versions and fixture-generation commands for replay events, dashboard summaries, and operator-facing artifact contracts, then make CI block on contract drift unless fixtures/docs are updated in the same change.
**Rationale:** Current failing replay baseline test shows contract drift risk on core evidence artifacts. This idea closes the trust gap between runtime behavior and expected evidence outputs.
**Downsides:** Adds process overhead when intentionally changing event fields; requires disciplined fixture update workflow.
**Confidence:** 93%
**Complexity:** Medium
**Status:** Unexplored

### 2. Idempotent Live Recovery Ledger v2
**Description:** Harden `recover_live_state` and processed-trade persistence by introducing restart-safe replay checkpoints, canonical trade identity normalization, and dedicated restart-simulation test suites.
**Rationale:** A current failing runtime test indicates idempotency drift in a high-risk path. This is a direct blocker for safe shadow/small-live progression.
**Downsides:** Requires careful migration of existing runtime state assumptions and regression coverage around duplicate trade handling.
**Confidence:** 91%
**Complexity:** High
**Status:** Unexplored

### 3. Phase2 Determinism Gate (Fixture + Feature Toggle Matrix)
**Description:** Build a determinism gate for crypto phase2 replay that pins fixture metadata, model config hashes, and selection toggles, then enforces expected range/shape checks before exact-count assertions.
**Rationale:** Current test mismatch (`signals_generated` expected 5, actual 3) suggests replay outputs are sensitive to evolving assumptions. This gate reduces false confidence and makes drift explainable.
**Downsides:** Requires redesign of some brittle exact-value tests and may initially expose more hidden instability.
**Confidence:** 88%
**Complexity:** Medium
**Status:** Unexplored

### 4. External Alert Escalation Path for Runtime Failures
**Description:** Add pluggable outbound notification channels (webhook-first, then Slack/Telegram adapters) with dedupe, cooldown, and severity thresholds tied to halt/pause policy.
**Rationale:** Docs and known issues show alerts are mostly local state/artifacts today. For non-technical operation and real-money phases, external wake-up signals are mandatory.
**Downsides:** Introduces secrets/integration management and potential alert noise if thresholds are poorly tuned.
**Confidence:** 86%
**Complexity:** Medium
**Status:** Unexplored

### 5. Operator Control Surface Lite (Web-First, Not Full Redesign)
**Description:** Build a minimal operator web console that reads existing runtime artifacts and exposes a small set of guarded controls (`status`, `risk utilization`, `last rejection`, `manual resume/pause`) without replacing current CLI.
**Rationale:** Repository is already rich in runtime evidence but still CLI-heavy. A thin control layer improves usability for non-technical owners while preserving current architecture.
**Downsides:** Requires secure command bridge design and can become scope creep if expanded too quickly.
**Confidence:** 82%
**Complexity:** High
**Status:** Unexplored

### 6. Promotion Gatekeeper Command (Executable Maturity Criteria)
**Description:** Create one command that computes stage readiness (`paper`, `shadow`, `small_live`) from hard prerequisites (tests green, risk protections active, evidence completeness, alert health) and emits a machine-readable go/no-go decision.
**Rationale:** Maturity docs are strong, but promotion logic is still partly document-driven. Turning gates into executable policy reduces interpretation risk and keeps stage naming honest.
**Downsides:** Requires consensus on strict thresholds and maintenance when policies evolve.
**Confidence:** 84%
**Complexity:** Medium
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Full GUI redesign now | Too expensive before core runtime trust gaps are closed. |
| 2 | Expand sports+weather maturity in parallel | Duplicates documented anti-pattern; weakens crypto-first focus. |
| 3 | Add more strategy presets immediately | Risks tuning on unstable foundation and noisy evidence. |
| 4 | Replace CLI with new framework in one pass | Large blast radius; low short-term value relative to risk. |
| 5 | Introduce distributed microservices now | Premature for current repo scale and stage. |
| 6 | Add monthly-only retrospective reports | Helpful but lower leverage than closing current failing gates. |
| 7 | Build advanced ML model stack first | Not grounded in immediate blockers (contract drift, idempotency, alerting). |
| 8 | Add auto live-trading by default | Violates current staged safety posture. |
| 9 | Rewrite all docs before code fixes | Wrong order; trust comes from executable behavior first. |
| 10 | Add many new data providers now | Increases failure surface before stabilizing existing sources. |
| 11 | Massive package renaming/structure reorg | Not needed for current pain points; high migration cost. |
| 12 | Multi-board orchestration dashboard first | Better deferred until one board reaches mature baseline. |
| 13 | Real-time mobile app alerts first | Channel choice is secondary; outbound alert pipeline is the real dependency. |
| 14 | Immediate high-frequency execution mode | Increases market risk before base controls are proven. |
| 15 | Remove strict mypy to speed delivery | Conflicts with long-term maintainability bar and current quality goals. |
| 16 | Backtest-only roadmap | Ignores live/paper divergence and operator readiness requirements. |
| 17 | Manual checklist-only promotion governance | Inferior to executable gatekeeper for repeatability. |
| 18 | Deep optimize paper fill model now | Valuable later, but not before determinism and recovery correctness. |

## Session Log

- 2026-04-01: Initial ideation - 24 candidates generated, 6 survived.
