"""Paper execution adapter for non-live runs."""

from __future__ import annotations

from pm_bot.core.types import OrderIntent


class PaperExecutionAdapter:
    """In-memory execution adapter for research, paper, and tests."""

    def __init__(self) -> None:
        self.submitted_orders: list[OrderIntent] = []

    async def submit(self, intent: OrderIntent) -> str:
        order_id = f"paper-{len(self.submitted_orders) + 1}"
        self.submitted_orders.append(intent)
        return order_id

    async def cancel_stale(self) -> int:
        return 0

