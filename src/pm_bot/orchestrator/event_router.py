"""Runtime orchestration.

The router remains category-agnostic. It fans normalized snapshots out to enabled
strategies and passes signals through risk, planning, execution, and recording.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pm_bot.core.interfaces import (
    EventRecorder,
    ExecutionAdapter,
    MarketDataAdapter,
    RiskManager,
    Strategy,
)
from pm_bot.core.types import MarketSnapshot
from pm_bot.execution.order_planner import signal_to_order_intent


class EventRouter:
    """Coordinates adapters, strategies, risk, and execution without owning alpha."""

    # Runtime flow:
    #
    # snapshot
    #   -> strategies
    #   -> signals
    #   -> risk review
    #   -> order intent
    #   -> execution
    #   -> risk state update
    #   -> recorder / dashboard

    def __init__(
        self,
        market_data: MarketDataAdapter,
        strategies: Sequence[Strategy],
        risk_manager: RiskManager,
        execution: ExecutionAdapter,
        recorder: EventRecorder | None = None,
        default_order_size: float = 10.0,
    ) -> None:
        self.market_data = market_data
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.execution = execution
        self.recorder = recorder
        self.default_order_size = default_order_size
        self.snapshot_cache: dict[str, MarketSnapshot] = {}

    async def run_once(
        self,
        snapshot: MarketSnapshot,
        context: Mapping[str, object] | None = None,
    ) -> list[str]:
        submitted_order_ids: list[str] = []
        self.snapshot_cache[snapshot.market_id] = snapshot
        runtime_context = dict(context or {})
        runtime_context["snapshot_cache"] = tuple(self.snapshot_cache.values())
        runtime_context["snapshots_by_market_id"] = dict(self.snapshot_cache)
        runtime_context["dashboard_state"] = self.risk_manager.dashboard_state()

        for strategy in self.strategies:
            signals = await strategy.evaluate(snapshot=snapshot, context=runtime_context)
            for signal in signals:
                await self._record("signal.generated", {"strategy_id": signal.strategy_id})

                signal_decision = await self.risk_manager.review_signal(signal)
                if not signal_decision.approved:
                    await self._record(
                        "signal.rejected",
                        {
                            "strategy_id": signal.strategy_id,
                            "reason": signal_decision.reason,
                        },
                    )
                    continue

                intent = signal_to_order_intent(
                    signal=signal,
                    snapshot=snapshot,
                    default_size=self.default_order_size,
                )
                if intent is None:
                    continue

                order_decision = await self.risk_manager.review_order(intent)
                if not order_decision.approved:
                    await self._record(
                        "order.rejected",
                        {
                            "strategy_id": signal.strategy_id,
                            "reason": order_decision.reason,
                        },
                    )
                    continue

                order_id = await self.execution.submit(intent)
                await self.risk_manager.record_order_submission(intent, order_id)
                submitted_order_ids.append(order_id)
                await self._record(
                    "order.submitted",
                    {
                        "order_id": order_id,
                        "strategy_id": signal.strategy_id,
                        "market_id": signal.market_id,
                    },
                )

        return submitted_order_ids

    async def run_forever(self, context: Mapping[str, object] | None = None) -> None:
        async for snapshot in self.market_data.stream_snapshots():
            await self.run_once(snapshot=snapshot, context=context)

    async def _record(self, event_type: str, payload: Mapping[str, object]) -> None:
        if self.recorder is None:
            return

        await self.recorder.record(event_type=event_type, payload=payload)
