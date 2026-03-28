# Paper Baseline V1

## Purpose

This document freezes the first stable continuous-paper baseline before sample-acquisition tuning.

Use this baseline when you need:

- a reproducible reference configuration
- a fixed artifact set for later comparison
- a stable code-plus-config point that can stay aligned with future real-trading promotion work

## Version Label

- label: `paper-baseline-v1`
- frozen_at: `2026-03-26 Asia/Shanghai`
- status: `continuous paper runtime stable, zero-fill baseline`

## Config Profile

- config_dir: [paper-baseline-v1](/D:/dev/polymarket_bot2.0/configs/profiles/paper-baseline-v1)

Validation command:

```powershell
python -m pm_bot.cli validate-config --config-dir configs/profiles/paper-baseline-v1
```

## Frozen Baseline Artifacts

- metrics: [analysis-paper-session-metrics.v8.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v8.json)
- events: [analysis-paper-session-events.v8.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v8.jsonl)
- snapshot capture: [analysis-paper-session-capture.v8.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v8.jsonl)
- health: [analysis-paper-session-health.v8.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-health.v8.md)
- autoresearch: [analysis-paper-session-autoresearch.v8.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-autoresearch.v8.md)
- mined windows: [analysis-mined-windows.v2/summary.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-mined-windows.v2/summary.md)
- mined-window replay: [analysis-fixed-window-mined-window01.v4/summary.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-fixed-window-mined-window01.v4/summary.md)

## Baseline Summary

- processed_snapshots: `120`
- signals_generated: `31`
- orders_submitted: `15`
- orders_rejected: `16`
- orders_filled: `0`
- orders_expired: `10`
- orders_canceled: `4`
- dominant_rejection_reason: `daily order hard limit reached`
- baseline_classification: `execution-bound`

## Strategy Participation

- `crypto.maker`: active
- `crypto.surface`: inactive on the frozen `v8` dataset

## Interpretation

- This baseline is useful for runtime correctness and negative-sample analysis.
- This baseline is not yet sufficient for execution calibration or profitability claims because it contains no fills.
- Future sample-acquisition experiments should compare themselves against this baseline instead of replacing it.

## Verification State

- test_status: `140 passed`
- command: `pytest -q`

## Recommended Use

- Keep this profile unchanged.
- Use it as the comparison anchor for:
  - sample-acquisition paper configs
  - future paper/live calibration
  - promotion discussions for real trading
