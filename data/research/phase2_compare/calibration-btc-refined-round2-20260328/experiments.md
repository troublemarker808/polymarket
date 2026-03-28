# Crypto Calibration Experiments

- generated_at: 2026-03-27T21:14:47.073831+00:00
- baseline_candidate: baseline

## Dataset Split

- holdout: tests\fixtures\crypto_phase2\compare_snapshots.jsonl
- train: tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl
- validation: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl

## Results

### btc-r1-s165-b35-s65

- train_score: -25.57
- validation_score: -55.12
- holdout_score: 17.34
- aggregate_score: -25.85
- accepted: true

### btc-r1-s160-b40-s60

- train_score: -28.81
- validation_score: -62.13
- holdout_score: 15.43
- aggregate_score: -29.96
- accepted: true

### btc-r1-s165-b40-s60

- train_score: -30.01
- validation_score: -63.49
- holdout_score: 14.61
- aggregate_score: -31.13
- accepted: true

### btc-r1-s170-b40-s60

- train_score: -31.17
- validation_score: -64.81
- holdout_score: 13.81
- aggregate_score: -32.26
- accepted: true

### btc-r1-s165-b45-s55

- train_score: -34.44
- validation_score: -71.85
- holdout_score: 11.87
- aggregate_score: -36.40
- accepted: true

### btc-r1-s170-b45-s55

- train_score: -35.74
- validation_score: -73.34
- holdout_score: 10.97
- aggregate_score: -37.68
- accepted: true

### btc-r1-s175-b45-s55

- train_score: -37.01
- validation_score: -74.78
- holdout_score: 10.09
- aggregate_score: -38.92
- accepted: true

### baseline

- train_score: -75.34
- validation_score: -131.21
- holdout_score: -15.24
- aggregate_score: -80.08
- accepted: false
