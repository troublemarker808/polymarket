"""Final scorecard helpers for weather phase1 maturity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.strategies.weather.phase1.reports import (
    WeatherMarketSelectionReport,
    WeatherRunScorecardReport,
    WeatherSettlementAuditReport,
    generate_weather_market_selection_report,
    generate_weather_run_scorecard_report,
    generate_weather_settlement_audit_report,
)


@dataclass(slots=True, frozen=True)
class WeatherFinalScorecard:
    snapshot_path: str
    report_path: str
    recommended_action: str
    readiness_score: float
    tradable_subset_status: str
    settlement_audit_status: str
    actionable_series: int
    review_series: int
    average_monotonicity_gap_bps: float
    actionable_markets: int
    blocked_markets: int
    profit_focus: str
    secondary_profit_focus: str
    loss_ranking: tuple[str, ...]
    selection_quality_score: float
    settlement_quality_score: float
    execution_quality_score: float
    selection_loss: float
    settlement_loss: float
    execution_loss: float
    total_profit_loss: float
    tuning_priority: str
    tuning_actions: tuple[str, ...]
    reasons: tuple[str, ...]


def generate_weather_final_scorecard(
    *,
    snapshot_path: str | Path,
    forecast_payloads: list[dict[str, object]],
    skill_payloads: list[dict[str, object]],
    output_dir: str | Path | None = None,
) -> WeatherFinalScorecard:
    selection = generate_weather_market_selection_report(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
        output_dir=output_dir,
    )
    settlement = generate_weather_settlement_audit_report(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
        output_dir=output_dir,
    )
    run_scorecard = generate_weather_run_scorecard_report(
        snapshot_path=snapshot_path,
        forecast_payloads=forecast_payloads,
        skill_payloads=skill_payloads,
        output_dir=output_dir,
    )
    return build_weather_final_scorecard(
        selection_report=selection,
        settlement_report=settlement,
        run_scorecard_report=run_scorecard,
        output_dir=output_dir,
    )


def build_weather_final_scorecard(
    *,
    selection_report: WeatherMarketSelectionReport,
    settlement_report: WeatherSettlementAuditReport,
    run_scorecard_report: WeatherRunScorecardReport,
    output_dir: str | Path | None = None,
) -> WeatherFinalScorecard:
    reasons: list[str] = []
    if selection_report.actionable_markets <= 0:
        reasons.append("no actionable weather markets")
    if run_scorecard_report.actionable_series <= 0:
        reasons.append("no actionable weather runs")
    if settlement_report.reviewed_markets <= 0:
        reasons.append("no settlement audit evidence")
    elif settlement_report.average_monotonicity_gap_bps > 150:
        reasons.append("strip monotonicity gap exceeds weather threshold")
    if run_scorecard_report.review_series > run_scorecard_report.actionable_series:
        reasons.append("review runs dominate actionable runs")

    if not reasons:
        recommended_action = "proceed"
    elif settlement_report.average_monotonicity_gap_bps > 150 or selection_report.actionable_markets <= 0:
        recommended_action = "pause"
    else:
        recommended_action = "review"

    score = 1.0
    if selection_report.actionable_markets <= 0:
        score -= 0.35
    if run_scorecard_report.actionable_series <= 0:
        score -= 0.3
    if settlement_report.reviewed_markets <= 0:
        score -= 0.2
    elif settlement_report.average_monotonicity_gap_bps > 150:
        score -= 0.15
    if run_scorecard_report.review_series > run_scorecard_report.actionable_series:
        score -= 0.1

    selection_quality_score = _selection_quality_score(selection_report=selection_report, run_scorecard_report=run_scorecard_report)
    settlement_quality_score = _settlement_quality_score(settlement_report=settlement_report)
    execution_quality_score = _execution_quality_score(run_scorecard_report=run_scorecard_report)
    component_scores = {
        "selection": selection_quality_score,
        "settlement": settlement_quality_score,
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
    scorecard = WeatherFinalScorecard(
        snapshot_path=selection_report.snapshot_path,
        report_path=str(_resolve_report_path(output_dir=output_dir, snapshot_path=selection_report.snapshot_path)),
        recommended_action=recommended_action,
        readiness_score=max(0.0, round(score, 4)),
        tradable_subset_status=(
            "ready"
            if selection_report.actionable_markets > 0 and run_scorecard_report.actionable_series > 0
            else "thin"
        ),
        settlement_audit_status=(
            "ready"
            if settlement_report.reviewed_markets > 0 and settlement_report.average_monotonicity_gap_bps <= 150
            else "fragile"
        ),
        actionable_series=run_scorecard_report.actionable_series,
        review_series=run_scorecard_report.review_series,
        average_monotonicity_gap_bps=settlement_report.average_monotonicity_gap_bps,
        actionable_markets=selection_report.actionable_markets,
        blocked_markets=selection_report.blocked_markets,
        profit_focus=profit_focus,
        secondary_profit_focus=secondary_profit_focus,
        loss_ranking=loss_ranking,
        selection_quality_score=selection_quality_score,
        settlement_quality_score=settlement_quality_score,
        execution_quality_score=execution_quality_score,
        selection_loss=dict(ordered_losses)["selection"],
        settlement_loss=dict(ordered_losses)["settlement"],
        execution_loss=dict(ordered_losses)["execution"],
        total_profit_loss=round(sum(loss for _component, loss in ordered_losses), 4),
        tuning_priority=tuning_priority,
        tuning_actions=tuning_actions,
        reasons=tuple(reasons) if reasons else ("weather threshold evidence is stable enough to proceed",),
    )
    _write_report(scorecard=scorecard, path=Path(scorecard.report_path))
    return scorecard


def format_weather_final_scorecard(scorecard: WeatherFinalScorecard) -> str:
    lines = [
        "# Weather Final Scorecard",
        "",
        f"- snapshot_path: {scorecard.snapshot_path}",
        f"- recommended_action: {scorecard.recommended_action}",
        f"- readiness_score: {scorecard.readiness_score:.4f}",
        f"- tradable_subset_status: {scorecard.tradable_subset_status}",
        f"- settlement_audit_status: {scorecard.settlement_audit_status}",
        f"- actionable_series: {scorecard.actionable_series}",
        f"- review_series: {scorecard.review_series}",
        f"- average_monotonicity_gap_bps: {scorecard.average_monotonicity_gap_bps:.2f}",
        f"- actionable_markets: {scorecard.actionable_markets}",
        f"- blocked_markets: {scorecard.blocked_markets}",
        "",
        "## Profit Components",
        "",
        f"- profit_focus: {scorecard.profit_focus}",
        f"- secondary_profit_focus: {scorecard.secondary_profit_focus}",
        f"- loss_ranking: {', '.join(scorecard.loss_ranking)}",
        f"- selection_quality_score: {scorecard.selection_quality_score:.4f}",
        f"- settlement_quality_score: {scorecard.settlement_quality_score:.4f}",
        f"- execution_quality_score: {scorecard.execution_quality_score:.4f}",
        f"- selection_loss: {scorecard.selection_loss:.4f}",
        f"- settlement_loss: {scorecard.settlement_loss:.4f}",
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
    selection_report: WeatherMarketSelectionReport,
    run_scorecard_report: WeatherRunScorecardReport,
) -> float:
    market_total = selection_report.actionable_markets + selection_report.blocked_markets
    run_total = run_scorecard_report.actionable_series + run_scorecard_report.review_series
    market_score = (
        selection_report.actionable_markets / market_total
        if market_total > 0
        else 0.0
    )
    run_score = (
        run_scorecard_report.actionable_series / run_total
        if run_total > 0
        else 0.0
    )
    return round(min(1.0, max(0.0, (market_score + run_score) / 2.0)), 4)


def _settlement_quality_score(*, settlement_report: WeatherSettlementAuditReport) -> float:
    if settlement_report.reviewed_markets <= 0:
        return 0.0
    gap = min(abs(settlement_report.average_monotonicity_gap_bps), 250.0)
    return round(max(0.0, 1.0 - (gap / 250.0)), 4)


def _execution_quality_score(*, run_scorecard_report: WeatherRunScorecardReport) -> float:
    run_total = run_scorecard_report.actionable_series + run_scorecard_report.review_series
    if run_total <= 0:
        return 0.0
    review_ratio = run_scorecard_report.review_series / run_total
    return round(max(0.0, 1.0 - review_ratio), 4)


def _tuning_actions(profit_focus: str) -> tuple[str, ...]:
    if profit_focus == "selection":
        return (
            "tighten weather selection toward stable threshold series with cleaner liquidity",
            "raise minimum entry gates for fragile market families before adding more flow",
        )
    if profit_focus == "settlement":
        return (
            "review settlement mapping and strip monotonicity on repeated fragile runs",
            "test earlier official-forecast switching for unstable settlement windows",
        )
    return (
        "restrict execution to stronger forecast windows",
        "reduce noisy run combinations before increasing weather participation",
    )


def _resolve_report_path(*, output_dir: str | Path | None, snapshot_path: str | Path) -> Path:
    base_dir = Path(output_dir) if output_dir is not None else Path(snapshot_path).parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "weather_final_scorecard.md"


def _write_report(*, scorecard: WeatherFinalScorecard, path: Path) -> None:
    path.write_text(format_weather_final_scorecard(scorecard), encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(asdict(scorecard), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
