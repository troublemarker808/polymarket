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
        self._intent_sequence = 0

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
            runtime_context["recent_events"] = _recent_runtime_events(self.recorder)
            signals = await strategy.evaluate(snapshot=snapshot, context=runtime_context)
            for signal in signals:
                await self._record(
                    "signal.generated",
                    {
                        "strategy_id": signal.strategy_id,
                        "market_id": signal.market_id,
                        "token_id": signal.token_id,
                        "fair_probability": signal.fair_probability,
                        "confidence": signal.confidence,
                        "side": signal.side.value,
                        "edge_bps": signal.edge_bps,
                        "target_price": signal.target_price,
                        "target_size": signal.target_size,
                        "time_in_force": signal.time_in_force,
                        "quote_ttl_seconds": signal.quote_ttl_seconds,
                        "rationale_tags": list(signal.rationale_tags),
                        "diagnostics": dict(signal.diagnostics),
                        "generated_at": signal.generated_at.isoformat(),
                    },
                )

                signal_decision = await self.risk_manager.review_signal(signal)
                if not signal_decision.approved:
                    await self._record(
                        "signal.rejected",
                        {
                            "strategy_id": signal.strategy_id,
                            "market_id": signal.market_id,
                            "side": signal.side.value,
                            "reason": signal_decision.reason,
                            "generated_at": signal.generated_at.isoformat(),
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
                intent = self._assign_intent_id(intent)

                order_decision = await self.risk_manager.review_order(intent)
                if not order_decision.approved:
                    await self._record(
                        "order.rejected",
                        {
                            "intent_id": intent.intent_id,
                            "strategy_id": signal.strategy_id,
                            "market_id": signal.market_id,
                            "side": signal.side.value,
                            "reason": order_decision.reason,
                            "created_at": intent.created_at.isoformat(),
                            "signal_edge_bps": signal.edge_bps,
                        },
                    )
                    continue

                if order_decision.replacement_order_id is not None:
                    canceled_order = await self.execution.cancel_order(
                        order_decision.replacement_order_id,
                        now=intent.created_at,
                    )
                    if canceled_order is None:
                        await self._record(
                        "order.rejected",
                        {
                            "intent_id": intent.intent_id,
                            "strategy_id": signal.strategy_id,
                            "market_id": signal.market_id,
                            "side": signal.side.value,
                            "reason": "replacement cancel failed",
                            "created_at": intent.created_at.isoformat(),
                                "signal_edge_bps": signal.edge_bps,
                            },
                        )
                        continue
                    await self.risk_manager.record_order_cancellation(canceled_order.order_id)
                    runtime_context["dashboard_state"] = self.risk_manager.dashboard_state()
                    await self._record(
                        "order.canceled",
                        {
                            **_tracked_order_payload(canceled_order),
                            "reason": "open_order_replaced",
                            "replacement_market_id": intent.market_id,
                        },
                    )

                try:
                    order_id = await self.execution.submit(intent)
                except Exception as exc:
                    await self._record(
                        "order.rejected",
                        {
                            "intent_id": intent.intent_id,
                            "strategy_id": signal.strategy_id,
                            "market_id": signal.market_id,
                            "token_id": intent.token_id,
                            "side": signal.side.value,
                            "reason": f"execution submit failed: {type(exc).__name__}: {exc}",
                            "created_at": intent.created_at.isoformat(),
                            "signal_edge_bps": signal.edge_bps,
                            "price": intent.price,
                            "size": intent.size,
                            "notional": intent.notional,
                        },
                    )
                    continue
                await self.risk_manager.record_order_submission(intent, order_id)
                runtime_context["dashboard_state"] = self.risk_manager.dashboard_state()
                submitted_order_ids.append(order_id)
                await self._record(
                    "order.submitted",
                    {
                        "order_id": order_id,
                        "intent_id": intent.intent_id,
                        "strategy_id": signal.strategy_id,
                        "market_id": signal.market_id,
                        "token_id": intent.token_id,
                        "side": signal.side.value,
                        "price": intent.price,
                        "size": intent.size,
                        "notional": intent.notional,
                        "created_at": intent.created_at.isoformat(),
                        "replaced_order_id": order_decision.replacement_order_id,
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

    def _assign_intent_id(self, intent):
        if getattr(intent, "intent_id", None):
            return intent
        self._intent_sequence += 1
        intent.intent_id = f"intent-{self._intent_sequence:08d}"
        return intent


def _tracked_order_payload(order: object) -> dict[str, object]:
    created_at = getattr(order, "created_at", None)
    updated_at = getattr(order, "updated_at", None)
    status = getattr(getattr(order, "status", None), "value", getattr(order, "status", ""))
    return {
        "order_id": getattr(order, "order_id", ""),
        "intent_id": getattr(order, "intent_id", None),
        "time_in_force": getattr(order, "time_in_force", "GTC"),
        "market_id": getattr(order, "market_id", ""),
        "token_id": getattr(order, "token_id", ""),
        "strategy_id": getattr(order, "strategy_id", ""),
        "trade_side": getattr(order, "trade_side", ""),
        "status": status,
        "limit_price": getattr(order, "limit_price", 0.0),
        "requested_shares": getattr(order, "requested_shares", 0.0),
        "requested_notional": getattr(order, "requested_notional", 0.0),
        "quote_ttl_seconds": getattr(order, "quote_ttl_seconds", None),
        "signal_edge_bps": getattr(order, "signal_edge_bps", None),
        "matched_shares": getattr(order, "matched_shares", 0.0),
        "matched_notional": getattr(order, "matched_notional", 0.0),
        "fees_paid_total": getattr(order, "fees_paid", 0.0),
        "created_at": created_at.isoformat() if created_at is not None else "",
        "updated_at": updated_at.isoformat() if updated_at is not None else "",
    }


def _recent_runtime_events(recorder: object, *, limit: int = 64) -> tuple[dict[str, object], ...]:
    if recorder is None:
        return ()
    events = getattr(recorder, "events", None)
    if not isinstance(events, list):
        return ()
    recent: list[dict[str, object]] = []
    for raw_event in events[-limit:]:
        if not isinstance(raw_event, dict):
            continue
        event_type = raw_event.get("event_type")
        payload = raw_event.get("payload")
        if not isinstance(event_type, str) or not isinstance(payload, dict):
            continue
        recent.append({"event_type": event_type, "payload": dict(payload)})
    return tuple(recent)
