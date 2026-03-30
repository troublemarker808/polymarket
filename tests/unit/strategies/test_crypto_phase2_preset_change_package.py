from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.crypto.phase2.preset_change_package import build_crypto_phase2_preset_change_package


def test_build_crypto_phase2_preset_change_package_marks_ready_when_evidence_and_patch_align() -> None:
    lifecycle = SimpleNamespace(
        next_working_preset="execution_faster_quotes",
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current promotion conditions over baseline",
        working_preset="baseline",
        candidate_presets=("execution_faster_quotes",),
        retired_presets=("baseline",),
        strategy_state="candidate",
        strategy_state_reason="candidate clears version comparison",
    )
    evidence = SimpleNamespace(
        ready_to_apply=True,
        report_count=2,
        recurring_promotion_target="execution_faster_quotes",
        recurring_promotion_count=2,
        recurring_targeted_improvement=0.06,
    )
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            experiment_family="execution",
            variants=(
                SimpleNamespace(
                    name="execution_faster_quotes",
                    focus="execution",
                    overrides={"maker_quote_ttl_seconds": 45},
                    rationale=("reduce expiration pressure",),
                ),
            ),
        ),
    )

    package = build_crypto_phase2_preset_change_package(
        lifecycle=lifecycle,
        evidence=evidence,
        report=report,
        base_match={"underlying": "ETH", "event_family": "dip"},
    )

    assert package.ready_to_apply is True
    assert package.recurring_targeted_improvement == 0.06
    assert package.patch["execution_faster_quotes"]["match"] == {"underlying": "ETH", "event_family": "dip"}


def test_build_crypto_phase2_preset_change_package_blocks_apply_when_strategy_state_is_degraded() -> None:
    lifecycle = SimpleNamespace(
        next_working_preset="execution_faster_quotes",
        promotion_decision="promote_candidate",
        promotion_reason="winner clears current promotion conditions over baseline",
        working_preset="baseline",
        candidate_presets=("execution_faster_quotes",),
        retired_presets=(),
        strategy_state="degraded",
        strategy_state_reason="candidate still degrades pnl efficiency",
    )
    evidence = SimpleNamespace(
        ready_to_apply=True,
        report_count=2,
        recurring_promotion_target="execution_faster_quotes",
        recurring_promotion_count=2,
        recurring_targeted_improvement=0.06,
    )
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            experiment_family="execution",
            variants=(
                SimpleNamespace(
                    name="execution_faster_quotes",
                    focus="execution",
                    overrides={"maker_quote_ttl_seconds": 45},
                    rationale=("reduce expiration pressure",),
                ),
            ),
        ),
    )

    package = build_crypto_phase2_preset_change_package(
        lifecycle=lifecycle,
        evidence=evidence,
        report=report,
        base_match={"underlying": "ETH", "event_family": "dip"},
    )

    assert package.ready_to_apply is False
