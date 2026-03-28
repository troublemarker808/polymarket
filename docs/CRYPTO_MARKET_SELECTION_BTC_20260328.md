# Crypto Market Selection BTC 2026-03-28

## 1. Purpose

After BTC-specific calibration round 2, the remaining question was whether the
BTC ladder problem was still mostly model-shape error or whether the whole
series should simply be filtered out as a non-tradable strip.

This note answers that by producing a series-level market-selection report under
the current working calibration baseline:

- `steepness = 1.65`
- `fusion barrier weight = 0.35`
- `fusion surface weight = 0.65`

## 2. Command

```powershell
python -m pm_bot crypto-market-selection-report --snapshot-path tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl --underlying-state-path tests\fixtures\crypto_phase2\runtime_underlying_states.json --output-dir data\research\phase2_compare\btc-market-selection-20260328
```

## 3. Artifacts

- `data/research/phase2_compare/btc-market-selection-20260328/report.json`
- `data/research/phase2_compare/btc-market-selection-20260328/markets.jsonl`
- `data/research/phase2_compare/btc-market-selection-20260328/summary.md`

## 4. Result

Series:

- `what-price-will-bitcoin-hit-before-2027`

Current report:

- market_count: `3`
- positive_net_edge_count: `0`
- mean_net_edge_bps: `-1056.38`
- median_net_edge_bps: `-1026.89`
- mean_entry_cost_bps: `50.00`
- min_liquidity_score: `0.9794`
- recommended_action: `skip_series`

Reasons:

- `all_rungs_negative`
- `strip_overpriced`
- `quality_fine_model_negative`

## 5. Interpretation

This is the key result:

- the BTC ladder is not being rejected because spreads are too wide
- it is not being rejected because liquidity is bad
- it is being rejected because the entire strip remains overpriced even after
  the current best calibration pass

That means the right next action is not execution tuning.

It also means the first market-selection rule is now justified:

- skip a crypto ladder series when all tracked rungs are negative on net edge,
  mean net edge is worse than about `-750 bps`, and microstructure is otherwise
  acceptable

## 6. Conclusion

For the current BTC runtime ladder family, the system should treat the whole
series as a `skip_series` candidate until either:

1. BTC-specific calibration improves enough to create positive net-edge rungs
2. a different BTC ladder family shows healthier repricing behavior

So the next round should be:

- formalize a ladder-series market-selection filter in research first
- then decide whether to promote that filter into the strategy/runtime path
