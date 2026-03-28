# Crypto Phase 2 Paper Path 2026-03-28

## 1. What Was Added

The repo now has a dedicated continuous paper-session entrypoint for
`crypto.phase2`:

```powershell
python -m pm_bot run-paper-crypto-phase2-session --underlying-state-path <underlying_states.json> --config-dir configs
```

When `--config-dir configs` is used, the command resolves to:

- `configs/profiles/paper-crypto-phase2-v1`
- `crypto.phase2`
- file-backed underlying-state refresh
- runtime fair-value recomputation
- runtime ladder-series selection filtering
- runtime position-intent tracking
- runtime reentry-state tracking

## 2. Main Files

- `src/pm_bot/runtime/underlying_state.py`
- `src/pm_bot/strategies/crypto/phase1/state_loader.py`
- `src/pm_bot/strategies/crypto/phase2/runtime_context.py`
- `src/pm_bot/runtime/paper_session.py`
- `src/pm_bot/cli.py`
- `configs/profiles/paper-crypto-phase2-v1/base.example.toml`
- `configs/profiles/paper-crypto-phase2-v1/crypto.v1.example.toml`

## 3. What The Runtime Context Supplies

Each snapshot cycle can now inject:

- `fair_values_by_market_id`
- `position_intents_by_market_id`
- `reentry_state_by_market_id`
- `blocked_series_keys`

That means `crypto.phase2` is no longer limited to offline replay assumptions.

## 4. Validation

Focused regression coverage now includes:

- profile load for `paper-crypto-phase2-v1`
- CLI exposure for `run-paper-crypto-phase2-session`
- file-backed underlying-state reload behavior
- runtime context fair-value + series-block generation
- `PaperSessionRunner` context injection path

## 5. Remaining Boundary

This path is ready for controlled paper runs, but the underlying-state source is
still file-backed. The remaining upgrade is to replace that with a true runtime
spot/volatility feed before treating `crypto.phase2` as live-ready.
