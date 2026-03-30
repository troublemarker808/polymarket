"""Cross-run learning summaries for sports final scorecards."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class SportsLearningReport:
    run_count: int
    recurring_reasons: tuple[str, ...]
    recurring_focuses: tuple[str, ...]
    recurring_secondary_focuses: tuple[str, ...]
    recommended_next_experiment: str
    recommended_actions: tuple[str, ...]
    focus_counts: dict[str, int]
    average_component_losses: dict[str, float]
    recurring_loss_ranking: tuple[str, ...]
    average_clv_bps: float
    average_actionable_market_ratio: float


def build_sports_learning_report(
    *,
    scorecard_paths: list[str | Path],
) -> SportsLearningReport:
    reason_counter: Counter[str] = Counter()
    focus_counter: Counter[str] = Counter()
    secondary_focus_counter: Counter[str] = Counter()
    component_loss_totals: dict[str, float] = {
        "selection": 0.0,
        "pricing": 0.0,
        "execution": 0.0,
    }
    component_loss_counts: dict[str, int] = {key: 0 for key in component_loss_totals}
    clv_total = 0.0
    clv_count = 0
    actionable_market_ratio_total = 0.0
    actionable_market_ratio_count = 0

    for scorecard_path in scorecard_paths:
        payload = _load_payload(scorecard_path)
        for reason in _string_list(payload.get("reasons")):
            reason_counter[reason] += 1
        focus = _infer_focus(payload)
        if focus:
            focus_counter[focus] += 1
        secondary_focus = str(payload.get("secondary_profit_focus", "")).strip()
        if secondary_focus:
            secondary_focus_counter[secondary_focus] += 1
        for component in component_loss_totals:
            loss_value = payload.get(f"{component}_loss")
            if isinstance(loss_value, (int, float)):
                component_loss_totals[component] += float(loss_value)
                component_loss_counts[component] += 1
        average_clv_bps = payload.get("average_clv_bps")
        if isinstance(average_clv_bps, (int, float)):
            clv_total += float(average_clv_bps)
            clv_count += 1
        actionable_markets = payload.get("actionable_markets")
        blocked_markets = payload.get("blocked_markets")
        if isinstance(actionable_markets, int) and isinstance(blocked_markets, int):
            market_total = actionable_markets + blocked_markets
            if market_total > 0:
                actionable_market_ratio_total += actionable_markets / market_total
                actionable_market_ratio_count += 1

    recurring_reasons = tuple(reason for reason, count in reason_counter.items() if count >= 2)
    recurring_focuses = tuple(focus for focus, count in focus_counter.items() if count >= 2)
    recurring_secondary_focuses = tuple(focus for focus, count in secondary_focus_counter.items() if count >= 2)
    average_component_losses = {
        component: round(component_loss_totals[component] / component_loss_counts[component], 4)
        for component in component_loss_totals
        if component_loss_counts[component] > 0
    }
    recurring_loss_ranking = tuple(
        component
        for component, _loss in sorted(
            average_component_losses.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    average_clv_bps = round(clv_total / clv_count, 4) if clv_count > 0 else 0.0
    average_actionable_market_ratio = (
        round(actionable_market_ratio_total / actionable_market_ratio_count, 4)
        if actionable_market_ratio_count > 0
        else 0.0
    )
    recommended_next_experiment = (
        recurring_loss_ranking[0]
        if recurring_loss_ranking
        else (focus_counter.most_common(1)[0][0] if focus_counter else "collect_more_runs")
    )
    recommended_actions = _recommended_actions(recommended_next_experiment)
    return SportsLearningReport(
        run_count=len(scorecard_paths),
        recurring_reasons=recurring_reasons,
        recurring_focuses=recurring_focuses,
        recurring_secondary_focuses=recurring_secondary_focuses,
        recommended_next_experiment=recommended_next_experiment,
        recommended_actions=recommended_actions,
        focus_counts=dict(sorted(focus_counter.items())),
        average_component_losses=average_component_losses,
        recurring_loss_ranking=recurring_loss_ranking,
        average_clv_bps=average_clv_bps,
        average_actionable_market_ratio=average_actionable_market_ratio,
    )


def format_sports_learning_report(report: SportsLearningReport) -> str:
    lines = [
        "# Sports Learning Report",
        "",
        f"- run_count: {report.run_count}",
        f"- recommended_next_experiment: {report.recommended_next_experiment}",
        f"- recurring_focuses: {', '.join(report.recurring_focuses) if report.recurring_focuses else 'none'}",
        f"- recurring_secondary_focuses: {', '.join(report.recurring_secondary_focuses) if report.recurring_secondary_focuses else 'none'}",
        f"- recurring_reasons: {', '.join(report.recurring_reasons) if report.recurring_reasons else 'none'}",
        f"- recurring_loss_ranking: {', '.join(report.recurring_loss_ranking) if report.recurring_loss_ranking else 'none'}",
        f"- average_clv_bps: {report.average_clv_bps:.4f}",
        f"- average_actionable_market_ratio: {report.average_actionable_market_ratio:.4f}",
        "",
        "## Recommended Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in report.recommended_actions)
    lines.extend(["", "## Focus Counts", ""])
    for focus, count in report.focus_counts.items():
        lines.append(f"- {focus}: {count}")
    lines.extend(["", "## Average Component Losses", ""])
    for component, loss in report.average_component_losses.items():
        lines.append(f"- {component}: {loss:.4f}")
    return "\n".join(lines) + "\n"


def write_sports_learning_report(
    *,
    report: SportsLearningReport,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_sports_learning_report(report), encoding="utf-8")
    target_path.with_suffix(".json").write_text(
        json.dumps(asdict(report), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_payload(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _infer_focus(payload: dict[str, Any]) -> str:
    explicit_focus = str(payload.get("profit_focus", "")).strip()
    if explicit_focus:
        return explicit_focus
    tradable_subset_status = str(payload.get("tradable_subset_status", "")).strip()
    closing_line_status = str(payload.get("closing_line_status", "")).strip()
    if tradable_subset_status != "ready":
        return "selection"
    if closing_line_status != "ready":
        return "pricing"
    return "execution"


def _string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _recommended_actions(focus: str) -> tuple[str, ...]:
    if focus == "selection":
        return (
            "tighten sports market selection around actionable pregame subsets",
            "de-prioritize leagues or events that repeatedly fail readiness",
        )
    if focus == "pricing":
        return (
            "review closing-line drift and anchor adjustments for repeated fragile events",
            "compare fair value calibration against event-level CLV outliers",
        )
    if focus == "execution":
        return (
            "keep current sports working preset and collect more event windows",
        )
    return ("collect more sports scorecard runs before changing presets",)
