from __future__ import annotations

import json
from pathlib import Path

from pm_bot.core.settings import TradingSettings
from pm_bot.promotion_artifacts import (
    build_combined_operator_summary,
    build_promotion_artifact_review,
    build_session_operator_bundle,
    format_promotion_artifact_review,
    format_combined_operator_summary,
    format_promotion_operator_summary,
    format_session_operator_bundle,
    load_combined_operator_summary,
    load_promotion_operator_summary,
    write_combined_operator_summary,
    write_promotion_operator_summary,
    write_operator_note_template,
)
from pm_bot.promotion import PromotionReadinessReport
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeState, RuntimeStatus, runtime_state_to_dict


def test_write_operator_note_template_creates_standard_note(tmp_path: Path) -> None:
    note_path = write_operator_note_template(
        path=tmp_path / "operator-note.md",
        stage="sync_shadow_to_small_live_baseline",
        run_id="run-123",
        market_window="BTC/ETH 15m",
    )

    content = note_path.read_text(encoding="utf-8")
    assert "run_id: run-123" in content
    assert "market_window: BTC/ETH 15m" in content
    assert "outcome: pending" in content


def test_build_promotion_artifact_review_summarizes_source_and_shadow(tmp_path: Path) -> None:
    source_metrics, source_state, source_events = _write_artifacts(tmp_path / "source", orders_submitted=2, orders_filled=1)
    shadow_metrics, shadow_state, shadow_events = _write_artifacts(tmp_path / "shadow", orders_submitted=2, orders_filled=0)
    note_path = tmp_path / "operator-note.md"
    note_path.write_text("# note\n", encoding="utf-8")

    review = build_promotion_artifact_review(
        stage="sync_shadow_to_small_live_baseline",
        metrics_path=source_metrics,
        state_path=source_state,
        event_path=source_events,
        note_path=note_path,
        shadow_metrics_path=shadow_metrics,
        shadow_state_path=shadow_state,
        shadow_event_path=shadow_events,
    )

    assert review.note_present is True
    assert review.source_orders_submitted == 2
    assert review.shadow_orders_submitted == 2
    rendered = format_promotion_artifact_review(review)
    assert "Promotion Artifact Review" in rendered
    assert "## Shadow" in rendered


def test_format_promotion_operator_summary_combines_readiness_and_review(tmp_path: Path) -> None:
    source_metrics, source_state, source_events = _write_artifacts(tmp_path / "source", orders_submitted=2, orders_filled=1)
    review = build_promotion_artifact_review(
        stage="paper_to_sync_shadow",
        metrics_path=source_metrics,
        state_path=source_state,
        event_path=source_events,
    )
    readiness = PromotionReadinessReport(
        stage="paper_to_sync_shadow",
        ready=False,
        source_config_dir="configs/profiles/paper-baseline-v1",
        target_config_dir="configs/profiles/sync-promotion-shadow-v1",
        blockers=("missing operator note",),
        warnings=(),
        checks={"operator_note": "missing"},
        rollback_triggers=("runtime halted",),
        escalation_actions=("inspect artifacts",),
    )

    rendered = format_promotion_operator_summary(readiness=readiness, review=review)

    assert "Promotion Operator Summary" in rendered
    assert "pause: missing operator note" in rendered
    assert "Rollback Triggers" in rendered


def test_write_promotion_operator_summary_writes_sidecar_json(tmp_path: Path) -> None:
    source_metrics, source_state, source_events = _write_artifacts(tmp_path / "source", orders_submitted=2, orders_filled=1)
    review = build_promotion_artifact_review(
        stage="paper_to_sync_shadow",
        metrics_path=source_metrics,
        state_path=source_state,
        event_path=source_events,
    )
    readiness = PromotionReadinessReport(
        stage="paper_to_sync_shadow",
        ready=True,
        source_config_dir="configs/profiles/paper-baseline-v1",
        target_config_dir="configs/profiles/sync-promotion-shadow-v1",
        blockers=(),
        warnings=("review drift",),
        checks={},
        rollback_triggers=("runtime halted",),
        escalation_actions=("inspect artifacts",),
    )

    target = write_promotion_operator_summary(
        path=tmp_path / "promotion-summary.md",
        readiness=readiness,
        review=review,
    )

    loaded = load_promotion_operator_summary(target)
    assert loaded is not None
    assert loaded.stage == "paper_to_sync_shadow"
    assert loaded.action == "review"
    assert loaded.warning_count == 1
    assert target.with_suffix(".json").exists()


def test_combined_operator_summary_merges_runtime_and_promotion_actions(tmp_path: Path) -> None:
    source_metrics, source_state, source_events = _write_artifacts(tmp_path / "source", orders_submitted=2, orders_filled=1)
    review = build_promotion_artifact_review(
        stage="paper_to_sync_shadow",
        metrics_path=source_metrics,
        state_path=source_state,
        event_path=source_events,
    )
    readiness = PromotionReadinessReport(
        stage="paper_to_sync_shadow",
        ready=True,
        source_config_dir="configs/profiles/paper-baseline-v1",
        target_config_dir="configs/profiles/sync-promotion-shadow-v1",
        blockers=(),
        warnings=(),
        checks={},
        rollback_triggers=(),
        escalation_actions=(),
    )
    promotion_summary = load_promotion_operator_summary(
        write_promotion_operator_summary(
            path=tmp_path / "promotion-summary.md",
            readiness=readiness,
            review=review,
        )
    )
    assert promotion_summary is not None

    summary = build_combined_operator_summary(
        dashboard=DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(),
            pending_orders=(),
            status=RuntimeStatus.RUNNING,
            halt_reason=HaltReason.NONE,
            halt_message=None,
            last_alert=None,
            daily_order_count=0,
            daily_order_soft_limit_reached=False,
        ),
        trading_settings=TradingSettings(),
        promotion_summary=promotion_summary,
    )

    assert summary.overall_action == "proceed"
    assert summary.next_step == "proceed_sync_shadow"
    assert summary.alert_count == 0
    assert "overall_action: proceed" in format_combined_operator_summary(summary)


def test_write_combined_operator_summary_writes_sidecar_json(tmp_path: Path) -> None:
    target = write_combined_operator_summary(
        path=tmp_path / "operator-summary.md",
        dashboard=DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(),
            pending_orders=(),
            status=RuntimeStatus.HALTED,
            halt_reason=HaltReason.STALE_DATA,
            halt_message="stale",
            last_alert="stale",
            daily_order_count=0,
            daily_order_soft_limit_reached=False,
        ),
    )

    loaded = load_combined_operator_summary(target)
    assert loaded is not None
    assert loaded.overall_action == "pause"
    assert loaded.rollback_target == "previous_stage"
    assert loaded.alert_count >= 1
    assert target.with_suffix(".json").exists()


def test_build_session_operator_bundle_includes_execution_feedback(tmp_path: Path) -> None:
    metrics_path, state_path, event_path = _write_artifacts(
        tmp_path / "session",
        orders_submitted=3,
        orders_filled=1,
        include_closed_trade=True,
    )
    bundle = build_session_operator_bundle(
        dashboard=DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(),
            pending_orders=(),
            status=RuntimeStatus.RUNNING,
            halt_reason=HaltReason.NONE,
            halt_message=None,
            last_alert=None,
            daily_order_count=0,
            daily_order_soft_limit_reached=False,
        ),
        trading_settings=TradingSettings(),
        metrics_path=metrics_path,
        state_path=state_path,
        event_path=event_path,
        session_label="paper-session",
    )

    assert bundle.artifacts.event_count == 2
    assert bundle.execution_feedback is not None
    assert bundle.execution_feedback.recommended_route_bias == "more_passive"
    rendered = format_session_operator_bundle(bundle)
    assert "## Session Artifacts" in rendered
    assert "## Execution Feedback" in rendered
    assert "session_label: paper-session" in rendered


def _write_artifacts(
    tmp_path: Path,
    *,
    orders_submitted: int,
    orders_filled: int,
    include_closed_trade: bool = False,
) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    metrics_path = tmp_path / "metrics.json"
    state_path = tmp_path / "state.json"
    event_path = tmp_path / "events.jsonl"
    metrics_path.write_text(
        json.dumps(
            {
                "orders_submitted": orders_submitted,
                "orders_filled": orders_filled,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    state = RuntimeState(starting_equity=100.0, day_starting_equity=100.0)
    state_path.write_text(json.dumps(runtime_state_to_dict(state), ensure_ascii=True), encoding="utf-8")
    event_lines = ['{"event_type":"order.submitted"}']
    if include_closed_trade:
        event_lines.append(
            json.dumps(
                {
                    "event_type": "trade.closed",
                    "payload": {
                        "market_id": "btc-market",
                        "token_id": "token-1",
                        "strategy_id": "crypto.phase2",
                        "realized_pnl": -3.5,
                        "fees_paid": 0.1,
                        "closed_at": "2026-03-29T00:00:00+00:00",
                    },
                },
                ensure_ascii=True,
            )
        )
    event_path.write_text("\n".join(event_lines) + "\n", encoding="utf-8")
    return metrics_path, state_path, event_path
