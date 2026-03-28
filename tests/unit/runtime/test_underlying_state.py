import json
from pathlib import Path

from pm_bot.runtime.underlying_state import FileBackedUnderlyingStateProvider


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
