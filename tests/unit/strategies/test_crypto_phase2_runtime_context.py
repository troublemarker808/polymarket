from datetime import UTC, datetime
import json
from pathlib import Path

from pm_bot.research.engine import load_market_snapshots
from pm_bot.storage.recorder import PaperRuntimeRecorder
from pm_bot.strategies.crypto.phase2.runtime_context import CryptoPhase2PaperContextBuilder


def test_crypto_phase2_paper_context_builder_generates_fair_values_and_static_series_blocks() -> None:
    builder = CryptoPhase2PaperContextBuilder(
        underlying_state_path=Path("tests/fixtures/crypto_phase2/runtime_underlying_states.json"),
        apply_series_filter=True,
        selection_report_path=Path("data/research/selection-overlay-phase2-v35-btc-reach-marketfilter/report.json"),
    )
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/btc_runtime_ladder_window.jsonl"))
    recorder = PaperRuntimeRecorder()

    context = builder.build_context(snapshot_cache=snapshots, recorder=recorder)

    fair_values_by_market_id = context["fair_values_by_market_id"]
    blocked_series_keys = context["blocked_series_keys"]
    blocked_market_ids = context["blocked_market_ids"]
    blocked_market_reasons = context["blocked_market_reasons"]
    market_selection_actions = context["market_selection_actions"]

    assert {"1339767", "1339768", "701502"} <= set(fair_values_by_market_id)
    assert "what-price-will-bitcoin-hit-before-2027" not in blocked_series_keys
    assert "701495" in blocked_market_ids
    assert "execution_no_fill" in blocked_market_reasons["701495"]
    assert market_selection_actions["701495"] == "watch_market"
    assert context["position_intents_by_market_id"] == {}
    assert context["reentry_state_by_market_id"] == {}


def test_crypto_phase2_paper_context_builder_updates_reentry_state_from_closed_loss() -> None:
    builder = CryptoPhase2PaperContextBuilder(
        underlying_state_path=Path("tests/fixtures/crypto_phase1/underlying_state.json"),
        apply_series_filter=False,
    )
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"))
    recorder = PaperRuntimeRecorder()
    recorder.events.extend(
        [
            {
                "event_type": "order.filled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "token_id": "eth-dip-1000-yes",
                    "updated_at": datetime(2026, 3, 28, 0, 0, tzinfo=UTC).isoformat(),
                },
            },
            {
                "event_type": "trade.closed",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "realized_pnl": -0.25,
                    "closed_at": datetime(2026, 3, 28, 0, 1, tzinfo=UTC).isoformat(),
                },
            },
        ]
    )

    context = builder.build_context(snapshot_cache=snapshots, recorder=recorder)
    reentry_state = context["reentry_state_by_market_id"]["eth-dip-1000"]

    assert "eth-dip-1000" not in context["position_intents_by_market_id"]
    assert reentry_state.stop_out_count == 1
    assert reentry_state.blocked_until is not None


def test_crypto_phase2_paper_context_builder_ignores_recovered_live_events() -> None:
    builder = CryptoPhase2PaperContextBuilder(
        underlying_state_path=Path("tests/fixtures/crypto_phase1/underlying_state.json"),
        apply_series_filter=False,
    )
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"))
    recorder = PaperRuntimeRecorder()
    recorder.events.extend(
        [
            {
                "event_type": "order.filled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "token_id": "eth-dip-1000-yes",
                    "strategy_id": "recovered.live",
                    "updated_at": datetime(2026, 3, 28, 0, 0, tzinfo=UTC).isoformat(),
                },
            },
            {
                "event_type": "trade.closed",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "strategy_id": "recovered.live",
                    "realized_pnl": -0.25,
                    "closed_at": datetime(2026, 3, 28, 0, 1, tzinfo=UTC).isoformat(),
                },
            },
        ]
    )

    context = builder.build_context(snapshot_cache=snapshots, recorder=recorder)

    assert context["position_intents_by_market_id"] == {}
    assert context["reentry_state_by_market_id"] == {}


def test_crypto_phase2_paper_context_builder_captures_fill_quality_in_position_intent() -> None:
    builder = CryptoPhase2PaperContextBuilder(
        underlying_state_path=Path("tests/fixtures/crypto_phase1/underlying_state.json"),
        apply_series_filter=False,
    )
    snapshots = load_market_snapshots(Path("tests/fixtures/crypto_phase2/compare_snapshots.jsonl"))
    recorder = PaperRuntimeRecorder()
    recorder.events.append(
        {
            "event_type": "order.filled",
            "payload": {
                "market_id": "eth-dip-1000",
                "token_id": "eth-dip-1000-yes",
                "average_fill_price": 0.110055,
                "mid_price": 0.105,
                "fill_source": "taker",
                "updated_at": datetime(2026, 3, 28, 0, 0, tzinfo=UTC).isoformat(),
            },
        }
    )

    context = builder.build_context(snapshot_cache=snapshots, recorder=recorder)
    intent = context["position_intents_by_market_id"]["eth-dip-1000"]

    assert intent.entry_fill_price == 0.110055
    assert intent.entry_mid_price == 0.105
    assert intent.entry_fill_source == "taker"


def test_crypto_phase2_paper_context_builder_blocks_watch_only_series_from_runtime_events() -> None:
    builder = CryptoPhase2PaperContextBuilder(
        underlying_state_path=Path("tests/fixtures/crypto_phase2/runtime_underlying_states.json"),
        apply_series_filter=True,
        selection_report_path=Path("data/research/selection-overlay-phase2-v35-btc-reach-marketfilter/report.json"),
    )
    snapshots = load_market_snapshots(Path("data/research/family-export-phase2-v35-btc-reach/snapshots.jsonl"))
    recorder = PaperRuntimeRecorder()
    recorder.events.extend(
        [
            json.loads(line)
            for line in Path("data/research/family-export-phase2-v35-btc-reach/events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
    )

    context = builder.build_context(snapshot_cache=snapshots, recorder=recorder)

    assert "what-price-will-bitcoin-hit-before-2027" not in context["blocked_series_keys"]
    assert "701495" in context["blocked_market_ids"]
    assert "execution_no_fill" in context["blocked_market_reasons"]["701495"]
    assert context["market_selection_actions"]["701495"] == "watch_market"
