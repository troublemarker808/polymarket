from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.crypto.phase2.tuning_plan import (
    build_crypto_phase2_candidate_preset_registry,
    build_crypto_phase2_tuning_plan,
    format_crypto_phase2_tuning_plan,
)


def test_build_crypto_phase2_tuning_plan_produces_execution_variants(tmp_path: Path) -> None:
    suite_a = tmp_path / "suite-a.json"
    suite_b = tmp_path / "suite-b.json"
    payload = {
        "final_scorecard": {
            "profit_focus": "execution",
            "secondary_profit_focus": "exit",
            "loss_ranking": ["execution", "exit", "sizing", "pricing", "selection"],
            "tuning_priority": "execution",
            "tuning_actions": [
                "reduce maker_quote_ttl_seconds or increase maker_aggressiveness for the active preset",
            ],
            "execution_loss": 0.35,
            "edge_capture_ratio": 0.4,
            "average_signal_edge_bps": 120.0,
            "average_adverse_fill_bps": 58.0,
            "pnl_per_notional": -0.01,
            "average_trade_expected_edge_bps": 120.0,
            "average_trade_execution_drag_bps": 24.0,
            "average_trade_realized_pnl_bps": -12.0,
            "average_win_trade_pnl": 0.08,
            "average_loss_trade_pnl": -0.16,
            "average_submitted_notional": 5.4,
            "large_notional_share": 0.34,
            "exit_family_balance_score": 0.48,
            "small_bucket_pnl_per_notional": 0.009,
            "medium_bucket_pnl_per_notional": -0.003,
            "large_bucket_pnl_per_notional": -0.019,
            "dominant_exit_reason": "aging_exit",
            "stop_loss_exit_share": 0.12,
            "passive_cleanup_exit_share": 0.4,
        }
    }
    suite_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    suite_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_crypto_phase2_tuning_plan(suite_paths=[suite_a, suite_b])

    assert plan.experiment_family == "execution"
    assert len(plan.variants) >= 2
    assert plan.secondary_profit_focus == "exit"
    assert any("maker_quote_ttl_seconds" in variant.overrides for variant in plan.variants)
    assert any(variant.name == "execution_exit_guard" for variant in plan.variants)
    assert any(variant.name == "execution_capture_repricing" for variant in plan.variants)
    assert any(variant.name == "execution_trade_drag_guard" for variant in plan.variants)
    rendered = format_crypto_phase2_tuning_plan(plan)
    assert "execution_faster_quotes" in rendered
    assert "secondary_profit_focus: exit" in rendered
    assert "recommended_next_experiment: execution" in rendered


def test_build_crypto_phase2_candidate_preset_registry_uses_match_overrides(tmp_path: Path) -> None:
    suite_a = tmp_path / "suite-a.json"
    suite_b = tmp_path / "suite-b.json"
    payload = {
        "final_scorecard": {
            "profit_focus": "selection",
            "secondary_profit_focus": "pricing",
            "loss_ranking": ["selection", "pricing", "execution", "exit", "sizing"],
            "tuning_priority": "selection",
            "tuning_actions": ["raise min_net_edge_bps for the weakest family preset before adding more order flow"],
            "selection_loss": 0.28,
            "pricing_loss": 0.22,
            "execution_loss": 0.05,
            "exit_loss": 0.04,
            "sizing_loss": 0.03,
            "edge_capture_ratio": 0.52,
            "average_signal_edge_bps": 95.0,
            "average_adverse_fill_bps": 44.0,
            "pnl_per_notional": 0.002,
            "average_trade_expected_edge_bps": 95.0,
            "average_trade_execution_drag_bps": 12.0,
            "average_trade_realized_pnl_bps": 2.0,
            "average_win_trade_pnl": 0.09,
            "average_loss_trade_pnl": -0.04,
            "average_submitted_notional": 4.8,
            "large_notional_share": 0.18,
            "exit_family_balance_score": 0.72,
            "small_bucket_pnl_per_notional": 0.011,
            "medium_bucket_pnl_per_notional": 0.006,
            "large_bucket_pnl_per_notional": 0.003,
            "dominant_exit_reason": "fair_value_reached",
            "stop_loss_exit_share": 0.08,
            "passive_cleanup_exit_share": 0.12,
        }
    }
    suite_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    suite_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_crypto_phase2_tuning_plan(suite_paths=[suite_a, suite_b])
    assert any(variant.name == "selection_pricing_high_confidence" for variant in plan.variants)
    registry = build_crypto_phase2_candidate_preset_registry(
        plan=plan,
        base_match={"underlying": "ETH", "event_family": "dip"},
    )

    assert registry
    first = next(iter(registry.values()))
    assert first["match"] == {"underlying": "ETH", "event_family": "dip"}


def test_build_crypto_phase2_tuning_plan_adds_exit_and_sizing_efficiency_variants(tmp_path: Path) -> None:
    suite_a = tmp_path / "suite-a.json"
    suite_b = tmp_path / "suite-b.json"
    payload = {
        "final_scorecard": {
            "profit_focus": "sizing",
            "secondary_profit_focus": "exit",
            "loss_ranking": ["sizing", "exit", "execution", "pricing", "selection"],
            "tuning_priority": "sizing",
            "tuning_actions": ["reduce default_notional for families with negative average trade pnl"],
            "selection_loss": 0.08,
            "pricing_loss": 0.09,
            "execution_loss": 0.14,
            "exit_loss": 0.22,
            "sizing_loss": 0.31,
            "edge_capture_ratio": 0.58,
            "average_signal_edge_bps": 108.0,
            "average_adverse_fill_bps": 34.0,
            "pnl_per_notional": -0.006,
            "average_trade_expected_edge_bps": 108.0,
            "average_trade_execution_drag_bps": 17.0,
            "average_trade_realized_pnl_bps": -7.0,
            "average_win_trade_pnl": 0.06,
            "average_loss_trade_pnl": -0.14,
            "average_submitted_notional": 5.7,
            "large_notional_share": 0.44,
            "exit_family_balance_score": 0.57,
            "small_bucket_pnl_per_notional": 0.01,
            "medium_bucket_pnl_per_notional": -0.002,
            "large_bucket_pnl_per_notional": -0.019,
            "dominant_exit_reason": "stop_loss",
            "stop_loss_exit_share": 0.34,
            "passive_cleanup_exit_share": 0.18,
        }
    }
    suite_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    suite_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_crypto_phase2_tuning_plan(suite_paths=[suite_a, suite_b])

    assert any(variant.name == "sizing_large_clip_concentration_guard" for variant in plan.variants)
    assert any(variant.name == "sizing_bucket_efficiency_guard" for variant in plan.variants)
    assert any(variant.name == "exit_stop_loss_cluster_guard" for variant in plan.variants) is False


def test_build_crypto_phase2_tuning_plan_adds_exit_reason_variants(tmp_path: Path) -> None:
    suite_a = tmp_path / "suite-a.json"
    suite_b = tmp_path / "suite-b.json"
    payload = {
        "final_scorecard": {
            "profit_focus": "exit",
            "secondary_profit_focus": "execution",
            "loss_ranking": ["exit", "execution", "sizing", "pricing", "selection"],
            "tuning_priority": "exit",
            "tuning_actions": ["tighten exit asymmetry before expanding flow"],
            "selection_loss": 0.08,
            "pricing_loss": 0.09,
            "execution_loss": 0.14,
            "exit_loss": 0.31,
            "sizing_loss": 0.1,
            "edge_capture_ratio": 0.56,
            "average_signal_edge_bps": 108.0,
            "average_adverse_fill_bps": 34.0,
            "pnl_per_notional": -0.003,
            "average_trade_expected_edge_bps": 108.0,
            "average_trade_execution_drag_bps": 16.0,
            "average_trade_realized_pnl_bps": -5.0,
            "average_win_trade_pnl": 0.05,
            "average_loss_trade_pnl": -0.16,
            "average_submitted_notional": 4.9,
            "large_notional_share": 0.21,
            "exit_family_balance_score": 0.44,
            "small_bucket_pnl_per_notional": 0.008,
            "medium_bucket_pnl_per_notional": -0.001,
            "large_bucket_pnl_per_notional": -0.004,
            "dominant_exit_reason": "stop_loss",
            "stop_loss_exit_share": 0.33,
            "passive_cleanup_exit_share": 0.39,
        }
    }
    suite_a.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    suite_b.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    plan = build_crypto_phase2_tuning_plan(suite_paths=[suite_a, suite_b])

    assert any(variant.name == "exit_stop_loss_cluster_guard" for variant in plan.variants)
    assert any(variant.name == "exit_passive_cleanup_guard" for variant in plan.variants)
    assert any(variant.name == "exit_family_rebalance_guard" for variant in plan.variants)
