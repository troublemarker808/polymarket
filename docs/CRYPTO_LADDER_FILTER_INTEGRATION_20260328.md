# Crypto Ladder Filter Integration 2026-03-28

## 1. Scope

This started as a replay-only change.

It now covers both:

- the `crypto.phase2` research replay path
- the dedicated `crypto.phase2` continuous paper path

## 2. What Changed

Added a series-level selection report:

- `src/pm_bot/strategies/crypto/phase1/selection.py`

Added a reusable skip-set helper:

- `recommended_skip_series_keys(report)`

Integrated the skip-set into `crypto.phase2` entry evaluation:

- `src/pm_bot/strategies/crypto/phase2/strategy.py`
- `src/pm_bot/strategies/crypto/phase2/replay.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/runtime/paper_session.py`

Behavior:

- entry signals respect `blocked_series_keys`
- exit logic is unchanged
- replay uses the current working BTC-aware baseline:
  - `steepness = 1.65`
  - `fusion barrier weight = 0.35`
  - `fusion surface weight = 0.65`

## 3. Verification

Command:

```powershell
python -m pm_bot crypto-phase2-replay --snapshot-path tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl --underlying-state-path tests\fixtures\crypto_phase2\runtime_underlying_states.json --output-dir data\research\phase2_compare\phase2-btc-filtered-20260328
```

Artifact:

- `data/research/phase2_compare/phase2-btc-filtered-20260328/metrics.json`

Observed result:

- `processed_snapshots = 24`
- `signals_generated = 0`
- `submitted_orders = 0`
- `events_recorded = 0`
- `status = completed`

## 4. Interpretation

This confirms the filter is no longer just a research note.

It now changes the replay trading path in the intended place:

- BTC yearly dip ladder runtime window
- current research baseline
- zero entry attempts because the whole series is marked `skip_series`

## 5. Current Status

The filter now gates entry in the dedicated paper path too, but it still does
not touch the generic legacy `crypto.surface` paper path.

That keeps the rollout scoped:

- `crypto.phase2` research replay: enabled
- `crypto.phase2` dedicated paper mode: enabled
- legacy generic paper path: unchanged

## 6. Next Step

The next safe promotion path is:

1. observe filter behavior in longer dedicated `crypto.phase2` paper windows
2. confirm signal quality and inactivity periods look sane
3. only then consider broader runtime promotion
