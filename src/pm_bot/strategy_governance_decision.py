"""Compact decision artifact for unified strategy governance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.strategy_change_window import StrategyChangeWindow
from pm_bot.strategy_governance import StrategyGovernanceReport


@dataclass(slots=True, frozen=True)
class StrategyGovernanceDecision:
    governance_action: str
    governance_reason: str
    window_action: str
    first_step: str
    apply_ready_boards: tuple[str, ...]
    rollback_boards: tuple[str, ...]


def build_strategy_governance_decision(
    report: StrategyGovernanceReport,
    window: StrategyChangeWindow,
) -> StrategyGovernanceDecision:
    return StrategyGovernanceDecision(
        governance_action=report.overall_action,
        governance_reason=report.overall_reason,
        window_action=window.window_action,
        first_step=window.first_step,
        apply_ready_boards=report.apply_ready_boards,
        rollback_boards=report.rollback_boards,
    )


def format_strategy_governance_decision(decision: StrategyGovernanceDecision) -> str:
    lines = [
        "# Strategy Governance Decision",
        "",
        f"- governance_action: {decision.governance_action}",
        f"- governance_reason: {decision.governance_reason}",
        f"- window_action: {decision.window_action}",
        f"- first_step: {decision.first_step}",
        f"- apply_ready_boards: {', '.join(decision.apply_ready_boards) if decision.apply_ready_boards else 'none'}",
        f"- rollback_boards: {', '.join(decision.rollback_boards) if decision.rollback_boards else 'none'}",
    ]
    return "\n".join(lines) + "\n"


def write_strategy_governance_decision(
    *,
    path: str | Path,
    decision: StrategyGovernanceDecision,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_strategy_governance_decision(decision), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(asdict(decision), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target
