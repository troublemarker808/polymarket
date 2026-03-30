from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.weather.phase1.preset_change_package import build_weather_preset_change_package
from pm_bot.strategies.weather.phase1.preset_lifecycle import build_weather_preset_lifecycle
from pm_bot.strategies.weather.phase1.preset_promotion_evidence import build_weather_preset_promotion_evidence


def test_build_weather_preset_lifecycle_promotes_candidate() -> None:
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            variants=(SimpleNamespace(name="settlement_higher_strip_gate", focus="settlement", overrides={"min_strip_inconsistency_bps": 45.0}, rationale=("tighten",)),)
        ),
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current weather promotion conditions over baseline",
        promotion_target="settlement_higher_strip_gate",
    )

    lifecycle = build_weather_preset_lifecycle(
        report=report,
        evidence=SimpleNamespace(ready_to_apply=True),
        strategy_state="candidate",
        strategy_state_reason="candidate clears version comparison",
    )

    assert lifecycle.next_working_preset == "settlement_higher_strip_gate"
    assert lifecycle.retired_presets == ("baseline",)
    assert lifecycle.apply_ready is True


def test_build_weather_preset_change_package_marks_ready_when_evidence_and_patch_align(tmp_path) -> None:
    auto_a = tmp_path / "auto-a.json"
    auto_b = tmp_path / "auto-b.json"
    payload = {
        "promotion_decision": "promote_candidate",
        "promotion_target": "settlement_higher_strip_gate",
        "winner": {"recommended_action": "proceed", "targeted_loss_improvement": 0.09},
    }
    auto_a.write_text(__import__("json").dumps(payload), encoding="utf-8")
    auto_b.write_text(__import__("json").dumps(payload), encoding="utf-8")
    evidence = build_weather_preset_promotion_evidence(auto_experiment_paths=[auto_a, auto_b])
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            variants=(SimpleNamespace(name="settlement_higher_strip_gate", focus="settlement", overrides={"min_strip_inconsistency_bps": 45.0}, rationale=("tighten",)),)
        ),
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current weather promotion conditions over baseline",
        promotion_target="settlement_higher_strip_gate",
    )
    lifecycle = build_weather_preset_lifecycle(
        report=report,
        evidence=evidence,
        strategy_state="candidate",
        strategy_state_reason="candidate clears version comparison",
    )

    package = build_weather_preset_change_package(
        lifecycle=lifecycle,
        evidence=evidence,
        report=report,
        base_match={"event_family": "daily_high_temperature_threshold", "settlement_source": "official"},
    )

    assert package.ready_to_apply is True
    assert package.recurring_targeted_improvement >= 0.03
    assert package.patch["settlement_higher_strip_gate"]["match"] == {
        "event_family": "daily_high_temperature_threshold",
        "settlement_source": "official",
    }


def test_build_weather_preset_change_package_blocks_apply_when_strategy_state_is_degraded(tmp_path) -> None:
    auto_a = tmp_path / "auto-a.json"
    auto_b = tmp_path / "auto-b.json"
    payload = {
        "promotion_decision": "promote_candidate",
        "promotion_target": "settlement_higher_strip_gate",
        "winner": {"recommended_action": "proceed", "targeted_loss_improvement": 0.09},
    }
    auto_a.write_text(__import__("json").dumps(payload), encoding="utf-8")
    auto_b.write_text(__import__("json").dumps(payload), encoding="utf-8")
    evidence = build_weather_preset_promotion_evidence(auto_experiment_paths=[auto_a, auto_b])
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            variants=(SimpleNamespace(name="settlement_higher_strip_gate", focus="settlement", overrides={"min_strip_inconsistency_bps": 45.0}, rationale=("tighten",)),)
        ),
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current weather promotion conditions over baseline",
        promotion_target="settlement_higher_strip_gate",
    )
    lifecycle = build_weather_preset_lifecycle(
        report=report,
        evidence=evidence,
        strategy_state="degraded",
        strategy_state_reason="candidate still degrades aggregate weather quality",
    )

    package = build_weather_preset_change_package(
        lifecycle=lifecycle,
        evidence=evidence,
        report=report,
        base_match={"event_family": "daily_high_temperature_threshold", "settlement_source": "official"},
    )

    assert package.ready_to_apply is False
