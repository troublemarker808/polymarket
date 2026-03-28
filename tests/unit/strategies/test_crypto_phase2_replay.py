from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase2.replay import (
    compute_crypto_phase2_fair_values,
    run_crypto_phase2_replay,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")
FIXTURE_COMPARE = Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl")
FIXTURE_BTC_RUNTIME = Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl")


def test_compute_crypto_phase2_fair_values_reuses_phase1_fair_value_stack() -> None:
    fair_values = compute_crypto_phase2_fair_values(
        snapshot_path=FIXTURE_SNAPSHOTS,
        underlying_states={
            "ETH": build_underlying_state(
                underlying="ETH",
                as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
                spot_price=1850.0,
                realized_volatility=0.62,
                implied_volatility=0.71,
            )
        },
    )

    assert tuple(item.market_id for item in fair_values) == ("eth-dip-1000", "eth-dip-1500", "eth-dip-800")
    assert all(item.model_id == "crypto.phase1.fused" for item in fair_values)
    assert all("net_edge_bps" in item.supporting_values for item in fair_values)


def test_run_crypto_phase2_replay_writes_phase2_artifacts(tmp_path: Path) -> None:
    fair_values = asyncio.run(
        run_crypto_phase2_replay(
            snapshot_path=FIXTURE_SNAPSHOTS,
            underlying_states={
                "ETH": build_underlying_state(
                    underlying="ETH",
                    as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
                    spot_price=1850.0,
                    realized_volatility=0.62,
                    implied_volatility=0.71,
                )
            },
            output_dir=tmp_path / "crypto-phase2-run",
            run_id="crypto-phase2-test",
        )
    )

    assert fair_values
    attribution_path = tmp_path / "crypto-phase2-run" / "attribution.jsonl"
    metrics_path = tmp_path / "crypto-phase2-run" / "metrics.json"
    summary_path = tmp_path / "crypto-phase2-run" / "summary.md"
    assert attribution_path.exists()
    assert metrics_path.exists()
    assert summary_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["board"] == "crypto"
    assert metrics["run_id"] == "crypto-phase2-test"

    attribution_lines = [
        json.loads(line)
        for line in attribution_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert attribution_lines
    assert attribution_lines[0]["strategy_id"] == "crypto.phase2"


def test_run_crypto_phase2_replay_generates_events_on_tradable_compare_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-phase2-compare"
    underlying_states = {
        "ETH": build_underlying_state(
            underlying="ETH",
            as_of=datetime.fromisoformat("2026-03-23T12:00:00+00:00"),
            spot_price=1850.0,
            realized_volatility=0.62,
            implied_volatility=0.71,
        )
    }

    asyncio.run(
        run_crypto_phase2_replay(
            snapshot_path=FIXTURE_COMPARE,
            underlying_states=underlying_states,
            output_dir=output_dir,
            run_id="crypto-phase2-compare-test",
            barrier_model_config=CryptoBarrierModelConfig(),
            fusion_model_config=CryptoFusionModelConfig(),
            apply_series_filter=False,
        )
    )
    asyncio.run(
        run_crypto_phase2_replay(
            snapshot_path=FIXTURE_COMPARE,
            underlying_states=underlying_states,
            output_dir=output_dir,
            run_id="crypto-phase2-compare-test",
            barrier_model_config=CryptoBarrierModelConfig(),
            fusion_model_config=CryptoFusionModelConfig(),
            apply_series_filter=False,
        )
    )

    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (output_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert metrics["signals_generated"] == 2
    assert metrics["submitted_orders"] == 2
    assert metrics["events_recorded"] == 7
    assert len(events) == 7
    assert [event["event_type"] for event in events] == [
        "signal.generated",
        "order.submitted",
        "order.filled",
        "signal.generated",
        "order.submitted",
        "order.filled",
        "trade.closed",
    ]
    assert events[-1]["event_type"] == "trade.closed"


def test_run_crypto_phase2_replay_applies_series_filter_to_btc_runtime_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "crypto-phase2-btc-filtered"
    underlying_states = {
        "BTC": build_underlying_state(
            underlying="BTC",
            as_of=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
            spot_price=79000.0,
            daily_return=-0.028,
            realized_volatility=0.58,
            implied_volatility=0.66,
        )
    }

    asyncio.run(
        run_crypto_phase2_replay(
            snapshot_path=FIXTURE_BTC_RUNTIME,
            underlying_states=underlying_states,
            output_dir=output_dir,
            run_id="crypto-phase2-btc-filtered-test",
        )
    )

    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    events_text = (output_dir / "events.jsonl").read_text(encoding="utf-8")

    assert metrics["signals_generated"] == 0
    assert metrics["submitted_orders"] == 0
    assert metrics["events_recorded"] == 0
    assert events_text == ""
