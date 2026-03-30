from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.crypto.phase2.preset_apply_plan import build_crypto_phase2_preset_apply_plan


def test_build_crypto_phase2_preset_apply_plan_holds_when_not_ready() -> None:
    package = SimpleNamespace(
        next_working_preset="execution_faster_quotes",
        ready_to_apply=False,
        recurring_targeted_improvement=0.01,
        patch={},
    )

    plan = build_crypto_phase2_preset_apply_plan(package=package)

    assert plan.apply_mode == "hold"
    assert plan.blockers


def test_build_crypto_phase2_preset_apply_plan_reviews_when_ready() -> None:
    package = SimpleNamespace(
        next_working_preset="execution_faster_quotes",
        ready_to_apply=True,
        recurring_targeted_improvement=0.06,
        patch={"execution_faster_quotes": {"match": {}, "overrides": {}}},
    )

    plan = build_crypto_phase2_preset_apply_plan(package=package)

    assert plan.apply_mode == "review_then_apply"
    assert not plan.blockers
    assert any("recurring targeted improvement" in step for step in plan.steps)
