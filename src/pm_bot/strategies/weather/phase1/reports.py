"""Weather Phase 1 tradability and settlement audit reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot
from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.common import implied_yes_probability
from pm_bot.strategies.weather.phase1.forecasts import ingest_forecast_runs
from pm_bot.strategies.weather.phase1.fusion import fuse_weather_fair_value, to_fair_value_estimate
from pm_bot.strategies.weather.phase1.models import WeatherMarketDefinition
from pm_bot.strategies.weather.phase1.normalization import normalize_weather_market
from pm_bot.strategies.weather.phase1.pricing import (
    build_forecast_distribution,
    build_weather_peer_probability_map,
    estimate_strip_consistency,
    estimate_threshold_probability,
)
from pm_bot.strategies.weather.phase1.skill import apply_bias_corrections, load_model_skill_store


@dataclass(slots=True, frozen=True)
class WeatherMarketSelectionRow:
    market_id: str
    event_family: str
    series_key: str
    station_id: str
    settlement_source: str
    action: str
    confidence: float
    observed_probability: float
    fair_probability: float
    edge_bps: float
    weighted_sigma_f: float
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class WeatherMarketSelectionReport:
    snapshot_path: str
    report_path: str
    actionable_markets: int
    watch_only_markets: int
    blocked_markets: int
    rows: tuple[WeatherMarketSelectionRow, ...]


@dataclass(slots=True, frozen=True)
class WeatherSettlementAuditRow:
    market_id: str
    station_id: str
    settlement_source: str
    threshold: float
    comparator: str
    threshold_probability: float
    strip_probability: float | None
    monotonicity_gap_bps: float
    weighted_mean_temp_f: float
    weighted_sigma_f: float
    deterministic_mapping: bool


@dataclass(slots=True, frozen=True)
class WeatherSettlementAuditReport:
    snapshot_path: str
    report_path: str
    reviewed_markets: int
    deterministic_markets: int
    average_monotonicity_gap_bps: float
    rows: tuple[WeatherSettlementAuditRow, ...]


@dataclass(slots=True, frozen=True)
class WeatherRunScorecardRow:
    series_key: str
    station_id: str
    settlement_source: str
    market_count: int
    actionable_markets: int
    average_edge_bps: float
    average_sigma_f: float
    average_monotonicity_gap_bps: float
    recommended_action: str


@dataclass(slots=True, frozen=True)
class WeatherRunScorecardReport:
    snapshot_path: str
    report_path: str
    reviewed_series: int
    actionable_series: int
    review_series: int
    rows: tuple[WeatherRunScorecardRow, ...]


def generate_weather_market_selection_report(
    *,
    snapshot_path: str | Path,
    forecast_payloads: list[dict[str, object]],
    skill_payloads: list[dict[str, object]],
    output_dir: str | Path | None = None,
) -> WeatherMarketSelectionReport:
    snapshots = load_market_snapshots(snapshot_path)
    latest_by_market: dict[str, MarketSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.category != Category.WEATHER:
            continue
        latest_by_market[snapshot.market_id] = snapshot

    rows: list[WeatherMarketSelectionRow] = []
    for snapshot in latest_by_market.values():
        normalized = normalize_weather_market(snapshot)
        observed_probability = implied_yes_probability(snapshot) or snapshot.last_traded_price or 0.0
        if normalized is None:
            rows.append(
                WeatherMarketSelectionRow(
                    market_id=snapshot.market_id,
                    event_family="unsupported",
                    series_key=str(snapshot.metadata.get("event_slug", snapshot.slug)),
                    station_id="unknown",
                    settlement_source="unknown",
                    action="blocked",
                    confidence=0.0,
                    observed_probability=observed_probability,
                    fair_probability=observed_probability,
                    edge_bps=0.0,
                    weighted_sigma_f=0.0,
                    reasons=_unsupported_weather_reasons(snapshot),
                )
            )
            continue
        fair_value, distribution = _weather_market_fair_value(
            snapshot=snapshot,
            market=normalized,
            forecast_payloads=forecast_payloads,
            skill_payloads=skill_payloads,
            peer_rows=(),
        )
        if fair_value is None or distribution is None:
            rows.append(
                WeatherMarketSelectionRow(
                    market_id=snapshot.market_id,
                    event_family=normalized.event_family,
                    series_key=normalized.series_key,
                    station_id=normalized.location.station_id,
                    settlement_source=normalized.location.settlement_source,
                    action="blocked",
                    confidence=0.0,
                    observed_probability=observed_probability,
                    fair_probability=observed_probability,
                    edge_bps=0.0,
                    weighted_sigma_f=0.0,
                    reasons=("missing_forecast_support",),
                )
            )
            continue
        action, reasons = _selection_action(
            event_family=normalized.event_family,
            confidence=fair_value.confidence,
            edge_bps=(fair_value.fair_probability - observed_probability) * 10000,
            weighted_sigma_f=distribution.weighted_sigma_f,
        )
        rows.append(
            WeatherMarketSelectionRow(
                market_id=snapshot.market_id,
                event_family=normalized.event_family,
                series_key=normalized.series_key,
                station_id=normalized.location.station_id,
                settlement_source=normalized.location.settlement_source,
                action=action,
                confidence=fair_value.confidence,
                observed_probability=observed_probability,
                fair_probability=fair_value.fair_probability,
                edge_bps=(fair_value.fair_probability - observed_probability) * 10000,
                weighted_sigma_f=distribution.weighted_sigma_f,
                reasons=reasons,
            )
        )

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.action, -abs(row.edge_bps), row.market_id)))
    output_path = _resolve_report_path(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        filename="weather_market_selection_report.md",
    )
    report = WeatherMarketSelectionReport(
        snapshot_path=str(Path(snapshot_path)),
        report_path=str(output_path),
        actionable_markets=sum(1 for row in ordered_rows if row.action == "actionable"),
        watch_only_markets=sum(1 for row in ordered_rows if row.action == "watch_only"),
        blocked_markets=sum(1 for row in ordered_rows if row.action == "blocked"),
        rows=ordered_rows,
    )
    _write_report(
        path=output_path,
        markdown=format_weather_market_selection_report(report),
        payload={
            "snapshot_path": report.snapshot_path,
            "report_path": report.report_path,
            "actionable_markets": report.actionable_markets,
            "watch_only_markets": report.watch_only_markets,
            "blocked_markets": report.blocked_markets,
            "rows": [_selection_row_payload(row) for row in report.rows],
        },
    )
    return report


def format_weather_market_selection_report(report: WeatherMarketSelectionReport) -> str:
    lines = [
        "# Weather Market Selection Report",
        "",
        f"- snapshot_path: {report.snapshot_path}",
        f"- actionable_markets: {report.actionable_markets}",
        f"- watch_only_markets: {report.watch_only_markets}",
        f"- blocked_markets: {report.blocked_markets}",
        "",
        "## Markets",
        "",
    ]
    for row in report.rows:
        lines.append(
            "- "
            + f"{row.market_id}:{row.station_id}:{row.event_family}:"
            + f"action={row.action}:"
            + f"edge_bps={row.edge_bps:.1f}:"
            + f"confidence={row.confidence:.2f}:"
            + f"sigma_f={row.weighted_sigma_f:.2f}:"
            + f"reasons={','.join(row.reasons)}"
        )
    return "\n".join(lines) + "\n"


def generate_weather_settlement_audit_report(
    *,
    snapshot_path: str | Path,
    forecast_payloads: list[dict[str, object]],
    skill_payloads: list[dict[str, object]],
    output_dir: str | Path | None = None,
) -> WeatherSettlementAuditReport:
    snapshots = load_market_snapshots(snapshot_path)
    latest_by_market: dict[str, MarketSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.category != Category.WEATHER:
            continue
        latest_by_market[snapshot.market_id] = snapshot

    normalized_rows: list[tuple[MarketSnapshot, WeatherMarketDefinition]] = []
    for snapshot in latest_by_market.values():
        normalized = normalize_weather_market(snapshot)
        if normalized is not None:
            normalized_rows.append((snapshot, normalized))

    by_series: dict[str, list[tuple[MarketSnapshot, WeatherMarketDefinition]]] = {}
    for snapshot, market in normalized_rows:
        by_series.setdefault(market.series_key, []).append((snapshot, market))

    rows: list[WeatherSettlementAuditRow] = []
    for series_rows in by_series.values():
        ordered_markets = tuple(
            market
            for _, market in sorted(series_rows, key=lambda item: item[1].threshold)
        )
        peer_probabilities = tuple(
            (market, probability)
            for snapshot, market in series_rows
            if (probability := implied_yes_probability(snapshot)) is not None
        )
        peer_probability_map = build_weather_peer_probability_map(
            markets=ordered_markets,
            snapshots=peer_probabilities,
        )
        for snapshot, market in series_rows:
            observed_probability = implied_yes_probability(snapshot)
            if observed_probability is None:
                continue
            fair_value, distribution = _weather_market_fair_value(
                snapshot=snapshot,
                market=market,
                forecast_payloads=forecast_payloads,
                skill_payloads=skill_payloads,
                peer_rows=series_rows,
                peer_probability_map=peer_probability_map,
                ordered_markets=ordered_markets,
            )
            if fair_value is None or distribution is None:
                continue
            rows.append(
                WeatherSettlementAuditRow(
                    market_id=market.normalized.market_id,
                    station_id=market.location.station_id,
                    settlement_source=market.location.settlement_source,
                    threshold=market.threshold,
                    comparator=market.comparator,
                    threshold_probability=_numeric_supporting_value(
                        fair_value=fair_value,
                        key="threshold_probability",
                    ),
                    strip_probability=(
                        _numeric_supporting_value(
                            fair_value=fair_value,
                            key="strip_probability",
                        )
                        if fair_value.supporting_values.get("strip_probability") is not None
                        else None
                    ),
                    monotonicity_gap_bps=_numeric_supporting_value(
                        fair_value=fair_value,
                        key="monotonicity_gap_bps",
                    ),
                    weighted_mean_temp_f=_numeric_supporting_value(
                        fair_value=fair_value,
                        key="weighted_mean_temp_f",
                    ),
                    weighted_sigma_f=_numeric_supporting_value(
                        fair_value=fair_value,
                        key="weighted_sigma_f",
                    ),
                    deterministic_mapping=bool(market.location.station_id and market.location.settlement_source),
                )
            )

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.station_id, row.threshold, row.market_id)))
    output_path = _resolve_report_path(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        filename="weather_settlement_audit_report.md",
    )
    report = WeatherSettlementAuditReport(
        snapshot_path=str(Path(snapshot_path)),
        report_path=str(output_path),
        reviewed_markets=len(ordered_rows),
        deterministic_markets=sum(1 for row in ordered_rows if row.deterministic_mapping),
        average_monotonicity_gap_bps=(
            sum(row.monotonicity_gap_bps for row in ordered_rows) / len(ordered_rows)
            if ordered_rows
            else 0.0
        ),
        rows=ordered_rows,
    )
    _write_report(
        path=output_path,
        markdown=format_weather_settlement_audit_report(report),
        payload={
            "snapshot_path": report.snapshot_path,
            "report_path": report.report_path,
            "reviewed_markets": report.reviewed_markets,
            "deterministic_markets": report.deterministic_markets,
            "average_monotonicity_gap_bps": report.average_monotonicity_gap_bps,
            "rows": [asdict(row) for row in report.rows],
        },
    )
    return report


def format_weather_settlement_audit_report(report: WeatherSettlementAuditReport) -> str:
    lines = [
        "# Weather Settlement Audit Report",
        "",
        f"- snapshot_path: {report.snapshot_path}",
        f"- reviewed_markets: {report.reviewed_markets}",
        f"- deterministic_markets: {report.deterministic_markets}",
        f"- average_monotonicity_gap_bps: {report.average_monotonicity_gap_bps:.2f}",
        "",
        "## Markets",
        "",
    ]
    for row in report.rows:
        lines.append(
            "- "
            + f"{row.market_id}:{row.station_id}:{row.settlement_source}:"
            + f"threshold={row.threshold:.1f}:{row.comparator}:"
            + f"threshold_prob={row.threshold_probability:.3f}:"
            + f"strip_prob={_optional_float(row.strip_probability)}:"
            + f"monotonicity_gap_bps={row.monotonicity_gap_bps:.1f}:"
            + f"deterministic_mapping={str(row.deterministic_mapping).lower()}"
        )
    return "\n".join(lines) + "\n"


def generate_weather_run_scorecard_report(
    *,
    snapshot_path: str | Path,
    forecast_payloads: list[dict[str, object]],
    skill_payloads: list[dict[str, object]],
    output_dir: str | Path | None = None,
) -> WeatherRunScorecardReport:
    selection_report = generate_weather_market_selection_report(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
        output_dir=output_dir,
    )
    settlement_report = generate_weather_settlement_audit_report(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
        output_dir=output_dir,
    )
    settlement_by_market = {row.market_id: row for row in settlement_report.rows}
    grouped: dict[str, list[WeatherMarketSelectionRow]] = {}
    for row in selection_report.rows:
        grouped.setdefault(row.series_key, []).append(row)

    rows: list[WeatherRunScorecardRow] = []
    for series_key, series_rows in grouped.items():
        first = series_rows[0]
        related_settlement = [
            settlement_by_market[row.market_id]
            for row in series_rows
            if row.market_id in settlement_by_market
        ]
        avg_edge = sum(abs(row.edge_bps) for row in series_rows) / len(series_rows)
        avg_sigma = sum(row.weighted_sigma_f for row in series_rows) / len(series_rows)
        avg_gap = (
            sum(row.monotonicity_gap_bps for row in related_settlement) / len(related_settlement)
            if related_settlement
            else 0.0
        )
        actionable_markets = sum(1 for row in series_rows if row.action == "actionable")
        recommended_action = _run_scorecard_action(
            actionable_markets=actionable_markets,
            average_edge_bps=avg_edge,
            average_sigma_f=avg_sigma,
            average_monotonicity_gap_bps=avg_gap,
        )
        rows.append(
            WeatherRunScorecardRow(
                series_key=series_key,
                station_id=first.station_id,
                settlement_source=first.settlement_source,
                market_count=len(series_rows),
                actionable_markets=actionable_markets,
                average_edge_bps=avg_edge,
                average_sigma_f=avg_sigma,
                average_monotonicity_gap_bps=avg_gap,
                recommended_action=recommended_action,
            )
        )

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.recommended_action, -row.average_edge_bps, row.series_key)))
    output_path = _resolve_report_path(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        filename="weather_run_scorecard_report.md",
    )
    report = WeatherRunScorecardReport(
        snapshot_path=str(Path(snapshot_path)),
        report_path=str(output_path),
        reviewed_series=len(ordered_rows),
        actionable_series=sum(1 for row in ordered_rows if row.recommended_action == "proceed"),
        review_series=sum(1 for row in ordered_rows if row.recommended_action == "review"),
        rows=ordered_rows,
    )
    _write_report(
        path=output_path,
        markdown=format_weather_run_scorecard_report(report),
        payload={
            "snapshot_path": report.snapshot_path,
            "report_path": report.report_path,
            "reviewed_series": report.reviewed_series,
            "actionable_series": report.actionable_series,
            "review_series": report.review_series,
            "rows": [asdict(row) for row in report.rows],
        },
    )
    return report


def format_weather_run_scorecard_report(report: WeatherRunScorecardReport) -> str:
    lines = [
        "# Weather Run Scorecard Report",
        "",
        f"- snapshot_path: {report.snapshot_path}",
        f"- reviewed_series: {report.reviewed_series}",
        f"- actionable_series: {report.actionable_series}",
        f"- review_series: {report.review_series}",
        "",
        "## Series",
        "",
    ]
    for row in report.rows:
        lines.append(
            "- "
            + f"{row.series_key}:{row.station_id}:{row.settlement_source}:"
            + f"markets={row.market_count}:"
            + f"actionable={row.actionable_markets}:"
            + f"avg_edge_bps={row.average_edge_bps:.1f}:"
            + f"avg_sigma_f={row.average_sigma_f:.2f}:"
            + f"avg_monotonicity_gap_bps={row.average_monotonicity_gap_bps:.1f}:"
            + f"recommended_action={row.recommended_action}"
        )
    return "\n".join(lines) + "\n"


def _weather_market_fair_value(
    *,
    snapshot: MarketSnapshot,
    market: WeatherMarketDefinition,
    forecast_payloads: list[dict[str, object]],
    skill_payloads: list[dict[str, object]],
    peer_rows: Any,
    peer_probability_map: dict[str, float] | None = None,
    ordered_markets: tuple[WeatherMarketDefinition, ...] | None = None,
) -> tuple[FairValueEstimate | None, Any | None]:
    observed_probability = implied_yes_probability(snapshot)
    if observed_probability is None:
        return None, None
    forecast_runs = ingest_forecast_runs(
        market=market,
        run_payloads=forecast_payloads,
    )
    if not forecast_runs:
        return None, None
    skill_store = load_model_skill_store(
        market=market,
        skill_payloads=skill_payloads,
    )
    corrected = apply_bias_corrections(
        market=market,
        forecast_runs=forecast_runs,
        skill_store=skill_store,
    )
    distribution = build_forecast_distribution(
        market=market,
        corrected_forecasts=corrected,
    )
    if distribution is None:
        return None, None
    threshold_estimate = estimate_threshold_probability(
        market=market,
        distribution=distribution,
    )
    if ordered_markets is None:
        ordered_markets = (market,)
    if peer_probability_map is None:
        peer_probability_map = build_weather_peer_probability_map(
            markets=ordered_markets,
            snapshots=((market, observed_probability),),
        )
    strip_estimate = estimate_strip_consistency(
        series_key=market.series_key,
        market=market,
        observed_probability=observed_probability,
        peer_probabilities=peer_probability_map,
        ordered_markets=ordered_markets,
    )
    fused = fuse_weather_fair_value(
        market=market,
        distribution=distribution,
        threshold_estimate=threshold_estimate,
        strip_estimate=strip_estimate,
        observed_probability=observed_probability,
    )
    fair_value = to_fair_value_estimate(
        market=market,
        fused=fused,
        distribution=distribution,
        observed_probability=observed_probability,
    )
    fair_value.supporting_values["monotonicity_gap_bps"] = strip_estimate.monotonicity_gap_bps
    return fair_value, distribution


def _selection_action(
    *,
    event_family: str,
    confidence: float,
    edge_bps: float,
    weighted_sigma_f: float,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if event_family != "daily_high_temperature_threshold":
        reasons.append("unsupported_event_family")
    if confidence < 0.65:
        reasons.append("low_confidence")
    if abs(edge_bps) < 120:
        reasons.append("insufficient_net_edge")
    if weighted_sigma_f > 4.5:
        reasons.append("wide_distribution")
    if not reasons:
        return "actionable", ("daily_high_temperature_threshold", "edge_survives_distribution")
    if "unsupported_event_family" in reasons:
        return "blocked", tuple(reasons)
    return "watch_only", tuple(reasons)


def _run_scorecard_action(
    *,
    actionable_markets: int,
    average_edge_bps: float,
    average_sigma_f: float,
    average_monotonicity_gap_bps: float,
) -> str:
    if actionable_markets >= 1 and average_edge_bps >= 120 and average_sigma_f <= 4.5 and average_monotonicity_gap_bps <= 150:
        return "proceed"
    return "review"


def _unsupported_weather_reasons(snapshot: MarketSnapshot) -> tuple[str, ...]:
    combined = " ".join(
        (
            str(snapshot.metadata.get("question", "")),
            str(snapshot.metadata.get("event_title", "")),
            snapshot.slug,
        )
    ).lower()
    reasons: list[str] = []
    if "high temperature" not in combined:
        reasons.append("unsupported_event_family")
    if not any(token in combined for token in ("above", "over", "below", "under")):
        reasons.append("unsupported_threshold_direction")
    if not reasons:
        reasons.append("unsupported_weather_market")
    return tuple(reasons)


def _selection_row_payload(row: WeatherMarketSelectionRow) -> dict[str, object]:
    payload = asdict(row)
    payload["reasons"] = list(row.reasons)
    return payload


def _resolve_report_path(
    *,
    output_dir: str | Path | None,
    snapshot_path: str | Path,
    filename: str,
) -> Path:
    base_dir = Path(output_dir) if output_dir is not None else Path(snapshot_path).parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / filename


def _write_report(*, path: Path, markdown: str, payload: dict[str, object]) -> None:
    path.write_text(markdown, encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _optional_float(value: float | None) -> str:
    if value is None:
        return "none"
    return f"{value:.3f}"


def _numeric_supporting_value(
    *,
    fair_value: FairValueEstimate,
    key: str,
) -> float:
    value = fair_value.supporting_values.get(key)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return 0.0
