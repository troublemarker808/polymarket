# Crypto Calibration Experiments

- generated_at: 2026-03-27T20:45:16.729893+00:00
- baseline_candidate: baseline

## Dataset Split

- holdout: tests\fixtures\crypto_phase1\ladder_snapshots.jsonl
- train: tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl
- validation: tests\fixtures\crypto_phase2\compare_snapshots.jsonl

## Results

### much-shallower-plus-surface

- train_score: -43.10
- validation_score: 6.21
- holdout_score: -40.93
- aggregate_score: -27.87
- accepted: true

### shallower-plus-surface

- train_score: -53.55
- validation_score: -0.71
- holdout_score: -51.06
- aggregate_score: -37.20
- accepted: true

### surface-heavier

- train_score: -62.91
- validation_score: -7.28
- holdout_score: -60.44
- aggregate_score: -45.73
- accepted: true

### shallower-barrier

- train_score: -64.27
- validation_score: -7.47
- holdout_score: -61.16
- aggregate_score: -46.61
- accepted: true

### baseline

- train_score: -75.34
- validation_score: -15.24
- holdout_score: -72.24
- aggregate_score: -56.69
- accepted: true
