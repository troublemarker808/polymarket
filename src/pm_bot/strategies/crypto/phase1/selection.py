"""Market-selection reporting for Crypto Phase 1 ladder research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from pm_bot.core.types import MarketSnapshot, SignalSide
from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.common import parse_float
from pm_bot.strategies.crypto.phase1.baseline import resolve_crypto_calibration_model_configs
from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig
from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.normalization import normalize_crypto_market
from pm_bot.strategies.crypto.phase1.replay import compute_crypto_phase1_fair_values_from_snapshots


@dataclass(slots=True, frozen=True)
class CryptoRuntimeTradabilityPolicy:
    max_runtime_spread_bps: float
    min_top_book_depth: float
    min_nearby_book_depth: float
    max_quote_age_seconds: float
    min_tradeable_contract_price: float
    watch_thin_liquidity: bool = False
    execution_no_fill_min_expired_orders: int = 2


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
    spread_bps: float | None
    liquidity_score: float
    tick_size: float | None
    min_order_size: float | None
    top_book_depth: float | None
    nearby_book_depth: float | None
    quote_age_seconds: float | None
    signal_count: int
    submitted_order_count: int
    filled_order_count: int
    expired_order_count: int
    recommended_action: str
    reasons: tuple[str, ...]
    profit_quality_score: float


@dataclass(slots=True, frozen=True)
class CryptoSeriesSelectionReport:
    series_key: str
    underlying: str
    event_family: str
    market_count: int
    runtime_actionable_market_count: int
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
    profit_quality_score: float
    selection_rank: int


@dataclass(slots=True, frozen=True)
class CryptoMarketSelectionReport:
    generated_at: datetime
    snapshot_path: str
    model_parameters: dict[str, Any]
    series_reports: tuple[CryptoSeriesSelectionReport, ...]
    market_rows: tuple[CryptoMarketSelectionRow, ...]


_HARD_RUNTIME_BLOCK_REASONS = frozenset(
    {
        "orders_disabled",
        "stale_quote",
        "execution_no_fill",
        "negative_edge",
        "deep_negative_edge",
        "thin_nearby_depth",
    }
)
_EXECUTION_NO_FILL_MIN_EXPIRED_ORDERS = 2


def recommended_skip_series_keys(report: CryptoMarketSelectionReport) -> tuple[str, ...]:
    return tuple(
        series.series_key
        for series in report.series_reports
        if series.recommended_action == "skip_series"
    )


def recommended_runtime_blocked_series_keys(report: CryptoMarketSelectionReport) -> tuple[str, ...]:
    return tuple(
        series.series_key
        for series in report.series_reports
        if (
            series.recommended_action == "skip_series"
            or (
                series.recommended_action == "watch_only"
                and not _series_has_runtime_actionable_market(report=report, series_key=series.series_key)
            )
        )
    )


def recommended_runtime_blocked_series_reasons(
    report: CryptoMarketSelectionReport,
) -> dict[str, tuple[str, ...]]:
    return {
        series.series_key: series.reasons
        for series in report.series_reports
        if series.series_key in recommended_runtime_blocked_series_keys(report)
    }


def load_runtime_blocked_series_keys(report_path: str | Path) -> tuple[str, ...]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    series_reports = decoded.get("series_reports", [])
    if not isinstance(series_reports, list):
        return ()
    return tuple(
        str(series.get("series_key", ""))
        for series in series_reports
        if isinstance(series, Mapping)
        and (
            str(series.get("recommended_action", "")) == "skip_series"
            or (
                str(series.get("recommended_action", "")) == "watch_only"
                and not _decoded_series_has_runtime_actionable_market(
                    series_key=str(series.get("series_key", "")),
                    market_rows=decoded.get("market_rows", []),
                )
            )
        )
        and str(series.get("series_key", ""))
    )


def load_runtime_blocked_series_reasons(report_path: str | Path) -> dict[str, tuple[str, ...]]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    series_reports = decoded.get("series_reports", [])
    market_rows = decoded.get("market_rows", [])
    if not isinstance(series_reports, list):
        return {}
    blocked_keys = set(load_runtime_blocked_series_keys(report_path))
    reasons: dict[str, tuple[str, ...]] = {}
    for series in series_reports:
        if not isinstance(series, Mapping):
            continue
        series_key = str(series.get("series_key", ""))
        if not series_key or series_key not in blocked_keys:
            continue
        reasons[series_key] = tuple(str(reason) for reason in series.get("reasons", []))
    if reasons:
        return reasons
    if isinstance(market_rows, list):
        return {
            key: tuple()
            for key in blocked_keys
        }
    return {}


def recommended_runtime_blocked_market_ids(report: CryptoMarketSelectionReport) -> tuple[str, ...]:
    return tuple(
        row.market_id
        for row in report.market_rows
        if row.recommended_action in {"watch_market", "skip_market"}
    )


def recommended_runtime_blocked_market_reasons(
    report: CryptoMarketSelectionReport,
) -> dict[str, tuple[str, ...]]:
    return {
        row.market_id: row.reasons
        for row in report.market_rows
        if row.market_id in recommended_runtime_blocked_market_ids(report)
    }


def load_runtime_blocked_market_ids(report_path: str | Path) -> tuple[str, ...]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    market_rows = decoded.get("market_rows", [])
    if not isinstance(market_rows, list):
        return ()
    return tuple(
        str(row.get("market_id", ""))
        for row in market_rows
        if isinstance(row, Mapping)
        and str(row.get("recommended_action", "")) in {"watch_market", "skip_market"}
        and str(row.get("market_id", ""))
    )


def load_runtime_blocked_market_reasons(report_path: str | Path) -> dict[str, tuple[str, ...]]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    market_rows = decoded.get("market_rows", [])
    if not isinstance(market_rows, list):
        return {}
    reasons: dict[str, tuple[str, ...]] = {}
    for row in market_rows:
        if not isinstance(row, Mapping):
            continue
        market_id = str(row.get("market_id", ""))
        if not market_id or str(row.get("recommended_action", "")) not in {"watch_market", "skip_market"}:
            continue
        reasons[market_id] = tuple(str(reason) for reason in row.get("reasons", []))
    return reasons


def runtime_market_selection_actions(report: CryptoMarketSelectionReport) -> dict[str, str]:
    return {row.market_id: row.recommended_action for row in report.market_rows}


def runtime_market_selection_reasons(report: CryptoMarketSelectionReport) -> dict[str, tuple[str, ...]]:
    return {row.market_id: row.reasons for row in report.market_rows}


def load_runtime_market_selection_actions(report_path: str | Path) -> dict[str, str]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    market_rows = decoded.get("market_rows", [])
    if not isinstance(market_rows, list):
        return {}
    actions: dict[str, str] = {}
    for row in market_rows:
        if not isinstance(row, Mapping):
            continue
        market_id = str(row.get("market_id", ""))
        action = str(row.get("recommended_action", ""))
        if market_id and action:
            actions[market_id] = action
    return actions


def load_runtime_market_selection_reasons(report_path: str | Path) -> dict[str, tuple[str, ...]]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    market_rows = decoded.get("market_rows", [])
    if not isinstance(market_rows, list):
        return {}
    reasons: dict[str, tuple[str, ...]] = {}
    for row in market_rows:
        if not isinstance(row, Mapping):
            continue
        market_id = str(row.get("market_id", ""))
        if not market_id:
            continue
        reasons[market_id] = tuple(str(reason) for reason in row.get("reasons", []))
    return reasons


def load_runtime_preferred_market_ids(report_path: str | Path) -> tuple[str, ...]:
    decoded = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    market_rows = decoded.get("market_rows", [])
    if not isinstance(market_rows, list):
        return ()
    preferred_ids: list[str] = []
    for row in market_rows:
        if not isinstance(row, Mapping):
            continue
        market_id = str(row.get("market_id", "")).strip()
        action = str(row.get("recommended_action", "")).strip()
        if market_id and action == "tradable_market":
            preferred_ids.append(market_id)
    return tuple(preferred_ids)


def generate_crypto_market_selection_report(
    *,
    snapshot_path: str | Path,
    underlying_states: Mapping[str, CryptoUnderlyingState],
    event_path: str | Path | None = None,
    events: Sequence[Mapping[str, object]] | None = None,
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
        events=events,
        output_dir=output_dir,
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )


def generate_crypto_market_selection_report_from_snapshots(
    *,
    snapshots: Sequence[MarketSnapshot],
    snapshot_label: str,
    underlying_states: Mapping[str, CryptoUnderlyingState],
    event_path: str | Path | None = None,
    events: Sequence[Mapping[str, object]] | None = None,
    output_dir: str | Path | None = None,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
) -> CryptoMarketSelectionReport:
    baseline_preset, resolved_barrier_model_config, resolved_fusion_model_config, resolved_residual_model_config = resolve_crypto_calibration_model_configs(
        barrier_model_config=barrier_model_config,
        fusion_model_config=fusion_model_config,
    )
    active_snapshots = tuple(snapshot for snapshot in snapshots if not _is_resolved_snapshot(snapshot))
    latest_by_market_id: dict[str, MarketSnapshot] = {
        snapshot.market_id: snapshot for snapshot in active_snapshots
    }
    fair_values = compute_crypto_phase1_fair_values_from_snapshots(
        snapshots=active_snapshots,
        underlying_states=underlying_states,
        barrier_model_config=resolved_barrier_model_config,
        fusion_model_config=resolved_fusion_model_config,
        residual_model_config=resolved_residual_model_config,
    )
    fair_values_by_market_id = {item.market_id: item for item in fair_values}
    event_counts_by_market_id = _event_counts_by_market_id(event_path=event_path, events=events)

    market_rows: list[CryptoMarketSelectionRow] = []
    grouped_rows: dict[str, list[CryptoMarketSelectionRow]] = {}
    for market_id, fair_value in sorted(fair_values_by_market_id.items()):
        snapshot = latest_by_market_id.get(market_id)
        normalized = normalize_crypto_market(snapshot) if snapshot is not None else None
        if snapshot is None or normalized is None or _is_resolved_snapshot(snapshot):
            continue
        entry_cost_bps = parse_float(fair_value.supporting_values, "entry_cost_bps") or 0.0
        net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
        runtime_policy = _runtime_tradability_policy(
            underlying=normalized.underlying,
            event_family=normalized.event_family,
        )
        trade_side = _trade_side_from_probabilities(
            observed_probability=fair_value.observed_probability or 0.0,
            fair_probability=fair_value.fair_probability,
        )
        spread_bps = _spread_bps(snapshot, side=trade_side)
        top_book_depth = _top_book_depth(snapshot, side=trade_side)
        nearby_book_depth = _nearby_book_depth(snapshot, side=trade_side)
        quote_age_seconds = _quote_age_seconds(snapshot)
        accepting_orders = _accepting_orders(snapshot)
        market_event_counts = event_counts_by_market_id.get(market_id, {})
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
            spread_bps=spread_bps,
            liquidity_score=snapshot.liquidity_score,
            tick_size=snapshot.tick_size,
            min_order_size=snapshot.min_order_size,
            top_book_depth=top_book_depth,
            nearby_book_depth=nearby_book_depth,
            quote_age_seconds=quote_age_seconds,
            signal_count=market_event_counts.get("signal.generated", 0),
            submitted_order_count=market_event_counts.get("order.submitted", 0),
            filled_order_count=market_event_counts.get("order.filled", 0),
            expired_order_count=market_event_counts.get("order.expired", 0),
            recommended_action=_market_action(
                observed_probability=fair_value.observed_probability or 0.0,
                fair_probability=fair_value.fair_probability,
                net_edge_bps=net_edge_bps,
                entry_cost_bps=entry_cost_bps,
                spread_bps=spread_bps,
                liquidity_score=snapshot.liquidity_score,
                top_book_depth=top_book_depth,
                nearby_book_depth=nearby_book_depth,
                quote_age_seconds=quote_age_seconds,
                accepting_orders=accepting_orders,
                min_order_size=snapshot.min_order_size,
                policy=runtime_policy,
                signal_count=market_event_counts.get("signal.generated", 0),
                submitted_order_count=market_event_counts.get("order.submitted", 0),
                filled_order_count=market_event_counts.get("order.filled", 0),
                expired_order_count=market_event_counts.get("order.expired", 0),
            ),
            reasons=_market_reasons(
                observed_probability=fair_value.observed_probability or 0.0,
                fair_probability=fair_value.fair_probability,
                net_edge_bps=net_edge_bps,
                entry_cost_bps=entry_cost_bps,
                spread_bps=spread_bps,
                liquidity_score=snapshot.liquidity_score,
                top_book_depth=top_book_depth,
                nearby_book_depth=nearby_book_depth,
                quote_age_seconds=quote_age_seconds,
                accepting_orders=accepting_orders,
                min_order_size=snapshot.min_order_size,
                policy=runtime_policy,
                signal_count=market_event_counts.get("signal.generated", 0),
                submitted_order_count=market_event_counts.get("order.submitted", 0),
                filled_order_count=market_event_counts.get("order.filled", 0),
                expired_order_count=market_event_counts.get("order.expired", 0),
            ),
            profit_quality_score=_market_profit_quality_score(
                net_edge_bps=net_edge_bps,
                entry_cost_bps=entry_cost_bps,
                liquidity_score=snapshot.liquidity_score,
                recommended_action=_market_action(
                    observed_probability=fair_value.observed_probability or 0.0,
                    fair_probability=fair_value.fair_probability,
                    net_edge_bps=net_edge_bps,
                    entry_cost_bps=entry_cost_bps,
                    spread_bps=spread_bps,
                    liquidity_score=snapshot.liquidity_score,
                    top_book_depth=top_book_depth,
                    nearby_book_depth=nearby_book_depth,
                    quote_age_seconds=quote_age_seconds,
                    accepting_orders=accepting_orders,
                    min_order_size=snapshot.min_order_size,
                    policy=runtime_policy,
                    signal_count=market_event_counts.get("signal.generated", 0),
                    submitted_order_count=market_event_counts.get("order.submitted", 0),
                    filled_order_count=market_event_counts.get("order.filled", 0),
                    expired_order_count=market_event_counts.get("order.expired", 0),
                ),
                signal_count=market_event_counts.get("signal.generated", 0),
                filled_order_count=market_event_counts.get("order.filled", 0),
                expired_order_count=market_event_counts.get("order.expired", 0),
            ),
        )
        market_rows.append(row)
        grouped_rows.setdefault(row.series_key, []).append(row)

    unsorted_series_reports = [
        _build_series_report(
            series_key=series_key,
            rows=rows,
            event_counts_by_market_id=event_counts_by_market_id,
        )
        for series_key, rows in grouped_rows.items()
    ]
    ranked_series_reports = sorted(
        unsorted_series_reports,
        key=lambda item: (-item.profit_quality_score, item.recommended_action, item.series_key),
    )
    series_reports = tuple(
        CryptoSeriesSelectionReport(
            series_key=series.series_key,
            underlying=series.underlying,
            event_family=series.event_family,
            market_count=series.market_count,
            runtime_actionable_market_count=series.runtime_actionable_market_count,
            positive_net_edge_count=series.positive_net_edge_count,
            mean_net_edge_bps=series.mean_net_edge_bps,
            median_net_edge_bps=series.median_net_edge_bps,
            mean_entry_cost_bps=series.mean_entry_cost_bps,
            min_liquidity_score=series.min_liquidity_score,
            signal_count=series.signal_count,
            submitted_order_count=series.submitted_order_count,
            filled_order_count=series.filled_order_count,
            expired_order_count=series.expired_order_count,
            recommended_action=series.recommended_action,
            reasons=series.reasons,
            profit_quality_score=series.profit_quality_score,
            selection_rank=index + 1,
        )
        for index, series in enumerate(ranked_series_reports)
    )
    report = CryptoMarketSelectionReport(
        generated_at=datetime.now(tz=timezone.utc),
        snapshot_path=snapshot_label,
        model_parameters={
            "baseline_preset": baseline_preset.preset_id,
            "baseline_candidate": baseline_preset.candidate_name,
            "barrier_steepness": resolved_barrier_model_config.steepness,
            "fusion_barrier_weight": resolved_fusion_model_config.barrier_weight,
            "fusion_surface_weight": resolved_fusion_model_config.surface_weight,
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
                f"- runtime_actionable_market_count: {series.runtime_actionable_market_count}",
                f"- positive_net_edge_count: {series.positive_net_edge_count}",
                f"- mean_net_edge_bps: {series.mean_net_edge_bps:.2f}",
                f"- median_net_edge_bps: {series.median_net_edge_bps:.2f}",
                f"- mean_entry_cost_bps: {series.mean_entry_cost_bps:.2f}",
                f"- min_liquidity_score: {series.min_liquidity_score:.4f}",
                f"- signal_count: {series.signal_count}",
                f"- submitted_order_count: {series.submitted_order_count}",
                f"- filled_order_count: {series.filled_order_count}",
                f"- expired_order_count: {series.expired_order_count}",
                f"- profit_quality_score: {series.profit_quality_score:.4f}",
                f"- selection_rank: {series.selection_rank}",
                f"- recommended_action: {series.recommended_action}",
                f"- reasons: {', '.join(series.reasons) if series.reasons else 'none'}",
                "",
            ]
        )
    lines.extend(["## Market Rows", ""])
    for row in report.market_rows:
        lines.extend(
            [
                f"- {row.market_id}: series_key={row.series_key}, instrument_key={row.instrument_key}, action={row.recommended_action}, reasons={', '.join(row.reasons) if row.reasons else 'none'}",
                f"  net_edge_bps={row.net_edge_bps:.2f}, entry_cost_bps={row.entry_cost_bps:.2f}, spread_bps={_format_optional_metric(row.spread_bps)}, liquidity_score={row.liquidity_score:.4f}, profit_quality_score={row.profit_quality_score:.4f}",
                f"  top_book_depth={_format_optional_metric(row.top_book_depth)}, nearby_book_depth={_format_optional_metric(row.nearby_book_depth)}, quote_age_seconds={_format_optional_metric(row.quote_age_seconds)}",
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
    runtime_actionable_market_count = sum(1 for row in ordered if row.recommended_action in {"tradable_market", "selective_market"})
    positive_net_edge_count = sum(1 for row in ordered if row.net_edge_bps > 0)
    mean_net_edge_bps = mean(row.net_edge_bps for row in ordered)
    median_net_edge_bps = median(row.net_edge_bps for row in ordered)
    mean_entry_cost_bps = mean(row.entry_cost_bps for row in ordered)
    min_liquidity_score = min(row.liquidity_score for row in ordered)
    signal_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("signal.generated", 0) for row in ordered)
    submitted_order_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("order.submitted", 0) for row in ordered)
    filled_order_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("order.filled", 0) for row in ordered)
    expired_order_count = sum(event_counts_by_market_id.get(row.market_id, {}).get("order.expired", 0) for row in ordered)
    repeated_execution_no_fill = _has_execution_no_fill(
        signal_count=signal_count,
        submitted_order_count=submitted_order_count,
        filled_order_count=filled_order_count,
        expired_order_count=expired_order_count,
    )
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
    if repeated_execution_no_fill:
        reasons.append("execution_no_fill")
    if runtime_actionable_market_count == 0:
        reasons.append("no_runtime_actionable_markets")

    if positive_net_edge_count == 0 and mean_net_edge_bps <= -750:
        recommended_action = "skip_series"
    elif repeated_execution_no_fill:
        recommended_action = "watch_only"
    elif runtime_actionable_market_count == 0:
        recommended_action = "watch_only"
    elif positive_net_edge_count == 0:
        recommended_action = "watch_only"
    elif positive_net_edge_count < len(ordered):
        recommended_action = "selective_only"
    else:
        recommended_action = "tradable"

    first = ordered[0]
    market_profit_quality_score = round(mean(row.profit_quality_score for row in ordered), 4)
    return CryptoSeriesSelectionReport(
        series_key=series_key,
        underlying=first.underlying,
        event_family=first.event_family,
        market_count=len(ordered),
        runtime_actionable_market_count=runtime_actionable_market_count,
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
        profit_quality_score=market_profit_quality_score,
        selection_rank=0,
    )


def _market_profit_quality_score(
    *,
    net_edge_bps: float,
    entry_cost_bps: float,
    liquidity_score: float,
    recommended_action: str,
    signal_count: int,
    filled_order_count: int,
    expired_order_count: int,
) -> float:
    edge_score = min(max((net_edge_bps + 50.0) / 150.0, 0.0), 1.0)
    cost_score = max(0.0, 1.0 - min(entry_cost_bps, 150.0) / 150.0)
    action_score = {
        "tradable_market": 1.0,
        "selective_market": 0.75,
        "watch_market": 0.35,
        "skip_market": 0.0,
    }.get(recommended_action, 0.0)
    execution_score = 0.5
    if signal_count > 0:
        if filled_order_count > 0:
            execution_score = 1.0
        elif expired_order_count > 0:
            execution_score = 0.2
    score = (
        0.4 * edge_score
        + 0.25 * cost_score
        + 0.2 * min(max(liquidity_score, 0.0), 1.0)
        + 0.1 * execution_score
        + 0.05 * action_score
    )
    return round(min(max(score, 0.0), 1.0), 4)


def _market_action(
    *,
    observed_probability: float,
    fair_probability: float,
    net_edge_bps: float,
    entry_cost_bps: float,
    spread_bps: float | None,
    liquidity_score: float,
    top_book_depth: float | None,
    nearby_book_depth: float | None,
    quote_age_seconds: float | None,
    accepting_orders: bool | None,
    min_order_size: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
    signal_count: int,
    submitted_order_count: int,
    filled_order_count: int,
    expired_order_count: int,
) -> str:
    repeated_execution_no_fill = _has_execution_no_fill(
        signal_count=signal_count,
        submitted_order_count=submitted_order_count,
        filled_order_count=filled_order_count,
        expired_order_count=expired_order_count,
        min_expired_orders=policy.execution_no_fill_min_expired_orders,
    )
    if accepting_orders is False:
        return "skip_market"
    if _is_stale_quote(quote_age_seconds=quote_age_seconds, policy=policy):
        return "watch_market"
    if repeated_execution_no_fill:
        return "watch_market"
    if net_edge_bps <= -750:
        return "skip_market"
    if net_edge_bps <= 0:
        return "watch_market"
    if _entry_contract_price(
        observed_probability=observed_probability,
        fair_probability=fair_probability,
    ) < policy.min_tradeable_contract_price:
        return "watch_market"
    thin_top_book = _is_thin_top_book(
        top_book_depth=top_book_depth,
        min_order_size=min_order_size,
        policy=policy,
    )
    thin_nearby_depth = _is_thin_nearby_depth(
        nearby_book_depth=nearby_book_depth,
        min_order_size=min_order_size,
        policy=policy,
    )
    resilient_nearby_depth = _has_resilient_nearby_depth(
        nearby_book_depth=nearby_book_depth,
        min_order_size=min_order_size,
        policy=policy,
    )
    if thin_nearby_depth or (thin_top_book and not resilient_nearby_depth):
        return "watch_market"
    if liquidity_score < 0.95 and policy.watch_thin_liquidity:
        return "watch_market"
    if (
        thin_top_book
        or entry_cost_bps > 75
        or liquidity_score < 0.95
        or _is_wide_runtime_spread(spread_bps=spread_bps, policy=policy)
    ):
        return "selective_market"
    return "tradable_market"


def _market_reasons(
    *,
    observed_probability: float,
    fair_probability: float,
    net_edge_bps: float,
    entry_cost_bps: float,
    spread_bps: float | None,
    liquidity_score: float,
    top_book_depth: float | None,
    nearby_book_depth: float | None,
    quote_age_seconds: float | None,
    accepting_orders: bool | None,
    min_order_size: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
    signal_count: int,
    submitted_order_count: int,
    filled_order_count: int,
    expired_order_count: int,
) -> tuple[str, ...]:
    reasons: list[str] = []
    repeated_execution_no_fill = _has_execution_no_fill(
        signal_count=signal_count,
        submitted_order_count=submitted_order_count,
        filled_order_count=filled_order_count,
        expired_order_count=expired_order_count,
        min_expired_orders=policy.execution_no_fill_min_expired_orders,
    )
    if accepting_orders is False:
        reasons.append("orders_disabled")
    if _is_stale_quote(quote_age_seconds=quote_age_seconds, policy=policy):
        reasons.append("stale_quote")
    if repeated_execution_no_fill:
        reasons.append("execution_no_fill")
    if net_edge_bps <= -1000:
        reasons.append("deep_negative_edge")
    elif net_edge_bps <= 0:
        reasons.append("negative_edge")
    if _entry_contract_price(
        observed_probability=observed_probability,
        fair_probability=fair_probability,
    ) < policy.min_tradeable_contract_price:
        reasons.append("contract_price_too_low")
    if _is_wide_runtime_spread(spread_bps=spread_bps, policy=policy):
        reasons.append("wide_runtime_spread")
    if entry_cost_bps > 75:
        reasons.append("wide_spread")
    if _is_thin_top_book(
        top_book_depth=top_book_depth,
        min_order_size=min_order_size,
        policy=policy,
    ):
        reasons.append("thin_top_book")
    if _is_thin_nearby_depth(
        nearby_book_depth=nearby_book_depth,
        min_order_size=min_order_size,
        policy=policy,
    ):
        reasons.append("thin_nearby_depth")
    if liquidity_score < 0.95:
        reasons.append("thin_liquidity")
    return tuple(reasons)


def _series_has_runtime_actionable_market(
    *,
    report: CryptoMarketSelectionReport,
    series_key: str,
) -> bool:
    return any(
        row.series_key == series_key
        and row.recommended_action in {"tradable_market", "selective_market"}
        and not any(reason in _HARD_RUNTIME_BLOCK_REASONS for reason in row.reasons)
        for row in report.market_rows
    )


def _has_execution_no_fill(
    *,
    signal_count: int,
    submitted_order_count: int,
    filled_order_count: int,
    expired_order_count: int,
    min_expired_orders: int = _EXECUTION_NO_FILL_MIN_EXPIRED_ORDERS,
) -> bool:
    return (
        signal_count > 0
        and submitted_order_count > 0
        and filled_order_count == 0
        and expired_order_count >= max(1, int(min_expired_orders))
    )


def _decoded_series_has_runtime_actionable_market(
    *,
    series_key: str,
    market_rows: object,
) -> bool:
    if not isinstance(market_rows, list):
        return False
    for row in market_rows:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("series_key", "")) != series_key:
            continue
        if str(row.get("recommended_action", "")) not in {"tradable_market", "selective_market"}:
            continue
        reasons = tuple(str(reason) for reason in row.get("reasons", []))
        if not any(reason in _HARD_RUNTIME_BLOCK_REASONS for reason in reasons):
            return True
    return False


def _runtime_tradability_policy(*, underlying: str, event_family: str) -> CryptoRuntimeTradabilityPolicy:
    if underlying == "BTC" and event_family == "reach":
        return CryptoRuntimeTradabilityPolicy(
            max_runtime_spread_bps=250.0,
            min_top_book_depth=15.0,
            min_nearby_book_depth=100.0,
            max_quote_age_seconds=780.0,
            min_tradeable_contract_price=0.30,
            watch_thin_liquidity=False,
            execution_no_fill_min_expired_orders=3,
        )
    if underlying == "BTC" and event_family == "dip":
        return CryptoRuntimeTradabilityPolicy(
            max_runtime_spread_bps=250.0,
            min_top_book_depth=5.0,
            min_nearby_book_depth=50.0,
            max_quote_age_seconds=780.0,
            min_tradeable_contract_price=0.35,
            watch_thin_liquidity=True,
            execution_no_fill_min_expired_orders=3,
        )
    if underlying == "ETH" and event_family == "reach":
        return CryptoRuntimeTradabilityPolicy(
            max_runtime_spread_bps=225.0,
            min_top_book_depth=5.0,
            min_nearby_book_depth=25.0,
            max_quote_age_seconds=180.0,
            min_tradeable_contract_price=0.05,
        )
    return CryptoRuntimeTradabilityPolicy(
        max_runtime_spread_bps=225.0,
        min_top_book_depth=5.0,
        min_nearby_book_depth=25.0,
        max_quote_age_seconds=180.0,
        min_tradeable_contract_price=0.05,
    )


def _entry_contract_price(*, observed_probability: float, fair_probability: float) -> float:
    if _trade_side_from_probabilities(
        observed_probability=observed_probability,
        fair_probability=fair_probability,
    ) == SignalSide.BUY_YES:
        return observed_probability
    return 1.0 - observed_probability


def _trade_side_from_probabilities(*, observed_probability: float, fair_probability: float) -> SignalSide:
    if fair_probability >= observed_probability:
        return SignalSide.BUY_YES
    return SignalSide.BUY_NO


def _spread_bps(snapshot: MarketSnapshot, *, side: SignalSide) -> float | None:
    best_bid, best_ask = _book_quotes(snapshot=snapshot, side=side)
    if best_bid is None or best_ask is None:
        return None
    return max(0.0, (best_ask - best_bid) * 10000.0)


def _top_book_depth(snapshot: MarketSnapshot, *, side: SignalSide) -> float | None:
    bid_size, ask_size = _book_sizes(snapshot=snapshot, side=side)
    if bid_size is not None and ask_size is not None:
        return min(bid_size, ask_size)
    bid_levels, ask_levels = _book_levels(snapshot=snapshot, side=side)
    if bid_levels and ask_levels:
        return min(bid_levels[0].size, ask_levels[0].size)
    return None


def _nearby_book_depth(snapshot: MarketSnapshot, *, side: SignalSide, level_count: int = 3) -> float | None:
    bid_levels, ask_levels = _book_levels(snapshot=snapshot, side=side)
    if bid_levels and ask_levels:
        bid_depth = sum(level.size for level in bid_levels[:level_count])
        ask_depth = sum(level.size for level in ask_levels[:level_count])
        return min(bid_depth, ask_depth)
    top_book_depth = _top_book_depth(snapshot, side=side)
    if top_book_depth is None:
        return None
    return top_book_depth


def _book_quotes(snapshot: MarketSnapshot, *, side: SignalSide) -> tuple[float | None, float | None]:
    if side == SignalSide.BUY_NO:
        return snapshot.best_bid_no, snapshot.best_ask_no
    return snapshot.best_bid_yes, snapshot.best_ask_yes


def _book_sizes(snapshot: MarketSnapshot, *, side: SignalSide) -> tuple[float | None, float | None]:
    if side == SignalSide.BUY_NO:
        return snapshot.best_bid_no_size, snapshot.best_ask_no_size
    return snapshot.best_bid_yes_size, snapshot.best_ask_yes_size


def _book_levels(snapshot: MarketSnapshot, *, side: SignalSide):
    if side == SignalSide.BUY_NO:
        return snapshot.no_bid_levels, snapshot.no_ask_levels
    return snapshot.yes_bid_levels, snapshot.yes_ask_levels


def _quote_age_seconds(snapshot: MarketSnapshot) -> float | None:
    for key in ("clob_timestamp", "updated_at"):
        raw_value = snapshot.metadata.get(key, "")
        if not raw_value:
            continue
        try:
            observed_at = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        age_seconds = (snapshot.timestamp - observed_at).total_seconds()
        return max(0.0, age_seconds)
    return None


def _accepting_orders(snapshot: MarketSnapshot) -> bool | None:
    raw_value = snapshot.metadata.get("accepting_orders", "")
    if not raw_value:
        return None
    normalized = raw_value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _is_stale_quote(
    *,
    quote_age_seconds: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
) -> bool:
    return quote_age_seconds is not None and quote_age_seconds > policy.max_quote_age_seconds


def _is_wide_runtime_spread(
    *,
    spread_bps: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
) -> bool:
    return spread_bps is not None and spread_bps > policy.max_runtime_spread_bps


def _is_thin_top_book(
    *,
    top_book_depth: float | None,
    min_order_size: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
) -> bool:
    if top_book_depth is None:
        return False
    minimum_depth = max(min_order_size or 0.0, policy.min_top_book_depth)
    return top_book_depth < minimum_depth


def _is_thin_nearby_depth(
    *,
    nearby_book_depth: float | None,
    min_order_size: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
) -> bool:
    if nearby_book_depth is None:
        return False
    minimum_depth = max((min_order_size or 0.0) * 3.0, policy.min_nearby_book_depth)
    return nearby_book_depth < minimum_depth


def _has_resilient_nearby_depth(
    *,
    nearby_book_depth: float | None,
    min_order_size: float | None,
    policy: CryptoRuntimeTradabilityPolicy,
) -> bool:
    if nearby_book_depth is None:
        return False
    robust_depth = max((min_order_size or 0.0) * 10.0, policy.min_nearby_book_depth * 2.0)
    return nearby_book_depth >= robust_depth


def _is_resolved_snapshot(snapshot: MarketSnapshot) -> bool:
    if snapshot.resolution_time is None:
        return False
    return snapshot.resolution_time.astimezone(timezone.utc) <= snapshot.timestamp.astimezone(timezone.utc)


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value


def _format_optional_metric(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def _event_counts_by_market_id(
    *,
    event_path: str | Path | None = None,
    events: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if events is not None:
        for decoded in events:
            _accumulate_event_count(counts=counts, decoded=decoded)
    if event_path is not None:
        with Path(event_path).open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                decoded = json.loads(line)
                _accumulate_event_count(counts=counts, decoded=decoded)
    return counts


def _accumulate_event_count(
    *,
    counts: dict[str, dict[str, int]],
    decoded: Mapping[str, object],
) -> None:
    event_type = str(decoded.get("event_type", ""))
    payload = decoded.get("payload", {})
    if not isinstance(payload, Mapping):
        return
    market_id = str(payload.get("market_id", ""))
    if not market_id or not event_type:
        return
    bucket = counts.setdefault(market_id, {})
    bucket[event_type] = bucket.get(event_type, 0) + 1
