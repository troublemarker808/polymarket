"""Sports Phase 1 tradability and closing-line reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import MarketSnapshot
from pm_bot.research.engine import load_market_snapshots
from pm_bot.strategies.sports.phase1.normalization import normalize_sports_market
from pm_bot.strategies.sports.phase1.pricing import (
    estimate_line_dislocation,
    estimate_pregame_fair_value,
)
from pm_bot.strategies.sports.phase1.validation import review_closing_line


@dataclass(slots=True, frozen=True)
class SportsMarketSelectionRow:
    market_id: str
    league: str
    market_family: str
    event_key: str
    action: str
    confidence: float
    observed_probability: float
    fair_probability: float
    raw_edge_bps: float
    context_adjusted_edge_bps: float
    minutes_to_start: float
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class SportsMarketSelectionReport:
    snapshot_path: str
    report_path: str
    actionable_markets: int
    watch_only_markets: int
    blocked_markets: int
    rows: tuple[SportsMarketSelectionRow, ...]


@dataclass(slots=True, frozen=True)
class SportsClosingLineRow:
    market_id: str
    league: str
    market_family: str
    open_probability: float
    fair_probability: float
    close_probability: float
    clv_bps: float
    moved_toward_fair: bool


@dataclass(slots=True, frozen=True)
class SportsClosingLineReport:
    snapshot_path: str
    report_path: str
    reviewed_markets: int
    moved_toward_fair: int
    average_clv_bps: float
    rows: tuple[SportsClosingLineRow, ...]


@dataclass(slots=True, frozen=True)
class SportsEventScorecardRow:
    event_key: str
    league: str
    market_family: str
    market_count: int
    actionable_markets: int
    blocked_markets: int
    average_context_edge_bps: float
    average_clv_bps: float
    recommended_action: str


@dataclass(slots=True, frozen=True)
class SportsEventScorecardReport:
    snapshot_path: str
    report_path: str
    reviewed_events: int
    actionable_events: int
    review_events: int
    rows: tuple[SportsEventScorecardRow, ...]


def generate_sports_market_selection_report(
    *,
    snapshot_path: str | Path,
    output_dir: str | Path | None = None,
) -> SportsMarketSelectionReport:
    snapshots = load_market_snapshots(snapshot_path)
    latest_by_market: dict[str, MarketSnapshot] = {}
    for snapshot in snapshots:
        if str(snapshot.category.value) != "sports":
            continue
        latest_by_market[snapshot.market_id] = snapshot

    rows: list[SportsMarketSelectionRow] = []
    for snapshot in latest_by_market.values():
        normalized = normalize_sports_market(snapshot)
        league = str(snapshot.metadata.get("league", snapshot.metadata.get("sport", ""))).strip().lower()
        market_family = str(snapshot.metadata.get("market_family", "")).strip().lower() or "unknown"
        if normalized is None:
            observed_probability = snapshot.last_traded_price or snapshot.best_ask_yes or snapshot.best_bid_yes or 0.0
            action, reasons = _unsupported_selection_action(snapshot)
            rows.append(
                SportsMarketSelectionRow(
                    market_id=snapshot.market_id,
                    league=league or "unknown",
                    market_family=market_family,
                    event_key=str(snapshot.metadata.get("event_title", snapshot.slug)),
                    action=action,
                    confidence=0.0,
                    observed_probability=observed_probability,
                    fair_probability=observed_probability,
                    raw_edge_bps=0.0,
                    context_adjusted_edge_bps=0.0,
                    minutes_to_start=0.0,
                    reasons=reasons,
                )
            )
            continue
        fair_value = _fair_value_from_snapshot(snapshot)
        action, reasons = _selection_action(
            league=normalized.league,
            market_family=normalized.market_family,
            confidence=fair_value.confidence,
            context_adjusted_edge_bps=float(fair_value.supporting_values.get("context_adjusted_edge_bps", 0.0) or 0.0),
            minutes_to_start=float(fair_value.supporting_values.get("minutes_to_start", 0.0) or 0.0),
        )
        rows.append(
            SportsMarketSelectionRow(
                market_id=snapshot.market_id,
                league=normalized.league,
                market_family=normalized.market_family,
                event_key=normalized.event_key,
                action=action,
                confidence=fair_value.confidence,
                observed_probability=fair_value.observed_probability or fair_value.fair_probability,
                fair_probability=fair_value.fair_probability,
                raw_edge_bps=float(fair_value.supporting_values.get("raw_edge_bps", 0.0) or 0.0),
                context_adjusted_edge_bps=float(fair_value.supporting_values.get("context_adjusted_edge_bps", 0.0) or 0.0),
                minutes_to_start=float(fair_value.supporting_values.get("minutes_to_start", 0.0) or 0.0),
                reasons=reasons,
            )
        )

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.action, -row.context_adjusted_edge_bps, row.market_id)))
    output_path = _resolve_report_path(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        filename="sports_market_selection_report.md",
    )
    report = SportsMarketSelectionReport(
        snapshot_path=str(Path(snapshot_path)),
        report_path=str(output_path),
        actionable_markets=sum(1 for row in ordered_rows if row.action == "actionable"),
        watch_only_markets=sum(1 for row in ordered_rows if row.action == "watch_only"),
        blocked_markets=sum(1 for row in ordered_rows if row.action == "blocked"),
        rows=ordered_rows,
    )
    _write_report(
        path=output_path,
        markdown=format_sports_market_selection_report(report),
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


def format_sports_market_selection_report(report: SportsMarketSelectionReport) -> str:
    lines = [
        "# Sports Market Selection Report",
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
            + f"{row.market_id}:{row.league}:{row.market_family}:"
            + f"action={row.action}:"
            + f"edge={row.context_adjusted_edge_bps:.1f}:"
            + f"confidence={row.confidence:.2f}:"
            + f"minutes_to_start={row.minutes_to_start:.1f}:"
            + f"reasons={','.join(row.reasons)}"
        )
    return "\n".join(lines) + "\n"


def generate_sports_closing_line_report(
    *,
    snapshot_path: str | Path,
    output_dir: str | Path | None = None,
) -> SportsClosingLineReport:
    snapshots = load_market_snapshots(snapshot_path)
    by_event: dict[str, list[MarketSnapshot]] = {}
    for snapshot in snapshots:
        normalized = normalize_sports_market(snapshot)
        if normalized is None:
            continue
        by_event.setdefault(normalized.event_key, []).append(snapshot)

    rows: list[SportsClosingLineRow] = []
    for event_key, event_snapshots in by_event.items():
        ordered = sorted(event_snapshots, key=lambda item: item.timestamp)
        if len(ordered) < 2:
            continue
        normalized = normalize_sports_market(ordered[-1])
        if normalized is None:
            continue
        open_probability = ordered[0].last_traded_price or ordered[0].best_ask_yes or ordered[0].best_bid_yes
        close_probability = ordered[-1].last_traded_price or ordered[-1].best_ask_yes or ordered[-1].best_bid_yes
        if open_probability is None or close_probability is None:
            continue
        fair_value = _fair_value_from_snapshot(ordered[-1])
        review = review_closing_line(
            market_id=event_key,
            open_probability=open_probability,
            fair_probability=fair_value.fair_probability,
            close_probability=close_probability,
        )
        rows.append(
            SportsClosingLineRow(
                market_id=event_key,
                league=normalized.league,
                market_family=normalized.market_family,
                open_probability=review.open_probability,
                fair_probability=review.fair_probability,
                close_probability=review.close_probability,
                clv_bps=review.clv_bps,
                moved_toward_fair=review.moved_toward_fair,
            )
        )

    ordered_rows = tuple(sorted(rows, key=lambda row: (-row.clv_bps, row.market_id)))
    output_path = _resolve_report_path(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        filename="sports_closing_line_report.md",
    )
    report = SportsClosingLineReport(
        snapshot_path=str(Path(snapshot_path)),
        report_path=str(output_path),
        reviewed_markets=len(ordered_rows),
        moved_toward_fair=sum(1 for row in ordered_rows if row.moved_toward_fair),
        average_clv_bps=(
            sum(row.clv_bps for row in ordered_rows) / len(ordered_rows)
            if ordered_rows
            else 0.0
        ),
        rows=ordered_rows,
    )
    _write_report(
        path=output_path,
        markdown=format_sports_closing_line_report(report),
        payload={
            "snapshot_path": report.snapshot_path,
            "report_path": report.report_path,
            "reviewed_markets": report.reviewed_markets,
            "moved_toward_fair": report.moved_toward_fair,
            "average_clv_bps": report.average_clv_bps,
            "rows": [asdict(row) for row in report.rows],
        },
    )
    return report


def format_sports_closing_line_report(report: SportsClosingLineReport) -> str:
    lines = [
        "# Sports Closing Line Report",
        "",
        f"- snapshot_path: {report.snapshot_path}",
        f"- reviewed_markets: {report.reviewed_markets}",
        f"- moved_toward_fair: {report.moved_toward_fair}",
        f"- average_clv_bps: {report.average_clv_bps:.2f}",
        "",
        "## Markets",
        "",
    ]
    for row in report.rows:
        lines.append(
            "- "
            + f"{row.market_id}:{row.league}:{row.market_family}:"
            + f"open={row.open_probability:.3f}:"
            + f"fair={row.fair_probability:.3f}:"
            + f"close={row.close_probability:.3f}:"
            + f"clv_bps={row.clv_bps:.1f}:"
            + f"moved_toward_fair={str(row.moved_toward_fair).lower()}"
        )
    return "\n".join(lines) + "\n"


def generate_sports_event_scorecard_report(
    *,
    snapshot_path: str | Path,
    output_dir: str | Path | None = None,
) -> SportsEventScorecardReport:
    selection_report = generate_sports_market_selection_report(
        snapshot_path=snapshot_path,
        output_dir=output_dir,
    )
    closing_line_report = generate_sports_closing_line_report(
        snapshot_path=snapshot_path,
        output_dir=output_dir,
    )
    clv_by_event = {row.market_id: row.clv_bps for row in closing_line_report.rows}
    grouped: dict[str, list[SportsMarketSelectionRow]] = {}
    for row in selection_report.rows:
        grouped.setdefault(row.event_key, []).append(row)

    rows: list[SportsEventScorecardRow] = []
    for event_key, event_rows in grouped.items():
        league = event_rows[0].league
        market_family = event_rows[0].market_family
        avg_edge = sum(row.context_adjusted_edge_bps for row in event_rows) / len(event_rows)
        avg_clv = clv_by_event.get(event_key, 0.0)
        actionable_markets = sum(1 for row in event_rows if row.action == "actionable")
        blocked_markets = sum(1 for row in event_rows if row.action == "blocked")
        recommended_action = _event_scorecard_action(
            actionable_markets=actionable_markets,
            average_context_edge_bps=avg_edge,
            average_clv_bps=avg_clv,
        )
        rows.append(
            SportsEventScorecardRow(
                event_key=event_key,
                league=league,
                market_family=market_family,
                market_count=len(event_rows),
                actionable_markets=actionable_markets,
                blocked_markets=blocked_markets,
                average_context_edge_bps=avg_edge,
                average_clv_bps=avg_clv,
                recommended_action=recommended_action,
            )
        )

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.recommended_action, -row.average_context_edge_bps, row.event_key)))
    output_path = _resolve_report_path(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        filename="sports_event_scorecard_report.md",
    )
    report = SportsEventScorecardReport(
        snapshot_path=str(Path(snapshot_path)),
        report_path=str(output_path),
        reviewed_events=len(ordered_rows),
        actionable_events=sum(1 for row in ordered_rows if row.recommended_action == "proceed"),
        review_events=sum(1 for row in ordered_rows if row.recommended_action == "review"),
        rows=ordered_rows,
    )
    _write_report(
        path=output_path,
        markdown=format_sports_event_scorecard_report(report),
        payload={
            "snapshot_path": report.snapshot_path,
            "report_path": report.report_path,
            "reviewed_events": report.reviewed_events,
            "actionable_events": report.actionable_events,
            "review_events": report.review_events,
            "rows": [asdict(row) for row in report.rows],
        },
    )
    return report


def format_sports_event_scorecard_report(report: SportsEventScorecardReport) -> str:
    lines = [
        "# Sports Event Scorecard Report",
        "",
        f"- snapshot_path: {report.snapshot_path}",
        f"- reviewed_events: {report.reviewed_events}",
        f"- actionable_events: {report.actionable_events}",
        f"- review_events: {report.review_events}",
        "",
        "## Events",
        "",
    ]
    for row in report.rows:
        lines.append(
            "- "
            + f"{row.event_key}:{row.league}:{row.market_family}:"
            + f"markets={row.market_count}:"
            + f"actionable={row.actionable_markets}:"
            + f"blocked={row.blocked_markets}:"
            + f"avg_edge_bps={row.average_context_edge_bps:.1f}:"
            + f"avg_clv_bps={row.average_clv_bps:.1f}:"
            + f"recommended_action={row.recommended_action}"
        )
    return "\n".join(lines) + "\n"


def _selection_action(
    *,
    league: str,
    market_family: str,
    confidence: float,
    context_adjusted_edge_bps: float,
    minutes_to_start: float,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if league != "nba":
        reasons.append("unsupported_league")
    if market_family != "pregame_moneyline":
        reasons.append("unsupported_market_family")
    if minutes_to_start <= 20:
        reasons.append("too_close_to_start")
    elif minutes_to_start > 24 * 60:
        reasons.append("too_early")
    if confidence < 0.62:
        reasons.append("low_confidence")
    if context_adjusted_edge_bps < 120:
        reasons.append("insufficient_net_edge")
    if not reasons:
        return "actionable", ("nba_pregame_moneyline", "edge_survives_context")
    if any(reason in {"unsupported_league", "unsupported_market_family", "too_close_to_start"} for reason in reasons):
        return "blocked", tuple(reasons)
    return "watch_only", tuple(reasons)


def _event_scorecard_action(
    *,
    actionable_markets: int,
    average_context_edge_bps: float,
    average_clv_bps: float,
) -> str:
    if actionable_markets >= 1 and average_context_edge_bps >= 120 and average_clv_bps >= 0:
        return "proceed"
    return "review"


def _unsupported_selection_action(snapshot: MarketSnapshot) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    league = str(snapshot.metadata.get("league", snapshot.metadata.get("sport", ""))).strip().lower()
    if league != "nba":
        reasons.append("unsupported_league")
    if any(
        key in snapshot.metadata
        for key in ("live_yes_probability", "live_model_yes_probability", "live_state_updated_at")
    ) or str(snapshot.metadata.get("game_status", "")).strip().lower() in {"in_progress", "final", "halftime"}:
        reasons.append("live_market")
    market_family = str(snapshot.metadata.get("market_family", "")).strip().lower()
    if market_family not in {"moneyline", ""}:
        reasons.append("unsupported_market_family")
    if not reasons:
        reasons.append("unsupported_market_shape")
    return "blocked", tuple(reasons)


def _fair_value_from_snapshot(snapshot: MarketSnapshot) -> FairValueEstimate:
    from pm_bot.strategies.sports.phase1.anchors import estimate_odds_anchor
    from pm_bot.strategies.sports.phase1.features import build_pregame_features
    from pm_bot.strategies.sports.phase1.pricing import to_fair_value_estimate

    normalized = normalize_sports_market(snapshot)
    if normalized is None:
        raise ValueError(f"Unsupported sports market: {snapshot.market_id}")
    anchor = estimate_odds_anchor(snapshot)
    features = build_pregame_features(
        snapshot=snapshot,
        event=normalized,
        anchor_probability=anchor.anchor_probability if anchor is not None else None,
    )
    if features is None:
        raise ValueError(f"Unable to build sports features for market: {snapshot.market_id}")
    fair_value = estimate_pregame_fair_value(features)
    dislocation = estimate_line_dislocation(
        observed_probability=features.observed_probability,
        fair_value=fair_value,
    )
    return to_fair_value_estimate(
        features=features,
        fair_value=fair_value,
        dislocation=dislocation,
    )


def _selection_row_payload(row: SportsMarketSelectionRow) -> dict[str, object]:
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
