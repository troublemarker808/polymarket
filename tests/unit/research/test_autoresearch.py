import json

from pm_bot.research.autoresearch import (
    evaluate_report_comparability,
    format_autoresearch_candidate_ranking,
    format_autoresearch_report,
    generate_autoresearch_report,
    rank_autoresearch_candidates,
)


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
    assert "edge_after_cost_proxy/fill_density" in report.next_follow_up_experiments[0]


def test_generate_autoresearch_report_excludes_recovered_live_noise_from_effective_baseline(
    tmp_path,
) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "signals_generated": 2,
                "orders_submitted": 1,
                "orders_rejected": 0,
                "orders_filled": 4,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 2,
                "fill_rate": 4.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 12.0,
                "market_data_failures": 0,
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "order.submitted",
                        "payload": {
                            "order_id": "order-1",
                            "strategy_id": "crypto.phase2",
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "order_id": "order-1",
                            "strategy_id": "crypto.phase2",
                            "fill_source": "taker",
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "order.filled",
                        "payload": {
                            "order_id": "legacy-1",
                            "strategy_id": "recovered.live",
                            "fill_source": "taker",
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "trade.closed",
                        "payload": {
                            "strategy_id": "recovered.live",
                            "net_pnl": -1.5,
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = generate_autoresearch_report(metrics_path=metrics_path, event_path=event_path)

    assert report.classification == "execution-bound"
    assert report.effective_orders_submitted == 1
    assert report.effective_orders_filled == 1
    assert report.effective_trades_closed == 0
    assert report.effective_fill_rate == 1.0
    assert report.effective_closed_trade_net_pnl == 0.0
    assert report.recovered_closed_trade_count == 1
    assert report.recovered_closed_trade_net_pnl == -1.5


def test_generate_autoresearch_report_includes_promotion_gate_summary_when_scorecard_is_provided(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "signals_generated": 1,
                "orders_submitted": 1,
                "orders_rejected": 0,
                "orders_filled": 1,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 1,
                "fill_rate": 1.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 1.0,
                "market_data_failures": 0,
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text("", encoding="utf-8")
    scorecard_path = tmp_path / "final_scorecard.json"
    scorecard_path.write_text(
        json.dumps(
            {
                "promotion_decision": "review",
                "promotion_stage_label": "paper available",
                "route_stage_acceptance_decision": "review",
                "route_stage_failed_stages": ["close_out_quality", "profitability_tail_risk"],
                "route_stage_statuses": {
                    "scan_quality": "pass",
                    "selection_pass_through": "pass",
                    "route_conversion_quality": "pass",
                    "close_out_quality": "blocked",
                    "profitability_tail_risk": "review",
                },
                "route_stage_blockers": {
                    "close_out_quality": ["close_out_no_closed_trades"],
                    "profitability_tail_risk": ["profitability_non_positive_pnl_per_notional"],
                },
                "promotion_blocking_reasons": ["insufficient_closed_trade_count"],
                "promotion_max_single_loss_pnl": -0.2,
                "observed_max_single_loss_pnl": -0.13697,
                "promotion_max_top3_loss_concentration_ratio": 0.75,
                "observed_top3_loss_concentration_ratio": 0.52,
                "top_loss_market_breakdown": [
                    {"market_id": "701496", "total_abs_loss": 0.13697, "loss_count": 1}
                ],
                "top_loss_signature_breakdown": [
                    {"signature": "entry|maker|default|buy_no", "total_abs_loss": 0.13697, "loss_count": 1}
                ],
                "top_loss_trades": [
                    {"market_id": "701496", "net_pnl": -0.13697}
                ],
            }
        ),
        encoding="utf-8",
    )

    report = generate_autoresearch_report(
        metrics_path=metrics_path,
        event_path=event_path,
        promotion_scorecard_path=scorecard_path,
    )

    assert report.promotion_gate_decision == "review"
    assert report.promotion_gate_stage_label == "paper available"
    assert report.route_stage_acceptance_decision == "review"
    assert report.route_stage_failed_stages == ("close_out_quality", "profitability_tail_risk")
    assert report.route_stage_statuses["close_out_quality"] == "blocked"
    assert report.route_stage_blockers["close_out_quality"] == ("close_out_no_closed_trades",)
    assert report.promotion_gate_blockers == ("insufficient_closed_trade_count",)
    assert report.top_loss_markets == ("701496",)
    assert report.top_loss_signatures == ("entry|maker|default|buy_no",)
    assert report.top_loss_trades == ("701496:-0.136970",)
    assert report.promotion_gate_max_single_loss_pnl == -0.2
    assert report.promotion_gate_observed_max_single_loss_pnl == -0.13697
    assert report.promotion_gate_max_top3_loss_concentration_ratio == 0.75
    assert report.promotion_gate_observed_top3_loss_concentration_ratio == 0.52


def test_generate_autoresearch_report_resolves_protocol_metadata_from_arguments_or_metrics(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "signals_generated": 1,
                "orders_submitted": 1,
                "orders_rejected": 0,
                "orders_filled": 1,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 1,
                "fill_rate": 1.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 1.0,
                "market_data_failures": 0,
                "window_set_id": "btc-windows-v1",
                "variant_id": "v118a",
                "evidence_tier": "paper",
                "loop_stage_set": "btc-closure-v1",
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text("", encoding="utf-8")

    from_metrics = generate_autoresearch_report(metrics_path=metrics_path, event_path=event_path)
    assert from_metrics.window_set_id == "btc-windows-v1"
    assert from_metrics.variant_id == "v118a"
    assert from_metrics.evidence_tier == "paper"
    assert from_metrics.loop_stage_set == "btc-closure-v1"

    from_args = generate_autoresearch_report(
        metrics_path=metrics_path,
        event_path=event_path,
        window_set_id="btc-windows-v2",
        variant_id="v119b",
        evidence_tier="replay",
        loop_stage_set="btc-closure-v2",
    )
    assert from_args.window_set_id == "btc-windows-v2"
    assert from_args.variant_id == "v119b"
    assert from_args.evidence_tier == "replay"
    assert from_args.loop_stage_set == "btc-closure-v2"


def test_evaluate_report_comparability_blocks_mixed_window_sets(tmp_path) -> None:
    metrics_a = tmp_path / "metrics_a.json"
    metrics_b = tmp_path / "metrics_b.json"
    for path, window_set_id in ((metrics_a, "ws-a"), (metrics_b, "ws-b")):
        path.write_text(
            json.dumps(
                {
                    "signals_generated": 1,
                    "orders_submitted": 1,
                    "orders_rejected": 0,
                    "orders_filled": 1,
                    "orders_partially_filled": 0,
                    "orders_expired": 0,
                    "orders_canceled": 0,
                    "trades_closed": 1,
                    "fill_rate": 1.0,
                    "cancel_rate": 0.0,
                    "avg_fill_price_vs_mid_bps": 1.0,
                    "market_data_failures": 0,
                    "window_set_id": window_set_id,
                    "evidence_tier": "paper",
                    "loop_stage_set": "btc-closure-v1",
                }
            ),
            encoding="utf-8",
        )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text("", encoding="utf-8")
    report_a = generate_autoresearch_report(metrics_path=metrics_a, event_path=event_path)
    report_b = generate_autoresearch_report(metrics_path=metrics_b, event_path=event_path)
    comparable, blockers = evaluate_report_comparability(reports=(report_a, report_b))
    assert comparable is False
    assert "mixed_window_set_id" in blockers


def test_evaluate_report_comparability_blocks_missing_loop_stage_set(tmp_path) -> None:
    metrics_a = tmp_path / "metrics_a.json"
    metrics_b = tmp_path / "metrics_b.json"
    metrics_a.write_text(
        json.dumps(
            {
                "signals_generated": 1,
                "orders_submitted": 1,
                "orders_rejected": 0,
                "orders_filled": 1,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 1,
                "fill_rate": 1.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 1.0,
                "market_data_failures": 0,
                "window_set_id": "ws-a",
                "evidence_tier": "paper",
                "loop_stage_set": "btc-closure-v1",
            }
        ),
        encoding="utf-8",
    )
    metrics_b.write_text(
        json.dumps(
            {
                "signals_generated": 1,
                "orders_submitted": 1,
                "orders_rejected": 0,
                "orders_filled": 1,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 1,
                "fill_rate": 1.0,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 1.0,
                "market_data_failures": 0,
                "window_set_id": "ws-a",
                "evidence_tier": "paper",
            }
        ),
        encoding="utf-8",
    )
    event_path = tmp_path / "events.jsonl"
    event_path.write_text("", encoding="utf-8")
    report_a = generate_autoresearch_report(metrics_path=metrics_a, event_path=event_path)
    report_b = generate_autoresearch_report(metrics_path=metrics_b, event_path=event_path)
    comparable, blockers = evaluate_report_comparability(reports=(report_a, report_b))
    assert comparable is False
    assert "missing_loop_stage_set" in blockers


def test_rank_autoresearch_candidates_prefers_better_acceptance_and_fewer_failed_stages(tmp_path) -> None:
    metrics_a = tmp_path / "metrics_a.json"
    metrics_b = tmp_path / "metrics_b.json"
    metrics_a.write_text(
        json.dumps(
            {
                "signals_generated": 10,
                "orders_submitted": 8,
                "orders_rejected": 0,
                "orders_filled": 6,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 4,
                "fill_rate": 0.75,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 1.0,
                "market_data_failures": 0,
                "window_set_id": "btc-window-v1",
                "variant_id": "candidate-a",
                "evidence_tier": "paper",
                "loop_stage_set": "btc-closure-v1",
            }
        ),
        encoding="utf-8",
    )
    metrics_b.write_text(
        json.dumps(
            {
                "signals_generated": 10,
                "orders_submitted": 8,
                "orders_rejected": 0,
                "orders_filled": 6,
                "orders_partially_filled": 0,
                "orders_expired": 0,
                "orders_canceled": 0,
                "trades_closed": 2,
                "fill_rate": 0.75,
                "cancel_rate": 0.0,
                "avg_fill_price_vs_mid_bps": 1.0,
                "market_data_failures": 0,
                "window_set_id": "btc-window-v1",
                "variant_id": "candidate-b",
                "evidence_tier": "paper",
                "loop_stage_set": "btc-closure-v1",
            }
        ),
        encoding="utf-8",
    )
    scorecard_a = tmp_path / "scorecard_a.json"
    scorecard_b = tmp_path / "scorecard_b.json"
    scorecard_a.write_text(
        json.dumps(
            {
                "route_stage_acceptance_decision": "proceed",
                "route_stage_failed_stages": [],
                "promotion_decision": "proceed",
                "promotion_stage_label": "shadow validation",
                "promotion_blocking_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    scorecard_b.write_text(
        json.dumps(
            {
                "route_stage_acceptance_decision": "review",
                "route_stage_failed_stages": ["close_out_quality"],
                "promotion_decision": "review",
                "promotion_stage_label": "paper available",
                "promotion_blocking_reasons": ["insufficient_closed_trade_count"],
            }
        ),
        encoding="utf-8",
    )

    report_a = generate_autoresearch_report(metrics_path=metrics_a, promotion_scorecard_path=scorecard_a)
    report_b = generate_autoresearch_report(metrics_path=metrics_b, promotion_scorecard_path=scorecard_b)
    ranking = rank_autoresearch_candidates(reports=(report_a, report_b))

    assert ranking.comparable is True
    assert ranking.ranked_entries[0].variant_id == "candidate-a"
    assert ranking.ranked_entries[1].variant_id == "candidate-b"
    rendered = format_autoresearch_candidate_ranking(ranking)
    assert "Autoresearch Candidate Ranking" in rendered
    assert "candidate-a" in rendered
