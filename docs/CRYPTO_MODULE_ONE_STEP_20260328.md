# Crypto Module One-Step Status 2026-03-28

## 1. What "One-Step" Means Here

For the current repo state, "one-step" still does not honestly mean:

- fully live-ready crypto trading in the continuous live session path

But it now does cover:

- a single, official crypto research entrypoint
- a dedicated continuous paper-session entrypoint
- pricing, calibration baseline, series filtering, and execution replay/paper
  wiring end to end

## 2. Official Entry Point

For research suites, use:

```powershell
python -m pm_bot crypto-phase2-suite --snapshot-path <snapshots.jsonl> --underlying-state-path <underlying_states.json> --output-dir <outdir>
```

This now runs, in one pass:

1. crypto ladder market selection
2. unfiltered `crypto.phase2` replay
3. filtered `crypto.phase2` replay
4. suite summary output

For continuous paper mode, use:

```powershell
python -m pm_bot run-paper-crypto-phase2-session --underlying-state-path <underlying_states.json> --config-dir configs
```

That command now resolves to:

- `configs/profiles/paper-crypto-phase2-v1`
- `crypto.phase2`
- runtime fair-value refresh
- runtime ladder-series blocking
- runtime position-intent and reentry-state updates

## 3. Current Crypto Baseline

The suite uses the current working calibration baseline:

- `steepness = 1.65`
- `fusion barrier weight = 0.35`
- `fusion surface weight = 0.65`

## 4. Current Coverage

The crypto module now has these connected layers:

- market normalization
- ladder series construction
- pricing inputs
- barrier model
- surface consistency model
- fair-value fusion
- net-edge calculation
- calibration reports
- BTC-specific validation
- series-level market selection
- `crypto.phase2` execution policy
- filtered and unfiltered replay
- one-command suite orchestration
- file-backed runtime underlying-state provider
- dedicated `crypto.phase2` continuous paper-session wiring

## 5. Current Hard Boundary

The biggest remaining boundary is no longer "paper wiring"; that is now present.

The remaining hard boundary is:

- production-grade runtime underlying-state ingestion

The current paper path uses a file-backed provider. That is good enough for
continuous paper sessions and controlled experiments, but not yet a robust live
feed with guaranteed freshness and failure handling.

## 6. Recommended Promotion Path

1. Keep `crypto.phase2` as the official crypto research path.
2. Use `crypto-phase2-suite` as the default evaluation command.
3. Use `run-paper-crypto-phase2-session` for controlled paper runs with a file-backed underlying-state payload.
4. Replace the file-backed provider with a real runtime spot/vol feed.
5. Then promote the same fair-value + filter stack into continuous live mode.
