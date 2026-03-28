"""Market-selection reporting for Crypto Phase 1 ladder research."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, median

from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.replay import compute_crypto_phase1_fair_values_from_snapshots


@dataclass(slots=True, frozen=True)
class CryptoMarketSelectionRow:
    market_id: str
    series_key: str
    instrument_key: str
    underlying: str
    event_family: str
    observed_probability: float
    fair_probability: float
    net_edge_bps: float
    entry_cost_bps: float
    liquidity_score: float
    tick_size: float | None
    min_order_size: float | None
    recommended_action: str
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoSeriesSelectionReport:
    series_key: str
    underlying: str
    event_family: str
    market_count: int
    positive_net_edge_count: int
    mean_net_edge_bps: float
    median_net_edge_bps: float
    mean_entry_cost_bps: float
    min_liquidity_score: float
    signal_count: int
    submitted_order_count: int
    filled_order_count: int
    expired_order_count: int
    recommended_action: str
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CryptoMarketSelectionReport:
    generated_at: datetime
    snapshot_path: str
    model_parameters: dict[str, float]
    series_reports: tuple[CryptoSeriesSelectionReport, ...]
    market_rows: tuple[CryptoMarketSelectionRow, ...]


def recommended_skip_series_keys(report: CryptoMarketSelectionReport) -> tuple[str, ...]:
    return tuple(
        series.series_key
        for series in report.series_reports
        if series.recommended_action == "skip_series"
    )


def generate_crypto_market_selection_report(
    *,
    snapshot_path: str | Path,
    underlying_states,
    event_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
) -> CryptoMarketSelectionReport:
    snapshots = load_market_snapshots(snapshot_path)
    return generate_crypto_market_selection_report_from_snapshots(
        snapshots=snapshots,
        snapshot_label=str(Path(snapshot_path)),
        underlying_states=underlying_states,
        event_path=event_path,
        output_dir=output_dir,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )


def generate_crypto_market_selection_report_from_snapshots(
    *,
    snapshots,
    snapshot_label: str,
    underlying_states,
    event_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
) -> CryptoMarketSelectionReport:
    latest_by_market_id = {snapshot.market_id: snapshot for snapshot in snapshots}
    fair_values = compute_crypto_phase1_fair_values_from_snapshots(
        snapshots=snapshots,
        underlying_states=underlying_states,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )
    fair_values_by_market_id = {item.market_id: item for item in fair_values}
    event_counts_by_market_id = _event_counts_by_market_id(event_path)

    market_rows: list[CryptoMarketSelectionRow] = []
    grouped_rows: dict[str, list[CryptoMarketSelectionRow]] = {}
    for market_id, fair_value in sorted(fair_values_by_market_id.items()):
        snapshot = latest_by_market_id.get(market_id)
        normalized = normalize_crypto_market(snapshot) if snapshot is not None else None
        if snapshot is None or normalized is None:
            continue
        entry_cost_bps = float(fair_value.supporting_values.get("entry_cost_bps", 0.0))
        net_edge_bps = float(fair_value.supporting_values.get("net_edge_bps", 0.0))
        row = CryptoMarketSelectionRow(
            market_id=market_id,
            series_key=normalized.series_key,
            instrument_key=normalized.normalized.instrument_key,
            underlying=normalized.underlying,
            event_family=normalized.event_family,
            observed_probability=fair_value.observed_probability or 0.0,
            fair_probability=fair_value.fair_probability,
            net_edge_bps=net_edge_bps,
            entry_cost_bps=entry_cost_bps,
            liquidity_score=snapshot.liquidity_score,
            tick_size=snapshot.tick_size,
            min_order_size=snapshot.min_order_size,
            recommended_action=_market_action(
                net_edge_bps=net_edge_bps,
                entry_cost_bps=entry_cost_bps,
                liquidity_score=snapshot.liquidity_score,
            ),
            reasons=_market_reasons(
                net_edge_bps=net_edge_bps,
                entry_cost_bps=entry_cost_bps,
                liquidity_score=snapshot.liquidity_score,
            ),
        )
        market_rows.append(row)
        grouped_rows.setdefault(row.series_key, []).append(row)

    series_reports = tuple(
        sorted(
            (
                _build_series_report(
                    series_key=series_key,
                    rows=rows,
                    event_counts_by_market_id=event_counts_by_market_id,
                )
                for series_key, rows in grouped_rows.items()
            ),
            key=lambda item: (item.recommended_action, item.series_key),
        )
    )
    report = CryptoMarketSelectionReport(
        generated_at=datetime.now(tz=timezone.utc),
        snapshot_path=snapshot_label,
        model_parameters={
            "barrier_steepness": (barrier_model_config.steepness if barrier_model_config is not None else CryptoBarrierModelConfig().steepness),
            "fusion_barrier_weight": (
                fusion_model_config.barrier_weight if fusion_model_config is not None else CryptoFusionModelConfig().barrier_weight
            ),
            "fusion_surface_weight": (
                fusion_model_config.surface_weight if fusion_model_config is not None else CryptoFusionModelConfig().surface_weight
            ),
        },
        series_reports=series_reports,
        market_rows=tuple(market_rows),
    )
    if output_dir is not None:
        write_crypto_market_selection_report(report=report, output_dir=output_dir)
    return report


def write_crypto_market_selection_report(*, report: CryptoMarketSelectionReport, output_dir: str | Path) -> None:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "report.json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "markets.jsonl").write_text(
        "".join(json.dumps(_normalize(asdict(row)), ensure_ascii=True) + "\n" for row in report.market_rows),
        encoding="utf-8",
    )
    (target_dir / "summary.md").write_text(format_crypto_market_selection_report(report), encoding="utf-8")


def format_crypto_market_selection_report(report: CryptoMarketSelectionReport) -> str:
    lines = [
        "# Crypto Market Selection Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- snapshot_path: {report.snapshot_path}",
        f"- barrier_steepness: {report.model_parameters['barrier_steepness']:.2f}",
        f"- fusion_barrier_weight: {report.model_parameters['fusion_barrier_weight']:.2f}",
        f"- fusion_surface_weight: {report.model_parameters['fusion_surface_weight']:.2f}",
        "",
        "## Series Reports",
        "",
    ]
    for series in report.series_reports:
        lines.extend(
            [
                f"### {series.series_key}",
                "",
                f"- underlying: {series.underlying}",
                f"- event_family: {series.event_family}",
                f"- market_count: {series.market_count}",
                f"- positive_net_edge_count: {series.positive_net_edge_count}",
                f"- mean_net_edge_bps: {series.mean_net_edge_bps:.2f}",
                f"- median_net_edge_bps: {series.median_net_edge_bps:.2f}",
                f"- mean_entry_cost_bps: {series.mean_entry_cost_bps:.2f}",
                f"- min_liquidity_score: {series.min_liquidity_score:.4f}",
                f"- signal_count: {series.signal_count}",
                f"- submitted_order_count: {series.submitted_order_count}",
                f"- filled_order_count: {series.filled_order_count}",
                f"- expired_order_count: {series.expired_order_count}",
                f"- recommended_action: {series.recommended_action}",
                f"- reasons: {', '.join(series.reasons) if series.reasons else 'none'}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_series_report(
    *,
    series_key: str,
    rows: list[CryptoMarketSelectionRow],
    event_counts_by_market_id: dict[str, dict[str, int]],
) -> CryptoSeriesSelectionReport:
    ordered = sorted(rows, key=lambda item: item.instrument_key)
    positive_net_edge_count = sum(1 for row in ordered if row.net_edge_bps > 0)
    mean_net_edge_bps = mean(row.net_edge_bps for row in ordered)
    median_net_edge_bps = median(row.net_edge_bps for row in ordered)
    mean_entry_cost_bps = mean(row.entry_cost_bps for row in ordered)
    min_liquidity_score = min(row.liquidity_score for row in ordered)
    signal_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("signal.generated", 0) for row in ordered)
    submitted_order_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("order.submitted", 0) for row in ordered)
    filled_order_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("order.filled", 0) for row in ordered)
    expired_order_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("order.expired", 0) for row in ordered)
    reasons: list[str] = []
    if positive_net_edge_count == 0:
        reasons.append("all_rungs_negative")
    if mean_net_edge_bps <= -750:
        reasons.append("strip_overpriced")
    if mean_entry_cost_bps <= 75 and min_liquidity_score >= 0.95 and positive_net_edge_count == 0:
        reasons.append("quality_fine_model_negative")
    if mean_entry_cost_bps > 75:
        reasons.append("wide_spread")
    if min_liquidity_score < 0.95:
        reasons.append("thin_liquidity")
    if signal_count > 0 and submitted_order_count > 0 and filled_order_count == 0 and expired_order_count > 0:
        reasons.append("execution_no_fill")

    if positive_net_edge_count == 0 and mean_net_edge_bps <= -750:
        recommended_action = "skip_series"
    elif signal_count > 0 and submitted_order_count > 0 and filled_order_count == 0 and expired_order_count > 0:
        recommended_action = "watch_only"
    elif positive_net_edge_count == 0:
        recommended_action = "watch_only"
    elif positive_net_edge_count < len(ordered):
        recommended_action = "selective_only"
    else:
        recommended_action = "tradable"

    first = ordered[0]
    return CryptoSeriesSelectionReport(
        series_key=series_key,
        underlying=first.underlying,
        event_family=first.event_family,
        market_count=len(ordered),
        positive_net_edge_count=positive_net_edge_count,
        mean_net_edge_bps=mean_net_edge_bps,
        median_net_edge_bps=median_net_edge_bps,
        mean_entry_cost_bps=mean_entry_cost_bps,
        min_liquidity_score=min_liquidity_score,
        signal_count=signal_count,
        submitted_order_count=submitted_order_count,
        filled_order_count=filled_order_count,
        expired_order_count=expired_order_count,
        recommended_action=recommended_action,
        reasons=tuple(reasons),
    )


def _market_action(*, net_edge_bps: float, entry_cost_bps: float, liquidity_score: float) -> str:
    if net_edge_bps <= -750:
        return "skip_market"
    if net_edge_bps <= 0:
        return "watch_market"
    if entry_cost_bps > 75 or liquidity_score < 0.95:
        return "selective_market"
    return "tradable_market"


def _market_reasons(*, net_edge_bps: float, entry_cost_bps: float, liquidity_score: float) -> tuple[str, ...]:
    reasons: list[str] = []
    if net_edge_bps <= -1000:
        reasons.append("deep_negative_edge")
    elif net_edge_bps <= 0:
        reasons.append("negative_edge")
    if entry_cost_bps > 75:
        reasons.append("wide_spread")
    if liquidity_score < 0.95:
        reasons.append("thin_liquidity")
    return tuple(reasons)


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


def _event_counts_by_market_id(event_path: str | Path | None) -> dict[str, dict[str, int]]:
    if event_path is None:
        return {}
    counts: dict[str, dict[str, int]] = {}
    with Path(event_path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            decoded = json.loads(line)
            event_type = str(decoded.get("event_type", ""))
            payload = decoded.get("payload", {})
            if not isinstance(payload, dict):
                continue
            market_id = str(payload.get("market_id", ""))
            if not market_id or not event_type:
                continue
            bucket = counts.setdefault(market_id, {})
            bucket[event_type] = bucket.get(event_type, 0) + 1
    return counts
