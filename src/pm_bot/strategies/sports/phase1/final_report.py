"""Final scorecard helpers for sports phase1 maturity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.strategies.sports.phase1.reports import (
    SportsClosingLineReport,
    SportsEventScorecardReport,
    SportsMarketSelectionReport,
    generate_sports_closing_line_report,
    generate_sports_event_scorecard_report,
    generate_sports_market_selection_report,
)


@dataclass(slots=True, frozen=True)
class SportsFinalScorecard:
    snapshot_path: str
    report_path: str
    recommended_action: str
    readiness_score: float
    tradable_subset_status: str
    closing_line_status: str
    actionable_events: int
    review_events: int
    average_clv_bps: float
    actionable_markets: int
    blocked_markets: int
    profit_focus: str
    secondary_profit_focus: str
    loss_ranking: tuple[str, ...]
    selection_quality_score: float
    pricing_quality_score: float
    execution_quality_score: float
    selection_loss: float
    pricing_loss: float
    execution_loss: float
    total_profit_loss: float
    tuning_priority: str
    tuning_actions: tuple[str, ...]
    reasons: tuple[str, ...]


def generate_sports_final_scorecard(
    *,
    snapshot_path: str | Path,
    output_dir: str | Path | None = None,
) -> SportsFinalScorecard:
    selection = generate_sports_market_selection_report(snapshot_path=snapshot_path, output_dir=output_dir)
    closing_line = generate_sports_closing_line_report(snapshot_path=snapshot_path, output_dir=output_dir)
    event_scorecard = generate_sports_event_scorecard_report(snapshot_path=snapshot_path, output_dir=output_dir)
    return build_sports_final_scorecard(
        selection_report=selection,
        closing_line_report=closing_line,
        event_scorecard_report=event_scorecard,
        output_dir=output_dir,
    )


def build_sports_final_scorecard(
    *,
    selection_report: SportsMarketSelectionReport,
    closing_line_report: SportsClosingLineReport,
    event_scorecard_report: SportsEventScorecardReport,
    output_dir: str | Path | None = None,
) -> SportsFinalScorecard:
    reasons: list[str] = []
    if selection_report.actionable_markets <= 0:
        reasons.append("no actionable sports markets")
    if event_scorecard_report.actionable_events <= 0:
        reasons.append("no actionable sports events")
    if closing_line_report.reviewed_markets <= 0:
        reasons.append("no closing-line evidence")
    elif closing_line_report.average_clv_bps < 0:
        reasons.append("closing line moved against sports fair value")
    if event_scorecard_report.review_events > event_scorecard_report.actionable_events:
        reasons.append("review events dominate actionable events")

    if not reasons:
        recommended_action = "proceed"
    elif closing_line_report.average_clv_bps < 0 or selection_report.actionable_markets <= 0:
        recommended_action = "pause"
    else:
        recommended_action = "review"

    score = 1.0
    if selection_report.actionable_markets <= 0:
        score -= 0.35
    if event_scorecard_report.actionable_events <= 0:
        score -= 0.3
    if closing_line_report.reviewed_markets <= 0:
        score -= 0.2
    elif closing_line_report.average_clv_bps < 0:
        score -= 0.15
    if event_scorecard_report.review_events > event_scorecard_report.actionable_events:
        score -= 0.1
    readiness_score = max(0.0, round(score, 4))
    selection_quality_score = _selection_quality_score(selection_report=selection_report, event_scorecard_report=event_scorecard_report)
    pricing_quality_score = _pricing_quality_score(closing_line_report=closing_line_report)
    execution_quality_score = _execution_quality_score(event_scorecard_report=event_scorecard_report)
    component_scores = {
        "selection": selection_quality_score,
        "pricing": pricing_quality_score,
        "execution": execution_quality_score,
    }
    ordered_losses = sorted(
        ((component, round(1.0 - score_value, 4)) for component, score_value in component_scores.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    profit_focus = ordered_losses[0][0]
    loss_ranking = tuple(component for component, _loss in ordered_losses)
    secondary_profit_focus = loss_ranking[1] if len(loss_ranking) > 1 else profit_focus
    tuning_priority = profit_focus
    tuning_actions = _tuning_actions(profit_focus)
    total_profit_loss = round(sum(loss for _component, loss in ordered_losses), 4)

    tradable_subset_status = (
        "ready"
        if selection_report.actionable_markets > 0 and event_scorecard_report.actionable_events > 0
        else "thin"
    )
    closing_line_status = (
        "ready"
        if closing_line_report.reviewed_markets > 0 and closing_line_report.average_clv_bps >= 0
        else "fragile"
    )
    output_path = _resolve_report_path(output_dir=output_dir, snapshot_path=selection_report.snapshot_path)
    scorecard = SportsFinalScorecard(
        snapshot_path=selection_report.snapshot_path,
        report_path=str(output_path),
        recommended_action=recommended_action,
        readiness_score=readiness_score,
        tradable_subset_status=tradable_subset_status,
        closing_line_status=closing_line_status,
        actionable_events=event_scorecard_report.actionable_events,
        review_events=event_scorecard_report.review_events,
        average_clv_bps=closing_line_report.average_clv_bps,
        actionable_markets=selection_report.actionable_markets,
        blocked_markets=selection_report.blocked_markets,
        profit_focus=profit_focus,
        secondary_profit_focus=secondary_profit_focus,
        loss_ranking=loss_ranking,
        selection_quality_score=selection_quality_score,
        pricing_quality_score=pricing_quality_score,
        execution_quality_score=execution_quality_score,
        selection_loss=dict(ordered_losses)["selection"],
        pricing_loss=dict(ordered_losses)["pricing"],
        execution_loss=dict(ordered_losses)["execution"],
        total_profit_loss=total_profit_loss,
        tuning_priority=tuning_priority,
        tuning_actions=tuning_actions,
        reasons=tuple(reasons) if reasons else ("sports pregame moneyline evidence is stable enough to proceed",),
    )
    _write_report(scorecard=scorecard, path=output_path)
    return scorecard


def format_sports_final_scorecard(scorecard: SportsFinalScorecard) -> str:
    lines = [
        "# Sports Final Scorecard",
        "",
        f"- snapshot_path: {scorecard.snapshot_path}",
        f"- recommended_action: {scorecard.recommended_action}",
        f"- readiness_score: {scorecard.readiness_score:.4f}",
        f"- tradable_subset_status: {scorecard.tradable_subset_status}",
        f"- closing_line_status: {scorecard.closing_line_status}",
        f"- actionable_events: {scorecard.actionable_events}",
        f"- review_events: {scorecard.review_events}",
        f"- average_clv_bps: {scorecard.average_clv_bps:.2f}",
        f"- actionable_markets: {scorecard.actionable_markets}",
        f"- blocked_markets: {scorecard.blocked_markets}",
        "",
        "## Profit Components",
        "",
        f"- profit_focus: {scorecard.profit_focus}",
        f"- secondary_profit_focus: {scorecard.secondary_profit_focus}",
        f"- loss_ranking: {', '.join(scorecard.loss_ranking)}",
        f"- selection_quality_score: {scorecard.selection_quality_score:.4f}",
        f"- pricing_quality_score: {scorecard.pricing_quality_score:.4f}",
        f"- execution_quality_score: {scorecard.execution_quality_score:.4f}",
        f"- selection_loss: {scorecard.selection_loss:.4f}",
        f"- pricing_loss: {scorecard.pricing_loss:.4f}",
        f"- execution_loss: {scorecard.execution_loss:.4f}",
        f"- total_profit_loss: {scorecard.total_profit_loss:.4f}",
        f"- tuning_priority: {scorecard.tuning_priority}",
        "",
        "## Tuning Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in scorecard.tuning_actions)
    lines.extend(
        [
            "",
        "## Reasons",
        "",
        ]
    )
    lines.extend(f"- {reason}" for reason in scorecard.reasons)
    return "\n".join(lines) + "\n"


def _selection_quality_score(
    *,
    selection_report: SportsMarketSelectionReport,
    event_scorecard_report: SportsEventScorecardReport,
) -> float:
    market_total = selection_report.actionable_markets + selection_report.blocked_markets
    event_total = event_scorecard_report.actionable_events + event_scorecard_report.review_events
    market_score = (
        selection_report.actionable_markets / market_total
        if market_total > 0
        else 0.0
    )
    event_score = (
        event_scorecard_report.actionable_events / event_total
        if event_total > 0
        else 0.0
    )
    return round(min(1.0, max(0.0, (market_score + event_score) / 2.0)), 4)


def _pricing_quality_score(*, closing_line_report: SportsClosingLineReport) -> float:
    if closing_line_report.reviewed_markets <= 0:
        return 0.0
    if closing_line_report.average_clv_bps >= 0:
        return round(min(1.0, 0.6 + min(closing_line_report.average_clv_bps, 25.0) / 62.5), 4)
    penalty = min(abs(closing_line_report.average_clv_bps), 25.0) / 50.0
    return round(max(0.0, 0.55 - penalty), 4)


def _execution_quality_score(*, event_scorecard_report: SportsEventScorecardReport) -> float:
    event_total = event_scorecard_report.actionable_events + event_scorecard_report.review_events
    if event_total <= 0:
        return 0.0
    review_ratio = event_scorecard_report.review_events / event_total
    return round(max(0.0, 1.0 - review_ratio), 4)


def _tuning_actions(profit_focus: str) -> tuple[str, ...]:
    if profit_focus == "selection":
        return (
            "tighten sports event selection toward consistently actionable NBA pregame subsets",
            "raise the minimum edge gate for recurring thin-event windows",
        )
    if profit_focus == "pricing":
        return (
            "review CLV drift and anchor calibration on repeated fragile events",
            "test stricter pricing gates before adding more order flow",
        )
    return (
        "shorten stale-state handling for late pregame windows",
        "re-test order timing around event start to reduce execution drag",
    )


def _resolve_report_path(*, output_dir: str | Path | None, snapshot_path: str | Path) -> Path:
    base_dir = Path(output_dir) if output_dir is not None else Path(snapshot_path).parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "sports_final_scorecard.md"


def _write_report(*, scorecard: SportsFinalScorecard, path: Path) -> None:
    path.write_text(format_sports_final_scorecard(scorecard), encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(asdict(scorecard), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
