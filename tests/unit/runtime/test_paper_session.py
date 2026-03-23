from datetime import UTC, datetime

from pm_bot.core.types import Category
from pm_bot.runtime.paper_session import format_dashboard_summary
from pm_bot.runtime.state import DashboardState, HaltReason, PositionState, RuntimeStatus


def test_format_dashboard_summary_includes_operator_fields() -> None:
    summary = format_dashboard_summary(
        {
            "processed_snapshots": 25,
            "submitted_orders": 2,
            "events_recorded": 7,
            "dashboard": DashboardState(
                total_equity=101.5,
                today_pnl=1.5,
                open_positions=(
                    PositionState(
                        market_id="m1",
                        token_id="t1",
                        category=Category.CRYPTO,
                        strategy_id="crypto.surface",
                        notional=5.0,
                        opened_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                    ),
                ),
                pending_orders=(),
                status=RuntimeStatus.RUNNING,
                halt_reason=HaltReason.NONE,
                halt_message=None,
                last_alert=None,
                daily_order_count=2,
                daily_order_soft_limit_reached=False,
            ),
        }
    )

    assert "runtime_dashboard" in summary
    assert "processed_snapshots=25" in summary
    assert "submitted_orders=2" in summary
    assert "total_equity=101.50" in summary
    assert "status=running" in summary
    assert "open_positions=1" in summary
