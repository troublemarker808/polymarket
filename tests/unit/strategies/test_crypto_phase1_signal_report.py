from __future__ import annotations

from pathlib import Path

from pm_bot.strategies.crypto.phase1.signal_report import (
    format_crypto_signal_report,
    generate_crypto_signal_report,
)


def test_generate_crypto_signal_report_reads_signal_diagnostics(tmp_path: Path) -> None:
    report = generate_crypto_signal_report(
        event_path=Path("data/research/fixed-window-phase2-v35-btc-reach-v7/train/baseline/events.jsonl"),
        snapshot_path=Path("data/research/family-export-phase2-v35-btc-reach/snapshots.jsonl"),
        output_dir=tmp_path / "signal-report",
    )

    assert len(report.signal_rows) == 1
    row = report.signal_rows[0]
    assert row.market_id == "701491"
    assert row.execution_route == "maker"
    assert row.signal_type in {"resolution_edge", "liquidity_edge", "repricing_edge", "no_trade"}
    assert (tmp_path / "signal-report" / "report.json").exists()
    assert (tmp_path / "signal-report" / "summary.md").exists()


def test_format_crypto_signal_report_contains_series_summaries() -> None:
    report = generate_crypto_signal_report(
        event_path=Path("data/research/fixed-window-phase2-v35-btc-reach-v7/train/baseline/events.jsonl"),
        snapshot_path=Path("data/research/family-export-phase2-v35-btc-reach/snapshots.jsonl"),
    )

    summary = format_crypto_signal_report(report)

    assert "Crypto Signal Report" in summary
    assert "Series Summaries" in summary
    assert "what-price-will-bitcoin-hit-before-2027" in summary
