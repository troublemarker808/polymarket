# Known Issues

Last updated: 2026-03-25

## 1. Replay/backtest can finish with pending paper orders

- Evidence:
  - `python -m pm_bot replay --config-dir configs --snapshot-path data/research/sample_snapshots.jsonl`
  - `python -m pm_bot backtest --config-dir configs --snapshot-path data/research/sample_snapshots.jsonl`
  - Both runs ended with `pending_orders=1`.
- Why it happens:
  - The paper engine now keeps realistic pending orders instead of silently dropping them.
  - If the input ends before a market becomes marketable again or before TTL expiry on that market, the order remains open at the end of the run.
- Follow-up direction:
  - Add an explicit end-of-run finalization policy in research mode.
  - Candidate code areas:
    - `src/pm_bot/research/engine.py`
    - `src/pm_bot/runtime/paper_sync.py`
    - `src/pm_bot/execution/paper_adapter.py`

## 2. Paper execution is closer to live, but still not exchange-equal

- Current behavior:
  - Paper now supports continuous sessions, partial fills, queue-ahead tracking, fee modeling, and configurable taker slippage.
  - Matching still relies on public book/trade updates rather than exchange-internal queue state.
- Impact:
  - Paper is now much more useful for execution diagnostics, but it still cannot perfectly reproduce true exchange priority, hidden liquidity, or cancel races under exchange-internal timing.
- Follow-up direction:
  - Add paper-vs-live calibration reports and fit queue/latency assumptions from small-live observations.
  - Candidate code areas:
    - `src/pm_bot/execution/paper_adapter.py`
    - `src/pm_bot/execution/paper_matching.py`
    - `src/pm_bot/execution/paper_metrics.py`

## 3. Data-source recovery markers stop at local state and event logs

- Current behavior:
  - Gamma HTTP bootstrap now retries transient failures.
  - Runtime state now tracks `last_data_success_at`, `last_data_error`, and `consecutive_data_failures`.
  - Failures/recovery are written into recorder events.
- Remaining gap:
  - There is still no external operator alerting path for repeated failures.
- Follow-up direction:
  - Add threshold-based alerting and optional halt escalation for prolonged feed degradation.
  - Candidate code areas:
    - `src/pm_bot/risk/manager.py`
    - `src/pm_bot/runtime/live_session.py`
    - `src/pm_bot/runtime/paper_session.py`
