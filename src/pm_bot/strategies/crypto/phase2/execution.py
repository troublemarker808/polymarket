"""Crypto Phase 2 execution policy helpers."""

from __future__ import annotations

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.exposure_keys import derive_exposure_keys
from pm_bot.strategies.common import implied_yes_probability, parse_float
from pm_bot.strategies.crypto.phase2.models import (
    CryptoExecutionDecision,
    CryptoSignalClassification,
    CryptoTradeEligibility,
)


def classify_crypto_signal(
    *,
    fair_value: FairValueEstimate,
) -> CryptoSignalClassification:
    observed_probability = fair_value.observed_probability or fair_value.fair_probability
    net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
    half_life_seconds = fair_value.half_life_seconds or 24 * 3600
    side = SignalSide.BUY_YES if fair_value.fair_probability >= observed_probability else SignalSide.BUY_NO

    if net_edge_bps <= 0:
        signal_type = "no_trade"
        expected_exit_mode = "none"
    elif half_life_seconds <= 2 * 3600 and net_edge_bps >= 250:
        signal_type = "repricing_edge"
        expected_exit_mode = "fair_value_reversion"
    elif fair_value.confidence >= 0.72 and half_life_seconds >= 12 * 3600:
        signal_type = "resolution_edge"
        expected_exit_mode = "time_decay_or_resolution"
    else:
        signal_type = "liquidity_edge"
        expected_exit_mode = "passive_fill_then_reprice"

    urgency_score = _urgency_score(
        confidence=fair_value.confidence,
        net_edge_bps=net_edge_bps,
        half_life_seconds=half_life_seconds,
    )
    return CryptoSignalClassification(
        market_id=fair_value.market_id,
        signal_type=signal_type,
        side=side,
        urgency_score=urgency_score,
        expected_exit_mode=expected_exit_mode,
        rationale_tags=(signal_type, expected_exit_mode),
    )


def evaluate_trade_eligibility(
    *,
    fair_value: FairValueEstimate,
    snapshot: MarketSnapshot,
    classification: CryptoSignalClassification,
    min_confidence: float = 0.6,
    min_net_edge_bps: float = 75.0,
    max_spread_bps: float = 250.0,
    min_liquidity_score: float = 0.0,
    min_contract_price: float = 0.05,
) -> CryptoTradeEligibility:
    net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
    market_spread_bps = spread_cost_bps(snapshot=snapshot, side=classification.side)
    contract_price = _contract_price(snapshot=snapshot, side=classification.side)

    if classification.signal_type == "no_trade":
        return _ineligible(fair_value.market_id, net_edge_bps, market_spread_bps, "no_trade_signal")
    if fair_value.confidence < min_confidence:
        return _ineligible(fair_value.market_id, net_edge_bps, market_spread_bps, "low_confidence")
    if net_edge_bps < min_net_edge_bps:
        return _ineligible(fair_value.market_id, net_edge_bps, market_spread_bps, "insufficient_net_edge")
    if market_spread_bps > max_spread_bps:
        return _ineligible(fair_value.market_id, net_edge_bps, market_spread_bps, "spread_too_wide")
    if snapshot.liquidity_score < min_liquidity_score:
        return _ineligible(fair_value.market_id, net_edge_bps, market_spread_bps, "liquidity_too_low")
    if contract_price is not None and contract_price < min_contract_price:
        return _ineligible(fair_value.market_id, net_edge_bps, market_spread_bps, "contract_price_too_low")

    return CryptoTradeEligibility(
        market_id=fair_value.market_id,
        eligible=True,
        reason="eligible",
        net_edge_bps=net_edge_bps,
        market_spread_bps=market_spread_bps,
        rationale_tags=(classification.signal_type, "eligible"),
    )


def route_execution(
    *,
    fair_value: FairValueEstimate,
    snapshot: MarketSnapshot,
    classification: CryptoSignalClassification,
    eligibility: CryptoTradeEligibility,
    taker_urgency_threshold: float = 0.72,
    maker_min_edge_bps: float = 100.0,
    resolution_maker_min_edge_bps: float = 150.0,
    high_edge_taker_min_edge_bps: float = 2000.0,
    high_edge_taker_max_spread_bps: float = 250.0,
    taker_max_entry_premium_bps: float = 750.0,
    maker_quote_ttl_seconds: int = 60,
    resolution_maker_quote_ttl_seconds: int = 180,
    maker_aggressiveness: float = 1.0,
) -> CryptoExecutionDecision:
    if not eligibility.eligible:
        return CryptoExecutionDecision(
            market_id=fair_value.market_id,
            route="skip",
            side=classification.side,
            target_price=None,
            quote_ttl_seconds=None,
            urgency_score=classification.urgency_score,
            rationale_tags=(eligibility.reason,),
        )

    net_edge_bps = parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0
    observed_probability = implied_yes_probability(snapshot) or fair_value.observed_probability or fair_value.fair_probability
    quote_ttl_seconds = (
        resolution_maker_quote_ttl_seconds
        if classification.signal_type == "resolution_edge"
        else maker_quote_ttl_seconds
    )
    taker_entry_premium_bps = _taker_entry_premium_bps(snapshot=snapshot, side=classification.side)

    if (
        classification.signal_type == "repricing_edge"
        and classification.urgency_score >= taker_urgency_threshold
        and taker_entry_premium_bps <= taker_max_entry_premium_bps
    ):
        return CryptoExecutionDecision(
            market_id=fair_value.market_id,
            route="taker",
            side=classification.side,
            target_price=_taker_price(snapshot=snapshot, side=classification.side, fair_probability=fair_value.fair_probability),
            quote_ttl_seconds=30,
            urgency_score=classification.urgency_score,
            rationale_tags=(classification.signal_type, "taker"),
        )
    repricing_taker_too_expensive = (
        classification.signal_type == "repricing_edge"
        and classification.urgency_score >= taker_urgency_threshold
        and taker_entry_premium_bps > taker_max_entry_premium_bps
    )

    if (
        classification.signal_type in {"liquidity_edge", "resolution_edge"}
        and net_edge_bps >= high_edge_taker_min_edge_bps
        and eligibility.market_spread_bps <= high_edge_taker_max_spread_bps
        and taker_entry_premium_bps <= taker_max_entry_premium_bps
    ):
        return CryptoExecutionDecision(
            market_id=fair_value.market_id,
            route="taker",
            side=classification.side,
            target_price=_taker_price(snapshot=snapshot, side=classification.side, fair_probability=fair_value.fair_probability),
            quote_ttl_seconds=15,
            urgency_score=classification.urgency_score,
            rationale_tags=(classification.signal_type, "high_edge_taker"),
        )

    if classification.signal_type == "resolution_edge" and net_edge_bps < max(maker_min_edge_bps, resolution_maker_min_edge_bps):
        return CryptoExecutionDecision(
            market_id=fair_value.market_id,
            route="skip",
            side=classification.side,
            target_price=None,
            quote_ttl_seconds=None,
            urgency_score=classification.urgency_score,
            rationale_tags=("resolution_edge_too_thin",),
        )

    if net_edge_bps >= maker_min_edge_bps:
        return CryptoExecutionDecision(
            market_id=fair_value.market_id,
            route="maker",
            side=classification.side,
            target_price=_maker_price(
                snapshot=snapshot,
                side=classification.side,
                observed_probability=observed_probability,
                fair_probability=fair_value.fair_probability,
                net_edge_bps=net_edge_bps,
                maker_aggressiveness=maker_aggressiveness,
            ),
            quote_ttl_seconds=quote_ttl_seconds,
            urgency_score=classification.urgency_score,
            rationale_tags=(
                ("repricing_taker_too_expensive", "maker_fallback")
                if repricing_taker_too_expensive
                else (classification.signal_type, "maker")
            ),
        )

    return CryptoExecutionDecision(
        market_id=fair_value.market_id,
        route="skip",
        side=classification.side,
        target_price=None,
        quote_ttl_seconds=None,
        urgency_score=classification.urgency_score,
        rationale_tags=("edge_not_actionable",),
    )


def build_order_intent(
    *,
    fair_value: FairValueEstimate,
    snapshot: MarketSnapshot,
    decision: CryptoExecutionDecision,
    default_notional: float,
    taker_time_in_force: str = "IOC",
    strategy_id: str = "crypto.phase2.execution",
) -> OrderIntent | None:
    if decision.route == "skip" or decision.target_price is None or decision.target_price <= 0:
        return None

    token_id = snapshot.token_id
    if decision.side in {SignalSide.BUY_NO, SignalSide.SELL_NO}:
        token_id = snapshot.metadata.get("no_token_id", token_id)

    size = round(default_notional / decision.target_price, 6)
    if size <= 0:
        return None

    time_in_force = taker_time_in_force.upper() if decision.route == "taker" else "GTC"
    exposure_keys = derive_exposure_keys(snapshot)
    return OrderIntent(
        strategy_id=strategy_id,
        category=fair_value.category,
        market_id=fair_value.market_id,
        token_id=token_id,
        action=OrderAction.PLACE,
        side=decision.side,
        price=decision.target_price,
        size=size,
        time_in_force=time_in_force,
        created_at=snapshot.timestamp,
        notional=default_notional,
        quote_ttl_seconds=decision.quote_ttl_seconds,
        signal_edge_bps=parse_float(fair_value.supporting_values, "net_edge_bps") or 0.0,
        exposure_group_id=exposure_keys.exposure_group_id,
        thesis_group_id=exposure_keys.thesis_group_id,
        underlying_group_id=exposure_keys.underlying_group_id,
    )


def spread_cost_bps(*, snapshot: MarketSnapshot, side: SignalSide) -> float:
    if side == SignalSide.BUY_YES:
        return _half_spread_bps(snapshot.best_bid_yes, snapshot.best_ask_yes)
    if side == SignalSide.BUY_NO:
        return _half_spread_bps(snapshot.best_bid_no, snapshot.best_ask_no)
    return 0.0


def _maker_price(
    *,
    snapshot: MarketSnapshot,
    side: SignalSide,
    observed_probability: float,
    fair_probability: float,
    net_edge_bps: float,
    maker_aggressiveness: float,
) -> float:
    tick_size = snapshot.tick_size or 0.01
    if side == SignalSide.BUY_YES:
        best_bid = snapshot.best_bid_yes
        best_ask = snapshot.best_ask_yes
        if best_bid is not None:
            improved_bid = best_bid + (
                _maker_improvement_ticks(
                    net_edge_bps=net_edge_bps,
                    maker_aggressiveness=maker_aggressiveness,
                )
                * tick_size
            )
            midpoint_bid = _high_edge_midpoint_bid(
                best_bid=best_bid,
                best_ask=best_ask,
                tick_size=tick_size,
                net_edge_bps=net_edge_bps,
                maker_aggressiveness=maker_aggressiveness,
            )
            if best_ask is not None:
                safe_ceiling = min(
                    max(best_bid, best_ask - tick_size),
                    max(best_bid, fair_probability),
                )
                return round(min(max(improved_bid, midpoint_bid), safe_ceiling), 4)
            return round(improved_bid, 4)
        return round(max(0.01, observed_probability - tick_size), 4)
    best_bid_no = snapshot.best_bid_no
    best_ask_no = snapshot.best_ask_no
    if best_bid_no is not None:
        improved_bid_no = best_bid_no + (
            _maker_improvement_ticks(
                net_edge_bps=net_edge_bps,
                maker_aggressiveness=maker_aggressiveness,
            )
            * tick_size
        )
        midpoint_bid_no = _high_edge_midpoint_bid(
            best_bid=best_bid_no,
            best_ask=best_ask_no,
            tick_size=tick_size,
            net_edge_bps=net_edge_bps,
            maker_aggressiveness=maker_aggressiveness,
        )
        if best_ask_no is not None:
            fair_no_probability = 1.0 - fair_probability
            safe_ceiling = min(
                max(best_bid_no, best_ask_no - tick_size),
                max(best_bid_no, fair_no_probability),
            )
            return round(min(max(improved_bid_no, midpoint_bid_no), safe_ceiling), 4)
        return round(improved_bid_no, 4)
    return round(max(0.01, (1.0 - observed_probability) - tick_size), 4)


def _taker_price(*, snapshot: MarketSnapshot, side: SignalSide, fair_probability: float) -> float:
    if side == SignalSide.BUY_YES:
        return round(snapshot.best_ask_yes or fair_probability, 4)
    return round(snapshot.best_ask_no or (1.0 - fair_probability), 4)


def _taker_entry_premium_bps(*, snapshot: MarketSnapshot, side: SignalSide) -> float:
    if side == SignalSide.BUY_YES:
        best_bid = snapshot.best_bid_yes
        best_ask = snapshot.best_ask_yes
    else:
        best_bid = snapshot.best_bid_no
        best_ask = snapshot.best_ask_no
    if best_bid is None or best_ask is None:
        return 0.0
    midpoint = (best_bid + best_ask) / 2
    if midpoint <= 0:
        return 0.0
    return max(0.0, (best_ask - midpoint) / midpoint * 10000)


def _contract_price(*, snapshot: MarketSnapshot, side: SignalSide) -> float | None:
    observed_yes = implied_yes_probability(snapshot)
    if observed_yes is None:
        return None
    if side in {SignalSide.BUY_YES, SignalSide.SELL_YES}:
        return observed_yes
    return 1.0 - observed_yes


def _maker_improvement_ticks(*, net_edge_bps: float, maker_aggressiveness: float) -> int:
    if net_edge_bps >= 3000:
        base_ticks = 3
    elif net_edge_bps >= 2000:
        base_ticks = 2
    else:
        base_ticks = 1
    scaled_ticks = int(round(base_ticks * max(0.0, maker_aggressiveness)))
    return max(0, scaled_ticks)


def _high_edge_midpoint_bid(
    *,
    best_bid: float,
    best_ask: float | None,
    tick_size: float,
    net_edge_bps: float,
    maker_aggressiveness: float,
) -> float:
    midpoint_edge_threshold = max(1000.0, 2000.0 / max(0.5, maker_aggressiveness))
    if best_ask is None or tick_size <= 0 or net_edge_bps < midpoint_edge_threshold:
        return best_bid
    spread_ticks = int(round(max(best_ask - best_bid, 0.0) / tick_size))
    if spread_ticks < 4:
        return best_bid
    midpoint_ticks = max(1, spread_ticks // 2)
    return best_bid + (midpoint_ticks * tick_size)


def _half_spread_bps(best_bid: float | None, best_ask: float | None) -> float:
    if best_bid is None or best_ask is None:
        return 0.0
    return max(best_ask - best_bid, 0.0) * 5000


def _urgency_score(*, confidence: float, net_edge_bps: float, half_life_seconds: int) -> float:
    confidence_component = min(0.4, confidence * 0.4)
    edge_component = min(0.4, max(0.0, net_edge_bps) / 1000 * 0.4)
    half_life_component = 0.2 if half_life_seconds <= 2 * 3600 else (0.1 if half_life_seconds <= 8 * 3600 else 0.02)
    return round(min(1.0, confidence_component + edge_component + half_life_component), 4)

def _ineligible(
    market_id: str,
    net_edge_bps: float,
    market_spread_bps: float,
    reason: str,
) -> CryptoTradeEligibility:
    return CryptoTradeEligibility(
        market_id=market_id,
        eligible=False,
        reason=reason,
        net_edge_bps=net_edge_bps,
        market_spread_bps=market_spread_bps,
        rationale_tags=(reason,),
    )
