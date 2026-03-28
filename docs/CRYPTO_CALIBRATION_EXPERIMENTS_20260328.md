# Crypto Calibration Experiments 2026-03-28

## 1. Purpose

This note records the first narrow calibration sweep over the crypto Phase 1
fair-value stack.

Scope of this round:

- adjust barrier steepness only
- adjust barrier/surface fusion weights only
- keep runtime safety and execution assumptions fixed

## 2. Command

```powershell
python -m pm_bot crypto-calibration-experiments --train-snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --validation-snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --holdout-snapshot-path tests\fixtures\crypto_phase1\ladder_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase1\underlying_state.json --output-dir data\research\phase2_compare\calibration-experiments-20260328
```

Artifacts:

- `data/research/phase2_compare/calibration-experiments-20260328/experiments.json`
- `data/research/phase2_compare/calibration-experiments-20260328/experiments.md`

## 3. Candidate Matrix

Candidates tested:

- `baseline`
  - barrier steepness: `2.4`
  - fusion weights: `0.65 / 0.35`
- `shallower-barrier`
  - barrier steepness: `2.0`
  - fusion weights: `0.65 / 0.35`
- `surface-heavier`
  - barrier steepness: `2.4`
  - fusion weights: `0.55 / 0.45`
- `shallower-plus-surface`
  - barrier steepness: `2.0`
  - fusion weights: `0.55 / 0.45`
- `much-shallower-plus-surface`
  - barrier steepness: `1.8`
  - fusion weights: `0.50 / 0.50`

## 4. Result Ranking

1. `much-shallower-plus-surface`
   - train: `-43.10`
   - validation: `6.21`
   - holdout: `-40.93`
   - aggregate: `-27.87`
2. `shallower-plus-surface`
   - train: `-53.55`
   - validation: `-0.71`
   - holdout: `-51.06`
   - aggregate: `-37.20`
3. `surface-heavier`
   - train: `-62.91`
   - validation: `-7.28`
   - holdout: `-60.44`
   - aggregate: `-45.73`
4. `shallower-barrier`
   - train: `-64.27`
   - validation: `-7.47`
   - holdout: `-61.16`
   - aggregate: `-46.61`
5. `baseline`
   - train: `-75.34`
   - validation: `-15.24`
   - holdout: `-72.24`
   - aggregate: `-56.69`

## 5. Interpretation

The ranking is consistent:

- every move toward a shallower barrier model helped
- every move toward heavier surface weighting helped
- the best candidate combined both changes

The most important result is not that any score became positive overall. It is
that the best candidate improved all three splits versus baseline:

- train improved by `32.24`
- validation improved by `21.45`
- holdout improved by `31.31`

This strongly suggests the current baseline is systematically too conservative,
and the first profitable direction is:

- reduce barrier steepness
- let surface consistency correct more of the barrier output

## 6. Next Round

The next calibration round should stay narrow.

Recommended candidate family:

- barrier steepness between `1.7` and `2.0`
- fusion barrier weight between `0.45` and `0.55`
- fusion surface weight between `0.45` and `0.55`

Do not widen scope yet to:

- execution thresholds
- slippage assumptions
- market-family expansion

Those are downstream. The current evidence still points to fair-value
calibration as the primary bottleneck.
