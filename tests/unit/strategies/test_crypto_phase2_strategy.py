import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PendingOrderState, PositionState, RuntimeStatus
from pm_bot.strategies.crypto.phase2 import (
    CryptoDynamicEligibilityGate,
    CryptoExecutionFeedback,
    CryptoPhase2Strategy,
    build_position_intent,
    classify_crypto_signal,
)
from pm_bot.strategies.crypto.phase2.models import CryptoReentryState


FIXTURE_CASES = Path("tests/fixtures/crypto_phase2/execution_cases.json")


def test_crypto_phase2_strategy_generates_entry_signal_from_phase1_fair_value() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "market_selection_actions": {"eth-dip-1000": "tradable_market"},
                "market_selection_reasons": {"eth-dip-1000": ("tight_runtime_spread",)},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.BUY_YES
    assert signal.target_price == 0.11
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds == 30
    assert signal.rationale_tags == ("repricing_edge", "taker")
    assert signal.diagnostics["signal_type"] == "repricing_edge"
    assert signal.diagnostics["execution_route"] == "taker"
    assert signal.diagnostics["decision_trace_version"] == "v1"
    assert signal.diagnostics["entry_decision_reason_code"] == "repricing_edge"
    assert signal.diagnostics["entry_eligibility_reason"] == "eligible"
    assert signal.diagnostics["entry_route_policy_bias"] == "stable"
    assert signal.diagnostics["entry_decision_rationale_tags"] == ["repricing_edge", "taker"]
    assert signal.diagnostics["selection_action"] == "tradable_market"
    assert signal.diagnostics["selection_reasons"] == ["tight_runtime_spread"]


def test_crypto_phase2_strategy_forces_selective_market_entries_to_stay_passive() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "market_selection_actions": {"eth-dip-1000": "selective_market"},
                "market_selection_reasons": {"eth-dip-1000": ("wide_spread",)},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.10
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 60
    assert signal.rationale_tags == ("repricing_edge", "maker")
    assert signal.diagnostics["selection_action"] == "selective_market"
    assert signal.diagnostics["execution_route"] == "maker"


def test_crypto_phase2_strategy_allows_selective_market_taker_when_aggressive_override_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "selective_market_allow_taker_when_aggressive": True,
            "taker_urgency_threshold": 0.8,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "market_selection_actions": {"eth-dip-1000": "selective_market"},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.0,
                    taker_shortfall_bps=0.0,
                    repeated_expiration_rate=1.0,
                    repeated_stop_out_rate=0.0,
                    recommended_route_bias="more_aggressive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "IOC"
    assert signal.diagnostics["selection_action"] == "selective_market"
    assert signal.diagnostics["execution_route"] == "taker"


def test_crypto_phase2_strategy_allows_selective_market_taker_when_explicitly_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "selective_market_allow_taker": True,
            "taker_urgency_threshold": 0.75,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "market_selection_actions": {"eth-dip-1000": "selective_market"},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "IOC"
    assert signal.diagnostics["execution_route"] == "taker"


def test_crypto_phase2_strategy_allows_selective_market_taker_for_reach_family_when_aggressive() -> None:
    base_fair_value = _fair_value("repricing_yes")
    fair_value = FairValueEstimate(
        market_id="btc-reach-1000",
        category=base_fair_value.category,
        fair_probability=base_fair_value.fair_probability,
        confidence=base_fair_value.confidence,
        half_life_seconds=base_fair_value.half_life_seconds,
        observed_probability=base_fair_value.observed_probability,
        model_id=base_fair_value.model_id,
        rationale_tags=base_fair_value.rationale_tags,
        supporting_values=dict(base_fair_value.supporting_values),
    )
    strategy = CryptoPhase2Strategy(
        {
            "selective_market_allow_taker_when_aggressive": False,
            "selective_market_allow_taker_when_aggressive_reach": True,
            "taker_urgency_threshold": 0.75,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="btc-reach-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-1000": fair_value},
                "market_selection_actions": {"btc-reach-1000": "selective_market"},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.0,
                    taker_shortfall_bps=0.0,
                    repeated_expiration_rate=1.0,
                    repeated_stop_out_rate=0.0,
                    recommended_route_bias="more_aggressive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "IOC"
    assert signal.diagnostics["execution_route"] == "taker"


def test_crypto_phase2_strategy_keeps_selective_market_maker_for_dip_family_when_aggressive_disabled_by_family() -> None:
    base_fair_value = _fair_value("repricing_yes")
    fair_value = FairValueEstimate(
        market_id="btc-dip-1000",
        category=base_fair_value.category,
        fair_probability=base_fair_value.fair_probability,
        confidence=base_fair_value.confidence,
        half_life_seconds=base_fair_value.half_life_seconds,
        observed_probability=base_fair_value.observed_probability,
        model_id=base_fair_value.model_id,
        rationale_tags=base_fair_value.rationale_tags,
        supporting_values=dict(base_fair_value.supporting_values),
    )
    strategy = CryptoPhase2Strategy(
        {
            "selective_market_allow_taker_when_aggressive": True,
            "selective_market_allow_taker_when_aggressive_dip": False,
            "taker_urgency_threshold": 0.75,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="btc-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-dip-1000": fair_value},
                "market_selection_actions": {"btc-dip-1000": "selective_market"},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.0,
                    taker_shortfall_bps=0.0,
                    repeated_expiration_rate=1.0,
                    repeated_stop_out_rate=0.0,
                    recommended_route_bias="more_aggressive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.diagnostics["execution_route"] == "maker"


def test_crypto_phase2_strategy_blocks_entry_when_same_family_recent_activity_within_family_cooldown() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_family_cooldown_seconds": 120.0,
            "entry_market_cooldown_seconds": 0.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-family-cooldown",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-family-cooldown": fair_value},
                "market_selection_actions": {"btc-reach-family-cooldown": "tradable_market"},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "btc-reach-older",
                            "side": SignalSide.BUY_YES.value,
                            "underlying_group_id": "crypto:btc",
                            "diagnostics": {"phase2_preset": "btc_reach_short_shadow"},
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_block_entry_when_recent_activity_is_other_family() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_family_cooldown_seconds": 120.0,
            "entry_market_cooldown_seconds": 0.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-family-cooldown-open",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-family-cooldown-open": fair_value},
                "market_selection_actions": {"btc-reach-family-cooldown-open": "tradable_market"},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "btc-dip-older",
                            "side": SignalSide.BUY_YES.value,
                            "underlying_group_id": "crypto:btc",
                            "diagnostics": {"phase2_preset": "btc_dip_short_shadow"},
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1


def test_crypto_phase2_strategy_applies_family_pnl_notional_haircut_for_negative_family_efficiency() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_market_cooldown_seconds": 0.0,
            "entry_family_cooldown_seconds": 0.0,
            "family_pnl_notional_haircut_enabled": True,
            "family_pnl_notional_haircut_min_closed_samples": 1,
            "family_pnl_notional_haircut_full_haircut_pnl_per_notional": -0.02,
            "family_pnl_notional_haircut_min_multiplier": 0.5,
            "family_pnl_notional_haircut_max_multiplier": 1.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-pnl-haircut",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-pnl-haircut": fair_value},
                "market_selection_actions": {"btc-reach-pnl-haircut": "tradable_market"},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "btc-reach-prev",
                            "side": SignalSide.BUY_YES.value,
                            "underlying_group_id": "crypto:btc",
                            "diagnostics": {"phase2_preset": "btc_reach_short_shadow"},
                            "notional": 10.0,
                            "created_at": (now - timedelta(seconds=90)).isoformat(),
                        },
                    },
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-reach-prev",
                            "underlying_group_id": "crypto:btc",
                            "diagnostics": {"phase2_preset": "btc_reach_short_shadow"},
                            "net_pnl": -0.2,
                            "closed_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.diagnostics["family_pnl_notional_status"] == "family_pnl_haircut_applied"
    assert signal.diagnostics["family_pnl_notional_multiplier"] < 1.0


def test_crypto_phase2_strategy_keeps_family_pnl_notional_multiplier_at_max_for_positive_efficiency() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_market_cooldown_seconds": 0.0,
            "entry_family_cooldown_seconds": 0.0,
            "family_pnl_notional_haircut_enabled": True,
            "family_pnl_notional_haircut_min_closed_samples": 1,
            "family_pnl_notional_haircut_min_multiplier": 0.5,
            "family_pnl_notional_haircut_max_multiplier": 1.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-pnl-haircut-healthy",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-pnl-haircut-healthy": fair_value},
                "market_selection_actions": {"btc-reach-pnl-haircut-healthy": "tradable_market"},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "btc-reach-prev-healthy",
                            "side": SignalSide.BUY_YES.value,
                            "underlying_group_id": "crypto:btc",
                            "diagnostics": {"phase2_preset": "btc_reach_short_shadow"},
                            "notional": 10.0,
                            "created_at": (now - timedelta(seconds=90)).isoformat(),
                        },
                    },
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-reach-prev-healthy",
                            "underlying_group_id": "crypto:btc",
                            "diagnostics": {"phase2_preset": "btc_reach_short_shadow"},
                            "net_pnl": 0.15,
                            "closed_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.diagnostics["family_pnl_notional_status"] == "family_pnl_haircut_healthy"
    assert signal.diagnostics["family_pnl_notional_multiplier"] == 1.0


def test_crypto_phase2_strategy_uses_dedicated_ttl_for_repricing_maker_fallback() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "maker_quote_ttl_seconds": 10,
            "repricing_fallback_quote_ttl_seconds": 20,
            "repricing_taker_max_entry_premium_bps": 1.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-fallback-ttl",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-fallback-ttl": fair_value},
                "market_selection_actions": {"eth-dip-fallback-ttl": "tradable_market"},
                "market_selection_reasons": {"eth-dip-fallback-ttl": ("tight_runtime_spread",)},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 20
    assert signal.rationale_tags == ("repricing_taker_too_expensive", "maker_fallback")
    assert signal.diagnostics["execution_route"] == "maker"


def test_crypto_phase2_strategy_applies_taker_slippage_guard_before_repricing_taker_route() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "repricing_taker_max_entry_premium_bps": 1.0,
            "taker_slippage_guard_bps": 20.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-slippage-guard",
        best_bid_yes=0.63,
        best_ask_yes=0.64,
        best_bid_no=0.36,
        best_ask_no=0.37,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-slippage-guard": fair_value},
                "market_selection_actions": {"eth-dip-slippage-guard": "tradable_market"},
                "market_selection_reasons": {"eth-dip-slippage-guard": ("tight_runtime_spread",)},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.rationale_tags == ("repricing_taker_too_expensive", "maker_fallback")
    assert signal.diagnostics["execution_route"] == "maker"


def test_crypto_phase2_strategy_skips_selective_wide_spread_entries_when_configured() -> None:
    strategy = CryptoPhase2Strategy({"skip_selective_wide_spread_markets": True})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "market_selection_actions": {"eth-dip-1000": "selective_market"},
                "market_selection_reasons": {"eth-dip-1000": ("wide_spread",)},
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events == [
        {
            "event_type": "strategy.skipped",
            "payload": {
                "strategy_id": "crypto.phase2",
                "market_id": "eth-dip-1000",
                "slug": "eth-dip-1000",
                "reason": "selection_wide_spread_selective_blocked",
                "updated_at": snapshot.timestamp.isoformat(),
                "phase2_preset": "default",
                "selection_action": "selective_market",
                "selection_reasons": ["wide_spread"],
            },
        }
    ]


def test_crypto_phase2_strategy_emits_cost_regime_skip_reason_when_dynamic_gate_tightens() -> None:
    strategy = CryptoPhase2Strategy({"min_net_edge_bps": 75.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.78,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 180.0, "gross_edge_bps": 400.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.1,
                    taker_shortfall_bps=25.0,
                    repeated_expiration_rate=0.0,
                    repeated_stop_out_rate=0.6,
                    recommended_route_bias="more_passive",
                ),
                "dynamic_eligibility_gates": {
                    "ETH:dip": CryptoDynamicEligibilityGate(
                        family_key="ETH:dip",
                        sample_count=6,
                        min_net_edge_bps=260.0,
                        taker_max_entry_premium_bps=300.0,
                        repricing_taker_max_entry_premium_bps=80.0,
                        reason_tag="dynamic_more_passive",
                    )
                },
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "entry_not_actionable"
    assert runtime_events[-1]["payload"]["eligibility_reason"] == "cost_regime_min_net_edge"


def test_crypto_phase2_strategy_emits_execution_drag_skip_reason_when_entry_edge_too_thin() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "min_net_edge_bps": 100.0,
            "entry_execution_drag_bps": 40.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.78,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 120.0, "gross_edge_bps": 400.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "entry_not_actionable"
    assert runtime_events[-1]["payload"]["eligibility_reason"] == "execution_drag_min_net_edge"
    assert runtime_events[-1]["payload"]["entry_execution_drag_bps"] == 40.0
    assert runtime_events[-1]["payload"]["effective_min_net_edge_bps"] == 140.0


def test_crypto_phase2_strategy_counterfactual_gate_blocks_when_alternative_is_stronger() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "counterfactual_entry_gate_enabled": True,
            "counterfactual_entry_top_k": 1,
            "counterfactual_entry_min_candidates": 2,
            "counterfactual_entry_min_score_margin_bps": 25.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    current_snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-a",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    alternative_snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-b",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    current_fair_value = FairValueEstimate(
        market_id="eth-dip-a",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.68,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 180.0, "gross_edge_bps": 260.0},
    )
    alternative_fair_value = FairValueEstimate(
        market_id="eth-dip-b",
        category=Category.CRYPTO,
        fair_probability=0.16,
        confidence=0.82,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 520.0, "gross_edge_bps": 580.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=current_snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {
                    "eth-dip-a": current_fair_value,
                    "eth-dip-b": alternative_fair_value,
                },
                "snapshots_by_market_id": {
                    "eth-dip-a": current_snapshot,
                    "eth-dip-b": alternative_snapshot,
                },
                "market_selection_actions": {
                    "eth-dip-a": "tradable_market",
                    "eth-dip-b": "tradable_market",
                },
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "counterfactual_replaced"
    assert runtime_events[-1]["payload"]["counterfactual_best_market_id"] == "eth-dip-b"
    assert runtime_events[-1]["payload"]["counterfactual_candidate_count"] >= 2


def test_crypto_phase2_strategy_counterfactual_gate_blocks_ambiguous_margin() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "counterfactual_entry_gate_enabled": True,
            "counterfactual_entry_top_k": 1,
            "counterfactual_entry_min_candidates": 2,
            "counterfactual_entry_min_score_margin_bps": 400.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    current_snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-c",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    alternative_snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-d",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    current_fair_value = FairValueEstimate(
        market_id="eth-dip-c",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.70,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 220.0, "gross_edge_bps": 280.0},
    )
    alternative_fair_value = FairValueEstimate(
        market_id="eth-dip-d",
        category=Category.CRYPTO,
        fair_probability=0.15,
        confidence=0.71,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 240.0, "gross_edge_bps": 290.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=current_snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {
                    "eth-dip-c": current_fair_value,
                    "eth-dip-d": alternative_fair_value,
                },
                "snapshots_by_market_id": {
                    "eth-dip-c": current_snapshot,
                    "eth-dip-d": alternative_snapshot,
                },
                "market_selection_actions": {
                    "eth-dip-c": "tradable_market",
                    "eth-dip-d": "tradable_market",
                },
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "counterfactual_margin_too_low"


def test_crypto_phase2_strategy_blocks_entry_when_market_probation_active() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "market_probation_enabled": True,
            "market_probation_loss_streak_for_probation": 2,
            "market_probation_loss_streak_for_quarantine": 3,
            "market_probation_recovery_win_streak_required": 2,
            "market_probation_cooldown_seconds": 300.0,
            "loss_reentry_cooldown_seconds": 0.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 5, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-probation",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-probation",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.78,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 220.0, "gross_edge_bps": 280.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-probation": fair_value},
                "recent_events": (
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "eth-dip-probation",
                            "strategy_id": "crypto.phase2",
                            "net_pnl": -0.2,
                            "closed_at": (now - timedelta(seconds=120)).isoformat(),
                        },
                    },
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "eth-dip-probation",
                            "strategy_id": "crypto.phase2",
                            "net_pnl": -0.1,
                            "closed_at": (now - timedelta(seconds=60)).isoformat(),
                        },
                    },
                ),
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "market_probation_active"


def test_crypto_phase2_strategy_blocks_entry_when_family_trade_budget_is_exhausted() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "family_trade_budget_enabled": True,
            "family_trade_budget_min_samples": 3,
            "family_trade_budget_low_quality_share": 0.25,
            "family_trade_budget_stable_share": 0.5,
            "family_trade_budget_high_quality_share": 0.75,
            "family_trade_budget_lookback_events": 8,
        }
    )
    now = datetime(2026, 3, 28, 0, 5, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-budget",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-budget",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.78,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 220.0, "gross_edge_bps": 280.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-budget": fair_value},
                "execution_feedback_by_family": {
                    "ETH:dip": CryptoExecutionFeedback(
                        maker_fill_rate=0.1,
                        taker_shortfall_bps=15.0,
                        repeated_expiration_rate=0.6,
                        repeated_stop_out_rate=0.7,
                        recommended_route_bias="more_passive",
                    )
                },
                "dynamic_eligibility_gates": {
                    "ETH:dip": CryptoDynamicEligibilityGate(
                        family_key="ETH:dip",
                        sample_count=6,
                        min_net_edge_bps=75.0,
                        taker_max_entry_premium_bps=750.0,
                        repricing_taker_max_entry_premium_bps=90.0,
                        reason_tag="dynamic_more_passive",
                    )
                },
                "recent_events": tuple(
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "eth-dip-budget",
                            "updated_at": (now - timedelta(seconds=10 + i)).isoformat(),
                        },
                    }
                    for i in range(5)
                ),
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "family_trade_budget_exhausted"


def test_crypto_phase2_strategy_filters_extreme_repricing_mispricing() -> None:
    strategy = CryptoPhase2Strategy({"repricing_max_net_edge_bps": 600.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.78,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 900.0, "gross_edge_bps": 950.0},
    )
    runtime_events: list[dict[str, object]] = []

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "_strategy_runtime_events": runtime_events,
            },
        )
    )

    assert signals == []
    assert runtime_events[-1]["event_type"] == "strategy.skipped"
    assert runtime_events[-1]["payload"]["reason"] == "repricing_extreme_mispricing_filtered"
    assert runtime_events[-1]["payload"]["signal_net_edge_bps"] == 900.0
    assert runtime_events[-1]["payload"]["repricing_max_net_edge_bps"] == 600.0


def test_crypto_phase2_strategy_generates_exit_signal_for_existing_position() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.185,
        best_ask_yes=0.19,
        best_bid_no=0.81,
        best_ask_no=0.82,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.185,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.target_price == 0.185
    assert signal.time_in_force == "IOC"
    assert signal.rationale_tags == ("fair_value_reached",)


def test_crypto_phase2_strategy_generates_exit_signal_when_position_intent_missing() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.185,
        best_ask_yes=0.19,
        best_bid_no=0.81,
        best_ask_no=0.82,
    )
    fair_value = _fair_value("repricing_yes")
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.185,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.target_price == 0.185
    assert signal.time_in_force == "IOC"
    assert signal.rationale_tags == ("fair_value_reached",)


def test_crypto_phase2_strategy_generates_sell_no_exit_when_no_position_intent_missing() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.185,
        best_ask_yes=0.19,
        best_bid_no=0.81,
        best_ask_no=0.82,
    )
    fair_value = _fair_value("repricing_yes")
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.89,
        mark_price=0.815,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_NO
    assert signal.token_id == "eth-dip-1000-no"


def test_crypto_phase2_strategy_uses_fallback_fair_value_for_exit_when_missing() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 5.0,
            "time_stop_max_remaining_edge_bps": 10000.0,
            "max_holding_multiplier": 1.0,
            "min_holding_seconds_before_exit": 1.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.49,
        best_ask_yes=0.50,
        best_bid_no=0.50,
        best_ask_no=0.51,
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=10.0,
        average_entry_price=0.52,
        mark_price=0.495,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {},
                "position_intents_by_market_id": {},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.time_in_force in {"IOC", "GTC"}
    assert "fallback_exit_no_fair_value" in signal.rationale_tags or signal.rationale_tags in {
        ("time_stop",),
        ("fair_value_reached",),
        ("aging_exit",),
        ("stale_position_cleanup",),
        ("stop_loss",),
    }


def test_crypto_phase2_strategy_uses_passive_exit_for_stale_position_cleanup() -> None:
    strategy = CryptoPhase2Strategy({"execution_max_holding_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.162,
        best_ask_yes=0.17,
        best_bid_no=0.83,
        best_ask_no=0.84,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.162,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.target_price == 0.172
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 15
    assert signal.rationale_tags == ("stale_position_cleanup",)


def test_crypto_phase2_strategy_does_not_reprice_identical_pending_exit() -> None:
    strategy = CryptoPhase2Strategy({"execution_max_holding_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.162,
        best_ask_yes=0.17,
        best_bid_no=0.83,
        best_ask_no=0.84,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.162,
    )
    pending_order = PendingOrderState(
        order_id="paper-1",
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side="sell_yes",
        limit_price=0.172,
        requested_shares=45.0,
        requested_notional=7.65,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=2),
        updated_at=now - timedelta(seconds=2),
        quote_ttl_seconds=15,
        time_in_force="GTC",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position, pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_submit_second_passive_exit_while_first_pending() -> None:
    strategy = CryptoPhase2Strategy({"execution_max_holding_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )
    pending_order = PendingOrderState(
        order_id="paper-exit-1",
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side="sell_yes",
        limit_price=0.13,
        requested_shares=45.0,
        requested_notional=5.85,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=5),
        updated_at=now - timedelta(seconds=5),
        quote_ttl_seconds=5,
        time_in_force="GTC",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position, pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_respects_exit_repost_cooldown_after_expiry() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "exit_repost_cooldown_seconds": 30.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": "sell_yes",
                            "limit_price": 0.12,
                            "updated_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_submit_second_passive_exit_from_recent_event_lock() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "exit_repost_cooldown_seconds": 30.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": SignalSide.SELL_YES.value,
                            "price": 0.13,
                            "created_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_forces_ioc_after_repeated_time_stop_expiries() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "exit_repost_cooldown_seconds": 0.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "trade_side": "SELL",
                            "limit_price": 0.13,
                            "updated_at": (now - timedelta(seconds=20)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "trade_side": "SELL",
                            "limit_price": 0.13,
                            "updated_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.12
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds is None
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_uses_immediate_ioc_for_taker_repricing_time_stop() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.12
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds is None
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_can_disable_immediate_ioc_for_taker_repricing_time_stop() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "time_stop_force_ioc_for_repricing_taker": False,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.13
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 5
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_allows_configured_time_stop_passive_ttl() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_for_repricing_taker": False,
            "time_stop_passive_quote_ttl_seconds": 12,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.12,
        best_ask_yes=0.14,
        best_bid_no=0.86,
        best_ask_no=0.88,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.12,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 12
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_uses_passive_exit_for_small_adverse_taker_time_stop_when_threshold_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "time_stop_force_ioc_for_repricing_taker": True,
            "time_stop_force_ioc_min_adverse_move_bps": 200.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.108,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.892,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.108,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.11
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 5
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_uses_passive_exit_for_wide_spread_taker_time_stop_when_spread_guard_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "time_stop_force_ioc_for_repricing_taker": True,
            "time_stop_force_ioc_min_adverse_move_bps": 50.0,
            "time_stop_force_ioc_max_spread_bps": 100.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.108,
        best_ask_yes=0.116,
        best_bid_no=0.884,
        best_ask_no=0.892,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.108,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.116
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 5
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_uses_passive_exit_for_high_remaining_edge_taker_time_stop_when_edge_guard_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "time_stop_force_ioc_for_repricing_taker": True,
            "time_stop_force_ioc_min_adverse_move_bps": 50.0,
            "time_stop_force_ioc_max_spread_bps": 200.0,
            "time_stop_force_ioc_max_remaining_edge_bps": 200.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.108,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.892,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.108,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.11
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 5
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_uses_passive_exit_for_low_remaining_edge_taker_time_stop_when_skip_threshold_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "execution_max_holding_seconds": 300.0,
            "time_stop_force_ioc_after_expiries": 2,
            "time_stop_force_ioc_for_repricing_taker": True,
            "time_stop_force_ioc_min_adverse_move_bps": 50.0,
            "time_stop_force_ioc_max_spread_bps": 200.0,
            "time_stop_force_ioc_skip_below_remaining_edge_bps": 100.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.117,
        best_ask_yes=0.119,
        best_bid_no=0.881,
        best_ask_no=0.883,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.11,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.117,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_price == 0.119
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 5
    assert signal.rationale_tags == ("time_stop",)


def test_crypto_phase2_strategy_applies_escalated_entry_exit_containment_from_lineage_events() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "exit_edge_bps": 0.0,
            "escalated_entry_exit_containment_enabled": True,
            "escalated_entry_adverse_fill_exit_bps": 50.0,
            "escalated_entry_adverse_fill_max_remaining_edge_bps": 300.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-escalated-exit",
        best_bid_yes=0.368,
        best_ask_yes=0.369,
        best_bid_no=0.631,
        best_ask_no=0.632,
    )
    fair_value = FairValueEstimate(
        market_id="btc-reach-escalated-exit",
        category=Category.CRYPTO,
        fair_probability=0.37,
        confidence=0.72,
        half_life_seconds=3600,
        observed_probability=0.34,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model",),
        supporting_values={"net_edge_bps": 600.0, "gross_edge_bps": 700.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="btc-reach-escalated-exit-yes",
        created_at=now - timedelta(minutes=2),
        entry_fill_price=0.37,
        entry_mid_price=0.365,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="btc-reach-escalated-exit",
        token_id="btc-reach-escalated-exit-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=2),
        shares=13.5,
        average_entry_price=0.37,
        mark_price=0.368,
    )
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"btc-reach-escalated-exit": fair_value},
                "position_intents_by_market_id": {"btc-reach-escalated-exit": intent},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-escalated-entry",
                            "market_id": "btc-reach-escalated-exit",
                            "side": SignalSide.BUY_YES.value,
                            "diagnostics": {"repricing_fallback_taker_escalated": True},
                            "created_at": (now - timedelta(minutes=2)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "order_id": "paper-escalated-entry",
                            "market_id": "btc-reach-escalated-exit",
                            "token_id": "btc-reach-escalated-exit-yes",
                            "trade_side": "BUY",
                            "fill_source": "taker",
                            "updated_at": (now - timedelta(minutes=2)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rationale_tags == ("adverse_fill_reversal",)
    assert signal.diagnostics["escalated_entry_lineage"] is True
    assert signal.diagnostics["escalated_entry_tail_guard_active"] is True


def test_crypto_phase2_strategy_allows_family_override_to_enable_escalated_tail_guard_for_reach() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "exit_edge_bps": 0.0,
            "escalated_entry_exit_containment_enabled": False,
            "escalated_entry_exit_containment_enabled_reach": True,
            "escalated_entry_adverse_fill_exit_bps_reach": 50.0,
            "escalated_entry_adverse_fill_max_remaining_edge_bps_reach": 300.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-escalated-exit-family-on",
        best_bid_yes=0.368,
        best_ask_yes=0.369,
        best_bid_no=0.631,
        best_ask_no=0.632,
    )
    fair_value = FairValueEstimate(
        market_id="btc-reach-escalated-exit-family-on",
        category=Category.CRYPTO,
        fair_probability=0.37,
        confidence=0.72,
        half_life_seconds=3600,
        observed_probability=0.34,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model",),
        supporting_values={"net_edge_bps": 600.0, "gross_edge_bps": 700.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="btc-reach-escalated-exit-family-on-yes",
        created_at=now - timedelta(minutes=2),
        entry_fill_price=0.37,
        entry_mid_price=0.365,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="btc-reach-escalated-exit-family-on",
        token_id="btc-reach-escalated-exit-family-on-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=2),
        shares=13.5,
        average_entry_price=0.37,
        mark_price=0.368,
    )
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"btc-reach-escalated-exit-family-on": fair_value},
                "position_intents_by_market_id": {"btc-reach-escalated-exit-family-on": intent},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-escalated-entry-reach-on",
                            "market_id": "btc-reach-escalated-exit-family-on",
                            "side": SignalSide.BUY_YES.value,
                            "diagnostics": {"repricing_fallback_taker_escalated": True},
                            "created_at": (now - timedelta(minutes=2)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "order_id": "paper-escalated-entry-reach-on",
                            "market_id": "btc-reach-escalated-exit-family-on",
                            "token_id": "btc-reach-escalated-exit-family-on-yes",
                            "trade_side": "BUY",
                            "fill_source": "taker",
                            "updated_at": (now - timedelta(minutes=2)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rationale_tags == ("adverse_fill_reversal",)
    assert signal.diagnostics["escalated_entry_tail_guard_active"] is True
    assert signal.diagnostics["escalated_entry_tail_guard_family_enabled"] is True


def test_crypto_phase2_strategy_allows_family_override_to_disable_escalated_tail_guard_for_dip() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "exit_edge_bps": 0.0,
            "escalated_entry_exit_containment_enabled": True,
            "escalated_entry_exit_containment_enabled_dip": False,
            "escalated_entry_adverse_fill_exit_bps": 50.0,
            "escalated_entry_adverse_fill_max_remaining_edge_bps": 300.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 2, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-dip-escalated-exit-family-off",
        best_bid_yes=0.368,
        best_ask_yes=0.369,
        best_bid_no=0.631,
        best_ask_no=0.632,
    )
    fair_value = FairValueEstimate(
        market_id="btc-dip-escalated-exit-family-off",
        category=Category.CRYPTO,
        fair_probability=0.37,
        confidence=0.72,
        half_life_seconds=3600,
        observed_probability=0.34,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model",),
        supporting_values={"net_edge_bps": 600.0, "gross_edge_bps": 700.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="btc-dip-escalated-exit-family-off-yes",
        created_at=now - timedelta(minutes=2),
        entry_fill_price=0.37,
        entry_mid_price=0.365,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="btc-dip-escalated-exit-family-off",
        token_id="btc-dip-escalated-exit-family-off-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=2),
        shares=13.5,
        average_entry_price=0.37,
        mark_price=0.368,
    )
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"btc-dip-escalated-exit-family-off": fair_value},
                "position_intents_by_market_id": {"btc-dip-escalated-exit-family-off": intent},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-escalated-entry-dip-off",
                            "market_id": "btc-dip-escalated-exit-family-off",
                            "side": SignalSide.BUY_YES.value,
                            "diagnostics": {"repricing_fallback_taker_escalated": True},
                            "created_at": (now - timedelta(minutes=2)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "order_id": "paper-escalated-entry-dip-off",
                            "market_id": "btc-dip-escalated-exit-family-off",
                            "token_id": "btc-dip-escalated-exit-family-off-yes",
                            "trade_side": "BUY",
                            "fill_source": "taker",
                            "updated_at": (now - timedelta(minutes=2)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_counts_stale_exit_cancels_toward_ioc_escalation() -> None:
    strategy = CryptoPhase2Strategy({"time_stop_force_ioc_after_expiries": 2})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.185,
        best_ask_yes=0.19,
        best_bid_no=0.81,
        best_ask_no=0.82,
    )
    fair_value = _fair_value("repricing_yes")
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=45.0,
        average_entry_price=0.11,
        mark_price=0.185,
    )
    context = {
        "dashboard_state": _dashboard(position=position),
        "fair_values_by_market_id": {"eth-dip-1000": fair_value},
        "position_intents_by_market_id": {"eth-dip-1000": intent},
        "recent_events": [
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "order_id": "order-1",
                    "side": SignalSide.SELL_YES.value,
                    "reason": "stale_ttl_cancel",
                    "created_at": (now - timedelta(seconds=90)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "order_id": "order-1",
                    "side": SignalSide.SELL_YES.value,
                    "reason": "exchange_canceled",
                    "created_at": (now - timedelta(seconds=89)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "eth-dip-1000",
                    "order_id": "order-2",
                    "side": SignalSide.SELL_YES.value,
                    "reason": "stale_ttl_cancel",
                    "created_at": (now - timedelta(seconds=40)).isoformat(),
                },
            },
        ],
    }

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context=context))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds is None


def test_crypto_phase2_strategy_uses_passive_exit_first_for_adverse_fill_reversal() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.51,
        best_ask_yes=0.52,
        best_bid_no=0.48,
        best_ask_no=0.49,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.515,
        confidence=0.75,
        half_life_seconds=1800,
        observed_probability=0.50,
        model_id="crypto.phase1.fused",
        rationale_tags=("repricing",),
        supporting_values={"net_edge_bps": 150.0, "gross_edge_bps": 220.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.52,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=10.0,
        average_entry_price=0.52,
        mark_price=0.51,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rationale_tags == ("adverse_fill_reversal",)
    assert signal.time_in_force == "GTC"
    assert signal.quote_ttl_seconds == 5
    assert signal.target_price == 0.52


def test_crypto_phase2_strategy_forces_ioc_for_adverse_fill_reversal_when_enabled() -> None:
    strategy = CryptoPhase2Strategy({"adverse_fill_force_ioc": True})
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.51,
        best_ask_yes=0.52,
        best_bid_no=0.48,
        best_ask_no=0.49,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.515,
        confidence=0.75,
        half_life_seconds=1800,
        observed_probability=0.50,
        model_id="crypto.phase1.fused",
        rationale_tags=("repricing",),
        supporting_values={"net_edge_bps": 150.0, "gross_edge_bps": 220.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.52,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=10.0,
        average_entry_price=0.52,
        mark_price=0.51,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rationale_tags == ("adverse_fill_reversal",)
    assert signal.time_in_force == "IOC"
    assert signal.quote_ttl_seconds is None
    assert signal.target_price == 0.51


def test_crypto_phase2_strategy_scales_out_first_time_stop_exit_when_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "exit_scaleout_enabled": True,
            "time_stop_scaleout_fraction": 0.5,
            "execution_max_holding_seconds": 5.0,
            "max_holding_multiplier": 1.0,
            "time_stop_max_remaining_edge_bps": 10000.0,
            "min_holding_seconds_before_exit": 1.0,
            "adverse_fill_exit_bps": 10000.0,
            "stop_loss_bps": 10000.0,
            "aging_exit_edge_bps": -1.0,
            "stale_exit_edge_bps": -1.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.49,
        best_ask_yes=0.50,
        best_bid_no=0.50,
        best_ask_no=0.51,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.53,
        confidence=0.75,
        half_life_seconds=5,
        observed_probability=0.50,
        model_id="crypto.phase1.fused",
        rationale_tags=("repricing",),
        supporting_values={"net_edge_bps": 200.0, "gross_edge_bps": 260.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=2),
        entry_fill_price=0.52,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=2),
        shares=10.0,
        average_entry_price=0.52,
        mark_price=0.495,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rationale_tags == ("time_stop",)
    assert signal.target_size == 2.5


def test_crypto_phase2_strategy_scales_out_first_adverse_fill_exit_when_enabled() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "exit_scaleout_enabled": True,
            "adverse_fill_scaleout_fraction": 0.4,
            "min_holding_seconds_before_exit": 1.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 20, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.51,
        best_ask_yes=0.52,
        best_bid_no=0.48,
        best_ask_no=0.49,
    )
    fair_value = FairValueEstimate(
        market_id="eth-dip-1000",
        category=Category.CRYPTO,
        fair_probability=0.515,
        confidence=0.75,
        half_life_seconds=1800,
        observed_probability=0.50,
        model_id="crypto.phase1.fused",
        rationale_tags=("repricing",),
        supporting_values={"net_edge_bps": 150.0, "gross_edge_bps": 220.0},
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    intent = build_position_intent(
        fair_value=fair_value,
        classification=classification,
        token_id="eth-dip-1000-yes",
        created_at=now - timedelta(minutes=10),
        entry_fill_price=0.52,
        entry_fill_source="taker",
    )
    position = PositionState(
        market_id="eth-dip-1000",
        token_id="eth-dip-1000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=10),
        shares=10.0,
        average_entry_price=0.52,
        mark_price=0.51,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=position),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "position_intents_by_market_id": {"eth-dip-1000": intent},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rationale_tags == ("adverse_fill_reversal",)
    assert signal.target_size == 2.08


def test_crypto_phase2_strategy_respects_reentry_block() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    reentry_state = CryptoReentryState(
        market_id="eth-dip-1000",
        blocked_until=now + timedelta(minutes=5),
        stop_out_count=1,
        quarantine_active=False,
        reason="cooldown",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "reentry_state_by_market_id": {"eth-dip-1000": reentry_state},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_respects_entry_repost_cooldown_after_expiry() -> None:
    strategy = CryptoPhase2Strategy({"entry_repost_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": "buy_yes",
                            "limit_price": 0.1,
                            "updated_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_respects_entry_failure_cooldown_after_rejection() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_repost_cooldown_seconds": 120.0,
            "entry_failure_cooldown_seconds": 180.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.rejected",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "side": "buy_yes",
                            "reason": "execution submit failed: RuntimeError: FOK couldn't be fully filled",
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_blocks_repeat_entry_after_recent_submission_same_market() -> None:
    strategy = CryptoPhase2Strategy({"entry_failure_cooldown_seconds": 180.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "side": "buy_yes",
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_blocks_same_market_reentry_after_recent_loss() -> None:
    strategy = CryptoPhase2Strategy({"loss_reentry_cooldown_seconds": 1800.0})
    now = datetime(2026, 3, 28, 0, 10, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "realized_pnl": -0.22,
                            "net_pnl": -0.22,
                            "closed_at": (now - timedelta(minutes=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_allows_same_market_reentry_after_loss_cooldown_expires() -> None:
    strategy = CryptoPhase2Strategy({"loss_reentry_cooldown_seconds": 300.0})
    now = datetime(2026, 3, 28, 0, 10, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "realized_pnl": -0.22,
                            "net_pnl": -0.22,
                            "closed_at": (now - timedelta(minutes=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1


def test_crypto_phase2_strategy_quarantines_market_after_configured_loss_count() -> None:
    strategy = CryptoPhase2Strategy({"max_loss_trades_per_market": 1, "loss_reentry_cooldown_seconds": 0.0})
    now = datetime(2026, 3, 28, 1, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "realized_pnl": -0.12,
                            "net_pnl": -0.12,
                            "closed_at": (now - timedelta(minutes=40)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_blocks_sibling_market_after_recent_exposure_group_loss() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "loss_reentry_cooldown_seconds": 1800.0,
            "max_loss_trades_per_market": 0,
        }
    )
    now = datetime(2026, 3, 28, 0, 10, tzinfo=UTC)
    snapshot = MarketSnapshot(
        market_id="btc-above-69000",
        token_id="btc-above-69000-yes",
        slug="will-the-price-of-bitcoin-be-above-69000-on-march-31",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 3, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
        tick_size=0.01,
        liquidity_score=0.5,
        metadata={
            "event_slug": "btc-price-march-31",
            "no_token_id": "btc-above-69000-no",
        },
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-above-69000": fair_value},
                "recent_events": (
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-above-68000",
                            "exposure_group_id": "crypto:btc-price-march-31",
                            "realized_pnl": -0.18,
                            "net_pnl": -0.18,
                            "closed_at": (now - timedelta(minutes=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_quarantines_exposure_group_after_configured_loss_count() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "loss_reentry_cooldown_seconds": 0.0,
            "max_loss_trades_per_exposure_group": 1,
        }
    )
    now = datetime(2026, 3, 28, 1, 0, tzinfo=UTC)
    snapshot = MarketSnapshot(
        market_id="btc-above-69000",
        token_id="btc-above-69000-yes",
        slug="will-the-price-of-bitcoin-be-above-69000-on-march-31",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 3, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
        tick_size=0.01,
        liquidity_score=0.5,
        metadata={
            "event_slug": "btc-price-march-31",
            "no_token_id": "btc-above-69000-no",
        },
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-above-69000": fair_value},
                "recent_events": (
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "btc-above-68000",
                            "exposure_group_id": "crypto:btc-price-march-31",
                            "realized_pnl": -0.18,
                            "net_pnl": -0.18,
                            "closed_at": (now - timedelta(minutes=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []
def test_crypto_phase2_strategy_blocks_sibling_market_when_same_thesis_position_exists() -> None:
    strategy = CryptoPhase2Strategy({"single_active_market_per_thesis": True})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-dip-45000",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")
    existing_position = PositionState(
        market_id="btc-dip-40000",
        token_id="btc-dip-40000-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        opened_at=now - timedelta(minutes=2),
        shares=10.0,
        average_entry_price=0.5,
        thesis_group_id="crypto:eth:dip",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(position=existing_position),
                "fair_values_by_market_id": {"btc-dip-45000": fair_value},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_quarantines_market_after_repeated_no_fill_attempts() -> None:
    strategy = CryptoPhase2Strategy({"max_no_fill_entry_attempts_per_market": 2})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-dip-50000",
        best_bid_yes=0.36,
        best_ask_yes=0.37,
        best_bid_no=0.63,
        best_ask_no=0.64,
    )
    fair_value = _fair_value("repricing_yes")
    context = {
        "dashboard_state": _dashboard(),
        "fair_values_by_market_id": {"btc-dip-50000": fair_value},
        "market_selection_actions": {"btc-dip-50000": "selective_market"},
        "market_selection_reasons": {"btc-dip-50000": ("wide_spread",)},
        "recent_events": [
            {
                "event_type": "order.submitted",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-1",
                    "created_at": (now - timedelta(seconds=60)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-1",
                    "reason": "stale_ttl_cancel",
                    "updated_at": (now - timedelta(seconds=30)).isoformat(),
                },
            },
            {
                "event_type": "order.submitted",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-2",
                    "created_at": (now - timedelta(seconds=20)).isoformat(),
                },
            },
            {
                "event_type": "order.canceled",
                "payload": {
                    "market_id": "btc-dip-50000",
                    "side": "buy_yes",
                    "order_id": "live-2",
                    "reason": "stale_ttl_cancel",
                    "updated_at": (now - timedelta(seconds=10)).isoformat(),
                },
            },
        ],
    }

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context=context))

    assert signals == []


def test_crypto_phase2_strategy_allows_retry_after_failure_cooldown_expires() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_repost_cooldown_seconds": 120.0,
            "entry_failure_cooldown_seconds": 60.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-2027",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-2027": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.rejected",
                        "payload": {
                            "market_id": "btc-reach-2027",
                            "side": "buy_yes",
                            "reason": "execution submit failed: RuntimeError: exchange rejected order",
                            "created_at": (now - timedelta(seconds=90)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1


def test_crypto_phase2_strategy_respects_exit_failure_cooldown_after_rejection() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "min_confidence": 0.6,
            "min_net_edge_bps": 50.0,
            "exit_failure_cooldown_seconds": 180.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 20, tzinfo=UTC),
        market_id="701502",
        best_bid_yes=0.55,
        best_ask_yes=0.56,
        best_bid_no=0.43,
        best_ask_no=0.44,
    )
    position = PositionState(
        market_id="701502",
        token_id="701502-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        shares=11.111111,
        average_entry_price=0.4509,
        opened_at=snapshot.timestamp - timedelta(minutes=10),
    )
    fair_value = FairValueEstimate(
        market_id="701502",
        category=Category.CRYPTO,
        fair_probability=0.4294996,
        confidence=0.75,
        half_life_seconds=60,
        observed_probability=0.565,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model",),
        supporting_values={"gross_edge_bps": -1355.0, "net_edge_bps": 1240.0},
    )
    rejected_at = snapshot.timestamp.isoformat()
    context = {
        "dashboard_state": _dashboard(position=position),
        "fair_values_by_market_id": {"701502": fair_value},
        "position_intents_by_market_id": {
            "701502": build_position_intent(
                fair_value=fair_value,
                classification=classify_crypto_signal(fair_value=fair_value),
                token_id="701502-no",
                created_at=snapshot.timestamp - timedelta(minutes=10),
                entry_fill_price=0.4509,
            )
        },
        "recent_events": [
            {
                "event_type": "order.rejected",
                "payload": {
                    "market_id": "701502",
                    "side": SignalSide.SELL_NO.value,
                    "created_at": rejected_at,
                },
            }
        ],
    }
    signals = list(asyncio.run(strategy.evaluate(snapshot, context)))
    assert signals == []


def test_crypto_phase2_strategy_skips_entry_when_series_is_blocked() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "blocked_series_keys": {"eth-dip-ladder"},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_skips_entry_when_market_is_blocked() -> None:
    strategy = CryptoPhase2Strategy({})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "blocked_market_ids": {"eth-dip-1000"},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_expand_notional_when_feedback_is_more_passive() -> None:
    strategy = CryptoPhase2Strategy({"default_notional": 5.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.5,
                    taker_shortfall_bps=20.0,
                    repeated_expiration_rate=0.4,
                    repeated_stop_out_rate=0.7,
                    recommended_route_bias="more_passive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size <= 5.0
    assert signal.diagnostics["execution_feedback_bias"] == "more_passive"
    assert signal.diagnostics["quality_sizing_status"] == "quality_sizing_applied"


def test_crypto_phase2_strategy_becomes_more_aggressive_when_feedback_says_so() -> None:
    strategy = CryptoPhase2Strategy({"default_notional": 5.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.0,
                    taker_shortfall_bps=0.0,
                    repeated_expiration_rate=1.0,
                    repeated_stop_out_rate=0.0,
                    recommended_route_bias="more_aggressive",
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.quote_ttl_seconds == 30
    assert signal.target_size > 5.0
    assert signal.diagnostics["execution_feedback_bias"] == "more_aggressive"


def test_crypto_phase2_strategy_expands_notional_for_high_quality_signal_within_bounds() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "default_notional": 5.0,
            "quality_sizing_min_multiplier": 0.80,
            "quality_sizing_max_multiplier": 1.20,
            "quality_sizing_edge_reference_bps": 600.0,
            "quality_sizing_confidence_weight": 0.0,
            "quality_sizing_edge_weight": 1.0,
            "quality_sizing_route_feedback_weight": 0.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=1.0,
                    taker_shortfall_bps=0.0,
                    repeated_expiration_rate=0.0,
                    repeated_stop_out_rate=0.0,
                    recommended_route_bias="stable",
                ),
            },
        )
    )
    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size > 5.0
    assert signal.target_size <= 6.0
    assert signal.diagnostics["quality_sizing_multiplier"] <= 1.2


def test_crypto_phase2_strategy_shrinks_notional_for_low_quality_signal_without_zeroing() -> None:
    strategy = CryptoPhase2Strategy(
            {
                "default_notional": 5.0,
                "min_net_edge_bps": 20.0,
                "maker_min_edge_bps": 20.0,
                "quality_sizing_min_multiplier": 0.80,
                "quality_sizing_max_multiplier": 1.20,
                "quality_sizing_edge_reference_bps": 1000.0,
            "quality_sizing_confidence_weight": 0.0,
            "quality_sizing_edge_weight": 1.0,
            "quality_sizing_route_feedback_weight": 0.0,
        }
    )
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1500",
        best_bid_yes=0.33,
        best_ask_yes=0.35,
        best_bid_no=0.65,
        best_ask_no=0.67,
    )
    fair_value = _fair_value("skip_low_edge")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1500": fair_value},
                "execution_feedback": CryptoExecutionFeedback(
                    maker_fill_rate=0.0,
                    taker_shortfall_bps=200.0,
                    repeated_expiration_rate=1.0,
                    repeated_stop_out_rate=1.0,
                    recommended_route_bias="more_passive",
                ),
            },
        )
    )
    assert len(signals) == 1
    signal = signals[0]
    assert 0.0 < signal.target_size < 5.0
    assert signal.diagnostics["quality_sizing_multiplier"] >= 0.8


def test_crypto_phase2_strategy_falls_back_to_base_notional_when_quality_components_missing() -> None:
    strategy = CryptoPhase2Strategy({"default_notional": 5.0})
    snapshot = _snapshot(
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=UTC),
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
            },
        )
    )
    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size == 5.0
    assert signal.diagnostics["quality_sizing_status"] == "quality_components_missing"


def test_crypto_phase2_strategy_applies_fragile_closer_notional_haircut_when_expired_ratio_is_high() -> None:
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    strategy = CryptoPhase2Strategy(
        {
            "default_notional": 5.0,
            "quality_sizing_enabled": False,
            "fragile_closer_notional_haircut_enabled": True,
            "fragile_closer_notional_haircut_min_multiplier": 0.5,
            "fragile_closer_notional_haircut_max_multiplier": 1.0,
            "fragile_closer_notional_haircut_expired_ratio_threshold": 0.4,
            "fragile_closer_notional_haircut_min_samples": 4,
            "fragile_closer_notional_haircut_lookback_events": 12,
        }
    )
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "created_at": (now - timedelta(seconds=60)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "created_at": (now - timedelta(seconds=45)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.canceled",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "reason": "stale_ttl_cancel",
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "closed_at": (now - timedelta(seconds=15)).isoformat(),
                        },
                    },
                ),
            },
        )
    )
    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size < 5.0
    assert signal.diagnostics["execution_feedback_notional"] < 5.0
    assert signal.diagnostics["execution_feedback_notional_pre_haircut"] == 5.0
    assert signal.diagnostics["fragile_closer_notional_status"] == "fragile_closer_haircut_applied"
    assert signal.diagnostics["fragile_closer_notional_sample_count"] == 4
    assert signal.diagnostics["fragile_closer_notional_expired_count"] == 3
    assert signal.diagnostics["fragile_closer_notional_closed_count"] == 1


def test_crypto_phase2_strategy_keeps_base_notional_when_fragile_closer_samples_are_insufficient() -> None:
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    strategy = CryptoPhase2Strategy(
        {
            "default_notional": 5.0,
            "quality_sizing_enabled": False,
            "fragile_closer_notional_haircut_enabled": True,
            "fragile_closer_notional_haircut_min_multiplier": 0.5,
            "fragile_closer_notional_haircut_max_multiplier": 1.0,
            "fragile_closer_notional_haircut_expired_ratio_threshold": 0.4,
            "fragile_closer_notional_haircut_min_samples": 6,
            "fragile_closer_notional_haircut_lookback_events": 12,
        }
    )
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "created_at": (now - timedelta(seconds=60)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "created_at": (now - timedelta(seconds=45)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.canceled",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "reason": "stale_ttl_cancel",
                            "created_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "closed_at": (now - timedelta(seconds=15)).isoformat(),
                        },
                    },
                ),
            },
        )
    )
    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size == 5.0
    assert signal.diagnostics["execution_feedback_notional"] == 5.0
    assert signal.diagnostics["fragile_closer_notional_multiplier"] == 1.0
    assert signal.diagnostics["fragile_closer_notional_status"] == "fragile_closer_insufficient_samples"
    assert signal.diagnostics["fragile_closer_notional_sample_count"] == 4


def test_crypto_phase2_strategy_applies_family_preset_registry() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "default_notional": 5.0,
            "taker_urgency_threshold": 0.72,
            "preset_registry": {
                "btc_reach_fast": {
                    "match": {"underlying": "BTC", "event_family": "reach"},
                    "overrides": {
                        "default_notional": 8.0,
                        "taker_urgency_threshold": 0.9,
                    },
                }
            },
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="btc-reach-100k",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"btc-reach-100k": fair_value},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size == 8.0
    assert signal.diagnostics["phase2_preset"] == "btc_reach_fast"
    assert signal.time_in_force == "GTC"


def test_crypto_phase2_strategy_applies_family_preset_registry_for_numeric_market_id_with_bitcoin_slug() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "default_notional": 5.0,
            "preset_registry": {
                "btc_reach_fast": {
                    "match": {"underlying": "BTC", "event_family": "reach"},
                    "overrides": {"default_notional": 8.0},
                }
            },
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = MarketSnapshot(
        market_id="701496",
        token_id="701496-yes",
        slug="will-bitcoin-reach-100000-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.91,
        tick_size=0.01,
        liquidity_score=0.5,
        metadata={"event_slug": "will-bitcoin-reach-100000", "no_token_id": "701496-no"},
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"701496": fair_value},
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.target_size == 8.0
    assert signal.diagnostics["phase2_preset"] == "btc_reach_fast"


def test_crypto_phase2_strategy_uses_dedicated_entry_market_cooldown() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_failure_cooldown_seconds": 30.0,
            "entry_market_cooldown_seconds": 120.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1000",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-1000": fair_value},
                "recent_events": (
                    {
                        "event_type": "signal.generated",
                        "payload": {
                            "market_id": "eth-dip-1000",
                            "side": SignalSide.BUY_YES.value,
                            "generated_at": (now - timedelta(seconds=60)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_allows_fast_repost_for_repricing_maker_fallback() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_repost_cooldown_seconds": 30.0,
            "repricing_fallback_entry_repost_cooldown_seconds": 5.0,
            "repricing_taker_max_entry_premium_bps": 90.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-fast-repost",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-fast-repost": fair_value},
                "market_selection_actions": {"eth-dip-fast-repost": "tradable_market"},
                "market_selection_reasons": {"eth-dip-fast-repost": ("tight_runtime_spread",)},
                "recent_events": (
                    {
                        "event_type": "order.expired",
                        "payload": {
                            "market_id": "eth-dip-fast-repost",
                            "side": SignalSide.BUY_YES.value,
                            "limit_price": 0.10,
                            "updated_at": (now - timedelta(seconds=10)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.rationale_tags == ("repricing_taker_too_expensive", "maker_fallback")


def test_crypto_phase2_strategy_allows_faster_market_retry_for_repricing_maker_fallback() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "entry_market_cooldown_seconds": 120.0,
            "repricing_fallback_entry_market_cooldown_seconds": 20.0,
            "repricing_taker_max_entry_premium_bps": 90.0,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-fast-market-retry",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-fast-market-retry": fair_value},
                "market_selection_actions": {"eth-dip-fast-market-retry": "tradable_market"},
                "market_selection_reasons": {"eth-dip-fast-market-retry": ("tight_runtime_spread",)},
                "recent_events": (
                    {
                        "event_type": "signal.generated",
                        "payload": {
                            "market_id": "eth-dip-fast-market-retry",
                            "side": SignalSide.BUY_YES.value,
                            "generated_at": (now - timedelta(seconds=60)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.rationale_tags == ("repricing_taker_too_expensive", "maker_fallback")


def test_crypto_phase2_strategy_escalates_repricing_maker_fallback_to_taker_after_no_fill_attempts() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "taker_urgency_threshold": 0.0,
            "taker_max_entry_premium_bps": 600.0,
            "repricing_taker_max_entry_premium_bps": 90.0,
            "repricing_fallback_taker_after_no_fill_attempts": 2,
            "entry_repost_cooldown_seconds": 0.0,
            "repricing_fallback_entry_repost_cooldown_seconds": 0.0,
            "entry_market_cooldown_seconds": 0.0,
            "repricing_fallback_entry_market_cooldown_seconds": 0.0,
            "entry_failure_cooldown_seconds": 0.0,
            "max_no_fill_entry_attempts_per_market": 10,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-fallback-escalate",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-fallback-escalate": fair_value},
                "market_selection_actions": {"eth-dip-fallback-escalate": "tradable_market"},
                "market_selection_reasons": {"eth-dip-fallback-escalate": ("tight_runtime_spread",)},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-old-1",
                            "market_id": "eth-dip-fallback-escalate",
                            "side": SignalSide.BUY_YES.value,
                            "rationale_tags": ["repricing_taker_too_expensive", "maker_fallback"],
                            "created_at": (now - timedelta(seconds=40)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-old-2",
                            "market_id": "eth-dip-fallback-escalate",
                            "side": SignalSide.BUY_YES.value,
                            "rationale_tags": ["repricing_taker_too_expensive", "maker_fallback"],
                            "created_at": (now - timedelta(seconds=20)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "IOC"
    assert signal.rationale_tags == ("repricing_edge", "taker")
    assert signal.diagnostics["repricing_fallback_no_fill_attempts"] == 2
    assert signal.diagnostics["repricing_fallback_taker_escalated"] is True
    assert signal.diagnostics["repricing_fallback_taker_escalation_block_reason"] is None


def test_crypto_phase2_strategy_blocks_repricing_fallback_escalation_when_spread_too_wide() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "taker_urgency_threshold": 1.0,
            "taker_max_entry_premium_bps": 600.0,
            "repricing_taker_max_entry_premium_bps": 1.0,
            "high_edge_taker_min_edge_bps": 5000.0,
            "repricing_fallback_taker_after_no_fill_attempts": 2,
            "repricing_fallback_taker_escalation_max_spread_bps": 80.0,
            "entry_repost_cooldown_seconds": 0.0,
            "repricing_fallback_entry_repost_cooldown_seconds": 0.0,
            "entry_market_cooldown_seconds": 0.0,
            "repricing_fallback_entry_market_cooldown_seconds": 0.0,
            "entry_failure_cooldown_seconds": 0.0,
            "max_no_fill_entry_attempts_per_market": 10,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-fallback-escalate-spread-guard",
        best_bid_yes=0.10,
        best_ask_yes=0.12,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"eth-dip-fallback-escalate-spread-guard": fair_value},
                "market_selection_actions": {"eth-dip-fallback-escalate-spread-guard": "tradable_market"},
                "market_selection_reasons": {"eth-dip-fallback-escalate-spread-guard": ("tight_runtime_spread",)},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-old-1",
                            "market_id": "eth-dip-fallback-escalate-spread-guard",
                            "side": SignalSide.BUY_YES.value,
                            "rationale_tags": ["repricing_taker_too_expensive", "maker_fallback"],
                            "created_at": (now - timedelta(seconds=40)).isoformat(),
                        },
                    },
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-old-2",
                            "market_id": "eth-dip-fallback-escalate-spread-guard",
                            "side": SignalSide.BUY_YES.value,
                            "rationale_tags": ["repricing_taker_too_expensive", "maker_fallback"],
                            "created_at": (now - timedelta(seconds=20)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.diagnostics["repricing_fallback_no_fill_attempts"] == 2
    assert signal.diagnostics["repricing_fallback_taker_escalated"] is False
    assert (
        signal.diagnostics["repricing_fallback_taker_escalation_block_reason"]
        == "repricing_fallback_escalation_spread_too_wide"
    )


def test_crypto_phase2_strategy_ignores_stale_pending_order_for_same_thesis_lock() -> None:
    strategy = CryptoPhase2Strategy({"thesis_entry_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1200",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    stale_pending_order = PendingOrderState(
        order_id="paper-stale",
        market_id="eth-dip-1100",
        token_id="eth-dip-1100-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side=SignalSide.BUY_YES.value,
        limit_price=0.10,
        requested_shares=50.0,
        requested_notional=5.0,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=30),
        updated_at=now - timedelta(seconds=30),
        quote_ttl_seconds=10,
        thesis_group_id="crypto:eth:dip",
        exposure_group_id="crypto:eth-alt-dip-ladder",
        underlying_group_id="crypto:eth",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(pending_orders=(stale_pending_order,)),
                "fair_values_by_market_id": {"eth-dip-1200": fair_value},
            },
        )
    )

    assert len(signals) == 1


def test_crypto_phase2_strategy_keeps_fresh_pending_order_lock_for_same_thesis() -> None:
    strategy = CryptoPhase2Strategy({"thesis_entry_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-1200",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    fresh_pending_order = PendingOrderState(
        order_id="paper-fresh",
        market_id="eth-dip-1100",
        token_id="eth-dip-1100-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side=SignalSide.BUY_YES.value,
        limit_price=0.10,
        requested_shares=50.0,
        requested_notional=5.0,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=5),
        updated_at=now - timedelta(seconds=5),
        quote_ttl_seconds=10,
        thesis_group_id="crypto:eth:dip",
        exposure_group_id="crypto:eth-alt-dip-ladder",
        underlying_group_id="crypto:eth",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(pending_orders=(fresh_pending_order,)),
                "fair_values_by_market_id": {"eth-dip-1200": fair_value},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_does_not_lock_same_bullish_thesis_on_unfilled_submission() -> None:
    strategy = CryptoPhase2Strategy({"thesis_entry_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    reach_snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=0.09,
        best_ask_yes=0.10,
        best_bid_no=0.90,
        best_ask_no=0.91,
        tick_size=0.01,
        liquidity_score=0.8,
        metadata={
            "question": "Will Bitcoin hit $150K by December 31, 2026?",
            "event_slug": "btc-reach-2026",
            "no_token_id": "reach-no",
        },
    )
    fair_value = FairValueEstimate(
        market_id="reach-150k",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.8,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 140.0, "gross_edge_bps": 400.0},
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=reach_snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"reach-150k": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "market_id": "dip-50k",
                            "side": SignalSide.BUY_NO.value,
                            "thesis_group_id": "crypto:btc:bullish",
                            "updated_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1


def test_crypto_phase2_strategy_locks_same_bullish_thesis_after_fill() -> None:
    strategy = CryptoPhase2Strategy({"thesis_entry_cooldown_seconds": 120.0})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    reach_snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=0.09,
        best_ask_yes=0.10,
        best_bid_no=0.90,
        best_ask_no=0.91,
        tick_size=0.01,
        liquidity_score=0.8,
        metadata={
            "question": "Will Bitcoin hit $150K by December 31, 2026?",
            "event_slug": "btc-reach-2026",
            "no_token_id": "reach-no",
        },
    )
    fair_value = FairValueEstimate(
        market_id="reach-150k",
        category=Category.CRYPTO,
        fair_probability=0.14,
        confidence=0.8,
        half_life_seconds=3600,
        observed_probability=0.10,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 140.0, "gross_edge_bps": 400.0},
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=reach_snapshot,
            context={
                "dashboard_state": _dashboard(),
                "fair_values_by_market_id": {"reach-150k": fair_value},
                "recent_events": (
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "market_id": "dip-50k",
                            "side": SignalSide.BUY_NO.value,
                            "thesis_group_id": "crypto:btc:bullish",
                            "updated_at": (now - timedelta(seconds=30)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_blocks_conflicting_exposure_group_thesis() -> None:
    strategy = CryptoPhase2Strategy({})
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = MarketSnapshot(
        market_id="btc-above-68000",
        token_id="btc-above-68000-yes",
        slug="bitcoin-above-68000-on-april-5",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 4, 5, 16, 0, tzinfo=UTC),
        best_bid_yes=0.38,
        best_ask_yes=0.39,
        best_bid_no=0.61,
        best_ask_no=0.62,
        tick_size=0.01,
        liquidity_score=0.9,
        metadata={
            "question": "Will the price of Bitcoin be above $68,000 on April 5?",
            "event_slug": "bitcoin-above-on-april-5",
            "no_token_id": "btc-above-68000-no",
        },
    )
    fair_value = FairValueEstimate(
        market_id="btc-above-68000",
        category=Category.CRYPTO,
        fair_probability=0.52,
        confidence=0.8,
        half_life_seconds=3600,
        observed_probability=0.38,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 1100.0, "gross_edge_bps": 1200.0},
    )
    pending_order = PendingOrderState(
        order_id="paper-1",
        market_id="btc-above-66000",
        token_id="btc-above-66000-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side=SignalSide.BUY_NO.value,
        limit_price=0.41,
        requested_shares=12.0,
        requested_notional=5.0,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=5),
        updated_at=now - timedelta(seconds=5),
        exposure_group_id="crypto:bitcoin-above-on-april-5",
        thesis_group_id="crypto:btc:bearish",
        underlying_group_id="crypto:btc",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"btc-above-68000": fair_value},
                "market_selection_actions": {"btc-above-68000": "tradable_market"},
                "market_selection_reasons": {"btc-above-68000": ()},
            },
        )
    )

    assert signals == []


def test_crypto_phase2_strategy_allows_refreshable_same_market_repricing_fallback_pending_order() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "taker_urgency_threshold": 0.62,
            "repricing_taker_max_entry_premium_bps": 90.0,
            "taker_slippage_guard_bps": 20.0,
            "repricing_fallback_quote_ttl_seconds": 20,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-refreshable",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    pending_order = PendingOrderState(
        order_id="paper-refreshable",
        market_id="eth-dip-refreshable",
        token_id="eth-dip-refreshable-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side=SignalSide.BUY_YES.value,
        limit_price=0.10,
        requested_shares=50.0,
        requested_notional=5.0,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=11),
        updated_at=now - timedelta(seconds=11),
        time_in_force="GTC",
        quote_ttl_seconds=20,
        exposure_group_id="crypto:eth-dip-refreshable",
        thesis_group_id="crypto:eth:bullish",
        underlying_group_id="crypto:eth",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"eth-dip-refreshable": fair_value},
                "market_selection_actions": {"eth-dip-refreshable": "tradable_market"},
                "market_selection_reasons": {"eth-dip-refreshable": ("tight_runtime_spread",)},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-refreshable",
                            "market_id": "eth-dip-refreshable",
                            "side": SignalSide.BUY_YES.value,
                            "rationale_tags": ["repricing_taker_too_expensive", "maker_fallback"],
                            "created_at": (now - timedelta(seconds=11)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.time_in_force == "GTC"
    assert signal.rationale_tags == ("repricing_taker_too_expensive", "maker_fallback")


def test_crypto_phase2_strategy_keeps_fresh_same_market_repricing_fallback_pending_order_blocked() -> None:
    strategy = CryptoPhase2Strategy(
        {
            "taker_urgency_threshold": 0.62,
            "repricing_taker_max_entry_premium_bps": 90.0,
            "taker_slippage_guard_bps": 20.0,
            "repricing_fallback_quote_ttl_seconds": 20,
        }
    )
    now = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
    snapshot = _snapshot(
        timestamp=now,
        market_id="eth-dip-refreshable",
        best_bid_yes=0.10,
        best_ask_yes=0.11,
        best_bid_no=0.89,
        best_ask_no=0.90,
    )
    fair_value = _fair_value("repricing_yes")
    pending_order = PendingOrderState(
        order_id="paper-refreshable",
        market_id="eth-dip-refreshable",
        token_id="eth-dip-refreshable-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side=SignalSide.BUY_YES.value,
        limit_price=0.10,
        requested_shares=50.0,
        requested_notional=5.0,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=now - timedelta(seconds=5),
        updated_at=now - timedelta(seconds=5),
        time_in_force="GTC",
        quote_ttl_seconds=20,
        exposure_group_id="crypto:eth-dip-refreshable",
        thesis_group_id="crypto:eth:bullish",
        underlying_group_id="crypto:eth",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={
                "dashboard_state": _dashboard(pending_orders=(pending_order,)),
                "fair_values_by_market_id": {"eth-dip-refreshable": fair_value},
                "market_selection_actions": {"eth-dip-refreshable": "tradable_market"},
                "market_selection_reasons": {"eth-dip-refreshable": ("tight_runtime_spread",)},
                "recent_events": (
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "paper-refreshable",
                            "market_id": "eth-dip-refreshable",
                            "side": SignalSide.BUY_YES.value,
                            "rationale_tags": ["repricing_taker_too_expensive", "maker_fallback"],
                            "created_at": (now - timedelta(seconds=5)).isoformat(),
                        },
                    },
                ),
            },
        )
    )

    assert signals == []


def _fair_value(case_key: str) -> FairValueEstimate:
    payload = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))[case_key]
    return FairValueEstimate(
        market_id=str(payload["market_id"]),
        category=Category.CRYPTO,
        fair_probability=float(payload["fair_probability"]),
        confidence=float(payload["confidence"]),
        half_life_seconds=int(payload["half_life_seconds"]),
        observed_probability=float(payload["observed_probability"]),
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={
            "net_edge_bps": float(payload["net_edge_bps"]),
            "gross_edge_bps": float(payload["gross_edge_bps"]),
        },
    )


def _snapshot(
    *,
    timestamp: datetime,
    market_id: str,
    best_bid_yes: float,
    best_ask_yes: float,
    best_bid_no: float,
    best_ask_no: float,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=market_id,
        category=Category.CRYPTO,
        timestamp=timestamp,
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=best_bid_no,
        best_ask_no=best_ask_no,
        tick_size=0.01,
        liquidity_score=0.5,
        metadata={"event_slug": "eth-dip-ladder", "no_token_id": f"{market_id}-no"},
    )


def _dashboard(
    position: PositionState | None = None,
    pending_orders: tuple[PendingOrderState, ...] = (),
) -> DashboardState:
    return DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=() if position is None else (position,),
        pending_orders=pending_orders,
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )

