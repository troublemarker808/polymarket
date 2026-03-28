# Crypto Phase 2 Compare 2026-03-28

## 1. Purpose

This note records the first direct replay comparison between:

- crypto Phase 1 baseline profile
- crypto Phase 2 replay path

Both runs used the same fixture input:

- `tests/fixtures/crypto_phase1/ladder_snapshots.jsonl`


## 2. Commands

Phase 1 baseline:

```powershell
python -m pm_bot phase1-replay --board crypto --snapshot-path tests\fixtures\crypto_phase1\ladder_snapshots.jsonl --output-dir data\research\phase2_compare\baseline-phase1
```

Phase 2 replay:

```powershell
python -m pm_bot crypto-phase2-replay --snapshot-path tests\fixtures\crypto_phase1\ladder_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase1\underlying_state.json --output-dir data\research\phase2_compare\phase2
```


## 3. Artifact Locations

Phase 1 baseline:

- `data/research/phase2_compare/baseline-phase1/`

Phase 2 replay:

- `data/research/phase2_compare/phase2/`


## 4. Result Summary

Phase 1 baseline metrics:

- processed_snapshots: 4
- signals_generated: 0
- submitted_orders: 0
- events_recorded: 0

Phase 2 metrics:

- processed_snapshots: 4
- signals_generated: 0
- submitted_orders: 0
- events_recorded: 0
- fair_values generated: 3

Bottom line:

- neither replay path produced trades on this fixture
- the difference is that Phase 2 now produced a full fair-value and attribution view for the ETH ladder


## 5. Why No Trades Happened

For the ETH ladder fixture, the Phase 2 fair values all came in below the
observed market probabilities:

- `eth-dip-1500`
  - observed: `0.71`
  - fair: `0.4362`
  - net_edge_bps: `-2523.35`
- `eth-dip-1000`
  - observed: `0.255`
  - fair: `0.1547`
  - net_edge_bps: `-888.07`
- `eth-dip-800`
  - observed: `0.195`
  - fair: `0.1090`
  - net_edge_bps: `-745.05`

This means the replay did not fail to trade because of a broken execution path.
It skipped because the current fused fair-value model judged the entire sampled
ETH dip strip to be too expensive.


## 6. Interpretation

This comparison is still useful even with zero trades:

- Phase 1 baseline proved the old profile does not blindly trade this fixture
- Phase 2 proved the new replay path can load fair values, produce attribution,
  and still decline non-actionable markets
- the next useful comparison is not "did Phase 2 trade more", but "on which
  fixtures does Phase 2 choose a different action than the baseline?"


## 7. Immediate Next Step

The next comparison pass should use at least one crypto fixture that contains:

- a clearly underpriced rung
- a clearly overpriced rung
- enough sequential snapshots for entry and exit behavior

That will let Phase 2 be evaluated on:

- maker vs taker routing
- position-intent persistence
- exit behavior
- reentry blocking after losses


## 8. Second Comparison Pass

After the initial zero-trade comparison, a second replay pass was run against a
dedicated compare fixture:

- `tests/fixtures/crypto_phase2/compare_snapshots.jsonl`

Commands:

```powershell
python -m pm_bot phase1-replay --board crypto --snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --output-dir data\research\phase2_compare\baseline-phase1-compare
python -m pm_bot crypto-phase2-replay --snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase1\underlying_state.json --output-dir data\research\phase2_compare\phase2-compare
```

Result:

Phase 1 baseline:

- processed_snapshots: `6`
- signals_generated: `0`
- submitted_orders: `0`

Phase 2:

- processed_snapshots: `6`
- signals_generated: `1`
- submitted_orders: `1`
- events_recorded: `2`

Observed Phase 2 behavior:

- market: `eth-dip-1000`
- side: `buy_yes`
- route effect: passive maker-style quote
- target_price: `0.10`
- edge_bps on generated signal: `121.93`

Interpretation:

- this is the first replay fixture where Phase 2 made a different decision than
  the baseline
- the difference is not yet realized PnL
- the difference is execution policy: Phase 2 judged the rung tradable enough
  to post a maker quote, while the baseline still did nothing

## 9. Third Comparison Pass

The compare fixture was then extended with later ETH 1000 snapshots so the
posted maker entry could fill and the exit path could complete.

Updated command:

```powershell
python -m pm_bot crypto-phase2-replay --snapshot-path tests\fixtures\crypto_phase2\compare_snapshots.jsonl --underlying-state-path tests\fixtures\crypto_phase1\underlying_state.json --output-dir data\research\phase2_compare\phase2-compare
```

Updated Phase 2 result:

- processed_snapshots: `11`
- signals_generated: `2`
- submitted_orders: `2`
- events_recorded: `7`
- today_pnl: `2.746125`
- total_equity: `1002.746125`

Observed event chain:

- `buy_yes` signal on `eth-dip-1000`
- maker `order.submitted` at `0.10`
- maker `order.filled` at `0.10`
- `sell_yes` exit signal
- exit `order.submitted`
- exit `order.filled` at `0.1549225`
- `trade.closed` with realized PnL `+2.746125`

Interpretation:

- Phase 2 now demonstrates a complete entry-to-exit replay path on the compare
  fixture
- the baseline still does nothing on the same snapshots
- the routing difference is no longer only "posts a quote"; it now leads to a
  completed trade with positive realized PnL

Implementation note:

- replay outputs are now reset before each rerun so `events.jsonl` and
  `engine.metrics.json` do not accumulate stale data when reusing the same
  output directory

## 10. Fourth Comparison Pass

After validating the synthetic compare fixture, a fourth pass was run against a
real ETH ladder window extracted from runtime capture data:

- `tests/fixtures/crypto_phase2/eth_runtime_ladder_window.jsonl`

Commands:

```powershell
python -m pm_bot phase1-replay --board crypto --snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --output-dir data\research\phase2_compare\baseline-eth-runtime
python -m pm_bot crypto-phase2-replay --snapshot-path tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl --underlying-state-path tests\fixtures\crypto_phase1\underlying_state.json --output-dir data\research\phase2_compare\phase2-eth-runtime
```

Result:

Phase 1 baseline:

- processed_snapshots: `24`
- signals_generated: `0`
- submitted_orders: `0`
- status: `completed`

Phase 2:

- processed_snapshots: `24`
- signals_generated: `0`
- submitted_orders: `0`
- status: `completed`

Phase 2 fair-value output on the extracted ETH dip ladder:

- `701552` / ETH dip 1500
  - observed: `0.72`
  - fair: `0.4390`
  - net_edge_bps: `-2594.64`
- `701553` / ETH dip 1000
  - observed: `0.27`
  - fair: `0.1593`
  - net_edge_bps: `-892.28`
- `701554` / ETH dip 800
  - observed: `0.205`
  - fair: `0.1120`
  - net_edge_bps: `-815.41`

Interpretation:

- this runtime-derived window confirms that the current Phase 2 stack is not
  failing because of replay wiring
- it is declining the ETH dip strip because the fused fair-value model still
  sees the observed ladder as too expensive
- the current bottleneck has moved from execution plumbing to model calibration
  and market selection

Supporting implementation fixes surfaced by this pass:

- research snapshot loading now accepts UTF-8 BOM input so Windows-generated
  JSONL fixtures can be replayed directly
- replay summaries now report `status: completed` for successful replay runs
