# Simulation Research Log

This file is the persistent discussion and change journal for paper/simulated trading work.

## Recording Rules

- Every discussion gets a new entry with a timestamp and a short question summary.
- Each entry separates:
  - `Discussion`
  - `Evidence`
  - `Conclusion`
  - `Post-Discussion Changes`
- Every code or config change made after a discussion should be appended under the most recent open entry until the next discussion starts.
- Artifact paths should be recorded exactly so later decisions can be traced back to the run that motivated them.

---

## Entry 2026-03-26-01

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: During the current paper-trading runs, what problems have shown up? Since there are still no fills, are recent code changes effectively being made based on guesses rather than actual samples?

### Evidence

- Continuous paper run artifact:
  - `2026-03-25T18:45:56Z`
  - [analysis-paper-session-metrics.v8.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v8.json)
  - [analysis-paper-session-events.v8.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v8.jsonl)
  - [analysis-paper-session-health.v8.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-health.v8.md)
  - [analysis-paper-session-autoresearch.v8.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-autoresearch.v8.md)
- Current baseline from those artifacts:
  - `signals_generated=31`
  - `orders_submitted=15`
  - `orders_rejected=16`
  - `orders_filled=0`
  - `orders_expired=10`
  - `orders_canceled=4`
  - dominant rejection reason: `daily order hard limit reached`
  - classification: `execution-bound`
- Mined high-signal windows:
  - [analysis-mined-windows.v2/summary.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-mined-windows.v2/summary.md)
- Fixed-window replay on mined window:
  - [analysis-fixed-window-mined-window01.v4/summary.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-fixed-window-mined-window01.v4/summary.md)
- Strategy participation check on the latest event log:
  - only `crypto.maker` produced signals or orders
  - `crypto.surface` produced no events in the `v8` paper run

### Conclusion

- Recent work was not purely blind guessing.
- The following changes were evidence-driven correctness or lifecycle fixes because the artifacts directly showed the failure mode:
  - paper stale-cancel
  - TTL wiring
  - monotonic timestamp guards
  - `max_open_orders` enforcement
  - open-order replacement path
  - paper health and autoresearch reporting
  - market-local failure cooldown
- But it is also true that after the runtime became stable, later maker tuning entered a low-signal regime.
- We now have many negative samples, but still no positive execution samples:
  - enough evidence to identify runtime and capacity problems
  - not enough evidence to claim realistic fill behavior, price improvement, or profitability
- So the precise statement is:
  - recent structural fixes were not guesses
  - recent execution and maker-parameter tuning is increasingly hypothesis-driven because there are still no fills
  - continuing to tune maker cadence alone without getting fills or activating another strategy path would become guess-heavy

### Post-Discussion Changes

- Created this persistent journal file so every future discussion and every following change can be recorded in-repo.

---

## Entry 2026-03-26-02

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: Why are there still no fills? Is the cause strategy quality, entry thresholds, or execution settings? Since this is paper trading, should the entry threshold be lowered to get samples?

### Evidence

- Latest continuous paper run:
  - [analysis-paper-session-metrics.v8.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v8.json)
  - [analysis-paper-session-events.v8.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v8.jsonl)
  - [analysis-paper-session-health.v8.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-health.v8.md)
- Measured from the `v8` event log:
  - all `31` generated signals had `edge_bps = 100.0`
  - all `15` submitted orders came from `crypto.maker`
  - `crypto.surface` generated `0` signals
  - all `16` order rejections were `daily order hard limit reached`
  - `10` maker orders expired
  - `4` maker orders were canceled because of replacement
- Surface participation check on the `v8` snapshot capture:
  - [analysis-paper-session-capture.v8.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v8.jsonl)
  - `surface` saw `120` crypto snapshots and still produced `0` signals
  - breakdown from a direct pass over the captured snapshots:
    - `too_few_peers = 68`
    - `fair_none = 43`
    - `direction_none = 6`
    - `edge_below_threshold = 3`
  - when surface had enough structure to evaluate edge, its observed maxima were far below current thresholds:
    - `max_buy_yes_edge_bps = 40`
    - `max_buy_no_edge_bps = -10`
    - no snapshot reached even `100` bps, let alone the configured `250` bps floor
- Window mining and fixed-window replay:
  - [analysis-mined-windows.v2/summary.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-mined-windows.v2/summary.md)
  - [analysis-fixed-window-mined-window01.v4/summary.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-fixed-window-mined-window01.v4/summary.md)
  - local maker changes can reduce expiry in train, but validation still shows no fills

### Conclusion

- The zero-fill problem is not caused by only one thing.
- Current root causes are:
  - `surface` is effectively inactive on the current dataset, so the system only has one live signal source.
  - `maker` is firing almost entirely at the exact minimum spread floor (`100` bps), which means its current quoting logic is not discovering a richer edge distribution.
  - submitted maker quotes are not converting before TTL or replacement, so the active issue remains execution realism or quote quality, not just signal count.
  - the daily order cap is reached before any fill appears, which further reduces the useful sample budget.
- Lowering thresholds can be justified in paper mode, but only as an explicitly labeled sample-acquisition experiment.
- It should not silently replace the baseline, because doing so would mix two goals:
  - realistic paper baseline
  - deliberate loose-threshold sample collection
- The strongest candidate for threshold relaxation is not maker first; it is `crypto.surface`, because the current data shows that its configured entry gate is far above observed opportunity magnitudes on this dataset.

### Post-Discussion Changes

- Added a frozen baseline version record:
  - [PAPER_BASELINE_V1.md](/D:/dev/polymarket_bot2.0/docs/PAPER_BASELINE_V1.md)
- Added immutable crypto-only config profile for the frozen baseline:
  - [paper-baseline-v1](/D:/dev/polymarket_bot2.0/configs/profiles/paper-baseline-v1)
- Added separate crypto-only sample-acquisition profile for future fill-seeking experiments:
  - [paper-sample-acquisition-v1](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1)
- Validation:
  - `python -m pm_bot.cli validate-config --config-dir configs/profiles/paper-baseline-v1`
  - `python -m pm_bot.cli validate-config --config-dir configs/profiles/paper-sample-acquisition-v1`
- Quick replay check for the sample-acquisition profile:
  - artifact: [analysis-sample-acquisition-replay.metrics.v1.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.metrics.v1.json)
  - artifact: [analysis-sample-acquisition-replay.events.v1.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.events.v1.jsonl)
  - result:
    - `signals_generated=23`
    - `submitted_orders=15`
    - `generated_by_strategy=crypto.maker:22, crypto.surface:1`
  - interpretation:
    - the new sample profile does activate `surface` at least once on the frozen capture
    - maker still dominates order submissions, so this profile is only the first sample-acquisition step, not a solved fill profile

---

## Entry 2026-03-26-03

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: Since the paper stage is mainly for sample acquisition, can the order-related limits be widened to an effectively infinite level? Also explain the earlier screenshot text about submitted orders versus blocked later attempts.

### Evidence

- Before widening the sample-acquisition limits:
  - [analysis-sample-acquisition-replay.metrics.v1.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.metrics.v1.json)
  - `submitted_orders=15`
  - `orders_rejected=7`
  - `generated_by_strategy=crypto.maker:22, crypto.surface:1`
- After widening the sample-acquisition limits:
  - [analysis-sample-acquisition-replay.metrics.v2.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.metrics.v2.json)
  - [analysis-sample-acquisition-replay.events.v2.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.events.v2.jsonl)
  - [analysis-sample-acquisition-replay.autoresearch.v2.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.autoresearch.v2.md)
  - `signals_generated=23`
  - `orders_submitted=22`
  - `orders_rejected=0`
  - `orders_expired=16`
  - `orders_filled=0`
- The sample-acquisition profile after widening uses:
  - `daily_order_soft_limit=100000`
  - `daily_order_hard_limit=100000`
  - `max_open_orders=100000`
  - `max_concurrent_positions=100000`

### Conclusion

- “Infinite” was implemented as an effectively unbounded research ceiling rather than mathematical infinity.
- This confirmed two things:
  - the daily order limits really were blocking later attempts
  - but they were not the root cause of zero fills
- After removing those limits from the sample profile:
  - rejections dropped from `7` to `0`
  - submissions rose from `15` to `22`
  - fills stayed at `0`
  - expiries stayed high
- Therefore the screenshot statement should be interpreted as:
  - first sentence: some orders were successfully submitted into the simulator, so the system was not failing before order placement
  - second sentence: daily limits were reducing the number of later attempts once earlier non-filling orders had already consumed the day budget
  - updated view after widening: that second blocker is now mostly removed in the sample profile, but the first blocker remains because submitted quotes still do not convert into fills

### Post-Discussion Changes

- Widened the sample-acquisition profile to effectively unbounded research limits:
  - [paper-sample-acquisition-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/base.example.toml)
- Validation:
  - `python -m pm_bot.cli validate-config --config-dir configs/profiles/paper-sample-acquisition-v1`
- Replay verification on the frozen `v8` capture:
  - `python -m pm_bot.cli replay --config-dir configs/profiles/paper-sample-acquisition-v1 --snapshot-path data/runtime/analysis-paper-session-capture.v8.jsonl --limit 120 --event-path data/runtime/analysis-sample-acquisition-replay.events.v2.jsonl --metrics-path data/runtime/analysis-sample-acquisition-replay.metrics.v2.json`
- Autoresearch verification:
  - `python -m pm_bot.cli autoresearch-report --metrics-path data/runtime/analysis-sample-acquisition-replay.metrics.v2.json --event-path data/runtime/analysis-sample-acquisition-replay.events.v2.jsonl --report-path data/runtime/analysis-sample-acquisition-replay.autoresearch.v2.md`

---

## Entry 2026-03-26-04

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: Investigate the real root cause of continued zero fills after widening the sample-acquisition limits.

### Evidence

- Current widened sample-acquisition replay:
  - [analysis-sample-acquisition-replay.metrics.v2.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.metrics.v2.json)
  - [analysis-sample-acquisition-replay.events.v2.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-sample-acquisition-replay.events.v2.jsonl)
  - result:
    - `orders_submitted=22`
    - `orders_rejected=0`
    - `orders_filled=0`
    - `orders_expired=16`
- Frozen capture used by the run:
  - [analysis-paper-session-capture.v8.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v8.jsonl)
  - measured structure:
    - `total_snapshots=120`
    - `unique_markets=120`
    - `single_snapshot_markets=120`
- Order follow-up check after submission on the widened replay:
  - every one of the `22` submitted orders had `0` later snapshots for the same market
  - therefore every submitted order had `0` same-market snapshots inside TTL after creation
- Matching engine behavior:
  - [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py#L104) only attempts maker or taker matching when `tracked.market_id == snapshot.market_id`
  - passive fill path begins at [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py#L229)
  - marketable sweep path begins at [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py#L298)
  - expiry is global, so orders can age out and expire even if their market never appears again
- Replay path:
  - [engine.py](/D:/dev/polymarket_bot2.0/src/pm_bot/research/engine.py#L193) iterates the provided snapshots once, sequentially
  - it syncs before and after `run_once` on each snapshot, but still depends on future same-market snapshots for fills
- Live paper feed shape:
  - [live_feed.py](/D:/dev/polymarket_bot2.0/src/pm_bot/adapters/polymarket/live_feed.py#L52)
  - when `include_initial=True`, it emits the bootstrap snapshot list first at [live_feed.py](/D:/dev/polymarket_bot2.0/src/pm_bot/adapters/polymarket/live_feed.py#L59) and [live_feed.py](/D:/dev/polymarket_bot2.0/src/pm_bot/adapters/polymarket/live_feed.py#L60)
  - with a short `max_market_snapshots` cap, the session can stop during the first pass over bootstrap markets before websocket revisits create any same-market follow-up
- Secondary findings:
  - `crypto.surface` still barely participates
  - `crypto.maker` remains almost the entire active signal source

### Conclusion

- The dominant root cause of current zero fills is the run shape and dataset shape, not just thresholds.
- On the current frozen `v8` run family, the bot is mostly seeing one snapshot per market.
- Because the paper matcher only evaluates fills when that same market appears again, those runs structurally provide almost no chance to fill.
- This means:
  - widening daily order limits removes later rejections
  - but it does not create fills if the submitted market never gets another snapshot
- Therefore the immediate bottleneck is:
  - sample-acquisition runs are collecting breadth across many markets
  - but not depth across the same market
- Strategy thresholds are still a secondary issue, especially for `surface`, but they are not the first reason the current `v8` runs have zero fills.

### Post-Discussion Changes

- Added a paper-session limit control so bootstrap warm-up snapshots can be excluded from the live-update cap:
  - [paper_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_session.py)
  - [cli.py](/D:/dev/polymarket_bot2.0/src/pm_bot/cli.py)
  - [run-paper-supervisor.ps1](/D:/dev/polymarket_bot2.0/scripts/run-paper-supervisor.ps1)
- Added regression coverage for the new limit semantics:
  - [test_paper_session_runner.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_paper_session_runner.py)
  - [test_cli.py](/D:/dev/polymarket_bot2.0/tests/unit/test_cli.py)
- Verification:
  - `pytest -q`
  - result: `141 passed`
- New live paper sample-acquisition run using bootstrap exclusion:
  - command:
    - `python -m pm_bot.cli run-paper-crypto-session --config-dir configs/profiles/paper-sample-acquisition-v1 --state-path data/runtime/analysis-paper-session-state.v9.json --event-path data/runtime/analysis-paper-session-events.v9.jsonl --metrics-path data/runtime/analysis-paper-session-metrics.v9.json --snapshot-path data/runtime/analysis-paper-session-capture.v9.jsonl --max-market-snapshots 120 --exclude-bootstrap-from-limit --summary-every-snapshots 0`
  - artifacts:
    - [analysis-paper-session-metrics.v9.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v9.json)
    - [analysis-paper-session-events.v9.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v9.jsonl)
    - [analysis-paper-session-capture.v9.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v9.jsonl)
    - [analysis-paper-session-health.v9.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-health.v9.md)
    - [analysis-paper-session-autoresearch.v9.md](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-autoresearch.v9.md)
  - result:
    - `processed_snapshots=604`
    - `orders_submitted=163`
    - `orders_rejected=0`
    - `orders_filled=0`
    - `orders_expired=152`
- Updated finding from the `v9` run:
  - the bootstrap-limit fix worked because the session no longer stops after the initial market sweep
  - but same-market depth is still too low for fills:
    - `unique_markets=484`
    - repeat histogram: `364 markets seen once`, `120 markets seen twice`
    - among `163` submitted orders:
      - `162` had no later same-market snapshot
      - `1` had a later same-market snapshot
      - `0` had a later same-market snapshot within the current `15s` TTL window
  - therefore the primary bottleneck has moved from `bootstrap truncation` to `revisit cadence vs TTL`

---

## Entry 2026-03-26-05

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: Between lengthening TTL and shrinking the watched market set, which is the better next move?

### Evidence

- Latest sample-acquisition live paper run:
  - [analysis-paper-session-metrics.v9.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v9.json)
  - [analysis-paper-session-capture.v9.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v9.jsonl)
- Observed sample shape:
  - `unique_markets=484`
  - `364` markets were seen once
  - `120` markets were seen twice
- Submitted-order follow-up:
  - out of `163` submitted orders:
    - `162` had no later same-market snapshot at all
    - `1` had a later same-market snapshot
    - `0` had a later same-market snapshot inside the current `15s` TTL

### Conclusion

- Shrinking the watched market set is the better next move.
- Reason:
  - extending TTL only helps when the same market actually comes back later
  - on the current `v9` run, that would only potentially help `1/163` submitted orders
  - shrinking the watched set attacks the primary problem directly by increasing same-market revisit frequency
- Best sequence:
  - first shrink the watched market universe for sample acquisition
  - then re-measure revisit cadence
  - only after that decide how much to lengthen TTL

### Post-Discussion Changes

- No code changed in this discussion step.
- Recorded the decision that market-universe narrowing should be prioritized over TTL expansion.

---

## Entry 2026-03-26-06

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: After shrinking the watched market universe, why did the narrowed live paper run still show zero fills?

### Evidence

- Existing narrowed-universe live paper artifacts:
  - [analysis-paper-session-metrics.v10.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v10.json)
  - [analysis-paper-session-events.v10.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v10.jsonl)
  - [analysis-paper-session-capture.v10.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v10.jsonl)
- Measured revisit improvement versus `v9`:
  - `v9`: `unique_markets=484`, `orders_with_later_same_market_snapshot=1/163`, `orders_with_ttl_same_market_snapshot=0/163`
  - `v10`: `unique_markets=18`, `orders_with_later_same_market_snapshot=5/5`, `orders_with_ttl_same_market_snapshot=3/5`
- Snapshot-level inconsistency found in the `v10` capture for market `701502`:
  - `best_ask_yes` updated from `0.48` to `0.47`
  - but `yes_ask_levels[0].price` stayed at `0.48`
  - the same stale-depth pattern appeared across repeated `best_bid_ask` updates
- Matching behavior relevant to the inconsistency:
  - [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py) prioritizes book depth before falling back to top-of-book summaries
  - when stale `yes_ask_levels` are present, a `BUY_YES @ 0.47` order is treated as non-marketable even though `best_ask_yes = 0.47`
- Verification after fixing stale-depth handling:
  - replay command:
    - `python -m pm_bot.cli replay --config-dir configs/profiles/paper-sample-acquisition-v1 --snapshot-path data/runtime/analysis-paper-session-capture.v10.jsonl --limit 138 --event-path data/runtime/analysis-paper-session-replay-after-depth-fix.events.v10.jsonl --metrics-path data/runtime/analysis-paper-session-replay-after-depth-fix.metrics.v10.json`
  - resulting artifacts:
    - [analysis-paper-session-replay-after-depth-fix.metrics.v10.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-replay-after-depth-fix.metrics.v10.json)
    - [analysis-paper-session-replay-after-depth-fix.events.v10.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-replay-after-depth-fix.events.v10.jsonl)
  - result:
    - `signals_generated=4`
    - `orders_submitted=4`
    - `orders_filled=1`
    - `orders_expired=3`
    - `fill_rate=0.25`
    - filled order source: `taker`
    - filled market: `701502`
    - `avg_time_to_fill_ms=430`

### Conclusion

- Shrinking the watched market set did work.
- The remaining `v10` zero-fill readout was not purely a strategy or TTL problem.
- A simulator data-contract bug was masking at least one valid taker fill:
  - websocket top-of-book updates were changing `best_bid_yes/best_ask_yes`
  - but stale depth arrays remained attached to the snapshot
  - the matcher then trusted the stale depth and missed a marketable fill
- Therefore the updated interpretation is:
  - market-universe narrowing successfully increased same-market revisit cadence
  - the earlier `v10` zero-fill result overstated the remaining problem
  - after fixing stale depth handling, the narrowed-universe sample does produce fills
- The next bottleneck is no longer "no revisits at all."
- The next bottlenecks to investigate are:
  - whether more fills appear on a fresh live paper run after the fix
  - whether current surface entries are too taker-heavy or too expensive
  - whether maker can now collect valid follow-up samples under the smaller universe

### Post-Discussion Changes

- Invalidated stale depth on websocket top-of-book-only updates:
  - [ws_client.py](/D:/dev/polymarket_bot2.0/src/pm_bot/adapters/polymarket/ws_client.py)
- Added matcher-side protection so inconsistent depth falls back to top-of-book summaries:
  - [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
- Added regression coverage:
  - [test_ws_client.py](/D:/dev/polymarket_bot2.0/tests/unit/adapters/test_ws_client.py)
  - [test_paper_matching.py](/D:/dev/polymarket_bot2.0/tests/unit/execution/test_paper_matching.py)
- Validation:
  - `pytest tests/unit`
  - result: `145 passed`

---

## Entry 2026-03-26-07

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: After the stale-depth fix, does a fresh narrowed live paper run now produce fills, or is revisit scarcity still the active bottleneck on real-time data?

### Evidence

- Fresh narrowed live paper run after the fix:
  - command:
    - `python -m pm_bot.cli run-paper-crypto-session --config-dir configs/profiles/paper-sample-acquisition-v1 --state-path data/runtime/analysis-paper-session-state.v11.json --event-path data/runtime/analysis-paper-session-events.v11.jsonl --metrics-path data/runtime/analysis-paper-session-metrics.v11.json --snapshot-path data/runtime/analysis-paper-session-capture.v11.jsonl --max-market-snapshots 120 --exclude-bootstrap-from-limit --summary-every-snapshots 0`
  - artifacts:
    - [analysis-paper-session-metrics.v11.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v11.json)
    - [analysis-paper-session-events.v11.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v11.jsonl)
    - [analysis-paper-session-capture.v11.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-capture.v11.jsonl)
- `v11` summary:
  - `processed_snapshots=138`
  - `signals_generated=2`
  - `orders_submitted=2`
  - `orders_filled=0`
  - `orders_expired=2`
  - both generated and submitted orders came from `crypto.surface`
- `v11` sample shape:
  - `unique_markets=18`
  - repeat histogram:
    - `3 markets seen twice`
    - `1 market seen 3 times`
    - `3 markets seen 4 times`
    - `3 markets seen 5 times`
    - `1 market seen 7 times`
    - `1 market seen 9 times`
    - `1 market seen 11 times`
    - `1 market seen 12 times`
    - `3 markets seen 14 times`
    - `1 market seen 21 times`
- Submitted-order follow-up in `v11`:
  - `orders_with_later_same_market_snapshot=0/2`
  - `orders_with_ttl_same_market_snapshot=0/2`
  - the two submitted markets were `1345531` and `701502`
  - neither had a later same-market snapshot after order creation in this run

### Conclusion

- The stale-depth bug is fixed, but it does not guarantee fills on every narrowed live run.
- `v11` shows that the active bottleneck is now conditional revisit scarcity on the specific markets that generate orders.
- The important update is:
  - overall revisit structure is much better than the pre-narrowing runs
  - but the order-triggering markets in `v11` still got `0` post-submit revisits
  - so this run had no structural chance to fill those specific orders
- Therefore the next move should not be "undo the bug fix" or "assume the fix failed."
- The next move should be one of:
  - run longer under the narrowed universe to increase post-submit revisit opportunities
  - shrink the sample-acquisition universe further toward the most chatty markets
  - only after more post-submit revisits are observed, re-evaluate TTL lengthening

### Post-Discussion Changes

- No code changed in this discussion step.
- Recorded the first fresh post-fix live paper result so later tuning can distinguish:
  - simulator bug fixes
  - universe/revisit improvements
  - remaining per-market sample sparsity

---

## Entry 2026-03-26-08

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: The goal before any real-money rollout is now explicit: use long-running paper trading to collect many real-execution-like fill samples. What changes are needed so paper can keep producing a large stream of fills instead of only occasional isolated fills?

### Evidence

- Existing narrowed-universe result before this step:
  - [analysis-paper-session-metrics.v11.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v11.json)
  - `processed_snapshots=138`
  - `orders_submitted=2`
  - `orders_filled=0`
  - `orders_with_later_same_market_snapshot=0/2`
- Root-cause update:
  - narrowing the universe fixed the earlier breadth problem
  - but sample volume was still gated by alpha-trigger frequency
  - in particular, active/high-revisit markets were not always the same markets that `surface` or `maker` chose to trade
  - therefore more universe tuning alone was unlikely to create a sustained stream of fills
- New implementation introduced:
  - dedicated paper-only sample-collection strategy:
    - [execution_sample/strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/execution_sample/strategy.py)
  - registry wiring:
    - [registry.py](/D:/dev/polymarket_bot2.0/src/pm_bot/registry.py)
  - sample profile updated to prioritize the new strategy and widen PnL-based paper halts:
    - [paper-sample-acquisition-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/base.example.toml)
    - [paper-sample-acquisition-v1/crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/crypto.v1.example.toml)
  - regression coverage:
    - [test_crypto_execution_sample_strategy.py](/D:/dev/polymarket_bot2.0/tests/unit/strategies/test_crypto_execution_sample_strategy.py)
- Validation:
  - `pytest tests/unit`
  - result: `149 passed`

## 2026-03-27-02 Phase 1 Small-Live Baseline Code Handoff

### Objective

- Prepare the missing `Phase 1 / Small-Live Baseline` code so the operator can
  run the first real micro-order PM calibration window without any more wiring
  work.

### Changes

- Added a shared comparable runtime recorder that persists `events` plus the
  paper metrics schema for both paper and live:
  - [recorder.py](/D:/dev/polymarket_bot2.0/src/pm_bot/storage/recorder.py)
- Added shared execution-artifact payload helpers:
  - [execution_artifacts.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/execution_artifacts.py)
- Upgraded live session output so it now:
  - keeps in-memory recent events for strategy context
  - writes comparable `metrics`
  - emits standardized `order.filled`, `order.partially_filled`,
    `order.canceled`, `order.rejected`, and `trade.closed` events
  - records `market.snapshot_processed.updated_at` so
    `crypto.execution_sample` can work in live
  - records `market_data.recovered` after data-source failures
  - files:
    - [live_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_session.py)
    - [polymarket_live.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/polymarket_live.py)
    - [paper_sync.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_sync.py)
- Updated the CLI so `run-live-crypto-session` now accepts the generic
  `--event-path` and `--metrics-path` artifact outputs and prints a richer
  summary:
  - [cli.py](/D:/dev/polymarket_bot2.0/src/pm_bot/cli.py)
- Added the dedicated small-live baseline profile:
  - [base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/base.example.toml)
  - [crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/crypto.v1.example.toml)
- Added the operator handoff note:
  - [SMALL_LIVE_BASELINE.md](/D:/dev/polymarket_bot2.0/docs/SMALL_LIVE_BASELINE.md)
- Updated the execution checklist:
  - [PAPER_REALISM_EXECUTION_CHECKLIST.md](/D:/dev/polymarket_bot2.0/docs/PAPER_REALISM_EXECUTION_CHECKLIST.md)

### Validation Scope

- No new long-running paper or live run was started.
- This batch is code-only plus unit tests; the first real small-live window is
  still to be started by the operator.

---

## Entry 2026-03-26-10

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: Convert the "make paper closer to real trading" discussion into a tracked execution checklist so later code changes can be reviewed against a fixed document, with the user keeping final control of when runs are started.

### Evidence

- Added a dedicated execution checklist:
  - [PAPER_REALISM_EXECUTION_CHECKLIST.md](/D:/dev/polymarket_bot2.0/docs/PAPER_REALISM_EXECUTION_CHECKLIST.md)
- The checklist explicitly records:
  - phase ordering
  - code areas per phase
  - required artifacts
  - acceptance criteria
  - the handoff rule that code/tests/report prep stop before the final run and the user starts the run

### Conclusion

- The paper-realism work now has a fixed review anchor instead of relying on chat history.
- Future changes should be checked against the checklist document before any new trust-building paper or small-live run is started.

### Post-Discussion Changes

- Added the tracked checklist document:
  - [PAPER_REALISM_EXECUTION_CHECKLIST.md](/D:/dev/polymarket_bot2.0/docs/PAPER_REALISM_EXECUTION_CHECKLIST.md)

---

## Entry 2026-03-27-01

### Discussion

- Timestamp: 2026-03-27 Asia/Shanghai
- Question: Finish the remaining `Phase 0 / Paper Integrity` work directly in code instead of stopping at the checklist.

### Evidence

- Existing Phase 0 gaps from the checklist:
  - NO/YES audit for remaining execution paths was still open
  - deterministic replay verification existed as a command, but fixed replay baseline artifacts were not yet checked into the repo
  - cumulative-vs-delta field semantics were still implicit
- Token-side audit targets:
  - [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
  - [position_ledger.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/position_ledger.py)
  - [paper_sync.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_sync.py)
- New fixed replay baseline artifacts:
  - [snapshots.jsonl](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/snapshots.jsonl)
  - [expected.metrics.json](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/expected.metrics.json)
  - [expected.events.jsonl](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/expected.events.jsonl)
  - [expected.summary.json](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/expected.summary.json)
- New field-semantics note:
  - [PAPER_ARTIFACT_FIELD_SEMANTICS.md](/D:/dev/polymarket_bot2.0/docs/PAPER_ARTIFACT_FIELD_SEMANTICS.md)

### Conclusion

- `Phase 0 / Paper Integrity` is now closed in code.
- The remaining NO/YES execution paths are now explicitly covered for:
  - taker fill fallback from complement book
  - mark price fallback from complement top-of-book and last trade
  - mid-price fallback from complement quotes
  - close-trade accounting for NO positions
- Replay now has both:
  - deterministic two-run self-checking
  - one checked-in fixed baseline sample with expected outputs
- The next real blocker is no longer simulator integrity.
- The next blocker is the absence of a small-live baseline.

### Post-Discussion Changes

- Extended paper matcher token-side fallback logic so NO orders can still derive sweepable book state from YES quotes when explicit NO depth is missing:
  - [paper_matching.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/paper_matching.py)
- Extended mark-to-market fallback logic so NO positions can be marked from YES quotes or last trade when explicit NO quotes are missing:
  - [position_ledger.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/position_ledger.py)
- Extended recorded fill payloads so NO-side `mid_price` can be reconstructed from YES quotes when needed:
  - [paper_sync.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_sync.py)
- Added regression coverage:
  - [test_paper_matching.py](/D:/dev/polymarket_bot2.0/tests/unit/execution/test_paper_matching.py)
  - [test_position_ledger.py](/D:/dev/polymarket_bot2.0/tests/unit/execution/test_position_ledger.py)
  - [test_paper_sync.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_paper_sync.py)
  - [test_replay_baseline.py](/D:/dev/polymarket_bot2.0/tests/unit/research/test_replay_baseline.py)
- Added checked-in replay baseline fixtures:
  - [snapshots.jsonl](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/snapshots.jsonl)
  - [expected.metrics.json](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/expected.metrics.json)
  - [expected.events.jsonl](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/expected.events.jsonl)
  - [expected.summary.json](/D:/dev/polymarket_bot2.0/tests/fixtures/replay_baseline/expected.summary.json)
- Added field semantics note:
  - [PAPER_ARTIFACT_FIELD_SEMANTICS.md](/D:/dev/polymarket_bot2.0/docs/PAPER_ARTIFACT_FIELD_SEMANTICS.md)
- Updated the checklist to mark `Phase 0` complete:
  - [PAPER_REALISM_EXECUTION_CHECKLIST.md](/D:/dev/polymarket_bot2.0/docs/PAPER_REALISM_EXECUTION_CHECKLIST.md)
- Validation:
  - `python -m pytest tests/unit/execution/test_paper_matching.py -q`
  - `python -m pytest tests/unit/execution/test_position_ledger.py -q`
  - `python -m pytest tests/unit/runtime/test_paper_sync.py -q`
  - `python -m pytest tests/unit/research/test_replay_determinism.py -q`
  - `python -m pytest tests/unit/research/test_replay_baseline.py -q`
  - `python -m pytest tests/unit/test_cli.py -q`
  - `python -m pytest tests/unit -q`

---

## Entry 2026-03-26-09

### Discussion

- Timestamp: 2026-03-26 Asia/Shanghai
- Question: Set the paper-trading principal to `1000` and verify whether the sample-acquisition profile can keep producing fills over a longer uninterrupted run.

### Evidence

- Sample-acquisition base profile updated:
  - [paper-sample-acquisition-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/base.example.toml)
  - `starting_equity = 1000.0`
- Config validation:
  - `python -m pm_bot.cli validate-config --config-dir configs/profiles/paper-sample-acquisition-v1`
  - result:
    - `mode=paper`
    - `strategies=['crypto.execution_sample', 'crypto.surface', 'crypto.maker']`
    - `starting_equity=1000.0`
    - `default_order_notional=5.0`
- Longer live paper run with the updated paper principal:
  - [analysis-paper-session-metrics.v15.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v15.json)
  - [analysis-paper-session-events.v15.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v15.jsonl)
  - [analysis-paper-session-state.v15.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-state.v15.json)
  - runtime window:
    - `day_started_at=2026-03-25T20:55:12.803047+00:00`
    - `updated_at=2026-03-25T21:14:26.744045+00:00`
    - about `19.2` minutes of uninterrupted live paper runtime
  - result:
    - `processed_snapshots=498`
    - `signals_generated=80`
    - `orders_submitted=80`
    - `orders_filled=51`
    - `orders_partially_filled=17`
    - `orders_expired=27`
    - `trades_closed=30`
    - `fill_rate=0.6375`
    - `avg_time_to_fill_ms=11253.73`
    - `avg_fill_price_vs_mid_bps=4.81`
    - `generated_by_strategy=crypto.execution_sample:71, crypto.surface:9`
    - `submitted_by_strategy=crypto.execution_sample:71, crypto.surface:9`
    - `status=running`
    - `halt_reason=none`
    - `total_equity=996.21`
    - `realized_pnl_today=-3.49`
    - `unrealized_pnl=-0.30`
- Important interpretation detail:
  - raising `starting_equity` to `1000` did not increase per-order size
  - the profile still uses `default_order_notional=5.0`
  - therefore the benefit of the capital change is more runtime buffer and less chance that future risk/pnl limits become the bottleneck during extended sample collection

### Conclusion

- The sample-acquisition profile now runs with a paper principal of `1000` and still produces a sustained stream of fills over a meaningfully longer session.
- `v15` is materially stronger evidence than the earlier shorter windows:
  - fills continued throughout the run instead of dropping back to isolated single-fill behavior
  - the session stayed in `status=running` with `halt_reason=none`
  - fill density remained high enough to support long-run execution-sample collection
- The main remaining caveat is unchanged:
  - this is still a taker-heavy sample-collection path with negative PnL
  - it is suitable for collecting execution samples, not for promotion to real trading

### Post-Discussion Changes

- Updated the sample-acquisition paper principal:
  - [paper-sample-acquisition-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/base.example.toml)
- Captured a longer validation run:
  - [analysis-paper-session-metrics.v15.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v15.json)
  - [analysis-paper-session-events.v15.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v15.jsonl)
  - [analysis-paper-session-state.v15.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-state.v15.json)
- Fresh live paper run with the new strategy before widening the PnL halts:
  - [analysis-paper-session-metrics.v12.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v12.json)
  - result:
    - `processed_snapshots=138`
    - `signals_generated=24`
    - `orders_submitted=18`
    - `orders_filled=15`
    - `orders_partially_filled=2`
    - `fill_rate=0.8333`
    - `generated_by_strategy=crypto.execution_sample:20, crypto.surface:4`
    - `submitted_by_strategy=crypto.execution_sample:14, crypto.surface:4`
  - blocker discovered:
    - the sample profile halted on `max_consecutive_losses`
    - this interrupted the continuous sample-collection objective
- After widening the sample profile's PnL-based halt thresholds:
  - [analysis-paper-session-metrics.v13.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v13.json)
  - result:
    - `processed_snapshots=138`
    - `orders_submitted=9`
    - `orders_filled=5`
    - `status=running`
    - `halt_reason=none`
- Longer-window confirmation:
  - [analysis-paper-session-metrics.v14.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v14.json)
  - [analysis-paper-session-events.v14.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-events.v14.jsonl)
  - result:
    - `processed_snapshots=240`
    - `orders_submitted=23`
    - `orders_filled=13`
    - `orders_partially_filled=3`
    - `trades_closed=5`
    - `fill_rate=0.5652`
    - `generated_by_strategy=crypto.execution_sample:18, crypto.surface:5`
    - `submitted_by_strategy=crypto.execution_sample:18, crypto.surface:5`
    - `status=running`
    - `halt_reason=none`

### Conclusion

- Paper trading now has a dedicated continuous sample-acquisition path that materially improves fill production.
- This is the first point in the project where the answer is no longer "paper can only occasionally produce a fill."
- The stronger statement is now:
  - the sample-acquisition profile can run continuously
  - it can generate repeated taker-side fills and closed trades
  - it no longer stops early because of consecutive-loss protection
- Current limitations still matter:
  - fills are still overwhelmingly taker-side
  - paper sample PnL is negative so this is not a promotion-ready strategy
  - the objective here is execution-sample collection, not alpha quality
- Therefore the immediate next optimization target should be:
  - increase sample density further without breaking the continuous-run property
  - then compare paper-vs-live execution assumptions using the larger sample set

### Post-Discussion Changes

- Fixed the live signature-resolution path for real orders:
  - [polymarket_live.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/polymarket_live.py)
- Fixed router behavior so exchange-side submit rejections no longer crash the live loop:
  - [event_router.py](/D:/dev/polymarket_bot2.0/src/pm_bot/orchestrator/event_router.py)
- Fixed reconnect-time duplicate trade replay accounting:
  - [polymarket_live.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/polymarket_live.py)
  - [live_reconcile.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_reconcile.py)
- Updated the small-live profile to keep micro orders above PM's effective minimum:
  - [small-live-baseline-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/base.example.toml)
- Added and updated regression coverage:
  - [test_polymarket_live.py](/D:/dev/polymarket_bot2.0/tests/unit/execution/test_polymarket_live.py)
  - [test_live_reconcile.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_live_reconcile.py)
  - [test_event_router.py](/D:/dev/polymarket_bot2.0/tests/unit/orchestrator/test_event_router.py)
  - [test_loader.py](/D:/dev/polymarket_bot2.0/tests/unit/config/test_loader.py)
- Validation:
  - `python -m pytest tests/unit -q`
  - result: `172 passed`
- Invalid live-baseline attempts to ignore:
  - `live-baseline-20260327-024441`:
    - failed on `invalid signature`
  - `live-baseline-20260327-025308`:
    - reached PM minimum-order rejection before submit errors were contained
  - `live-baseline-20260327-025736`:
    - exposed duplicate fill accounting across reconnects
- Current clean second-stage run:
  - [live-calibration-baseline.metrics.live-baseline-20260327-030314.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.metrics.live-baseline-20260327-030314.json)
  - [live-calibration-baseline.events.live-baseline-20260327-030314.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.events.live-baseline-20260327-030314.jsonl)
  - [live-calibration-baseline.state.live-baseline-20260327-030314.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.state.live-baseline-20260327-030314.json)
- Follow-up profile tuning for longer sample collection:
  - [small-live-baseline-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/base.example.toml)
  - widened `daily_order_hard_limit` from `30` to `120`
  - widened `max_daily_drawdown_pct` from `15.0` to `40.0`
  - widened `max_consecutive_losses` from `10` to `40`
  - single-order notional and concurrency caps were left unchanged

### Post-Discussion Changes

- Fixed the second-stage live-baseline runner boundary:
  - [live_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_session.py)
  - [live_reconcile.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_reconcile.py)
  - [settings.py](/D:/dev/polymarket_bot2.0/src/pm_bot/core/settings.py)
- Added a session-scoped recovery mode for fresh small-live windows:
  - [small-live-baseline-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/small-live-baseline-v1/base.example.toml)
  - [SMALL_LIVE_BASELINE.md](/D:/dev/polymarket_bot2.0/docs/SMALL_LIVE_BASELINE.md)
- Added regression coverage:
  - [test_live_session.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_live_session.py)
  - [test_live_reconcile.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_live_reconcile.py)
  - [test_loader.py](/D:/dev/polymarket_bot2.0/tests/unit/config/test_loader.py)
- Validation:
  - `python -m pytest tests/unit -q`
  - result: `168 passed`
- Why this mattered:
  - the first live-baseline attempt exited after the first clean stream cycle
  - it also replayed historical account activity into the new baseline state
  - that meant it was not a valid second-stage fresh baseline
- New expected behavior:
  - a no-limit live session keeps reconnecting instead of treating a clean stream end as completion
  - `small-live-baseline-v1` now restores only trades and open orders created after the run start timestamp

### Post-Discussion Changes

- Added the new `crypto.execution_sample` strategy:
  - [execution_sample/strategy.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/execution_sample/strategy.py)
  - [__init__.py](/D:/dev/polymarket_bot2.0/src/pm_bot/strategies/crypto/execution_sample/__init__.py)
- Registered the strategy:
  - [registry.py](/D:/dev/polymarket_bot2.0/src/pm_bot/registry.py)
- Updated the sample-acquisition profile to use the strategy and relax PnL halts:
  - [paper-sample-acquisition-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/base.example.toml)
  - [paper-sample-acquisition-v1/crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/crypto.v1.example.toml)
- Added unit coverage:
  - [test_crypto_execution_sample_strategy.py](/D:/dev/polymarket_bot2.0/tests/unit/strategies/test_crypto_execution_sample_strategy.py)
- Validation:
  - `pytest tests/unit`
  - result: `149 passed`

### Post-Discussion Changes

- Fixed live oversell accounting so second-stage baseline no longer opens phantom complement positions:
  - [position_ledger.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/position_ledger.py)
  - [polymarket_live.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/polymarket_live.py)
- Root cause:
  - during a cancel/fill race, a late `SELL NO` fill could arrive after the local position was already closed
  - live accounting was still using paper-style synthetic complement opening and turned that overflow into a fake `BUY YES`
  - this produced residual local positions that the exchange did not actually hold, followed by repeated `not enough balance / allowance` rejects
- Added regression coverage for the live-only semantic split:
  - [test_position_ledger.py](/D:/dev/polymarket_bot2.0/tests/unit/execution/test_position_ledger.py)
  - [test_polymarket_live.py](/D:/dev/polymarket_bot2.0/tests/unit/execution/test_polymarket_live.py)
  - [test_live_reconcile.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_live_reconcile.py)
- Validation:
  - `python -m pytest tests/unit -q`
  - result: `175 passed`
- Invalid live-baseline run to ignore:
  - `live-baseline-20260327-032849`
    - valid on session scoping, but polluted by the old live oversell/complement-accounting bug
- New clean second-stage run after the fix:
  - [live-calibration-baseline.metrics.live-baseline-20260327-034752.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.metrics.live-baseline-20260327-034752.json)
  - [live-calibration-baseline.events.live-baseline-20260327-034752.jsonl](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.events.live-baseline-20260327-034752.jsonl)
  - [live-calibration-baseline.state.live-baseline-20260327-034752.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.state.live-baseline-20260327-034752.json)

### Post-Discussion Changes

- Applied the first live-driven paper calibration pass using the clean small-live baseline:
  - [paper-sample-acquisition-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/base.example.toml)
  - [paper-sample-acquisition-v1/crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/paper-sample-acquisition-v1/crypto.v1.example.toml)
- Calibration source:
  - [live-calibration-baseline.metrics.live-baseline-20260327-034752.json](/D:/dev/polymarket_bot2.0/data/runtime/live-calibration-baseline.metrics.live-baseline-20260327-034752.json)
  - [analysis-paper-session-metrics.v15.json](/D:/dev/polymarket_bot2.0/data/runtime/analysis-paper-session-metrics.v15.json)
- Live vs paper drift at calibration time:
  - live `fill_rate=0.4487`, paper `fill_rate=0.6375`
  - live `cancel_rate=0.8333`, paper `cancel_rate=0.3375`
  - live `avg_time_to_fill_ms=11966.23`, paper `avg_time_to_fill_ms=11253.73`
  - live `avg_fill_price_vs_mid_bps=21.30`, paper `avg_fill_price_vs_mid_bps=4.81`
  - both sides `maker_fill_share=0.0`, `taker_fill_share=1.0`
- What changed in paper:
  - order size and market/category notional caps now mirror small-live baseline (`1.1 / 1.1 / 3.3`)
  - paper concurrency and open-order caps now mirror small-live baseline (`3` positions, `5` open orders)
  - default and execution-sample TTL now mirror small-live baseline (`20s`)
  - paper market universe and execution-sample strategy regime now mirror small-live baseline
  - `paper_taker_slippage_bps` widened from `5.0` to `20.0` to move paper fill-price realism toward the clean live baseline
- Added loader coverage for the calibrated paper sample profile:
  - [test_loader.py](/D:/dev/polymarket_bot2.0/tests/unit/config/test_loader.py)

### Post-Discussion Changes

- Added the formal paper-vs-live bias judgment using valid small-live artifacts:
  - [PAPER_LIVE_BIAS_ASSESSMENT_20260327.md](/D:/dev/polymarket_bot2.0/docs/PAPER_LIVE_BIAS_ASSESSMENT_20260327.md)
- Report scope:
  - excludes invalid live runs polluted by signature, duplicate-fill, history-recovery, and oversell-accounting bugs
  - uses clean live `034752`, paired live `045459`, and paired paper `045459`
- Formal result:
  - status `FAIL`
  - current paper is still too optimistic on `fill_rate`, `cancel_rate`, and `maker_fill_share`
  - live rejection pressure from `max concurrent positions` and `not enough balance / allowance` is not yet represented well enough in paper
  - `avg_fill_price_vs_mid_bps` remains unstable across valid live windows, so price realism is not yet trusted

---

## Entry 2026-03-27-10

### Discussion

- Timestamp: 2026-03-27 Asia/Shanghai
- Question: Stop treating `execution_sample` as the main second-stage path and implement the real target: one normal strategy, one shared signal source, one shared `intent_id`, and synchronized live + paper shadow execution.

### Evidence

- Recent user clarification:
  - paper and real trading must be synchronized
  - optimization only has value if paper changes can later be checked against the same live intent
- Current blocker identified from code review:
  - live and paper runtimes each build their own `EventRouter`
  - they generate signals independently from different runtime state
  - previous second-stage runs were execution-sampling runs, not synchronized normal trading
- Existing formal bias judgment:
  - [PAPER_LIVE_BIAS_ASSESSMENT_20260327.md](/D:/dev/polymarket_bot2.0/docs/PAPER_LIVE_BIAS_ASSESSMENT_20260327.md)
  - result `FAIL`
  - confirms that directionally calibrating paper without shared intent flow is not enough

### Conclusion

- The correct second-stage target is now explicit:
  - normal strategy
  - one shared intent stream
  - live as primary execution
  - paper as synchronized shadow execution
- `execution_sample` remains useful as historical bug-hunting evidence, but it is no longer the main validation route.
- The new synchronized runtime should compare the same `intent_id` across:
  - live submission / rejection / fill / close
  - shadow paper submission / fill / close

### Post-Discussion Changes

- Added `intent_id` to shared execution objects and comparable artifacts:
  - [types.py](/D:/dev/polymarket_bot2.0/src/pm_bot/core/types.py)
  - [order_tracker.py](/D:/dev/polymarket_bot2.0/src/pm_bot/execution/order_tracker.py)
  - [state.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/state.py)
  - [execution_artifacts.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/execution_artifacts.py)
- Event router now assigns deterministic run-local `intent_id` values and records them on comparable order events:
  - [event_router.py](/D:/dev/polymarket_bot2.0/src/pm_bot/orchestrator/event_router.py)
- Live recovery restore path now explicitly preserves the absence of intent lineage on historical exchange orders:
  - [live_reconcile.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_reconcile.py)
- Added synchronized normal shadow runtime:
  - [sync_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/sync_session.py)
  - live remains the primary execution path
  - successful live submissions and cancellations are mirrored into shadow paper
  - both sides write separate comparable artifacts
- Live session runner now supports optional shadow hooks without changing ordinary live mode behavior:
  - [live_session.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/live_session.py)
- Paper close-trade comparable events now carry `intent_id`:
  - [paper_sync.py](/D:/dev/polymarket_bot2.0/src/pm_bot/runtime/paper_sync.py)
- Added CLI entrypoint for synchronized runs:
  - [cli.py](/D:/dev/polymarket_bot2.0/src/pm_bot/cli.py)
  - command: `run-sync-crypto-session`
- Added first synchronized normal profile:
  - [sync-normal-shadow-v1/base.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/sync-normal-shadow-v1/base.example.toml)
  - [sync-normal-shadow-v1/crypto.v1.example.toml](/D:/dev/polymarket_bot2.0/configs/profiles/sync-normal-shadow-v1/crypto.v1.example.toml)
  - first route is `crypto.surface` only
- Added implementation note:
  - [SYNC_NORMAL_SHADOW_MODE.md](/D:/dev/polymarket_bot2.0/docs/SYNC_NORMAL_SHADOW_MODE.md)
- Added regression coverage:
  - [test_event_router.py](/D:/dev/polymarket_bot2.0/tests/unit/orchestrator/test_event_router.py)
  - [test_sync_session.py](/D:/dev/polymarket_bot2.0/tests/unit/runtime/test_sync_session.py)
  - [test_loader.py](/D:/dev/polymarket_bot2.0/tests/unit/config/test_loader.py)
  - [test_cli.py](/D:/dev/polymarket_bot2.0/tests/unit/test_cli.py)
- Validation:
  - `python -m pm_bot.cli validate-config --config-dir configs/profiles/sync-normal-shadow-v1`
  - `python -m pytest tests/unit -q`
  - result: `178 passed`
