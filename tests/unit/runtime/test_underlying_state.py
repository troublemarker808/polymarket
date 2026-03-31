import json
from pathlib import Path

from pm_bot.runtime.underlying_state import (
    FileBackedUnderlyingStateProvider,
    resolve_underlying_state_path,
)


def test_file_backed_underlying_state_provider_reloads_when_source_changes(tmp_path: Path) -> None:
    payload_path = tmp_path / "underlying_states.json"
    payload_path.write_text(
        json.dumps(
            [
                {
                    "underlying": "BTC",
                    "as_of": "2026-03-27T15:15:00Z",
                    "spot_price": 79000.0,
                    "daily_return": -0.028,
                    "realized_volatility": 0.58,
                    "implied_volatility": 0.66,
                }
            ],
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    provider = FileBackedUnderlyingStateProvider(payload_path)
    first = provider.current_states()
    assert first["BTC"].spot_price == 79000.0

    payload_path.write_text(
        json.dumps(
            [
                {
                    "underlying": "BTC",
                    "as_of": "2026-03-27T15:16:00Z",
                    "spot_price": 78000.0,
                    "daily_return": -0.031,
                    "realized_volatility": 0.59,
                    "implied_volatility": 0.67,
                }
            ],
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    second = provider.current_states()
    assert second["BTC"].spot_price == 78000.0


def test_resolve_underlying_state_path_falls_back_to_latest_runtime_copy(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    runtime_dir = workspace_root / "data" / "runtime" / "run-a"
    runtime_dir.mkdir(parents=True)
    fallback_path = runtime_dir / "crypto_underlying_states.json"
    fallback_path.write_text(
        json.dumps(
            [
                {
                    "underlying": "BTC",
                    "as_of": "2026-03-27T15:15:00Z",
                    "spot_price": 79000.0,
                    "daily_return": -0.028,
                    "realized_volatility": 0.58,
                    "implied_volatility": 0.66,
                }
            ],
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace_root)

    resolved = resolve_underlying_state_path("data/research/crypto_underlying_states.json")

    assert resolved == fallback_path
