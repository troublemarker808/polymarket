# Crypto Calibration BTC Round 2 2026-03-28

## 1. Purpose

This round starts from the broader-validation winner:

- `r2-s175-b45-s55`

and asks a narrower BTC-specific question:

- should BTC ladders use an even shallower barrier model?
- should fusion lean even harder toward the surface term?

## 2. Command

```powershell
python -m pm_bot crypto-calibration-experiments --candidate-set btc_refined --train-snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --validation-snapshot-path tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl --holdout-snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase2\runtime_underlying_states.json --output-dir data\research\phase2_compare\calibration-btc-refined-round2-20260328
```

Detailed best-candidate report:

```powershell
python - <<'PY'
from pathlib import Path
from pm_bot.cli import _load_underlying_states
from pm_bot.strategies.crypto.phase1.calibration import generate_crypto_calibration_report
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig

generate_crypto_calibration_report(
    train_snapshot_path=Path(r"tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl"),
    validation_snapshot_path=Path(r"tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"),
    holdout_snapshot_path=Path(r"tests/fixtures/crypto_phase2/compare_snapshots.jsonl"),
    underlying_states=_load_underlying_states(r"tests/fixtures/crypto_phase2/runtime_underlying_states.json"),
    output_dir=Path(r"data/research/phase2_compare/calibration-btc-round2-best-20260328"),
    barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
    fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
)
PY
```

## 3. Artifacts

- `data/research/phase2_compare/calibration-btc-refined-round2-20260328/experiments.json`
- `data/research/phase2_compare/calibration-btc-refined-round2-20260328/experiments.md`
- `data/research/phase2_compare/calibration-btc-round2-best-20260328/report.json`
- `data/research/phase2_compare/calibration-btc-round2-best-20260328/summary.md`

## 4. Candidate Matrix

- `baseline`
  - steepness `2.4`
  - fusion `0.65 / 0.35`
- `btc-r1-s175-b45-s55`
  - steepness `1.75`
  - fusion `0.45 / 0.55`
- `btc-r1-s170-b45-s55`
  - steepness `1.70`
  - fusion `0.45 / 0.55`
- `btc-r1-s165-b45-s55`
  - steepness `1.65`
  - fusion `0.45 / 0.55`
- `btc-r1-s170-b40-s60`
  - steepness `1.70`
  - fusion `0.40 / 0.60`
- `btc-r1-s165-b40-s60`
  - steepness `1.65`
  - fusion `0.40 / 0.60`
- `btc-r1-s160-b40-s60`
  - steepness `1.60`
  - fusion `0.40 / 0.60`
- `btc-r1-s165-b35-s65`
  - steepness `1.65`
  - fusion `0.35 / 0.65`

## 5. Result Ranking

1. `btc-r1-s165-b35-s65`
   - train: `-25.57`
   - validation: `-55.12`
   - holdout: `17.34`
   - aggregate: `-25.85`
2. `btc-r1-s160-b40-s60`
   - train: `-28.81`
   - validation: `-62.13`
   - holdout: `15.43`
   - aggregate: `-29.96`
3. `btc-r1-s165-b40-s60`
   - train: `-30.01`
   - validation: `-63.49`
   - holdout: `14.61`
   - aggregate: `-31.13`
4. `btc-r1-s170-b40-s60`
   - train: `-31.17`
   - validation: `-64.81`
   - holdout: `13.81`
   - aggregate: `-32.26`
5. `btc-r1-s165-b45-s55`
   - train: `-34.44`
   - validation: `-71.85`
   - holdout: `11.87`
   - aggregate: `-36.40`
6. `btc-r1-s175-b45-s55`
   - train: `-37.01`
   - validation: `-74.78`
   - holdout: `10.09`
   - aggregate: `-38.92`
7. `baseline`
   - train: `-75.34`
   - validation: `-131.21`
   - holdout: `-15.24`
   - aggregate: `-80.08`

## 6. Interpretation

This round is decisive.

The BTC-validated winner moved again in the same direction:

- shallower barrier
- more surface-heavy fusion

And it moved far enough that the old cross-underlying winner is no longer best.

New best candidate:

- `steepness = 1.65`
- `fusion barrier weight = 0.35`
- `fusion surface weight = 0.65`

Compared with the old BTC-validated winner `r2-s175-b45-s55`, the new best
candidate improved:

- train by about `+11.44`
- validation by about `+19.66`
- holdout by about `+7.25`
- aggregate by about `+13.07`

That is a large enough move that this should be treated as a real baseline
change, not a tie-breaker.

## 7. Remaining Limitation

Even the new best candidate still leaves BTC runtime ladders negative on net
edge:

- `BTC dip 50,000`: observed `0.6450`, fair `0.4942`, net edge `-1393.29 bps`
- `BTC dip 45,000`: observed `0.5050`, fair `0.3908`, net edge `-1026.89 bps`
- `BTC dip 40,000`: observed `0.3950`, fair `0.3086`, net edge `-748.95 bps`

So the model is clearly better, but still not at a point where BTC runtime
ladders become tradable on these windows.

## 8. Conclusion

The new working calibration baseline should become:

- `steepness = 1.65`
- `fusion barrier weight = 0.35`
- `fusion surface weight = 0.65`

The next round should not go wider again. It should pick exactly one of:

1. BTC market-selection filters
2. BTC-only barrier calibration below `1.65`

Execution-layer tuning is still premature.

Update:

- option `1` has now been run and recorded in
  `docs/CRYPTO_MARKET_SELECTION_BTC_20260328.md`
- that report recommends `skip_series` for the current BTC runtime ladder strip
