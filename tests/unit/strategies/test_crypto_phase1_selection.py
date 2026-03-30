from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.baseline import get_locked_crypto_calibration_baseline_preset
from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.selection import (
    format_crypto_market_selection_report,
    generate_crypto_market_selection_report,
    generate_crypto_market_selection_report_from_snapshots,
    recommended_runtime_blocked_market_ids,
    recommended_runtime_blocked_series_keys,
)


def test_generate_crypto_market_selection_report_marks_btc_runtime_strip_as_tradable(tmp_path: Path) -> None:
    preset = get_locked_crypto_calibration_baseline_preset()
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
        barrier_model_config=preset.barrier_model_config,
        fusion_model_config=preset.fusion_model_config,
    )

    assert len(report.series_reports) == 1
    series = report.series_reports[0]
    assert series.recommended_action == "tradable"
    assert series.positive_net_edge_count == 3
    assert series.profit_quality_score > 0.5
    assert series.selection_rank == 1
    assert report.model_parameters["baseline_preset"] == preset.preset_id
    assert report.model_parameters["baseline_candidate"] == preset.candidate_name
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
    assert "Market Rows" in summary
    assert "profit_quality_score" in summary
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


def test_recommended_runtime_blocked_series_keys_keeps_watch_only_series_open_when_actionable_markets_remain(tmp_path: Path) -> None:
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

    assert report.series_reports[0].recommended_action == "watch_only"
    assert recommended_runtime_blocked_series_keys(report) == ()


def test_generate_crypto_market_selection_report_marks_stale_quote_market_as_runtime_blocked() -> None:
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"))
    stale_snapshots = []
    for snapshot in snapshots:
        cloned = snapshot
        cloned.metadata = dict(snapshot.metadata)
        cloned.metadata["clob_timestamp"] = "2026-03-27T15:00:00+00:00"
        stale_snapshots.append(cloned)

    report = generate_crypto_market_selection_report_from_snapshots(
        snapshots=stale_snapshots,
        snapshot_label="stale-runtime-window",
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

    row = next(row for row in report.market_rows if row.market_id == "1339768")

    assert row.quote_age_seconds is not None
    assert row.quote_age_seconds > 180.0
    assert "stale_quote" in row.reasons
    assert row.recommended_action == "watch_market"
    assert "1339768" in recommended_runtime_blocked_market_ids(report)


def test_generate_crypto_market_selection_report_uses_locked_baseline_by_default() -> None:
    preset = get_locked_crypto_calibration_baseline_preset()
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
    )

    assert report.model_parameters["barrier_steepness"] == preset.barrier_model_config.steepness
    assert report.model_parameters["fusion_barrier_weight"] == preset.fusion_model_config.barrier_weight
    assert report.model_parameters["fusion_surface_weight"] == preset.fusion_model_config.surface_weight


def test_recommended_runtime_blocked_market_ids_marks_execution_no_fill_rungs(tmp_path: Path) -> None:
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

    blocked_market_ids = recommended_runtime_blocked_market_ids(report)

    assert "701495" in blocked_market_ids
    row = next(row for row in report.market_rows if row.market_id == "701495")
    assert row.signal_count >= 1
    assert row.expired_order_count >= 1
    assert "execution_no_fill" in row.reasons
