# Sync Normal Shadow Mode

## Goal

Run one normal crypto strategy once, generate one shared `intent_id`, and execute that same intent on:

- live small-notional trading
- paper shadow trading

This mode replaces the old `execution_sample` path as the main validation route for strategy realism.

## What Changed

- Added `intent_id` to:
  - `OrderIntent`
  - tracked orders
  - pending-order state
  - closed trades
  - comparable event payloads
- Added a new synchronized runtime:
  - live remains the primary execution path
  - shadow paper mirrors only successful live submissions and cancellations
  - both sides use the same snapshot stream
  - both sides write their own `events / metrics / state`
- Added a new CLI command:
  - `run-sync-crypto-session`
- Added a new normal-strategy profile:
  - `configs/profiles/sync-normal-shadow-v1`

## Architecture

1. `EventRouter` evaluates normal strategy signals once.
2. Router assigns a unique `intent_id`.
3. Live execution submits the order.
4. If live submission succeeds, the same `OrderIntent` is mirrored into shadow paper.
5. Live and shadow write separate comparable artifacts.
6. Later analysis compares both sides by the same `intent_id`.

## Current Boundary

- The first synchronized normal profile uses `crypto.surface` only.
- `crypto.maker` is intentionally not in the first shadow-normal profile because maker realism is still the least calibrated path.
- Signal generation uses live state only. Shadow does not generate its own signals.
- Start from a flat live account:
  - no open orders
  - no leftover positions
- Recommended recovery scope is `session`.

## Artifacts

Use paired files:

- live:
  - `live state`
  - `live events`
  - `live metrics`
- shadow:
  - `shadow state`
  - `shadow events`
  - `shadow metrics`

Both sides now contain matching `intent_id` on submitted orders and closed trades.

## Command

```powershell
python -m pm_bot.cli run-sync-crypto-session `
  --config-dir configs/profiles/sync-normal-shadow-v1 `
  --state-path data/runtime/sync-live-state.json `
  --event-path data/runtime/sync-live-events.jsonl `
  --metrics-path data/runtime/sync-live-metrics.json `
  --shadow-state-path data/runtime/sync-shadow-state.json `
  --shadow-event-path data/runtime/sync-shadow-events.jsonl `
  --shadow-metrics-path data/runtime/sync-shadow-metrics.json `
  --summary-every-snapshots 120
```

## Key Files

- `src/pm_bot/orchestrator/event_router.py`
- `src/pm_bot/runtime/live_session.py`
- `src/pm_bot/runtime/sync_session.py`
- `src/pm_bot/runtime/paper_sync.py`
- `src/pm_bot/runtime/live_reconcile.py`
- `configs/profiles/sync-normal-shadow-v1/base.example.toml`
- `configs/profiles/sync-normal-shadow-v1/crypto.v1.example.toml`
