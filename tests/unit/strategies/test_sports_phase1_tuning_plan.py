from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.sports.phase1.tuning_plan import (
    build_sports_candidate_preset_registry,
    build_sports_tuning_plan,
    format_sports_tuning_plan,
)


def test_build_sports_tuning_plan_produces_selection_variants(tmp_path: Path) -> None:
    scorecard_a = tmp_path / "sports-a.json"
    scorecard_b = tmp_path / "sports-b.json"
    payload = {
        "tradable_subset_status": "thin",
        "closing_line_status": "ready",
        "selection_loss": 0.55,
        "pricing_loss": 0.22,
        "execution_loss": 0.2,
        "average_clv_bps": 1.5,
        "actionable_markets": 2,
        "blocked_markets": 8,
        "reasons": ["review events dominate actionable events"],
    }
    scorecard_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    scorecard_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_sports_tuning_plan(scorecard_paths=[scorecard_a, scorecard_b])

    assert plan.experiment_family == "selection"
    assert plan.loss_ranking[0] == "selection"
    assert any("min_edge_bps" in variant.overrides for variant in plan.variants)
    assert any(variant.name == "selection_actionable_subset_guard" for variant in plan.variants)
    assert "selection_higher_edge_gate" in format_sports_tuning_plan(plan)


def test_build_sports_candidate_preset_registry_uses_base_match(tmp_path: Path) -> None:
    scorecard_a = tmp_path / "sports-a.json"
    scorecard_b = tmp_path / "sports-b.json"
    payload = {
        "tradable_subset_status": "ready",
        "closing_line_status": "fragile",
        "selection_loss": 0.22,
        "pricing_loss": 0.5,
        "execution_loss": 0.2,
        "average_clv_bps": -2.5,
        "actionable_markets": 6,
        "blocked_markets": 4,
        "reasons": ["closing line moved against sports fair value"],
    }
    scorecard_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    scorecard_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_sports_tuning_plan(scorecard_paths=[scorecard_a, scorecard_b])
    registry = build_sports_candidate_preset_registry(
        plan=plan,
        base_match={"league": "nba", "market_family": "moneyline"},
    )

    first = next(iter(registry.values()))
    assert first["match"] == {"league": "nba", "market_family": "moneyline"}
