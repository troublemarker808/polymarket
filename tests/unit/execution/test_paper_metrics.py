from pm_bot.execution.paper_metrics import PaperExecutionMetrics


def test_paper_execution_metrics_counts_order_canceled_once_per_order_id() -> None:
    metrics = PaperExecutionMetrics()
    metrics.record_event(
        event_type="order.canceled",
        payload={"order_id": "order-1", "reason": "stale_ttl_cancel"},
    )
    metrics.record_event(
        event_type="order.canceled",
        payload={"order_id": "order-1", "reason": "exchange_canceled"},
    )
    metrics.record_event(
        event_type="order.canceled",
        payload={"order_id": "order-2", "reason": "exchange_canceled"},
    )

    assert metrics.orders_canceled == 2
