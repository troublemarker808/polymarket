from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase2.suite import run_crypto_phase2_suite


def test_run_crypto_phase2_suite_writes_selection_and_replay_artifacts(tmp_path: Path) -> None:
    result = asyncio.run(
        run_crypto_phase2_suite(
            snapshot_path=Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"),
            underlying_states={
                "BTC": build_underlying_state(
                    underlying="BTC",
                    as_of=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
                    spot_price=79000.0,
                    daily_return=-0.028,
                    realized_volatility=0.58,
                    implied_volatility=0.66,
                )
            },
            output_dir=tmp_path / "crypto-suite",
            run_id="crypto-suite-test",
        )
    )

    suite_json = tmp_path / "crypto-suite" / "suite.json"
    suite_md = tmp_path / "crypto-suite" / "suite.md"
    selection_summary = tmp_path / "crypto-suite" / "selection" / "summary.md"
    unfiltered_metrics = tmp_path / "crypto-suite" / "replay-unfiltered" / "metrics.json"
    filtered_metrics = tmp_path / "crypto-suite" / "replay-filtered" / "metrics.json"

    assert suite_json.exists()
    assert suite_md.exists()
    assert selection_summary.exists()
    assert unfiltered_metrics.exists()
    assert filtered_metrics.exists()

    payload = json.loads(suite_json.read_text(encoding="utf-8"))
    assert payload["selection_skip_series_keys"] == ["what-price-will-bitcoin-hit-before-2027"]
    assert payload["filtered_replay"]["signals_generated"] == 0
    assert payload["unfiltered_replay"]["signals_generated"] >= 0
    assert result.selection_skip_series_keys == ("what-price-will-bitcoin-hit-before-2027",)
