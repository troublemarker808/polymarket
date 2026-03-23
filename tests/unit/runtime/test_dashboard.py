from datetime import UTC, datetime

from pm_bot.core.types import Category
from pm_bot.runtime.dashboard import render_dashboard
from pm_bot.runtime.state import DashboardState, HaltReason, PendingOrderState, PositionState, RuntimeStatus


def test_render_dashboard_outputs_operator_fields() -> None:
    rendered = render_dashboard(
        DashboardState(
            total_equity=100.5,
            today_pnl=0.5,
            open_positions=(
                PositionState(
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    notional=5.0,
                    shares=10.0,
                    average_entry_price=0.5,
                    mark_price=0.62,
                    unrealized_pnl=1.2,
                    opened_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                ),
            ),
            pending_orders=(
                PendingOrderState(
                    order_id="o1",
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    side="buy_yes",
                    limit_price=0.5,
                    requested_shares=10.0,
                    requested_notional=5.0,
                    matched_shares=4.0,
                    matched_notional=2.0,
                    fees_paid=0.0,
                    status="partially_filled",
                    created_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 23, 10, 1, 0, tzinfo=UTC),
                ),
            ),
            status=RuntimeStatus.HALTED,
            halt_reason=HaltReason.CONSECUTIVE_LOSSES,
            halt_message="halted after consecutive realized losses",
            last_alert="halted after consecutive realized losses",
            daily_order_count=4,
            daily_order_soft_limit_reached=False,
        )
    )

    assert "runtime_dashboard" in rendered
    assert "status=halted" in rendered
    assert "halt_reason=consecutive_losses" in rendered
    assert "open_positions=1" in rendered
    assert "pending_orders=1" in rendered
    assert "position=m1:crypto:notional=5.00:shares=10.000000:avg=0.500000:mark=0.620000:unrealized=1.20" in rendered
    assert "pending_order=o1:m1:crypto:buy_yes:status=partially_filled:limit=0.500000:req_shares=10.000000:matched_shares=4.000000:notional=5.00" in rendered
