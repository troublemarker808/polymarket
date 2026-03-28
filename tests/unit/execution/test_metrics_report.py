from pm_bot.execution.metrics_report import compare_metrics, format_metric_comparison


def test_compare_metrics_formats_numeric_delta() -> None:
    rows = compare_metrics(
        baseline={"orders_submitted": 2, "fill_rate": 0.25},
        candidate={"orders_submitted": 5, "fill_rate": 0.4},
        keys=("orders_submitted", "fill_rate"),
    )

    assert rows[0]["delta"] == 3
    assert rows[1]["delta"] == 0.15000000000000002
    output = format_metric_comparison(rows)
    assert "metric,baseline,candidate,delta" in output
    assert "orders_submitted,2,5,3" in output
