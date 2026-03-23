import asyncio
from datetime import UTC, datetime

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategies.weather.ensemble.strategy import WeatherEnsembleStrategy


def _snapshot(*, metadata: dict[str, str], best_bid_yes: float, best_ask_yes: float) -> MarketSnapshot:
    return MarketSnapshot(
        market_id="weather-ensemble-1",
        token_id="weather-ensemble-1-yes",
        slug="weather-ensemble-1",
        category=Category.WEATHER,
        timestamp=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
        resolution_time=datetime(2026, 3, 25, 0, 0, tzinfo=UTC),
        best_bid_yes=best_bid_yes,
        best_ask_yes=best_ask_yes,
        best_bid_no=1 - best_ask_yes,
        best_ask_no=1 - best_bid_yes,
        last_traded_price=(best_bid_yes + best_ask_yes) / 2,
        metadata=metadata,
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


def test_weather_ensemble_generates_buy_yes_signal() -> None:
    snapshot = _snapshot(
        metadata={
            "ensemble_probabilities": "0.78,0.80,0.76",
            "forecast_run_utc": "12:00",
        },
        best_bid_yes=0.71,
        best_ask_yes=0.72,
    )
    strategy = WeatherEnsembleStrategy({"min_edge_bps": 400, "model_runs_utc": ["12:00"]})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert len(signals) == 1
    assert signals[0].side == SignalSide.BUY_YES
    assert round(signals[0].fair_probability, 2) == 0.78


def test_weather_ensemble_respects_allowed_model_runs() -> None:
    snapshot = _snapshot(
        metadata={
            "ensemble_probabilities": "0.78,0.80,0.76",
            "forecast_run_utc": "12:00",
        },
        best_bid_yes=0.71,
        best_ask_yes=0.72,
    )
    strategy = WeatherEnsembleStrategy({"min_edge_bps": 400, "model_runs_utc": ["00:00"]})

    signals = asyncio.run(strategy.evaluate(snapshot=snapshot, context={"dashboard_state": _dashboard()}))

    assert signals == []
