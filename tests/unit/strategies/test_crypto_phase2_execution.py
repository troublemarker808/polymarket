from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.strategies.crypto.phase2 import (
    build_order_intent,
    classify_crypto_signal,
    evaluate_trade_eligibility,
    route_execution,
)


FIXTURE_CASES = Path("tests/fixtures/crypto_phase2/execution_cases.json")


def test_classify_crypto_signal_identifies_repricing_edge_for_short_half_life() -> None:
    fair_value = _fair_value("repricing_yes")

    classification = classify_crypto_signal(fair_value=fair_value)

    assert classification.signal_type == "repricing_edge"
    assert classification.side == SignalSide.BUY_YES
    assert classification.expected_exit_mode == "fair_value_reversion"
    assert classification.urgency_score == 0.77


def test_evaluate_trade_eligibility_rejects_low_net_edge_case() -> None:
    fair_value = _fair_value("skip_low_edge")
    snapshot = _snapshot(market_id="eth-dip-1500", best_bid_yes=0.33, best_ask_yes=0.35, best_bid_no=0.65, best_ask_no=0.67)
    classification = classify_crypto_signal(fair_value=fair_value)

    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
    )

    assert not eligibility.eligible
    assert eligibility.reason == "insufficient_net_edge"


def test_evaluate_trade_eligibility_rejects_ultra_tail_contract_price() -> None:
    fair_value = _fair_value("repricing_yes")
    snapshot = _snapshot(
        market_id="eth-dip-tail",
        best_bid_yes=0.002,
        best_ask_yes=0.003,
        best_bid_no=0.997,
        best_ask_no=0.998,
    )
    classification = classify_crypto_signal(fair_value=fair_value)

    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        min_contract_price=0.05,
        max_spread_bps=500.0,
    )

    assert not eligibility.eligible
    assert eligibility.reason == "contract_price_too_low"


def test_route_execution_prefers_taker_for_urgent_repricing_trade() -> None:
    fair_value = _fair_value("repricing_yes")
    snapshot = _snapshot(market_id="eth-dip-1000", best_bid_yes=0.10, best_ask_yes=0.11, best_bid_no=0.89, best_ask_no=0.90)
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
    )

    assert decision.route == "taker"
    assert decision.side == SignalSide.BUY_YES
    assert decision.target_price == 0.11
    assert decision.quote_ttl_seconds == 30


def test_build_order_intent_can_use_gtc_for_taker_validation_profile() -> None:
    fair_value = _fair_value("repricing_yes")
    snapshot = _snapshot(
        market_id="btc-above-short",
        best_bid_yes=0.41,
        best_ask_yes=0.42,
        best_bid_no=0.58,
        best_ask_no=0.59,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
    )
    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
    )

    intent = build_order_intent(
        fair_value=fair_value,
        snapshot=snapshot,
        decision=decision,
        default_notional=5.0,
        taker_time_in_force="GTC",
    )

    assert decision.route == "taker"
    assert intent is not None
    assert intent.time_in_force == "GTC"


def test_route_execution_maker_price_does_not_cross_one_tick_spread() -> None:
    fair_value = _fair_value("resolution_no")
    snapshot = _snapshot(
        market_id="eth-dip-one-tick",
        best_bid_yes=0.23,
        best_ask_yes=0.24,
        best_bid_no=0.76,
        best_ask_no=0.77,
        no_token_id="eth-dip-one-tick-no",
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        min_contract_price=0.05,
        max_spread_bps=500.0,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
    )

    assert decision.route == "maker"
    assert decision.target_price == 0.76


def test_route_execution_skips_thin_resolution_edge_trade() -> None:
    fair_value = FairValueEstimate(
        market_id="btc-dip-thin",
        category=Category.CRYPTO,
        fair_probability=0.10,
        confidence=0.80,
        half_life_seconds=48 * 3600,
        observed_probability=0.088,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 120.0, "gross_edge_bps": 140.0},
    )
    snapshot = _snapshot(
        market_id="btc-dip-thin",
        best_bid_yes=0.08,
        best_ask_yes=0.09,
        best_bid_no=0.91,
        best_ask_no=0.92,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
    )

    assert classification.signal_type == "resolution_edge"
    assert decision.route == "skip"
    assert decision.rationale_tags == ("resolution_edge_too_thin",)


def test_route_execution_uses_configured_resolution_maker_ttl() -> None:
    fair_value = _fair_value("resolution_no")
    snapshot = _snapshot(
        market_id="eth-dip-ttl",
        best_bid_yes=0.23,
        best_ask_yes=0.25,
        best_bid_no=0.75,
        best_ask_no=0.77,
        no_token_id="eth-dip-ttl-no",
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        resolution_maker_quote_ttl_seconds=45,
    )

    assert decision.route == "maker"
    assert decision.quote_ttl_seconds == 45


def test_route_execution_maker_price_steps_deeper_for_large_edge_without_crossing() -> None:
    fair_value = FairValueEstimate(
        market_id="eth-dip-wide",
        category=Category.CRYPTO,
        fair_probability=0.24,
        confidence=0.78,
        half_life_seconds=86400,
        observed_probability=0.16,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 2400.0, "gross_edge_bps": 2600.0},
    )
    snapshot = _snapshot(
        market_id="eth-dip-wide",
        best_bid_yes=0.16,
        best_ask_yes=0.20,
        best_bid_no=0.80,
        best_ask_no=0.84,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        min_contract_price=0.05,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        taker_urgency_threshold=0.95,
        high_edge_taker_max_spread_bps=100.0,
    )

    assert decision.route == "maker"
    assert decision.target_price == 0.18


def test_route_execution_high_edge_maker_uses_midpoint_inside_wide_spread() -> None:
    fair_value = FairValueEstimate(
        market_id="eth-dip-midpoint",
        category=Category.CRYPTO,
        fair_probability=0.28,
        confidence=0.70,
        half_life_seconds=10 * 3600,
        observed_probability=0.16,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 2400.0, "gross_edge_bps": 2600.0},
    )
    snapshot = _snapshot(
        market_id="eth-dip-midpoint",
        best_bid_yes=0.16,
        best_ask_yes=0.24,
        best_bid_no=0.76,
        best_ask_no=0.84,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        min_contract_price=0.05,
        max_spread_bps=500.0,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        taker_urgency_threshold=0.95,
        high_edge_taker_max_spread_bps=10.0,
    )

    assert decision.route == "maker"
    assert decision.target_price == 0.2


def test_route_execution_maker_aggressiveness_can_step_quote_deeper_without_crossing() -> None:
    fair_value = FairValueEstimate(
        market_id="btc-reach-aggr",
        category=Category.CRYPTO,
        fair_probability=0.12,
        confidence=0.75,
        half_life_seconds=24 * 3600,
        observed_probability=0.09,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 160.0, "gross_edge_bps": 300.0},
    )
    snapshot = _snapshot(
        market_id="btc-reach-aggr",
        best_bid_yes=0.09,
        best_ask_yes=0.12,
        best_bid_no=0.90,
        best_ask_no=0.91,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        min_contract_price=0.05,
        max_spread_bps=500.0,
    )

    baseline = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        maker_aggressiveness=1.0,
    )
    aggressive = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        maker_aggressiveness=1.5,
    )

    assert baseline.route == "maker"
    assert aggressive.route == "maker"
    assert baseline.target_price == 0.1
    assert aggressive.target_price == 0.11


def test_route_execution_prefers_taker_for_high_edge_liquidity_trade_when_spread_is_tight() -> None:
    fair_value = FairValueEstimate(
        market_id="eth-dip-tight",
        category=Category.CRYPTO,
        fair_probability=0.24,
        confidence=0.66,
        half_life_seconds=6 * 3600,
        observed_probability=0.16,
        model_id="crypto.phase1.fused",
        rationale_tags=("barrier_model", "surface_consistency"),
        supporting_values={"net_edge_bps": 2400.0, "gross_edge_bps": 2600.0},
    )
    snapshot = _snapshot(
        market_id="eth-dip-tight",
        best_bid_yes=0.16,
        best_ask_yes=0.17,
        best_bid_no=0.83,
        best_ask_no=0.84,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        min_contract_price=0.05,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        taker_urgency_threshold=0.95,
    )

    assert classification.signal_type == "liquidity_edge"
    assert decision.route == "taker"
    assert decision.target_price == 0.17
    assert decision.quote_ttl_seconds == 15


def test_route_execution_falls_back_to_maker_when_repricing_taker_is_too_expensive() -> None:
    fair_value = _fair_value("repricing_yes")
    snapshot = _snapshot(
        market_id="eth-dip-rich-ask",
        best_bid_yes=0.12,
        best_ask_yes=0.16,
        best_bid_no=0.84,
        best_ask_no=0.88,
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        max_spread_bps=1000.0,
    )

    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
        taker_max_entry_premium_bps=750.0,
    )

    assert classification.signal_type == "repricing_edge"
    assert decision.route == "maker"
    assert decision.target_price == 0.13
    assert decision.rationale_tags == ("repricing_taker_too_expensive", "maker_fallback")


def test_build_order_intent_uses_maker_route_and_no_token_for_buy_no() -> None:
    fair_value = _fair_value("resolution_no")
    snapshot = _snapshot(
        market_id="eth-dip-800",
        best_bid_yes=0.23,
        best_ask_yes=0.25,
        best_bid_no=0.75,
        best_ask_no=0.77,
        no_token_id="eth-dip-800-no",
    )
    classification = classify_crypto_signal(fair_value=fair_value)
    eligibility = evaluate_trade_eligibility(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
    )
    decision = route_execution(
        fair_value=fair_value,
        snapshot=snapshot,
        classification=classification,
        eligibility=eligibility,
    )

    intent = build_order_intent(
        fair_value=fair_value,
        snapshot=snapshot,
        decision=decision,
        default_notional=5.0,
    )

    assert decision.route == "maker"
    assert decision.side == SignalSide.BUY_NO
    assert decision.target_price == 0.76
    assert intent is not None
    assert intent.token_id == "eth-dip-800-no"
    assert intent.time_in_force == "GTC"
    assert intent.quote_ttl_seconds == 180
    assert intent.exposure_group_id == "crypto:eth-dip-ladder"
    assert intent.thesis_group_id == "crypto:eth:dip"
    assert intent.underlying_group_id == "crypto:eth"


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
    market_id: str,
    best_bid_yes: float,
    best_ask_yes: float,
    best_bid_no: float,
    best_ask_no: float,
    no_token_id: str | None = None,
) -> MarketSnapshot:
    metadata = {"event_slug": "eth-dip-ladder"}
    if no_token_id is not None:
        metadata["no_token_id"] = no_token_id
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=market_id,
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc),
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=timezone.utc),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=best_bid_no,
        best_ask_no=best_ask_no,
        tick_size=0.01,
        liquidity_score=0.5,
        metadata=metadata,
    )
