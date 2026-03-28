# Crypto Calibration Experiments

- generated_at: 2026-03-27T21:08:26.871507+00:00
- baseline_candidate: baseline

## Dataset Split

- holdout: tests\fixtures\crypto_phase2\compare_snapshots.jsonl
- train: tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl
- validation: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl

## Results

### r2-s175-b45-s55

- train_score: -37.01
- validation_score: -74.78
- holdout_score: 10.09
- aggregate_score: -38.92
- accepted: true

### r2-s180-b45-s55

- train_score: -38.24
- validation_score: -76.18
- holdout_score: 9.24
- aggregate_score: -40.13
- accepted: true

### r2-s175-b50-s50

- train_score: -41.73
- validation_score: -83.47
- holdout_score: 7.16
- aggregate_score: -44.47
- accepted: false

### r2-s180-b50-s50

- train_score: -43.10
- validation_score: -85.02
- holdout_score: 6.21
- aggregate_score: -45.81
- accepted: false

### r2-s185-b50-s50

- train_score: -44.42
- validation_score: -86.53
- holdout_score: 5.29
- aggregate_score: -47.11
- accepted: false

### r2-s180-b55-s45

- train_score: -47.95
- validation_score: -93.87
- holdout_score: 3.19
- aggregate_score: -51.50
- accepted: false

### baseline

- train_score: -75.34
- validation_score: -131.21
- holdout_score: -15.24
- aggregate_score: -80.08
- accepted: false
