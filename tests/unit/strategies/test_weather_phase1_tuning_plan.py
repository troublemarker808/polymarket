from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.weather.phase1.tuning_plan import (
    build_weather_candidate_preset_registry,
    build_weather_tuning_plan,
    format_weather_tuning_plan,
)


def test_build_weather_tuning_plan_produces_settlement_variants(tmp_path: Path) -> None:
    scorecard_a = tmp_path / "weather-a.json"
    scorecard_b = tmp_path / "weather-b.json"
    payload = {
        "tradable_subset_status": "ready",
        "settlement_audit_status": "fragile",
        "selection_loss": 0.2,
        "settlement_loss": 0.55,
        "execution_loss": 0.18,
        "average_monotonicity_gap_bps": 180.0,
        "actionable_markets": 4,
        "blocked_markets": 6,
        "reasons": ["strip monotonicity gap exceeds weather threshold"],
    }
    scorecard_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    scorecard_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_weather_tuning_plan(scorecard_paths=[scorecard_a, scorecard_b])

    assert plan.experiment_family == "settlement"
    assert plan.loss_ranking[0] == "settlement"
    assert any("min_strip_inconsistency_bps" in variant.overrides for variant in plan.variants)
    assert any(variant.name == "settlement_gap_recovery_gate" for variant in plan.variants)
    assert "settlement_higher_strip_gate" in format_weather_tuning_plan(plan)


def test_build_weather_candidate_preset_registry_uses_base_match(tmp_path: Path) -> None:
    scorecard_a = tmp_path / "weather-a.json"
    scorecard_b = tmp_path / "weather-b.json"
    payload = {
        "tradable_subset_status": "thin",
        "settlement_audit_status": "ready",
        "selection_loss": 0.45,
        "settlement_loss": 0.2,
        "execution_loss": 0.18,
        "average_monotonicity_gap_bps": 90.0,
        "actionable_markets": 3,
        "blocked_markets": 7,
        "reasons": ["no actionable weather markets"],
    }
    scorecard_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    scorecard_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_weather_tuning_plan(scorecard_paths=[scorecard_a, scorecard_b])
    registry = build_weather_candidate_preset_registry(
        plan=plan,
        base_match={"event_family": "daily_high_temperature_threshold", "settlement_source": "official"},
    )

    first = next(iter(registry.values()))
    assert first["match"] == {"event_family": "daily_high_temperature_threshold", "settlement_source": "official"}
