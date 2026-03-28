# Paper Calibration

## Purpose

Calibration is the step that turns paper execution from a plausible simulator into
something promotion-worthy.

The paper runtime now emits comparable execution metrics to JSON:

- `signals_generated`
- `signals_rejected`
- `orders_submitted`
- `orders_filled`
- `orders_partially_filled`
- `orders_expired`
- `orders_canceled`
- `fill_rate`
- `cancel_rate`
- `avg_time_to_fill_ms`
- `avg_fill_price_vs_mid_bps`
- `maker_fill_share`
- `taker_fill_share`

## Workflow

1. Run a paper session over the same market window you want to study.
2. Save the resulting metrics JSON.
3. Produce a second metrics JSON from the comparison run you want to treat as baseline.
4. Compare both files with:

```bash
python -m pm_bot compare-execution-metrics \
  --baseline-metrics-path data/runtime/live-calibration-baseline.json \
  --candidate-metrics-path data/runtime/paper-metrics.latest.json
```

## What To Compare

Treat these as promotion-facing metrics:

- submit rate
- fill rate
- cancel rate
- average time to fill
- average fill price vs mid
- maker/taker fill share

## Operator Rules

- Do not promote paper assumptions from a single day.
- Use the same market set and similar liquidity regimes when comparing runs.
- If maker fill share is much lower than the comparison baseline, the queue model is still too pessimistic.
- If taker fills are fast but `avg_fill_price_vs_mid_bps` is materially worse than baseline, slippage is too optimistic.
- If fills diverge but submit/reject counts match, the gap is execution realism, not strategy generation.

## Current Boundary

This workflow assumes both sides produce the same metrics schema. If the comparison
run comes from a different pipeline, normalize it into the same JSON shape before
using `compare-execution-metrics`.
