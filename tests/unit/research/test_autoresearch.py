import json

from pm_bot.research.autoresearch import format_autoresearch_report, generate_autoresearch_report


def test_generate_autoresearch_report_classifies_capacity_bound_run(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "signals_generated": 500,
                "orders_submitted": 5,
                "orders_rejected": 495,
                "orders_filled": 0,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 0,
                "fill_rate": 0.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 0.0,
                "market_data_failures": 0,
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        "\n".join(
            json.dumps({"event_type": "order.rejected", "payload": {"reason": "daily order hard limit reached"}})
            for _ in range(480)
        )
        + "\n"
        + "\n".join(
            json.dumps({"event_type": "order.rejected", "payload": {"reason": "max concurrent positions reached"}})
            for _ in range(15)
        ),
        encoding="utf-8",
    )

    report = generate_autoresearch_report(metrics_path=metrics_path, event_path=event_path)

    assert report.classification == "capacity-bound"
    assert report.dominant_rejection_reasons[0] == ("daily order hard limit reached", 480)
    assert report.event_diagnostics.capacity_bound_rejection_ratio == 1.0
    assert "fixed safety budget" in report.rewritten_objective
    rendered = format_autoresearch_report(report)
    assert "classification: capacity-bound" in rendered
    assert "strategy.maker.min_spread_bps" in rendered
    assert "strategy.maker.global_cooldown_seconds" in rendered
    assert "strategy.maker.market_cooldown_seconds" in rendered
    assert "strategy.maker.failure_cooldown_seconds" in rendered
    assert "strategy.maker.min_requote_edge_improvement_bps" in rendered
    assert "strategy.maker.failure_reentry_edge_improvement_bps" in rendered
    assert "risk.open_order_replacement_min_edge_improvement_bps" in rendered


def test_generate_autoresearch_report_classifies_alpha_bound_from_negative_closed_trade(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "signals_generated": 20,
                "orders_submitted": 6,
                "orders_rejected": 1,
                "orders_filled": 2,
                "orders_partially_filled": 1,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 1,
                "fill_rate": 0.5,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 2.0,
                "market_data_failures": 0,
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "order.filled", "payload": {"fill_source": "maker"}}),
                json.dumps({"event_type": "order.partially_filled", "payload": {"fill_source": "maker"}}),
                json.dumps(
                    {
                        "event_type": "trade.closed",
                        "payload": {"net_pnl": -1.25},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = generate_autoresearch_report(metrics_path=metrics_path, event_path=event_path)

    assert report.classification == "alpha-bound"
    assert report.event_diagnostics.closed_trade_net_pnl == -1.25
    assert report.fill_source_mix[0] == ("maker", 2)


def test_generate_autoresearch_report_classifies_zero_activity_as_alpha_bound(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "signals_generated": 0,
                "orders_submitted": 0,
                "orders_rejected": 0,
                "orders_filled": 0,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 0,
                "fill_rate": 0.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 0.0,
                "market_data_failures": 0,
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text("", encoding="utf-8")

    report = generate_autoresearch_report(metrics_path=metrics_path, event_path=event_path)

    assert report.classification == "alpha-bound"
    assert "demonstrable tradable alpha" in report.rewritten_objective
    assert report.experiment_matrix[0].name == "Mine eventful fixed windows"
    assert report.experiment_matrix[1].name == "Recalibrate ladder fair value"
    assert "mine-fixed-windows" in report.next_follow_up_experiments[0]
