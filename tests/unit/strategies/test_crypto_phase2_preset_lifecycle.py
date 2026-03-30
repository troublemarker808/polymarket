from __future__ import annotations

from types import SimpleNamespace

from pm_bot.strategies.crypto.phase2.preset_lifecycle import (
    build_crypto_phase2_preset_lifecycle,
    build_crypto_phase2_working_preset_patch,
)


def test_build_crypto_phase2_preset_lifecycle_promotes_candidate() -> None:
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
        promotion_decision="promote_candidate",
        promotion_target="execution_faster_quotes",
        promotion_reason="winner clears current promotion conditions over baseline",
    )
    evidence = SimpleNamespace(ready_to_apply=True)

    lifecycle = build_crypto_phase2_preset_lifecycle(
        report=report,
        evidence=evidence,
        current_working_preset="baseline",
        strategy_state="candidate",
        strategy_state_reason="candidate clears version comparison",
    )

    assert lifecycle.working_preset == "baseline"
    assert lifecycle.next_working_preset == "execution_faster_quotes"
    assert lifecycle.retired_presets == ("baseline",)
    assert lifecycle.apply_ready is True
    assert lifecycle.strategy_state == "candidate"


def test_build_crypto_phase2_working_preset_patch_returns_promoted_candidate() -> None:
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
    lifecycle = SimpleNamespace(
        promotion_decision="promote_candidate",
        next_working_preset="execution_faster_quotes",
        apply_ready=True,
    )

    patch = build_crypto_phase2_working_preset_patch(
        lifecycle=lifecycle,
        report=report,
        base_match={"underlying": "ETH", "event_family": "dip"},
    )

    assert patch["execution_faster_quotes"]["match"] == {"underlying": "ETH", "event_family": "dip"}


def test_build_crypto_phase2_preset_lifecycle_holds_candidate_when_evidence_is_not_ready() -> None:
    report = SimpleNamespace(
        tuning_plan=SimpleNamespace(
            experiment_family="selection",
            variants=(
                SimpleNamespace(
                    name="selection_pricing_high_confidence",
                    focus="selection+pricing",
                    overrides={"min_net_edge_bps": 105.0},
                    rationale=("tighten edge and confidence gates together",),
                ),
            ),
        ),
        promotion_decision="promote_candidate",
        promotion_target="selection_pricing_high_confidence",
        promotion_reason="winner clears current promotion conditions over baseline",
    )
    evidence = SimpleNamespace(ready_to_apply=False)

    lifecycle = build_crypto_phase2_preset_lifecycle(
        report=report,
        evidence=evidence,
        current_working_preset="baseline",
        strategy_state="degraded",
        strategy_state_reason="candidate still degrades pnl efficiency",
    )

    assert lifecycle.next_working_preset == "baseline"
    assert lifecycle.retired_presets == ()
    assert lifecycle.apply_ready is False
    assert lifecycle.strategy_state == "degraded"
