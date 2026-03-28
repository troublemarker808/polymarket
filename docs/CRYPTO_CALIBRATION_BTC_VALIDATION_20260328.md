# Crypto Calibration BTC Validation 2026-03-28

## 1. Purpose

This note widens the refined calibration round to include a real BTC runtime
ladder window, so the ETH-led result can be checked against another underlying
before promoting it as the working baseline.

## 2. Added Inputs

- BTC runtime ladder fixture:
  - `tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl`
- Multi-underlying state payload:
  - `tests/fixtures/crypto_phase2/runtime_underlying_states.json`

The BTC runtime window was extracted from:

- `data/runtime/analysis-paper-session-capture.paper-normal-observation-fix2-20260327-231542.jsonl`

Tracked BTC ladder market ids:

- `1339767` -> `BTC dip 50,000`
- `701502` -> `BTC dip 45,000`
- `1339768` -> `BTC dip 40,000`

## 3. Commands

Baseline with BTC validation:

```powershell
python -m pm_bot crypto-calibration-report --train-snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --validation-snapshot-path tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl --holdout-snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase2\runtime_underlying_states.json --output-dir data\research\phase2_compare\calibration-btc-baseline-20260328
```

Refined sweep with BTC validation:

```powershell
python -m pm_bot crypto-calibration-experiments --candidate-set refined --train-snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --validation-snapshot-path tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl --holdout-snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase2\runtime_underlying_states.json --output-dir data\research\phase2_compare\calibration-btc-refined-20260328
```

Best-candidate detailed report:

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
    output_dir=Path(r"data/research/phase2_compare/calibration-btc-best-candidate-20260328"),
    barrier_model_config=CryptoBarrierModelConfig(steepness=1.75),
    fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.45, surface_weight=0.55),
)
PY
```

## 4. Artifacts

- `data/research/phase2_compare/calibration-btc-baseline-20260328/report.json`
- `data/research/phase2_compare/calibration-btc-baseline-20260328/summary.md`
- `data/research/phase2_compare/calibration-btc-refined-20260328/experiments.json`
- `data/research/phase2_compare/calibration-btc-refined-20260328/experiments.md`
- `data/research/phase2_compare/calibration-btc-best-candidate-20260328/report.json`
- `data/research/phase2_compare/calibration-btc-best-candidate-20260328/summary.md`

## 5. Result Ranking

1. `r2-s175-b45-s55`
   - train: `-37.01`
   - validation: `-74.78`
   - holdout: `10.09`
   - aggregate: `-38.92`
2. `r2-s180-b45-s55`
   - train: `-38.24`
   - validation: `-76.18`
   - holdout: `9.24`
   - aggregate: `-40.13`
3. `r2-s175-b50-s50`
   - train: `-41.73`
   - validation: `-83.47`
   - holdout: `7.16`
   - aggregate: `-44.47`
4. `baseline`
   - train: `-75.34`
   - validation: `-131.21`
   - holdout: `-15.24`
   - aggregate: `-80.08`

## 6. Interpretation

The important result is not that BTC is already fixed. It is not.

The important result is that the same candidate that won on ETH also remains
the best candidate after BTC is introduced as a real runtime validation set.

That means:

- the refined direction generalizes better than the old baseline
- the current model error is still mostly the same kind of error
- but BTC dip ladders remain materially too conservative even after the refined
  tuning

Best-candidate BTC net edges:

- `1339767` / `BTC dip 50,000`: observed `0.6450`, fair `0.4452`, net edge `-1882.57 bps`
- `701502` / `BTC dip 45,000`: observed `0.5050`, fair `0.3523`, net edge `-1412.40 bps`
- `1339768` / `BTC dip 40,000`: observed `0.3950`, fair `0.2781`, net edge `-1053.78 bps`

So the direction is correct, but BTC is still far from producing positive net
edge candidates on real runtime windows.

## 7. Follow-up

This document is no longer the latest BTC-specific result.

A narrower BTC round has already been run and recorded in:

- `docs/CRYPTO_CALIBRATION_BTC_ROUND2_20260328.md`

That round kept the same conclusion about direction but moved the working
baseline further:

- from `1.75 / 0.45 / 0.55`
- to `1.65 / 0.35 / 0.65`

So this note should now be read as the first BTC validation checkpoint, not the
latest recommended baseline.
