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

```bash
python -m pytest
python -m pm_bot check-geoblock
python -m pm_bot validate-config --config-dir configs
python -m pm_bot validate-live-config --config-dir configs
python -m pm_bot paper-crypto-once --config-dir configs --limit 25 --event-path data/runtime/paper-once-events.jsonl --metrics-path data/runtime/paper-once-metrics.json
python -m pm_bot run-paper-crypto-session --config-dir configs --max-market-snapshots 50 --event-path data/runtime/paper-events.current.jsonl --metrics-path data/runtime/paper-metrics.latest.json
python -m pm_bot compare-execution-metrics --baseline-metrics-path data/runtime/paper-once-metrics.json --candidate-metrics-path data/runtime/paper-metrics.latest.json
python -m pm_bot autoresearch-report --metrics-path data/runtime/paper-metrics.latest.json --event-path data/runtime/paper-events.current.jsonl --state-path data/runtime/runtime_state.json --report-path data/runtime/autoresearch.latest.md
python -m pm_bot replay --config-dir configs --snapshot-path data/research/sample_snapshots.jsonl
python -m pm_bot backtest --config-dir configs --snapshot-path data/research/sample_snapshots.jsonl --event-path data/runtime/backtest-events.jsonl
# reconnects and replays live state until the requested caps are reached
python -m pm_bot run-live-crypto-session --config-dir configs --max-market-snapshots 10 --max-user-events 10
python -m pm_bot show-dashboard --config-dir configs
```
