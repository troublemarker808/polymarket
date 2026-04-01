# Crypto Calibration Experiments

- generated_at: 2026-04-01T14:54:04.136885+00:00
- baseline_candidate: btc-r1-s165-b35-s65

## Dataset Split

- baseline_candidate: btc-r1-s165-b35-s65
- baseline_preset: crypto-calibration-baseline-20260328
- holdout: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- train: data\runtime\phase2-paper-snapshots.btc-longtail.v58.20260327.jsonl
- validation: data\runtime\phase2-paper-snapshots.btc-longtail.v58.overnight.20260327.jsonl

## Promotion Decision

- decision: keep_locked_baseline
- locked_baseline_candidate: btc-r1-s165-b35-s65
- evaluated_locked_baseline: true
- recommended_candidate: btc-r1-s165-b35-s65
- reason: baseline ranked first, but it did not clear the full promotion gate against the locked baseline.

## Results

### baseline

- train_score: 224.09
- validation_score: -1.85
- holdout_score: 225.02
- aggregate_score: 156.49
- accepted: false

### btc-r1-s170-b45-s55

- train_score: 219.84
- validation_score: 14.50
- holdout_score: 196.81
- aggregate_score: 153.63
- accepted: false

### btc-r1-s175-b45-s55

- train_score: 219.54
- validation_score: 14.05
- holdout_score: 196.51
- aggregate_score: 153.29
- accepted: false

### btc-r1-s170-b40-s60

- train_score: 205.69
- validation_score: 16.61
- holdout_score: 190.67
- aggregate_score: 145.96
- accepted: false

### btc-r1-s165-b45-s55

- train_score: 196.15
- validation_score: 14.96
- holdout_score: 173.12
- aggregate_score: 137.19
- accepted: false

### btc-r1-s165-b40-s60

- train_score: 181.96
- validation_score: 17.02
- holdout_score: 166.94
- aggregate_score: 129.47
- accepted: false

### btc-r1-s160-b40-s60

- train_score: 176.60
- validation_score: 17.43
- holdout_score: 169.44
- aggregate_score: 127.42
- accepted: false

### btc-r1-s165-b35-s65

- train_score: 167.77
- validation_score: 19.08
- holdout_score: 162.95
- aggregate_score: 122.20
- accepted: false
