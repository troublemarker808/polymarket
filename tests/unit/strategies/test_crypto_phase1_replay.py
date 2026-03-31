from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path

import pytest

from pm_bot.core.research_types import Phase1RunSummary
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.research.engine import ResearchRunResult
from pm_bot.research.phase1_artifacts import Phase1ArtifactPaths
from pm_bot.research.phase1_runner import Phase1ReplayResult
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategies.crypto.phase1.baseline import get_locked_crypto_calibration_baseline_preset
from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase1.replay import (
    _spread_cost_bps_for_side,
    _trade_side_from_probabilities,
    compute_crypto_phase1_fair_values,
    run_crypto_phase1_replay,
)


FIXTURE_SNAPSHOTS = Path("tests/fixtures/crypto_phase1/ladder_snapshots.jsonl")


def test_compute_crypto_phase1_fair_values_returns_enriched_estimates_for_supported_ladder() -> None:
    fair_values = compute_crypto_phase1_fair_values(
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


def test_compute_crypto_phase1_fair_values_uses_locked_baseline_by_default() -> None:
    explicit_preset = get_locked_crypto_calibration_baseline_preset()
    default_fair_values = compute_crypto_phase1_fair_values(
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
    explicit_fair_values = compute_crypto_phase1_fair_values(
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
        barrier_model_config=explicit_preset.barrier_model_config,
        fusion_model_config=explicit_preset.fusion_model_config,
    )

    assert default_fair_values == explicit_fair_values


def test_spread_cost_bps_for_side_uses_buy_no_book_when_trade_flips_direction() -> None:
    snapshot = MarketSnapshot(
        market_id="btc-buy-no-side-aware",
        token_id="token",
        slug="bitcoin-above-68k-on-april-1",
        category=Category.CRYPTO,
        timestamp=datetime.fromisoformat("2026-03-27T15:15:00+00:00"),
        resolution_time=datetime.fromisoformat("2026-04-01T00:00:00+00:00"),
        best_bid_yes=0.58,
        best_ask_yes=0.68,
        best_bid_no=0.392,
        best_ask_no=0.400,
    )
    side = _trade_side_from_probabilities(fair_probability=0.40, observed_probability=0.62)

    assert side == SignalSide.BUY_NO
    assert _spread_cost_bps_for_side(snapshot=snapshot, side=side) == pytest.approx(40.0)


def test_run_crypto_phase1_replay_rewrites_attribution_artifact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def _fake_run_phase1_replay(**kwargs) -> Phase1ReplayResult:
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        events_path = output_dir / "events.jsonl"
        events_path.write_text(
            json.dumps(
                {
                    "event_type": "trade.closed",
                    "payload": {"market_id": "eth-dip-1000", "realized_pnl": 1.5},
                },
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        engine_metrics_path = output_dir / "engine.metrics.json"
        engine_metrics_path.write_text(json.dumps({"processed_snapshots": 4}, ensure_ascii=True), encoding="utf-8")
        summary = Phase1RunSummary(
            generated_at=datetime.fromisoformat("2026-03-28T00:00:00+00:00"),
            board=Category.CRYPTO,
            mode="replay",
            run_id="crypto-phase1-test",
            config_dir="configs/profiles/research-crypto-phase1-v1",
            snapshot_path=str(FIXTURE_SNAPSHOTS),
            output_dir=str(output_dir),
            processed_snapshots=4,
            signals_generated=2,
            signals_rejected=0,
            orders_rejected=0,
            submitted_orders=2,
            events_recorded=4,
            generated_by_strategy={"crypto.surface": 2},
            submitted_by_strategy={"crypto.surface": 2},
            total_equity=1000.0,
            today_pnl=0.0,
            status="running",
            halt_reason="none",
        )
        artifacts = Phase1ArtifactPaths(
            output_dir=output_dir,
            summary_path=output_dir / "summary.md",
            metrics_path=output_dir / "metrics.json",
            fair_values_path=output_dir / "fair_values.jsonl",
            attribution_path=output_dir / "attribution.jsonl",
        )
        for path in (artifacts.summary_path, artifacts.metrics_path, artifacts.fair_values_path, artifacts.attribution_path):
            path.write_text("", encoding="utf-8")
        return Phase1ReplayResult(
            board=Category.CRYPTO,
            run_id="crypto-phase1-test",
            config_dir="configs/profiles/research-crypto-phase1-v1",
            snapshot_path=str(FIXTURE_SNAPSHOTS),
            output_dir=output_dir,
            events_path=events_path,
            engine_metrics_path=engine_metrics_path,
            summary=summary,
            artifacts=artifacts,
            replay=ResearchRunResult(
                mode="replay",
                processed_snapshots=4,
                signals_generated=2,
                signals_rejected=0,
                orders_rejected=0,
                submitted_orders=2,
                events_recorded=4,
                generated_by_strategy={"crypto.surface": 2},
                submitted_by_strategy={"crypto.surface": 2},
                dashboard=_dashboard(),
            ),
        )

    monkeypatch.setattr("pm_bot.strategies.crypto.phase1.replay.run_phase1_replay", _fake_run_phase1_replay)

    asyncio.run(
        run_crypto_phase1_replay(
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
            output_dir=tmp_path / "crypto-phase1-run",
            run_id="crypto-phase1-test",
        )
    )

    attribution_rows = [
        json.loads(line)
        for line in (tmp_path / "crypto-phase1-run" / "attribution.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert attribution_rows
    assert attribution_rows[0]["market_id"] == "eth-dip-1000"
    assert attribution_rows[0]["realized_pnl"] == 1.5


def _dashboard() -> DashboardState:
    return DashboardState(
        total_equity=1000.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )
