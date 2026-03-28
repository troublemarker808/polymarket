# Paper Artifact Field Semantics

This document fixes the meaning of the main persisted paper artifacts so later
review does not guess whether a field is cumulative or incremental.

## Metrics JSON

Metrics are run-level cumulative summaries unless stated otherwise.

- `processed_snapshots`: cumulative count
- `paper_days_observed`: cumulative distinct UTC trading days
- `observed_trading_days`: cumulative distinct UTC day set
- `signals_generated`: cumulative count
- `signals_rejected`: cumulative count
- `orders_submitted`: cumulative count
- `orders_rejected`: cumulative count
- `orders_filled`: cumulative count of terminal full-fill events
- `orders_partially_filled`: cumulative count of partial-fill events
- `orders_expired`: cumulative count
- `orders_canceled`: cumulative count
- `trades_closed`: cumulative count
- `market_data_failures`: cumulative count
- `market_data_recoveries`: cumulative count
- `filled_shares_total`: cumulative filled-share sum
- `maker_filled_shares`: cumulative filled-share sum
- `taker_filled_shares`: cumulative filled-share sum
- `fill_rate`: derived ratio, not a raw counter
- `cancel_rate`: derived ratio, not a raw counter
- `avg_time_to_fill_ms`: derived average over terminal fills
- `avg_fill_price_vs_mid_bps`: derived share-weighted average
- `maker_fill_share`: derived ratio, not a raw counter
- `taker_fill_share`: derived ratio, not a raw counter
- `generated_by_strategy`: cumulative count map
- `submitted_by_strategy`: cumulative count map
- `updated_at`: latest artifact update timestamp

## Events JSONL

Events are append-only point-in-time records. Each line is one event.

### Submission / lifecycle fields

These fields are cumulative order state at the time of the event:

- `matched_shares`
- `matched_notional`
- `fees_paid_total`
- `average_fill_price`

These fields are event-local increments:

- `fill_shares_delta`
- `fill_notional_delta`
- `fees_paid_delta`

These fields describe the original order request and do not change meaning:

- `requested_shares`
- `requested_notional`
- `limit_price`
- `quote_ttl_seconds`
- `signal_edge_bps`

### Trade-close fields

- `realized_pnl`: close-event realized PnL before fees for that close record
- `fees_paid`: close-event fees for that close record
- `net_pnl`: close-event realized PnL after fees for that close record

`trade.closed` records are event-local close increments, not run-total values.

## State JSON

State is current runtime state at the time the file was persisted.

- `realized_pnl_today`: current-day cumulative realized PnL
- `unrealized_pnl`: current snapshot unrealized PnL
- `orders_today`: current-day cumulative order submission count
- `open_positions`: current open-position map, not history
- `pending_orders`: current pending-order map, not history
- `day_starting_equity`: fixed for the current trading day until rollover
- `day_open_unrealized_pnl`: unrealized PnL captured at day rollover
- `total_equity`: derived current value, not persisted directly
- `today_pnl`: derived current-day value, not persisted directly

## Review Rule

When computing totals from events:

- use `fill_*_delta` and `fees_paid_delta` for event-level volume accounting
- do not sum `matched_*` across events
- treat `matched_*` as cumulative order snapshots

When comparing metrics against events:

- compare metrics counters against counts reconstructed from event lines
- compare state fields against current-day aggregates reconstructed from event lines
