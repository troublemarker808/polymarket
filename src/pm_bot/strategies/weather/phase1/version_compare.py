"""Version comparison artifacts for weather presets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.weather.phase1.auto_experiments import WeatherAutoExperimentsReport
from pm_bot.strategies.weather.phase1.preset_promotion_evidence import WeatherPresetPromotionEvidence


@dataclass(slots=True, frozen=True)
class WeatherVersionComparison:
    current_version: str
    candidate_version: str
    recommendation: str
    strategy_state: str
    metric_wins: dict[str, str]
    targeted_improvement: float
    readiness_delta: float
    total_profit_loss_delta: float
    monotonicity_gap_delta: float
    actionable_market_ratio_delta: float
    reasons: tuple[str, ...]


def build_weather_version_comparison(
    *,
    report: WeatherAutoExperimentsReport,
    evidence: WeatherPresetPromotionEvidence | None = None,
) -> WeatherVersionComparison:
    baseline = report.baseline
    winner = report.winner
    targeted_improvement = float(getattr(winner, "targeted_loss_improvement", 0.0))
    readiness_delta = round(winner.readiness_score - baseline.readiness_score, 4)
    total_profit_loss_delta = round(baseline.total_profit_loss - winner.total_profit_loss, 4)
    monotonicity_gap_delta = round(
        float(getattr(baseline, "average_monotonicity_gap_bps", 0.0))
        - float(getattr(winner, "average_monotonicity_gap_bps", 0.0)),
        4,
    )
    baseline_actionable_ratio = _actionable_market_ratio(baseline)
    winner_actionable_ratio = _actionable_market_ratio(winner)
    actionable_market_ratio_delta = round(winner_actionable_ratio - baseline_actionable_ratio, 4)
    metric_wins = {
        "readiness": winner.variant_name if winner.readiness_score > baseline.readiness_score else baseline.variant_name,
        "profit_loss": winner.variant_name if winner.total_profit_loss < baseline.total_profit_loss else baseline.variant_name,
        "targeted_loss": winner.variant_name if targeted_improvement > 0 else baseline.variant_name,
        "monotonicity": winner.variant_name if monotonicity_gap_delta > 0 else baseline.variant_name,
        "actionable_ratio": winner.variant_name if actionable_market_ratio_delta > 0 else baseline.variant_name,
    }
    reasons: list[str] = []
    if baseline.recommended_action == "pause" or winner.recommended_action == "pause":
        recommendation = "quarantine"
        strategy_state = "quarantined"
        reasons.append("weather baseline or winner remains paused")
    elif (
        targeted_improvement <= 0.01
        and total_profit_loss_delta <= 0.03
        and monotonicity_gap_delta <= 0.0
        and actionable_market_ratio_delta <= 0.0
    ):
        recommendation = "quarantine"
        strategy_state = "quarantined"
        reasons.append("weather candidate fails to improve targeted loss, aggregate profitability, or settlement quality")
    elif report.promotion_decision == "promote_candidate":
        recommendation = "promote"
        strategy_state = "candidate"
        reasons.append("weather candidate clears promotion conditions")
    elif report.promotion_decision == "keep_baseline" and baseline.recommended_action == "proceed":
        recommendation = "keep_current"
        strategy_state = "stable"
        reasons.append("weather baseline remains the strongest stable preset")
    elif targeted_improvement > 0 and (
        readiness_delta >= 0
        or monotonicity_gap_delta > 0
        or actionable_market_ratio_delta > 0
    ):
        recommendation = "keep_current"
        strategy_state = "candidate"
        reasons.append("weather candidate is improving but still needs more repeated evidence")
    else:
        recommendation = "keep_current"
        strategy_state = "degraded"
        reasons.append("weather candidate does not yet improve the recurring loss stack")
    if evidence is not None and not evidence.ready_to_apply and strategy_state == "candidate":
        recommendation = "keep_current"
        strategy_state = "degraded"
        reasons.append("weather promotion evidence is not yet strong enough")
    return WeatherVersionComparison(
        current_version=baseline.variant_name,
        candidate_version=winner.variant_name,
        recommendation=recommendation,
        strategy_state=strategy_state,
        metric_wins=metric_wins,
        targeted_improvement=targeted_improvement,
        readiness_delta=readiness_delta,
        total_profit_loss_delta=total_profit_loss_delta,
        monotonicity_gap_delta=monotonicity_gap_delta,
        actionable_market_ratio_delta=actionable_market_ratio_delta,
        reasons=tuple(reasons),
    )


def format_weather_version_comparison(report: WeatherVersionComparison) -> str:
    lines = [
        "# Weather Version Comparison",
        "",
        f"- current_version: {report.current_version}",
        f"- candidate_version: {report.candidate_version}",
        f"- recommendation: {report.recommendation}",
        f"- strategy_state: {report.strategy_state}",
        f"- targeted_improvement: {report.targeted_improvement:.4f}",
        f"- readiness_delta: {report.readiness_delta:.4f}",
        f"- total_profit_loss_delta: {report.total_profit_loss_delta:.4f}",
        f"- monotonicity_gap_delta: {report.monotonicity_gap_delta:.4f}",
        f"- actionable_market_ratio_delta: {report.actionable_market_ratio_delta:.4f}",
        "",
        "## Metric Wins",
        "",
    ]
    for metric, winner in report.metric_wins.items():
        lines.append(f"- {metric}: {winner}")
    lines.extend(["", "## Reasons", ""])
    lines.extend(f"- {reason}" for reason in report.reasons or ("none",))
    return "\n".join(lines) + "\n"


def write_weather_version_comparison(
    *,
    report: WeatherVersionComparison,
    output_path: str | Path,
) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_weather_version_comparison(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value


def _actionable_market_ratio(scorecard: object) -> float:
    actionable_markets = float(getattr(scorecard, "actionable_markets", 0.0) or 0.0)
    blocked_markets = float(getattr(scorecard, "blocked_markets", 0.0) or 0.0)
    total = actionable_markets + blocked_markets
    return (actionable_markets / total) if total > 0 else 0.0
