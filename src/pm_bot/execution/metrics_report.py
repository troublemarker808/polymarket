"""Helpers for comparing persisted execution metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_COMPARE_KEYS = (
    "processed_snapshots",
    "signals_generated",
    "signals_rejected",
    "orders_submitted",
    "orders_rejected",
    "orders_filled",
    "orders_partially_filled",
    "orders_expired",
    "orders_canceled",
    "trades_closed",
    "filled_shares_total",
    "fill_rate",
    "cancel_rate",
    "avg_time_to_fill_ms",
    "avg_fill_price_vs_mid_bps",
    "maker_fill_share",
    "taker_fill_share",
    "market_data_failures",
    "market_data_recoveries",
)


def load_metrics_file(path: str | Path) -> dict[str, Any]:
    metrics_path = Path(path)
    with metrics_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Metrics file must contain a JSON object")
    return payload


def compare_metrics(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    keys: tuple[str, ...] = _DEFAULT_COMPARE_KEYS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in keys:
        baseline_value = baseline.get(key)
        candidate_value = candidate.get(key)
        delta = None
        if isinstance(baseline_value, (int, float)) and isinstance(candidate_value, (int, float)):
            delta = candidate_value - baseline_value
        rows.append(
            {
                "metric": key,
                "baseline": baseline_value,
                "candidate": candidate_value,
                "delta": delta,
            }
        )
    return rows


def format_metric_comparison(rows: list[dict[str, Any]]) -> str:
    lines = ["metric,baseline,candidate,delta"]
    for row in rows:
        delta = "" if row["delta"] is None else _format_number(row["delta"])
        lines.append(
            ",".join(
                (
                    str(row["metric"]),
                    _format_value(row["baseline"]),
                    _format_value(row["candidate"]),
                    delta,
                )
            )
        )
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return _format_number(value)
    return str(value)


def _format_number(value: int | float) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6f}"
