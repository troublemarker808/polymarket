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
    best_bid_no: float | None = None,
    best_ask_no: float | None = None,
    slug: str | None = None,
    event_slug: str = "microstrategy-sells-any-bitcoin-by-___",
    event_title: str = "MicroStrategy sells any Bitcoin by ___ ?",
    no_token_id: str | None = None,
) -> MarketSnapshot:
    no_token = no_token_id or f"{market_id}-no"
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=slug or market_id,
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 23, 9, 42, 51, 763712, tzinfo=UTC),
        resolution_time=datetime(2026, 12, 31, 0, 0, tzinfo=UTC),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=best_bid_no,
        best_ask_no=best_ask_no,
        metadata={
            "event_slug": event_slug,
            "event_title": event_title,
            "question": question,
            "group_item_threshold": threshold,
            "no_token_id": no_token,
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
    assert signal.generated_at == june.timestamp


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
    assert signal.generated_at == june.timestamp


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


def test_crypto_surface_strategy_does_not_flag_normal_dip_curve_as_buy_yes() -> None:
    strategy = CryptoSurfaceStrategy({"min_edge_bps": 250, "min_peer_count": 3})
    dip_1500 = build_snapshot(
        market_id="m1",
        threshold="13",
        question="Will Ethereum dip to $1,500 by December 31, 2026?",
        best_bid_yes=0.70,
        best_ask_yes=0.72,
        slug="will-ethereum-dip-to-1500-by-december-31-2026",
        event_slug="what-price-will-ethereum-hit-before-2027",
        event_title="What price will Ethereum hit in 2026?",
    )
    dip_1000 = build_snapshot(
        market_id="m2",
        threshold="14",
        question="Will Ethereum dip to $1,000 by December 31, 2026?",
        best_bid_yes=0.25,
        best_ask_yes=0.26,
        slug="will-ethereum-dip-to-1000-by-december-31-2026",
        event_slug="what-price-will-ethereum-hit-before-2027",
        event_title="What price will Ethereum hit in 2026?",
    )
    dip_800 = build_snapshot(
        market_id="m3",
        threshold="15",
        question="Will Ethereum dip to $800 by December 31, 2026?",
        best_bid_yes=0.19,
        best_ask_yes=0.20,
        slug="will-ethereum-dip-to-800-by-december-31-2026",
        event_slug="what-price-will-ethereum-hit-before-2027",
        event_title="What price will Ethereum hit in 2026?",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=dip_800,
            context={
                "snapshot_cache": (dip_1500, dip_1000, dip_800),
                "dashboard_state": empty_dashboard(),
            },
        )
    )

    assert signals == []


def test_crypto_surface_strategy_generates_buy_yes_for_underpriced_dip_rung() -> None:
    strategy = CryptoSurfaceStrategy({"min_edge_bps": 250, "min_peer_count": 3})
    dip_1500 = build_snapshot(
        market_id="m1",
        threshold="13",
        question="Will Ethereum dip to $1,500 by December 31, 2026?",
        best_bid_yes=0.70,
        best_ask_yes=0.72,
        slug="will-ethereum-dip-to-1500-by-december-31-2026",
        event_slug="what-price-will-ethereum-hit-before-2027",
        event_title="What price will Ethereum hit in 2026?",
    )
    dip_1000 = build_snapshot(
        market_id="m2",
        threshold="14",
        question="Will Ethereum dip to $1,000 by December 31, 2026?",
        best_bid_yes=0.09,
        best_ask_yes=0.11,
        slug="will-ethereum-dip-to-1000-by-december-31-2026",
        event_slug="what-price-will-ethereum-hit-before-2027",
        event_title="What price will Ethereum hit in 2026?",
    )
    dip_800 = build_snapshot(
        market_id="m3",
        threshold="15",
        question="Will Ethereum dip to $800 by December 31, 2026?",
        best_bid_yes=0.19,
        best_ask_yes=0.20,
        slug="will-ethereum-dip-to-800-by-december-31-2026",
        event_slug="what-price-will-ethereum-hit-before-2027",
        event_title="What price will Ethereum hit in 2026?",
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=dip_1000,
            context={
                "snapshot_cache": (dip_1500, dip_1000, dip_800),
                "dashboard_state": empty_dashboard(),
            },
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == SignalSide.BUY_YES
    assert round(signal.fair_probability, 4) == 0.195
    assert round(signal.edge_bps, 2) == 850.0


def test_crypto_surface_strategy_does_not_immediately_stop_out_no_position_on_spread() -> None:
    strategy = CryptoSurfaceStrategy(
        {"min_edge_bps": 250, "min_peer_count": 3, "exit_edge_bps": 75, "stop_loss_bps": 250}
    )
    lower = build_snapshot(
        market_id="m1",
        threshold="22",
        question="Will Bitcoin dip to $60,000 by December 31, 2026?",
        best_bid_yes=0.73,
        best_ask_yes=0.74,
        best_bid_no=0.15,
        best_ask_no=0.16,
        slug="will-bitcoin-dip-to-60000-by-december-31-2026",
        event_slug="what-price-will-bitcoin-hit-before-2027",
        event_title="What price will Bitcoin hit in 2026?",
    )
    current = build_snapshot(
        market_id="m2",
        threshold="23",
        question="Will Bitcoin dip to $55,000 by December 31, 2026?",
        best_bid_yes=0.76,
        best_ask_yes=0.77,
        best_bid_no=0.23,
        best_ask_no=0.24,
        slug="will-bitcoin-dip-to-55000-by-december-31-2026",
        event_slug="what-price-will-bitcoin-hit-before-2027",
        event_title="What price will Bitcoin hit in 2026?",
        no_token_id="m2-no",
    )
    higher = build_snapshot(
        market_id="m3",
        threshold="24",
        question="Will Bitcoin dip to $50,000 by December 31, 2026?",
        best_bid_yes=0.64,
        best_ask_yes=0.66,
        best_bid_no=0.34,
        best_ask_no=0.36,
        slug="will-bitcoin-dip-to-50000-by-december-31-2026",
        event_slug="what-price-will-bitcoin-hit-before-2027",
        event_title="What price will Bitcoin hit in 2026?",
    )
    dashboard = DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=(
            PositionState(
                market_id="m2",
                token_id="m2-no",
                category=Category.CRYPTO,
                strategy_id="crypto.surface",
                notional=5.0,
                shares=20.833333,
                average_entry_price=0.24012,
                mark_price=0.235,
                unrealized_pnl=-0.10625,
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
            snapshot=current,
            context={"snapshot_cache": (lower, current, higher), "dashboard_state": dashboard},
        )
    )

    assert signals == []


def test_crypto_surface_strategy_respects_stop_loss_cooldown_after_exit() -> None:
    strategy = CryptoSurfaceStrategy(
        {
            "min_edge_bps": 250,
            "min_peer_count": 3,
            "exit_edge_bps": 75,
            "stop_loss_bps": 250,
            "stop_loss_cooldown_seconds": 60,
        }
    )
    lower = build_snapshot(
        market_id="m1",
        threshold="22",
        question="Will Bitcoin dip to $60,000 by December 31, 2026?",
        best_bid_yes=0.84,
        best_ask_yes=0.85,
        best_bid_no=0.15,
        best_ask_no=0.16,
        slug="will-bitcoin-dip-to-60000-by-december-31-2026",
        event_slug="what-price-will-bitcoin-hit-before-2027",
        event_title="What price will Bitcoin hit in 2026?",
    )
    stop_snapshot = build_snapshot(
        market_id="m2",
        threshold="23",
        question="Will Bitcoin dip to $55,000 by December 31, 2026?",
        best_bid_yes=0.79,
        best_ask_yes=0.80,
        best_bid_no=0.20,
        best_ask_no=0.21,
        slug="will-bitcoin-dip-to-55000-by-december-31-2026",
        event_slug="what-price-will-bitcoin-hit-before-2027",
        event_title="What price will Bitcoin hit in 2026?",
        no_token_id="m2-no",
    )
    higher = build_snapshot(
        market_id="m3",
        threshold="24",
        question="Will Bitcoin dip to $50,000 by December 31, 2026?",
        best_bid_yes=0.64,
        best_ask_yes=0.66,
        best_bid_no=0.34,
        best_ask_no=0.36,
        slug="will-bitcoin-dip-to-50000-by-december-31-2026",
        event_slug="what-price-will-bitcoin-hit-before-2027",
        event_title="What price will Bitcoin hit in 2026?",
    )
    dashboard_with_position = DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=(
            PositionState(
                market_id="m2",
                token_id="m2-no",
                category=Category.CRYPTO,
                strategy_id="crypto.surface",
                notional=5.0,
                shares=20.833333,
                average_entry_price=0.24012,
                mark_price=0.20,
                unrealized_pnl=-0.835833,
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

    exit_signals = asyncio.run(
        strategy.evaluate(
            snapshot=stop_snapshot,
            context={
                "snapshot_cache": (lower, stop_snapshot, higher),
                "dashboard_state": dashboard_with_position,
            },
        )
    )

    assert len(exit_signals) == 1
    assert exit_signals[0].side == SignalSide.SELL_NO
    assert "stop_loss" in exit_signals[0].rationale_tags

    reentry_signals = asyncio.run(
        strategy.evaluate(
            snapshot=stop_snapshot,
            context={
                "snapshot_cache": (lower, stop_snapshot, higher),
                "dashboard_state": empty_dashboard(),
            },
        )
    )

    assert reentry_signals == []
