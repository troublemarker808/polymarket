"""Signal-level reporting for Crypto replay diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market


@dataclass(slots=True, frozen=True)
class CryptoSignalReportRow:
    market_id: str
    series_key: str
    instrument_key: str
    underlying: str
    event_family: str
    signal_side: str
    signal_type: str
    execution_route: str
    fair_probability: float
    observed_probability: float
    gross_edge_bps: float
    net_edge_bps: float
    target_price: float | None
    quote_ttl_seconds: int | None
    generated_at: str


@dataclass(slots=True, frozen=True)
class CryptoSignalSeriesSummary:
    series_key: str
    underlying: str
    event_family: str
    signal_count: int
    routes: tuple[str, ...]
    mean_gross_edge_bps: float
    mean_net_edge_bps: float


@dataclass(slots=True, frozen=True)
class CryptoSignalReport:
    generated_at: datetime
    event_path: str
    snapshot_path: str | None
    signal_rows: tuple[CryptoSignalReportRow, ...]
    series_summaries: tuple[CryptoSignalSeriesSummary, ...]


def generate_crypto_signal_report(
    *,
    event_path: str | Path,
    snapshot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> CryptoSignalReport:
    snapshots_by_market_id: dict[str, object] = {}
    if snapshot_path is not None:
        for snapshot in load_market_snapshots(snapshot_path):
            snapshots_by_market_id[snapshot.market_id] = snapshot

    rows: list[CryptoSignalReportRow] = []
    with Path(event_path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            decoded = json.loads(line)
            if decoded.get("event_type") != "signal.generated":
                continue
            payload = decoded.get("payload", {})
            if not isinstance(payload, dict):
                continue
            market_id = str(payload.get("market_id", ""))
            if not market_id:
                continue
            normalized = None
            snapshot = snapshots_by_market_id.get(market_id)
            if snapshot is not None:
                normalized = normalize_crypto_market(snapshot)
            diagnostics = payload.get("diagnostics", {})
            if not isinstance(diagnostics, dict):
                diagnostics = {}
            rows.append(
                CryptoSignalReportRow(
                    market_id=market_id,
                    series_key=(normalized.series_key if normalized is not None else ""),
                    instrument_key=(normalized.normalized.instrument_key if normalized is not None else market_id),
                    underlying=(normalized.underlying if normalized is not None else ""),
                    event_family=(normalized.event_family if normalized is not None else ""),
                    signal_side=str(payload.get("side", "")),
                    signal_type=str(diagnostics.get("signal_type", "")),
                    execution_route=str(diagnostics.get("execution_route", "")),
                    fair_probability=float(payload.get("fair_probability", 0.0) or 0.0),
                    observed_probability=float(diagnostics.get("observed_probability", 0.0) or 0.0),
                    gross_edge_bps=float(diagnostics.get("gross_edge_bps", 0.0) or 0.0),
                    net_edge_bps=float(diagnostics.get("net_edge_bps", 0.0) or 0.0),
                    target_price=_optional_float(payload.get("target_price")),
                    quote_ttl_seconds=_optional_int(payload.get("quote_ttl_seconds")),
                    generated_at=str(payload.get("generated_at", "")),
                )
            )

    grouped: dict[str, list[CryptoSignalReportRow]] = {}
    for row in rows:
        grouped.setdefault(row.series_key or row.market_id, []).append(row)

    series_summaries = tuple(
        sorted(
            (
                CryptoSignalSeriesSummary(
                    series_key=series_key,
                    underlying=group_rows[0].underlying,
                    event_family=group_rows[0].event_family,
                    signal_count=len(group_rows),
                    routes=tuple(sorted({row.execution_route for row in group_rows if row.execution_route})),
                    mean_gross_edge_bps=mean(row.gross_edge_bps for row in group_rows),
                    mean_net_edge_bps=mean(row.net_edge_bps for row in group_rows),
                )
                for series_key, group_rows in grouped.items()
            ),
            key=lambda item: (-item.signal_count, item.series_key),
        )
    )
    report = CryptoSignalReport(
        generated_at=datetime.now(tz=timezone.utc),
        event_path=str(Path(event_path)),
        snapshot_path=(str(Path(snapshot_path)) if snapshot_path is not None else None),
        signal_rows=tuple(rows),
        series_summaries=series_summaries,
    )
    if output_dir is not None:
        write_crypto_signal_report(report=report, output_dir=output_dir)
    return report


def write_crypto_signal_report(*, report: CryptoSignalReport, output_dir: str | Path) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "report.json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "signals.jsonl").write_text(
        "".join(json.dumps(_normalize(asdict(row)), ensure_ascii=True) + "\n" for row in report.signal_rows),
        encoding="utf-8",
    )
    (target_dir / "summary.md").write_text(format_crypto_signal_report(report), encoding="utf-8")


def format_crypto_signal_report(report: CryptoSignalReport) -> str:
    lines = [
        "# Crypto Signal Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- event_path: {report.event_path}",
        f"- snapshot_path: {report.snapshot_path or 'none'}",
        f"- signal_count: {len(report.signal_rows)}",
        "",
        "## Series Summaries",
        "",
    ]
    for summary in report.series_summaries:
        lines.extend(
            [
                f"### {summary.series_key}",
                "",
                f"- underlying: {summary.underlying or 'unknown'}",
                f"- event_family: {summary.event_family or 'unknown'}",
                f"- signal_count: {summary.signal_count}",
                f"- routes: {', '.join(summary.routes) if summary.routes else 'none'}",
                f"- mean_gross_edge_bps: {summary.mean_gross_edge_bps:.2f}",
                f"- mean_net_edge_bps: {summary.mean_net_edge_bps:.2f}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _normalize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
