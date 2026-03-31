from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pm_bot.core.types import Category, MarketSnapshot, OrderBookLevel, SignalSide
from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.baseline import get_locked_crypto_calibration_baseline_preset
from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.selection import (
    _market_action,
    _market_reasons,
    _nearby_book_depth,
    _runtime_tradability_policy,
    _spread_bps,
    _top_book_depth,
    _trade_side_from_probabilities,
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


def test_generate_crypto_market_selection_report_does_not_block_market_after_single_no_fill_attempt() -> None:
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"))
    report = generate_crypto_market_selection_report_from_snapshots(
        snapshots=snapshots,
        snapshot_label="single-no-fill",
        events=[
            {
                "event_type": "signal.generated",
                "payload": {"market_id": "1339768"},
            },
            {
                "event_type": "order.submitted",
                "payload": {"market_id": "1339768"},
            },
            {
                "event_type": "order.expired",
                "payload": {"market_id": "1339768"},
            },
        ],
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

    assert "execution_no_fill" not in row.reasons
    assert row.recommended_action != "watch_market"


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


def test_generate_crypto_market_selection_report_ignores_resolved_markets() -> None:
    snapshot = load_market_snapshots(Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"))[0]
    snapshot.timestamp = datetime.fromisoformat("2026-03-28T15:15:00+00:00")
    snapshot.resolution_time = datetime.fromisoformat("2026-03-28T15:00:00+00:00")

    report = generate_crypto_market_selection_report_from_snapshots(
        snapshots=[snapshot],
        snapshot_label="resolved-runtime-window",
        underlying_states={
            "BTC": build_underlying_state(
                underlying="BTC",
                as_of=datetime.fromisoformat("2026-03-28T15:15:00+00:00"),
                spot_price=79000.0,
                daily_return=-0.028,
                realized_volatility=0.58,
                implied_volatility=0.66,
            )
        },
        barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
        fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
    )

    assert report.market_rows == ()
    assert report.series_reports == ()


def test_generate_crypto_market_selection_report_softens_positive_edge_thin_top_book_when_nearby_depth_is_strong() -> None:
    snapshot = next(
        item
        for item in load_market_snapshots(Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"))
        if item.market_id == "1339768"
    )
    snapshot.best_ask_yes_size = 1.0
    snapshot.best_ask_no_size = 1.0

    report = generate_crypto_market_selection_report_from_snapshots(
        snapshots=[snapshot],
        snapshot_label="thin-top-book-softened",
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

    row = report.market_rows[0]

    assert row.net_edge_bps > 0
    assert row.recommended_action == "selective_market"
    assert "thin_top_book" in row.reasons
    assert recommended_runtime_blocked_series_keys(report) == ()


def test_market_selection_blocks_positive_edge_tail_contracts_before_phase2() -> None:
    policy = _runtime_tradability_policy(underlying="BTC", event_family="reach")

    action = _market_action(
        observed_probability=0.94,
        fair_probability=0.90,
        net_edge_bps=220.0,
        entry_cost_bps=30.0,
        spread_bps=80.0,
        liquidity_score=0.99,
        top_book_depth=30.0,
        nearby_book_depth=150.0,
        quote_age_seconds=10.0,
        accepting_orders=True,
        min_order_size=5.0,
        policy=policy,
        signal_count=0,
        submitted_order_count=0,
        filled_order_count=0,
        expired_order_count=0,
    )
    reasons = _market_reasons(
        observed_probability=0.94,
        fair_probability=0.90,
        net_edge_bps=220.0,
        entry_cost_bps=30.0,
        spread_bps=80.0,
        liquidity_score=0.99,
        top_book_depth=30.0,
        nearby_book_depth=150.0,
        quote_age_seconds=10.0,
        accepting_orders=True,
        min_order_size=5.0,
        policy=policy,
        signal_count=0,
        submitted_order_count=0,
        filled_order_count=0,
        expired_order_count=0,
    )

    assert action == "watch_market"
    assert "contract_price_too_low" in reasons


def test_market_selection_blocks_btc_thin_liquidity_as_watch_market() -> None:
    policy = _runtime_tradability_policy(underlying="BTC", event_family="reach")

    action = _market_action(
        observed_probability=0.42,
        fair_probability=0.30,
        net_edge_bps=350.0,
        entry_cost_bps=25.0,
        spread_bps=80.0,
        liquidity_score=0.80,
        top_book_depth=30.0,
        nearby_book_depth=150.0,
        quote_age_seconds=10.0,
        accepting_orders=True,
        min_order_size=5.0,
        policy=policy,
        signal_count=0,
        submitted_order_count=0,
        filled_order_count=0,
        expired_order_count=0,
    )

    assert action == "watch_market"


def test_market_selection_uses_no_book_side_for_buy_no_runtime_checks() -> None:
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
        best_bid_yes_size=2.0,
        best_ask_yes_size=2.0,
        best_bid_no_size=40.0,
        best_ask_no_size=40.0,
        yes_bid_levels=(
            OrderBookLevel(price=0.58, size=2.0),
            OrderBookLevel(price=0.57, size=2.0),
            OrderBookLevel(price=0.56, size=2.0),
        ),
        yes_ask_levels=(
            OrderBookLevel(price=0.68, size=2.0),
            OrderBookLevel(price=0.69, size=2.0),
            OrderBookLevel(price=0.70, size=2.0),
        ),
        no_bid_levels=(
            OrderBookLevel(price=0.392, size=40.0),
            OrderBookLevel(price=0.390, size=40.0),
            OrderBookLevel(price=0.388, size=40.0),
        ),
        no_ask_levels=(
            OrderBookLevel(price=0.400, size=40.0),
            OrderBookLevel(price=0.402, size=40.0),
            OrderBookLevel(price=0.404, size=40.0),
        ),
        liquidity_score=0.99,
    )
    policy = _runtime_tradability_policy(underlying="BTC", event_family="reach")
    side = _trade_side_from_probabilities(observed_probability=0.62, fair_probability=0.40)

    action = _market_action(
        observed_probability=0.62,
        fair_probability=0.40,
        net_edge_bps=320.0,
        entry_cost_bps=40.0,
        spread_bps=_spread_bps(snapshot, side=side),
        liquidity_score=snapshot.liquidity_score,
        top_book_depth=_top_book_depth(snapshot, side=side),
        nearby_book_depth=_nearby_book_depth(snapshot, side=side),
        quote_age_seconds=10.0,
        accepting_orders=True,
        min_order_size=5.0,
        policy=policy,
        signal_count=0,
        submitted_order_count=0,
        filled_order_count=0,
        expired_order_count=0,
    )
    reasons = _market_reasons(
        observed_probability=0.62,
        fair_probability=0.40,
        net_edge_bps=320.0,
        entry_cost_bps=40.0,
        spread_bps=_spread_bps(snapshot, side=side),
        liquidity_score=snapshot.liquidity_score,
        top_book_depth=_top_book_depth(snapshot, side=side),
        nearby_book_depth=_nearby_book_depth(snapshot, side=side),
        quote_age_seconds=10.0,
        accepting_orders=True,
        min_order_size=5.0,
        policy=policy,
        signal_count=0,
        submitted_order_count=0,
        filled_order_count=0,
        expired_order_count=0,
    )

    assert side == SignalSide.BUY_NO
    assert action == "tradable_market"
    assert "wide_spread" not in reasons
    assert "wide_runtime_spread" not in reasons
    assert "thin_top_book" not in reasons
    assert "thin_nearby_depth" not in reasons


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
