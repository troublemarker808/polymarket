from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.crypto.phase2.preset_promotion_evidence import (
    build_crypto_phase2_preset_promotion_evidence,
    format_crypto_phase2_preset_promotion_evidence,
)


def test_build_crypto_phase2_preset_promotion_evidence_requires_repeated_winner(tmp_path: Path) -> None:
    auto_a = tmp_path / "auto-a.json"
    auto_b = tmp_path / "auto-b.json"
    payload = {
        "promotion_decision": "promote_candidate",
        "promotion_target": "execution_faster_quotes",
        "targeted_loss_improvement": 0.06,
        "baseline": {"average_loss_trade_pnl": -0.15, "large_notional_share": 0.4},
        "winner": {"recommended_action": "proceed", "average_loss_trade_pnl": -0.08, "large_notional_share": 0.22},
    }
    auto_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    auto_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    evidence = build_crypto_phase2_preset_promotion_evidence(
        auto_experiment_paths=[auto_a, auto_b],
    )

    assert evidence.ready_to_apply is True
    assert evidence.winning_variant == "execution_faster_quotes"
    assert evidence.recurring_targeted_improvement == 0.06
    assert evidence.recurring_exit_asymmetry_improvement > 0.0
    assert evidence.recurring_size_concentration_improvement > 0.0
    rendered = format_crypto_phase2_preset_promotion_evidence(evidence)
    assert "ready_to_apply: true" in rendered


def test_build_crypto_phase2_preset_promotion_evidence_blocks_weak_targeted_improvement(tmp_path: Path) -> None:
    auto_a = tmp_path / "auto-a.json"
    auto_b = tmp_path / "auto-b.json"
    payload = {
        "promotion_decision": "promote_candidate",
        "promotion_target": "selection_pricing_high_confidence",
        "targeted_loss_improvement": 0.01,
        "baseline": {"average_loss_trade_pnl": -0.08, "large_notional_share": 0.18},
        "winner": {"recommended_action": "proceed", "average_loss_trade_pnl": -0.09, "large_notional_share": 0.22},
    }
    auto_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    auto_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    evidence = build_crypto_phase2_preset_promotion_evidence(
        auto_experiment_paths=[auto_a, auto_b],
    )

    assert evidence.ready_to_apply is False
    assert "targeted loss improvement is not strong enough across repeated auto-experiments" in evidence.blockers
    assert "losing-trade asymmetry still worsens across repeated auto-experiments" in evidence.blockers
    assert "large-notional concentration still worsens across repeated auto-experiments" in evidence.blockers
