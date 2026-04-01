# Crypto Calibration Report

- generated_at: 2026-04-01T14:54:28.544604+00:00
- baseline_classification: mixed
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
- residual_min_confidence
- residual_max_abs_correction_bps
- min_net_edge_bps
- maker_min_edge_bps

## Score Formula

- score = (40 * sign_alignment_rate) + (8 * positive_net_edge_count) - (0.02 * mean_abs_gap_bps) - (0.03 * max(-mean_net_edge_bps, 0))

## Dataset Split

- baseline_candidate: btc-r1-s165-b35-s65
- baseline_preset: crypto-calibration-baseline-20260328
- holdout: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- train: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl
- validation: data\runtime\phase2-paper-snapshots.btc-longtail.v58.overnight.20260327.jsonl

## Failure Mechanisms

- Synthetic compare windows can still produce repricing-aligned candidates, so the execution path is functional and the bottleneck has shifted toward model calibration and market selection.

## Dataset Reports

### train

- snapshot_path: tests\fixtures\crypto_phase2\btc_runtime_ladder_window.jsonl
- processed_snapshots: 24
- market_count: 3
- positive_gross_edge_count: 0
- positive_net_edge_count: 3
- repricing_observed_count: 0
- repricing_aligned_count: 0
- sign_alignment_rate: 0.0000
- mean_signed_gap_bps: -1171.38
- mean_abs_gap_bps: 1171.38
- mean_net_edge_bps: 1056.38
- median_net_edge_bps: 1026.89
- mean_barrier_miss_bps: 3346.79
- mean_surface_miss_bps: 0.00
- mean_fusion_miss_bps: 1171.38
- mean_late_repricing_miss_bps: 1171.38
- selection_miss_count: 0
- calibration_score: 0.57

### validation

- snapshot_path: data\runtime\phase2-paper-snapshots.btc-longtail.v58.overnight.20260327.jsonl
- processed_snapshots: 6278
- market_count: 2
- positive_gross_edge_count: 0
- positive_net_edge_count: 2
- repricing_observed_count: 2
- repricing_aligned_count: 1
- sign_alignment_rate: 0.5000
- mean_signed_gap_bps: -846.11
- mean_abs_gap_bps: 846.11
- mean_net_edge_bps: 506.11
- median_net_edge_bps: 506.11
- mean_barrier_miss_bps: 2160.32
- mean_surface_miss_bps: 150.00
- mean_fusion_miss_bps: 821.11
- mean_late_repricing_miss_bps: 696.11
- selection_miss_count: 0
- calibration_score: 19.08

### holdout

- snapshot_path: data\runtime\phase2-paper-snapshots.btc-combined.v74.jsonl
- processed_snapshots: 98681
- market_count: 30
- positive_gross_edge_count: 6
- positive_net_edge_count: 19
- repricing_observed_count: 18
- repricing_aligned_count: 11
- sign_alignment_rate: 0.6111
- mean_signed_gap_bps: -12.52
- mean_abs_gap_bps: 674.66
- mean_net_edge_bps: 545.99
- median_net_edge_bps: 78.81
- mean_barrier_miss_bps: 1858.73
- mean_surface_miss_bps: 138.83
- mean_fusion_miss_bps: 669.73
- mean_late_repricing_miss_bps: 669.73
- selection_miss_count: 0
- calibration_score: 162.95
