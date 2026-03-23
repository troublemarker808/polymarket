import asyncio
from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, PendingOrderState, PositionState, RuntimeStatus
from pm_bot.strategies.crypto.surface.strategy import CryptoSurfaceStrategy


def build_snapshot(
    *,
    market_id: str,
    threshold: str,
    question: str,
    best_bid_yes: float,
    best_ask_yes: float,
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=market_id,
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 9, 42, 51, 763712, tzinfo=UTC),
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        metadata={
            "event_slug": "microstrategy-sells-any-bitcoin-by-___",
            "event_title": "MicroStrategy sells any Bitcoin by ___ ?",
            "question": question,
            "group_item_threshold": threshold,
        },
    )


def empty_dashboard() -> DashboardState:
    return DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )


def test_crypto_surface_strategy_generates_buy_yes_for_underpriced_time_rung() -> None:
    strategy = CryptoSurfaceStrategy({"min_edge_bps": 250, "min_peer_count": 3})
    march = build_snapshot(
        market_id="m1",
        threshold="1",
        question="MicroStrategy sells any Bitcoin by March 31, 2026?",
        best_bid_yes=0.18,
        best_ask_yes=0.20,
    )
    june = build_snapshot(
        market_id="m2",
        threshold="2",
        question="MicroStrategy sells any Bitcoin by June 30, 2026?",
        best_bid_yes=0.14,
        best_ask_yes=0.16,
    )
    december = build_snapshot(
        market_id="m3",
        threshold="3",
        question="MicroStrategy sells any Bitcoin by December 31, 2026?",
        best_bid_yes=0.39,
        best_ask_yes=0.41,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=june,
            context={"snapshot_cache": (march, june, december), "dashboard_state": empty_dashboard()},
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.BUY_YES
    assert round(signal.fair_probability, 4) == 0.19
    assert round(signal.edge_bps, 2) == 300.0


def test_crypto_surface_strategy_generates_buy_no_for_overpriced_time_rung() -> None:
    strategy = CryptoSurfaceStrategy({"min_edge_bps": 250, "min_peer_count": 3})
    march = build_snapshot(
        market_id="m1",
        threshold="1",
        question="MicroStrategy sells any Bitcoin by March 31, 2026?",
        best_bid_yes=0.18,
        best_ask_yes=0.20,
    )
    june = build_snapshot(
        market_id="m2",
        threshold="2",
        question="MicroStrategy sells any Bitcoin by June 30, 2026?",
        best_bid_yes=0.49,
        best_ask_yes=0.51,
    )
    december = build_snapshot(
        market_id="m3",
        threshold="3",
        question="MicroStrategy sells any Bitcoin by December 31, 2026?",
        best_bid_yes=0.39,
        best_ask_yes=0.41,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=june,
            context={"snapshot_cache": (march, june, december), "dashboard_state": empty_dashboard()},
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.BUY_NO
    assert round(signal.fair_probability, 4) == 0.4
    assert round(signal.edge_bps, 2) == 900.0


def test_crypto_surface_strategy_requires_peer_context() -> None:
    strategy = CryptoSurfaceStrategy({"min_edge_bps": 250, "min_peer_count": 3})
    june = build_snapshot(
        market_id="m2",
        threshold="2",
        question="MicroStrategy sells any Bitcoin by June 30, 2026?",
        best_bid_yes=0.14,
        best_ask_yes=0.16,
    )

    signals = asyncio.run(strategy.evaluate(snapshot=june, context={"dashboard_state": empty_dashboard()}))

    assert signals == []


def test_crypto_surface_strategy_generates_sell_yes_when_curve_normalizes_with_position() -> None:
    strategy = CryptoSurfaceStrategy(
        {"min_edge_bps": 250, "min_peer_count": 3, "exit_edge_bps": 75, "stop_loss_bps": 250}
    )
    march = build_snapshot(
        market_id="m1",
        threshold="1",
        question="MicroStrategy sells any Bitcoin by March 31, 2026?",
        best_bid_yes=0.18,
        best_ask_yes=0.20,
    )
    june = build_snapshot(
        market_id="m2",
        threshold="2",
        question="MicroStrategy sells any Bitcoin by June 30, 2026?",
        best_bid_yes=0.145,
        best_ask_yes=0.155,
    )
    december = build_snapshot(
        market_id="m3",
        threshold="3",
        question="MicroStrategy sells any Bitcoin by December 31, 2026?",
        best_bid_yes=0.39,
        best_ask_yes=0.41,
    )
    dashboard = DashboardState(
        total_equity=101.0,
        today_pnl=1.0,
        open_positions=(
            PositionState(
                market_id="m2",
                    token_id="m2-yes",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    notional=5.0,
                    shares=25.0,
                    average_entry_price=0.18,
                    mark_price=0.145,
                    unrealized_pnl=-0.875,
                    opened_at=datetime(2026, 3, 23, 9, 40, tzinfo=UTC),
                ),
            ),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=1,
        daily_order_soft_limit_reached=False,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=june,
            context={"snapshot_cache": (march, june, december), "dashboard_state": dashboard},
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.SELL_YES
    assert signal.target_price == 0.145
    assert round(signal.target_size or 0.0, 4) == round(25.0 * 0.145, 4)


def test_crypto_surface_strategy_skips_market_with_pending_order() -> None:
    strategy = CryptoSurfaceStrategy({"min_edge_bps": 250, "min_peer_count": 3})
    march = build_snapshot(
        market_id="m1",
        threshold="1",
        question="MicroStrategy sells any Bitcoin by March 31, 2026?",
        best_bid_yes=0.18,
        best_ask_yes=0.20,
    )
    june = build_snapshot(
        market_id="m2",
        threshold="2",
        question="MicroStrategy sells any Bitcoin by June 30, 2026?",
        best_bid_yes=0.14,
        best_ask_yes=0.16,
    )
    december = build_snapshot(
        market_id="m3",
        threshold="3",
        question="MicroStrategy sells any Bitcoin by December 31, 2026?",
        best_bid_yes=0.39,
        best_ask_yes=0.41,
    )
    dashboard = DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(
            PendingOrderState(
                order_id="o1",
                market_id="m2",
                token_id="m2-yes",
                category=Category.CRYPTO,
                strategy_id="crypto.surface",
                side="buy_yes",
                limit_price=0.16,
                requested_shares=31.25,
                requested_notional=5.0,
                matched_shares=0.0,
                matched_notional=0.0,
                fees_paid=0.0,
                status="pending",
                created_at=datetime(2026, 3, 23, 9, 40, tzinfo=UTC),
                updated_at=datetime(2026, 3, 23, 9, 40, tzinfo=UTC),
            ),
        ),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=1,
        daily_order_soft_limit_reached=False,
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=june,
            context={"snapshot_cache": (march, june, december), "dashboard_state": dashboard},
        )
    )

    assert signals == []
