from datetime import UTC, datetime

from pm_bot.core.types import Category
from pm_bot.execution.portfolio import build_portfolio_state, portfolio_state_from_dashboard
from pm_bot.runtime.state import DashboardState, HaltReason, PendingOrderState, PositionState, RuntimeStatus


def test_build_portfolio_state_groups_open_and_pending_exposure() -> None:
    position = PositionState(
        market_id="m1",
        token_id="t1",
        category=Category.CRYPTO,
        strategy_id="crypto.surface",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.5,
        opened_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
    )
    pending = PendingOrderState(
        order_id="o1",
        market_id="m1",
        token_id="t1",
        category=Category.CRYPTO,
        strategy_id="crypto.surface",
        side="buy_yes",
        limit_price=0.5,
        requested_shares=10.0,
        requested_notional=5.0,
        matched_shares=0.0,
        matched_notional=0.0,
        fees_paid=0.0,
        status="pending",
        created_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
    )

    portfolio = build_portfolio_state(open_positions=(position,), pending_orders=(pending,))

    assert portfolio.total_open_notional == 5.0
    assert portfolio.total_pending_notional == 5.0
    assert portfolio.total_gross_notional == 10.0
    assert portfolio.by_market[0].gross_notional == 10.0
    assert portfolio.by_category[0].market_count == 1


def test_portfolio_state_from_dashboard_uses_dashboard_positions_and_orders() -> None:
    dashboard = DashboardState(
        total_equity=100.0,
        today_pnl=0.0,
        open_positions=(
            PositionState(
                market_id="sports-1",
                token_id="sports-1-yes",
                category=Category.SPORTS,
                strategy_id="sports.anchor",
                notional=4.0,
                opened_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
            ),
        ),
        pending_orders=(
            PendingOrderState(
                order_id="weather-order",
                market_id="weather-1",
                token_id="weather-1-yes",
                category=Category.WEATHER,
                strategy_id="weather.ensemble",
                side="buy_yes",
                limit_price=0.42,
                requested_shares=10.0,
                requested_notional=4.2,
                matched_shares=0.0,
                matched_notional=0.0,
                fees_paid=0.0,
                status="pending",
                created_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
            ),
        ),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=1,
        daily_order_soft_limit_reached=False,
    )

    portfolio = portfolio_state_from_dashboard(dashboard)

    assert portfolio.total_open_notional == 4.0
    assert portfolio.total_pending_notional == 4.2
    assert [exposure.category.value for exposure in portfolio.by_category] == ["sports", "weather"]
