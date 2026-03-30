"""Compact latest-ops decision artifact generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.ops_one_page import OpsOnePage


@dataclass(slots=True, frozen=True)
class OpsDecision:
    triage_action: str
    triage_reason: str
    overall_action: str
    overall_decision: str
    next_step: str
    rollback_target: str | None
    recommended_attention: str
    strategy_mode: str
    strategy_primary_board: str | None
    strategy_next_step: str
    strategy_cycle_status: str
    strategy_cycle_next_step: str


def build_ops_decision(page: OpsOnePage) -> OpsDecision:
    return OpsDecision(
        triage_action=page.triage_action,
        triage_reason=page.triage_reason,
        overall_action=page.console.overall_action,
        overall_decision=page.console.overall_decision,
        next_step=page.console.next_step,
        rollback_target=page.console.rollback_target,
        recommended_attention=page.control_panel.recommended_attention,
        strategy_mode=page.control_panel.strategy_mode,
        strategy_primary_board=(page.control_panel.strategy_primary_board or None),
        strategy_next_step=page.control_panel.strategy_next_step,
        strategy_cycle_status=page.control_panel.strategy_cycle_status,
        strategy_cycle_next_step=page.control_panel.strategy_cycle_next_step,
    )


def format_ops_decision(decision: OpsDecision) -> str:
    lines = [
        "# Ops Decision",
        "",
        f"- triage_action: {decision.triage_action}",
        f"- triage_reason: {decision.triage_reason}",
        f"- overall_action: {decision.overall_action}",
        f"- overall_decision: {decision.overall_decision}",
        f"- next_step: {decision.next_step}",
        f"- rollback_target: {decision.rollback_target or ''}",
        f"- recommended_attention: {decision.recommended_attention}",
        f"- strategy_mode: {decision.strategy_mode}",
        f"- strategy_primary_board: {decision.strategy_primary_board or ''}",
        f"- strategy_next_step: {decision.strategy_next_step}",
        f"- strategy_cycle_status: {decision.strategy_cycle_status}",
        f"- strategy_cycle_next_step: {decision.strategy_cycle_next_step}",
    ]
    return "\n".join(lines) + "\n"


def write_ops_decision(
    *,
    path: str | Path,
    decision: OpsDecision,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_ops_decision(decision), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(asdict(decision), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_ops_decision(path: str | Path) -> OpsDecision | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return OpsDecision(
        triage_action=str(payload.get("triage_action", "")),
        triage_reason=str(payload.get("triage_reason", "")),
        overall_action=str(payload.get("overall_action", "")),
        overall_decision=str(payload.get("overall_decision", "")),
        next_step=str(payload.get("next_step", "")),
        rollback_target=(
            str(payload["rollback_target"])
            if payload.get("rollback_target") not in (None, "")
            else None
        ),
        recommended_attention=str(payload.get("recommended_attention", "")),
        strategy_mode=str(payload.get("strategy_mode", "")),
        strategy_primary_board=(
            str(payload["strategy_primary_board"])
            if payload.get("strategy_primary_board") not in (None, "")
            else None
        ),
        strategy_next_step=str(payload.get("strategy_next_step", "")),
        strategy_cycle_status=str(payload.get("strategy_cycle_status", "")),
        strategy_cycle_next_step=str(payload.get("strategy_cycle_next_step", "")),
    )
