# Paper Realism Gap

## What Paper Can Prove

The current paper runtime is useful for:

- signal generation diagnostics
- risk-rejection diagnostics
- order funnel attribution
- queue-aware maker behavior
- multi-level taker sweep behavior
- latency, fee, and slippage sensitivity analysis

## What Paper Cannot Prove

Paper still cannot infer private exchange state. In particular:

- true queue priority inside the exchange
- hidden liquidity
- exchange-internal cancel timing
- exact maker/taker outcome during contention spikes

## How To Read A Zero-Fill Day

A zero-fill day is not actionable until the metrics say which of these happened:

- no signals were generated
- signals were generated but rejected by risk
- orders were submitted but stayed passive
- queue ahead never cleared
- orders expired or canceled before fills
- market data degraded

## Required Evidence Before Promotion

Before paper results influence live rollout decisions, capture:

- paper metrics JSON for the run
- health report with signal/order/fill funnel
- event log for spot-checking specific orders
- calibration comparison against a baseline metrics file

## Known Remaining Gaps

- Replace behavior is not yet exercised by the current strategy/order-planning path.
- Calibration quality still depends on the quality of the baseline metrics file.
- Public-data matching remains an approximation under fast-moving liquidity.
