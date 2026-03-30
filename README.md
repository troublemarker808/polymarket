# polymarket_bot2.0

Polymarket V1 bot planning repository focused on three isolated category engines:

- sports
- crypto
- weather

The repository is structured so category strategies can evolve independently without
changing the execution core, adapter layer, or other categories.

## V1 Goals

- Build a modular architecture for sports, crypto, and weather strategies.
- Keep strategy logic separate from data adapters, execution, and risk.
- Start with paper and shadow modes before any live trading.
- Make each strategy configurable and testable in isolation.

## Repository Layout

- `docs/`: planning, architecture, governance, and roadmap documents.
- `configs/`: base and category-specific example configs.
- `data/research/`: sample normalized snapshot datasets for replay and backtest flows.
- `src/pm_bot/core/`: shared domain types and interfaces.
- `src/pm_bot/adapters/`: Polymarket and external data adapters.
- `src/pm_bot/strategies/`: category-local strategy packages.
- `src/pm_bot/execution/`: order planning and portfolio execution logic.
- `src/pm_bot/risk/`: independent guardrails and policy checks.
- `src/pm_bot/research/`: replay and backtest entry points.
- `tests/`: unit and integration test mirrors.

## Design Rule

Strategies may read normalized inputs and emit signals. They may not call exchange
clients directly and they may not import code from other category strategy packages.

## First Documents To Read

- `docs/V1_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/WORKFLOW.md`
- `docs/REPO_GOVERNANCE.md`
- `docs/UPGRADE_ROADMAP.md`

## Foundation Status

The repository now includes:

- layered config loading
- strategy registry
- continuous paper session runner with event and metrics persistence
- queue-aware paper execution adapter with partial fills, TTL expiry, and configurable latency/slippage
- file-backed replay and backtest entry points for normalized snapshot datasets
- safe-by-default live execution adapter scaffold
- authenticated user-channel parser and order lifecycle tracker
- local position ledger for fill accounting and mark-to-market
- reconnect-supervised live session runner with state recovery
- runtime dashboard state that separates pending orders from filled positions
- runtime event router
- JSONL and in-memory recorders
- stateful risk manager with halt/resume rules
- Polymarket Gamma + CLOB + market WebSocket adapters
- implemented V1 strategies for sports anchor/live, crypto surface/maker, and weather ensemble/threshold

## Quick Validation

Install the dev validation toolchain once:

```bash
python -m pip install -e .[dev]
```

Run the full repository quality gate with one command:

```bash
python -m pm_bot validate-repo
```

This command runs `pytest`, `ruff`, and `mypy` in order. If the dev toolchain is
missing, it fails loudly and tells you to install `.[dev]` instead of silently
skipping lint or type-checking.

```bash
python -m pm_bot validate-repo
python -m pm_bot check-geoblock
python -m pm_bot validate-config --config-dir configs
python -m pm_bot validate-live-config --config-dir configs
python -m pm_bot paper-crypto-once --config-dir configs --limit 25 --event-path data/runtime/paper-once-events.jsonl --metrics-path data/runtime/paper-once-metrics.json
python -m pm_bot run-paper-crypto-session --config-dir configs --max-market-snapshots 50 --event-path data/runtime/paper-events.current.jsonl --metrics-path data/runtime/paper-metrics.latest.json
python -m pm_bot compare-execution-metrics --baseline-metrics-path data/runtime/paper-once-metrics.json --candidate-metrics-path data/runtime/paper-metrics.latest.json
python -m pm_bot autoresearch-report --metrics-path data/runtime/paper-metrics.latest.json --event-path data/runtime/paper-events.current.jsonl --state-path data/runtime/runtime_state.json --report-path data/runtime/autoresearch.latest.md
python -m pm_bot multi-board-ops-report --crypto-operator-summary-path data/runtime/crypto-operator-summary.md --sports-scorecard-path data/research/phase1/sports_event_scorecard_report.md --weather-scorecard-path data/research/phase1/weather_run_scorecard_report.md --ops-summary-path data/runtime/multi-board-ops.md
python -m pm_bot daily-ops-bundle --crypto-operator-summary-path data/runtime/crypto-operator-summary.md --sports-scorecard-path data/research/phase1/sports_event_scorecard_report.md --weather-scorecard-path data/research/phase1/weather_run_scorecard_report.md --daily-bundle-path data/runtime/daily-ops-bundle.md
python -m pm_bot ops-console --crypto-operator-summary-path data/runtime/crypto-operator-summary.md --sports-scorecard-path data/research/phase1/sports_event_scorecard_report.md --weather-scorecard-path data/research/phase1/weather_run_scorecard_report.md --console-path data/runtime/ops-console.md
python -m pm_bot ops-control-panel --config-dir configs --state-path data/runtime/runtime_state.json --crypto-operator-summary-path data/runtime/crypto-operator-summary.md --sports-scorecard-path data/research/phase1/sports_event_scorecard_report.md --weather-scorecard-path data/research/phase1/weather_run_scorecard_report.md
python -m pm_bot scheduled-ops-bundle --crypto-operator-summary-path data/runtime/crypto-operator-summary.md --sports-scorecard-path data/research/phase1/sports_event_scorecard_report.md --weather-scorecard-path data/research/phase1/weather_run_scorecard_report.md --promotion-evidence-stage small_live_stability --promotion-evidence-bundle-paths data/runtime/crypto-bundles/run-001.md data/runtime/crypto-bundles/run-002.md --output-root data/runtime/ops-runs --run-id morning-check
python -m pm_bot replay --config-dir configs --snapshot-path data/research/sample_snapshots.jsonl
python -m pm_bot backtest --config-dir configs --snapshot-path data/research/sample_snapshots.jsonl --event-path data/runtime/backtest-events.jsonl
# reconnects and replays live state until the requested caps are reached
python -m pm_bot run-live-crypto-session --config-dir configs --max-market-snapshots 10 --max-user-events 10
python -m pm_bot show-dashboard --config-dir configs
```

## BTC Shadow Validation Profiles

For BTC shadow validation, do not mix long-horizon thesis markets with short-horizon execution validation in the same profile.

- `configs/profiles/sync-btc-short-shadow-v1`
  Use this as the primary BTC validation pool. It scans short-horizon BTC price-barrier markets and excludes derivative BTC markets such as volatility, dominance, and premium contracts.
- `configs/profiles/sync-btc-shadow-v1`
  Use this as long-horizon thesis observation. It now scans long-horizon BTC price-barrier markets only and is not the main fast alpha validation pool.

Example commands:

```bash
python -m pm_bot validate-live-config --config-dir configs/profiles/sync-btc-short-shadow-v1
python -m pm_bot run-sync-crypto-session --config-dir configs/profiles/sync-btc-short-shadow-v1 --underlying-state-path data/research/crypto_underlying_states.json --max-market-snapshots 40 --max-user-events 80

python -m pm_bot validate-live-config --config-dir configs/profiles/sync-btc-shadow-v1
python -m pm_bot run-sync-crypto-session --config-dir configs/profiles/sync-btc-shadow-v1 --underlying-state-path data/research/crypto_underlying_states.json --max-market-snapshots 40 --max-user-events 80
```
