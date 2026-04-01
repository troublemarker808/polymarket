# Crypto Calibration Experiments

- generated_at: 2026-04-01T14:54:48.298945+00:00
- baseline_candidate: btc-r1-s165-b35-s65

## Dataset Split

- baseline_candidate: btc-r1-s165-b35-s65
- baseline_preset: crypto-calibration-baseline-20260328
- holdout: tests\fixtures\crypto_phase1\ladder_snapshots.jsonl
- train: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl
- validation: tests\fixtures\crypto_phase2\compare_snapshots.jsonl

## Promotion Decision

- decision: keep_locked_baseline
- locked_baseline_candidate: btc-r1-s165-b35-s65
- evaluated_locked_baseline: true
- recommended_candidate: btc-r1-s165-b35-s65
- reason: Locked baseline remains the strongest evaluated candidate on aggregate score.

## Results

### btc-r1-s165-b35-s65

- train_score: 0.57
- validation_score: 44.05
- holdout_score: 12.48
- aggregate_score: 16.00
- accepted: true

### btc-r1-s160-b40-s60

- train_score: -2.23
- validation_score: 43.12
- holdout_score: 11.31
- aggregate_score: 14.08
- accepted: true

### btc-r1-s165-b40-s60

- train_score: -2.77
- validation_score: 43.01
- holdout_score: 10.83
- aggregate_score: 13.68
- accepted: true

### btc-r1-s170-b40-s60

- train_score: -3.30
- validation_score: 42.90
- holdout_score: 10.37
- aggregate_score: 13.29
- accepted: true

### btc-r1-s165-b45-s55

- train_score: -6.12
- validation_score: 41.97
- holdout_score: 9.19
- aggregate_score: 11.37
- accepted: true

### btc-r1-s170-b45-s55

- train_score: -6.72
- validation_score: 41.85
- holdout_score: 8.66
- aggregate_score: 10.93
- accepted: true

### btc-r1-s175-b45-s55

- train_score: -7.29
- validation_score: 41.73
- holdout_score: 8.16
- aggregate_score: 10.51
- accepted: true

### baseline

- train_score: -29.86
- validation_score: 35.55
- holdout_score: -6.68
- aggregate_score: -5.60
- accepted: true
