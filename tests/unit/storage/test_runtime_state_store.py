from datetime import UTC, datetime

from pm_bot.core.types import Category
from pm_bot.runtime.state import HaltReason, PendingOrderState, PositionState, RuntimeState, RuntimeStatus
from pm_bot.storage.runtime_state_store import JsonRuntimeStateStore


def test_runtime_state_store_round_trips_state(tmp_path) -> None:
    store = JsonRuntimeStateStore(tmp_path / "runtime-state.json")
    state = RuntimeState(
        starting_equity=100.0,
        day_starting_equity=100.0,
        realized_pnl_today=1.25,
        unrealized_pnl=-0.25,
        consecutive_losses=2,
        orders_today=3,
        open_positions={
            "m1": PositionState(
                market_id="m1",
                token_id="t1",
                category=Category.CRYPTO,
                strategy_id="crypto.surface",
                notional=5.0,
                opened_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
            )
        },
        pending_orders={
            "o1": PendingOrderState(
                order_id="o1",
                market_id="m2",
                token_id="t2",
                category=Category.CRYPTO,
                strategy_id="crypto.maker",
                side="buy_no",
                limit_price=0.48,
                requested_shares=10.0,
                requested_notional=4.8,
                matched_shares=0.0,
                matched_notional=0.0,
                fees_paid=0.0,
                status="pending",
                created_at=datetime(2026, 3, 23, 10, 1, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 23, 10, 1, 0, tzinfo=UTC),
            )
        },
        status=RuntimeStatus.HALTED,
        halt_reason=HaltReason.DAILY_DRAWDOWN,
        halt_message="halted after daily drawdown threshold breach",
        last_alert="halted after daily drawdown threshold breach",
        updated_at=datetime(2026, 3, 23, 10, 5, 0, tzinfo=UTC),
    )

    store.save(state)
    loaded = store.load()

    assert loaded is not None
    assert loaded.status == RuntimeStatus.HALTED
    assert loaded.halt_reason == HaltReason.DAILY_DRAWDOWN
    assert loaded.orders_today == 3
    assert loaded.open_positions["m1"].category == Category.CRYPTO
    assert loaded.pending_orders["o1"].status == "pending"
    assert loaded.pending_orders["o1"].side == "buy_no"
