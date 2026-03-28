# Crypto Calibration Report

- generated_at: 2026-03-27T21:08:56.515013+00:00
- baseline_classification: alpha-bound
- rewritten_objective: Maximize repricing-aligned net-edge coverage on fixed crypto ladder windows while penalizing negative net-edge saturation and false-positive trade candidates.

## Locked Parameters

- starting_equity
- max_daily_drawdown_pct
- max_consecutive_losses
- max_open_orders
- daily_order_soft_limit
- daily_order_hard_limit
- paper_place_latency_ms
- paper_cancel_latency_ms
- paper_taker_slippage_bps

## Tunable Parameters

- barrier_distance_coefficient
- barrier_probability_floor
- barrier_probability_ceiling
- fusion_barrier_weight
- fusion_surface_weight
- min_net_edge_bps
- maker_min_edge_bps

## Score Formula

- score = (40 * sign_alignment_rate) + (8 * positive_net_edge_count) - (0.02 * mean_abs_gap_bps) - (0.03 * max(-mean_net_edge_bps, 0))

## Dataset Split

- holdout: tests\fixtures\crypto_phase2\compare_snapshots.jsonl
- train: tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl
- validation: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl

## Failure Mechanisms

- Real runtime ladder windows currently produce zero positive-net-edge candidates, which points to a conservative fair-value stack rather than an execution plumbing failure.
- Synthetic compare windows can still produce repricing-aligned candidates, so the execution path is functional and the bottleneck has shifted toward model calibration and market selection.

## Dataset Reports

### train

- snapshot_path: tests\fixtures\crypto_phase2\eth_runtime_ladder_window.jsonl
- processed_snapshots: 24
- market_count: 3
- positive_gross_edge_count: 0
- positive_net_edge_count: 0
- repricing_observed_count: 0
- repricing_aligned_count: 0
- sign_alignment_rate: 0.0000
- mean_signed_gap_bps: -849.19
- mean_abs_gap_bps: 849.19
- mean_net_edge_bps: -667.53
- median_net_edge_bps: -262.82
- calibration_score: -37.01

### validation

- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl
- processed_snapshots: 24
- market_count: 3
- positive_gross_edge_count: 0
- positive_net_edge_count: 0
- repricing_observed_count: 0
- repricing_aligned_count: 0
- sign_alignment_rate: 0.0000
- mean_signed_gap_bps: -1564.58
- mean_abs_gap_bps: 1564.58
- mean_net_edge_bps: -1449.58
- median_net_edge_bps: -1412.40
- calibration_score: -74.78

### holdout

- snapshot_path: tests\fixtures\crypto_phase2\compare_snapshots.jsonl
- processed_snapshots: 11
- market_count: 3
- positive_gross_edge_count: 1
- positive_net_edge_count: 1
- repricing_observed_count: 1
- repricing_aligned_count: 1
- sign_alignment_rate: 1.0000
- mean_signed_gap_bps: -559.64
- mean_abs_gap_bps: 1113.33
- mean_net_edge_bps: -521.31
- median_net_edge_bps: -735.37
- calibration_score: 10.09
