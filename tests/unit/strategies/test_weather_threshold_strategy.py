import asyncio
from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategies.weather.threshold.strategy import WeatherThresholdStrategy


def _snapshot(
    *,
    market_id: str,
    threshold: str,
    question: str,
    best_bid_yes: float,
    best_ask_yes: float,
    metadata: dict[str, str] | None = None,
) -> MarketSnapshot:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    return MarketSnapshot(
        market_id=market_id,
        token_id=f"{market_id}-yes",
        slug=market_id,
        category=Category.WEATHER,
        timestamp=now,
        resolution_time=datetime(2026, 3, 24, 0, 0, tzinfo=UTC),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=1 - best_ask_yes,
        best_ask_no=1 - best_bid_yes,
        last_traded_price=(best_bid_yes + best_ask_yes) / 2,
        metadata={
            "event_slug": "nyc-high-temp",
            "question": question,
            "event_title": question,
            "group_item_threshold": threshold,
            **(metadata or {}),
        },
    )


def _dashboard() -> DashboardState:
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


def test_weather_threshold_detects_strip_inconsistency() -> None:
    lower = _snapshot(
        market_id="w70",
        threshold="70",
        question="Will NYC high temperature be above 70F?",
        best_bid_yes=0.78,
        best_ask_yes=0.8,
    )
    middle = _snapshot(
        market_id="w75",
        threshold="75",
        question="Will NYC high temperature be above 75F?",
        best_bid_yes=0.72,
        best_ask_yes=0.74,
    )
    higher = _snapshot(
        market_id="w80",
        threshold="80",
        question="Will NYC high temperature be above 80F?",
        best_bid_yes=0.74,
        best_ask_yes=0.76,
    )
    strategy = WeatherThresholdStrategy({"min_strip_inconsistency_bps": 100})

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=higher,
            context={"snapshot_cache": (lower, middle, higher), "dashboard_state": _dashboard()},
        )
    )

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_NO
    assert round(signals[0].fair_probability, 2) == 0.73


def test_weather_threshold_uses_official_forecast_anchor() -> None:
    snapshot = _snapshot(
        market_id="w80",
        threshold="80",
        question="Will NYC high temperature be above 80F?",
        best_bid_yes=0.55,
        best_ask_yes=0.57,
        metadata={"official_forecast_value": "74"},
    )
    strategy = WeatherThresholdStrategy({"min_strip_inconsistency_bps": 100})

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={"snapshot_cache": (snapshot,), "dashboard_state": _dashboard()},
        )
    )

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_NO
    assert round(signals[0].fair_probability, 2) == 0.4


def test_weather_threshold_applies_preset_registry() -> None:
    snapshot = _snapshot(
        market_id="w80",
        threshold="80",
        question="Will NYC high temperature be above 80F?",
        best_bid_yes=0.55,
        best_ask_yes=0.57,
        metadata={
            "official_forecast_value": "74",
            "event_family": "daily_high_temperature_threshold",
            "settlement_source": "weather.gov",
        },
    )
    strategy = WeatherThresholdStrategy(
        {
            "min_strip_inconsistency_bps": 2000,
            "preset_registry": {
                "hot_day_threshold": {
                    "match": {
                        "event_family": "daily_high_temperature_threshold",
                        "settlement_source": "weather.gov",
                        "mode": "threshold",
                    },
                    "overrides": {"min_strip_inconsistency_bps": 100},
                }
            },
        }
    )

    signals = asyncio.run(
        strategy.evaluate(
            snapshot=snapshot,
            context={"snapshot_cache": (snapshot,), "dashboard_state": _dashboard()},
        )
    )

    assert len(signals) == 1
    assert signals[0].diagnostics["weather_preset"] == "hot_day_threshold"
