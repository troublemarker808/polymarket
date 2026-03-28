# Crypto Calibration Experiments

- generated_at: 2026-03-27T20:57:09.225919+00:00
- baseline_candidate: baseline

## Dataset Split

- holdout: tests\fixtures\crypto_phase1\ladder_snapshots.jsonl
- train: tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl
- validation: tests\fixtures\crypto_phase2\compare_snapshots.jsonl

## Results

### r2-s175-b45-s55

- train_score: -37.01
- validation_score: 10.09
- holdout_score: -35.16
- aggregate_score: -22.51
- accepted: true

### r2-s180-b45-s55

- train_score: -38.24
- validation_score: 9.24
- holdout_score: -36.39
- aggregate_score: -23.63
- accepted: true

### r2-s175-b50-s50

- train_score: -41.73
- validation_score: 7.16
- holdout_score: -39.56
- aggregate_score: -26.63
- accepted: true

### r2-s180-b50-s50

- train_score: -43.10
- validation_score: 6.21
- holdout_score: -40.93
- aggregate_score: -27.87
- accepted: true

### r2-s185-b50-s50

- train_score: -44.42
- validation_score: 5.29
- holdout_score: -42.26
- aggregate_score: -29.08
- accepted: true

### r2-s180-b55-s45

- train_score: -47.95
- validation_score: 3.19
- holdout_score: -45.46
- aggregate_score: -32.11
- accepted: true

### baseline

- train_score: -75.34
- validation_score: -15.24
- holdout_score: -72.24
- aggregate_score: -56.69
- accepted: true
