from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.sports.phase1.preset_change_package import build_sports_preset_change_package
from pm_bot.strategies.sports.phase1.preset_lifecycle import build_sports_preset_lifecycle
from pm_bot.strategies.sports.phase1.preset_promotion_evidence import build_sports_preset_promotion_evidence


def test_build_sports_preset_lifecycle_promotes_candidate() -> None:
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            variants=(SimpleNamespace(name="selection_higher_edge_gate", focus="selection", overrides={"min_edge_bps": 85.0}, rationale=("tighten",)),)
        ),
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current sports promotion conditions over baseline",
        promotion_target="selection_higher_edge_gate",
    )

    lifecycle = build_sports_preset_lifecycle(
        report=report,
        evidence=SimpleNamespace(ready_to_apply=True),
        strategy_state="candidate",
        strategy_state_reason="candidate clears version comparison",
    )

    assert lifecycle.next_working_preset == "selection_higher_edge_gate"
    assert lifecycle.retired_presets == ("baseline",)
    assert lifecycle.apply_ready is True


def test_build_sports_preset_change_package_marks_ready_when_evidence_and_patch_align(tmp_path) -> None:
    auto_a = tmp_path / "auto-a.json"
    auto_b = tmp_path / "auto-b.json"
    payload = {
        "promotion_decision": "promote_candidate",
        "promotion_target": "selection_higher_edge_gate",
        "winner": {"recommended_action": "proceed", "targeted_loss_improvement": 0.08},
    }
    auto_a.write_text(__import__("json").dumps(payload), encoding="utf-8")
    auto_b.write_text(__import__("json").dumps(payload), encoding="utf-8")
    evidence = build_sports_preset_promotion_evidence(auto_experiment_paths=[auto_a, auto_b])
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            variants=(SimpleNamespace(name="selection_higher_edge_gate", focus="selection", overrides={"min_edge_bps": 85.0}, rationale=("tighten",)),)
        ),
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current sports promotion conditions over baseline",
        promotion_target="selection_higher_edge_gate",
    )
    lifecycle = build_sports_preset_lifecycle(
        report=report,
        evidence=evidence,
        strategy_state="candidate",
        strategy_state_reason="candidate clears version comparison",
    )

    package = build_sports_preset_change_package(
        lifecycle=lifecycle,
        evidence=evidence,
        report=report,
        base_match={"league": "nba", "market_family": "moneyline"},
    )

    assert package.ready_to_apply is True
    assert package.recurring_targeted_improvement >= 0.03
    assert package.patch["selection_higher_edge_gate"]["match"] == {"league": "nba", "market_family": "moneyline"}


def test_build_sports_preset_change_package_blocks_apply_when_strategy_state_is_degraded(tmp_path) -> None:
    auto_a = tmp_path / "auto-a.json"
    auto_b = tmp_path / "auto-b.json"
    payload = {
        "promotion_decision": "promote_candidate",
        "promotion_target": "selection_higher_edge_gate",
        "winner": {"recommended_action": "proceed", "targeted_loss_improvement": 0.08},
    }
    auto_a.write_text(__import__("json").dumps(payload), encoding="utf-8")
    auto_b.write_text(__import__("json").dumps(payload), encoding="utf-8")
    evidence = build_sports_preset_promotion_evidence(auto_experiment_paths=[auto_a, auto_b])
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            variants=(SimpleNamespace(name="selection_higher_edge_gate", focus="selection", overrides={"min_edge_bps": 85.0}, rationale=("tighten",)),)
        ),
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current sports promotion conditions over baseline",
        promotion_target="selection_higher_edge_gate",
    )
    lifecycle = build_sports_preset_lifecycle(
        report=report,
        evidence=evidence,
        strategy_state="degraded",
        strategy_state_reason="candidate still degrades aggregate sports quality",
    )

    package = build_sports_preset_change_package(
        lifecycle=lifecycle,
        evidence=evidence,
        report=report,
        base_match={"league": "nba", "market_family": "moneyline"},
    )

    assert package.ready_to_apply is False
