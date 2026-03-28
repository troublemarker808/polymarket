# Crypto Calibration Refined Round 2026-03-28

## 1. Purpose

This note records the second, narrower calibration sweep after the first round
showed that the fair-value stack improved when:

- barrier steepness was reduced
- surface consistency received more weight in fusion

This round only searched inside that direction.

## 2. Command

```powershell
python -m pm_bot crypto-calibration-experiments --candidate-set refined --train-snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --validation-snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --holdout-snapshot-path tests\fixtures\crypto_phase1\ladder_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase1\underlying_state.json --output-dir data\research\phase2_compare\calibration-experiments-refined-20260328
```

Artifacts:

- `data/research/phase2_compare/calibration-experiments-refined-20260328/experiments.json`
- `data/research/phase2_compare/calibration-experiments-refined-20260328/experiments.md`

## 3. Candidate Matrix

Candidates tested:

- `baseline`
  - steepness `2.4`
  - fusion `0.65 / 0.35`
- `r2-s185-b50-s50`
  - steepness `1.85`
  - fusion `0.50 / 0.50`
- `r2-s180-b50-s50`
  - steepness `1.80`
  - fusion `0.50 / 0.50`
- `r2-s175-b50-s50`
  - steepness `1.75`
  - fusion `0.50 / 0.50`
- `r2-s180-b55-s45`
  - steepness `1.80`
  - fusion `0.55 / 0.45`
- `r2-s180-b45-s55`
  - steepness `1.80`
  - fusion `0.45 / 0.55`
- `r2-s175-b45-s55`
  - steepness `1.75`
  - fusion `0.45 / 0.55`

## 4. Result Ranking

1. `r2-s175-b45-s55`
   - train: `-37.01`
   - validation: `10.09`
   - holdout: `-35.16`
   - aggregate: `-22.51`
2. `r2-s180-b45-s55`
   - train: `-38.24`
   - validation: `9.24`
   - holdout: `-36.39`
   - aggregate: `-23.63`
3. `r2-s175-b50-s50`
   - train: `-41.73`
   - validation: `7.16`
   - holdout: `-39.56`
   - aggregate: `-26.63`
4. `r2-s180-b50-s50`
   - train: `-43.10`
   - validation: `6.21`
   - holdout: `-40.93`
   - aggregate: `-27.87`
5. `r2-s185-b50-s50`
   - train: `-44.42`
   - validation: `5.29`
   - holdout: `-42.26`
   - aggregate: `-29.08`
6. `r2-s180-b55-s45`
   - train: `-47.95`
   - validation: `3.19`
   - holdout: `-45.46`
   - aggregate: `-32.11`
7. `baseline`
   - train: `-75.34`
   - validation: `-15.24`
   - holdout: `-72.24`
   - aggregate: `-56.69`

## 5. Interpretation

This round sharpened the direction from round 1.

The best-performing candidates all share the same shape:

- barrier steepness around `1.75` to `1.80`
- surface-heavy fusion, especially `0.45 / 0.55`

The top candidate, `r2-s175-b45-s55`, improved over baseline by:

- train: `+38.33`
- validation: `+25.33`
- holdout: `+37.08`
- aggregate: `+34.18`

The ranking also shows that the best results are not just from lowering
steepness. They improve further when the surface term gets more say than the
barrier term.

That means the current model error is probably:

- the barrier model still over-penalizes distance
- and the fusion layer still trusts that barrier output too much

## 6. Recommended Next Move

Promote one candidate into a temporary calibration target:

- `barrier steepness = 1.75`
- `fusion barrier weight = 0.45`
- `fusion surface weight = 0.55`

That follow-up BTC validation has now been run and recorded in:

- `docs/CRYPTO_CALIBRATION_BTC_VALIDATION_20260328.md`

The BTC result did not overturn the ranking. `r2-s175-b45-s55` still remains
the best candidate once a real BTC ladder window is used as validation, but BTC
itself is still materially too conservative.

So the next move is no longer "add BTC data". That part is done.

The next move is now:

1. Treat `r2-s175-b45-s55` as the working calibration baseline.
2. Run a BTC-specific round that changes only one of:
   - barrier steepness by a narrower BTC-focused band
   - BTC market-selection filters

Do not start tuning execution thresholds yet. The evidence still says the
largest remaining gains are in fair-value calibration and market selection.
