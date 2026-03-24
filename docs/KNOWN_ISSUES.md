# Known Issues

Last updated: 2026-03-24

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

## 2. Paper execution is still a simplified fill model

- Current behavior:
  - Fills are all-or-nothing at top-of-book prices.
  - No queue position, no partial fills, no fees, no slippage model.
- Impact:
  - Replay/backtest and paper PnL are directionally useful, but they are still optimistic compared with live execution.
- Follow-up direction:
  - Add partial-fill simulation, fee modeling, and configurable slippage.
  - Candidate code area:
    - `src/pm_bot/execution/paper_adapter.py`

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
