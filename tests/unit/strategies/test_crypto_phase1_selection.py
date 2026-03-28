from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.selection import (
    format_crypto_market_selection_report,
    generate_crypto_market_selection_report,
)


def test_generate_crypto_market_selection_report_marks_btc_runtime_strip_as_tradable(tmp_path: Path) -> None:
    report = generate_crypto_market_selection_report(
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
        output_dir=tmp_path / "selection",
        barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
        fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
    )

    assert len(report.series_reports) == 1
    series = report.series_reports[0]
    assert series.recommended_action == "tradable"
    assert series.positive_net_edge_count == 3
    assert (tmp_path / "selection" / "report.json").exists()
    assert (tmp_path / "selection" / "summary.md").exists()


def test_format_crypto_market_selection_report_contains_series_section() -> None:
    report = generate_crypto_market_selection_report(
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
        barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
        fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
    )

    summary = format_crypto_market_selection_report(report)

    assert "Crypto Market Selection Report" in summary
    assert "Series Reports" in summary
    assert "recommended_action: tradable" in summary


def test_generate_crypto_market_selection_report_uses_event_overlay_to_mark_no_fill_series_watch_only(tmp_path: Path) -> None:
    report = generate_crypto_market_selection_report(
        snapshot_path=Path("data/research/family-export-phase2-v35-btc-reach/snapshots.jsonl"),
        event_path=Path("data/research/family-export-phase2-v35-btc-reach/events.jsonl"),
        underlying_states={
            "BTC": build_underlying_state(
                underlying="BTC",
                as_of=datetime.fromisoformat("2026-03-28T12:31:49+00:00"),
                spot_price=79000.0,
                daily_return=-0.028,
                realized_volatility=0.58,
                implied_volatility=0.66,
            )
        },
        output_dir=tmp_path / "selection-overlay",
        barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
        fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
    )

    series = report.series_reports[0]
    assert series.signal_count >= 1
    assert series.submitted_order_count >= 1
    assert series.expired_order_count >= 1
    assert series.filled_order_count == 0
    assert series.recommended_action == "watch_only"
    assert "execution_no_fill" in series.reasons
