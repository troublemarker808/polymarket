from pm_bot.execution.paper_metrics import PaperExecutionMetrics


def test_paper_metrics_track_fill_shares_and_fill_sources() -> None:
    metrics = PaperExecutionMetrics()

    metrics.record_event(
        "order.partially_filled",
        {
            "fill_shares_delta": 4.0,
            "fill_source": "maker",
            "average_fill_price": 0.48,
            "mid_price": 0.50,
            "fill_age_ms": 1000.0,
        },
    )
    metrics.record_event(
        "order.filled",
        {
            "fill_shares_delta": 6.0,
            "fill_source": "taker",
            "average_fill_price": 0.51,
            "mid_price": 0.50,
            "fill_age_ms": 2500.0,
        },
    )

    assert metrics.orders_partially_filled == 1
    assert metrics.orders_filled == 1
    assert metrics.filled_shares_total == 10.0
    assert metrics.maker_fill_share == 0.4
    assert metrics.taker_fill_share == 0.6
    assert metrics.avg_time_to_fill_ms == 2500.0
    assert round(metrics.avg_fill_price_vs_mid_bps, 6) == -40.0
