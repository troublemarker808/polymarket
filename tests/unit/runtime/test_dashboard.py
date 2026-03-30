from datetime import UTC, datetime
from pathlib import Path

from pm_bot.core.settings import TradingSettings
from pm_bot.core.types import Category
from pm_bot.promotion import PromotionReadinessReport
from pm_bot.promotion_artifacts import build_promotion_artifact_review, write_promotion_operator_summary
from pm_bot.runtime.dashboard import (
    render_dashboard,
    render_dashboard_with_ops_summary,
    render_dashboard_with_promotion_summary,
)
from pm_bot.runtime.state import DashboardState, HaltReason, PendingOrderState, PositionState, RuntimeStatus


def test_render_dashboard_outputs_operator_fields() -> None:
    rendered = render_dashboard(
        DashboardState(
            total_equity=100.5,
            today_pnl=0.5,
            open_positions=(
                PositionState(
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    notional=5.0,
                    shares=10.0,
                    average_entry_price=0.5,
                    mark_price=0.62,
                    unrealized_pnl=1.2,
                    opened_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                    exposure_group_id="crypto:btc-reach-ladder",
                    thesis_group_id="crypto:btc:reach",
                    underlying_group_id="crypto:btc",
                ),
            ),
            pending_orders=(
                PendingOrderState(
                    order_id="o1",
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    side="buy_yes",
                    limit_price=0.5,
                    requested_shares=10.0,
                    requested_notional=5.0,
                    matched_shares=4.0,
                    matched_notional=2.0,
                    fees_paid=0.0,
                    status="partially_filled",
                    created_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 23, 10, 1, 0, tzinfo=UTC),
                    exposure_group_id="crypto:btc-reach-ladder",
                    thesis_group_id="crypto:btc:reach",
                    underlying_group_id="crypto:btc",
                ),
            ),
            status=RuntimeStatus.HALTED,
            halt_reason=HaltReason.CONSECUTIVE_LOSSES,
            halt_message="halted after consecutive realized losses",
            last_alert="halted after consecutive realized losses",
            daily_order_count=4,
            daily_order_soft_limit_reached=False,
            last_order_rejection_reason="order exceeds exposure-group notional cap",
            last_order_rejection_market_id="m2",
            last_order_rejection_exposure_group_id="crypto:btc-reach-ladder",
            last_order_rejection_thesis_group_id="crypto:btc:reach",
            last_order_rejection_underlying_group_id="crypto:btc",
        )
    )

    assert "runtime_dashboard" in rendered
    assert "risk_action=pause" in rendered
    assert "risk_decision=pause:halted:consecutive_losses" in rendered
    assert "status=halted" in rendered
    assert "halt_reason=consecutive_losses" in rendered
    assert "open_positions=1" in rendered
    assert "pending_orders=1" in rendered
    assert "last_order_rejection_reason=order exceeds exposure-group notional cap" in rendered
    assert "last_order_rejection_market_id=m2" in rendered
    assert "last_order_rejection_exposure_group_id=crypto:btc-reach-ladder" in rendered
    assert "portfolio_total_gross_notional=10.00" in rendered
    assert "portfolio_exposure_groups=1" in rendered
    assert "portfolio_thesis_groups=1" in rendered
    assert "portfolio_underlying_groups=1" in rendered
    assert "exposure_group=crypto:btc-reach-ladder:crypto:markets=1:open=5.00:pending=5.00:gross=10.00" in rendered
    assert "thesis_group=crypto:btc:reach:crypto:markets=1:open=5.00:pending=5.00:gross=10.00" in rendered
    assert "underlying_group=crypto:btc:crypto:markets=1:open=5.00:pending=5.00:gross=10.00" in rendered
    assert "position=m1:crypto:notional=5.00:shares=10.000000:avg=0.500000:mark=0.620000:unrealized=1.20" in rendered
    assert "pending_order=o1:m1:crypto:buy_yes:status=partially_filled:limit=0.500000:req_shares=10.000000:matched_shares=4.000000:tif=GTC:notional=5.00" in rendered


def test_render_dashboard_marks_review_for_recent_risk_rejection() -> None:
    rendered = render_dashboard(
        DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(),
            pending_orders=(),
            status=RuntimeStatus.RUNNING,
            halt_reason=HaltReason.NONE,
            halt_message=None,
            last_alert=None,
            daily_order_count=1,
            daily_order_soft_limit_reached=False,
            last_order_rejection_reason="order exceeds exposure-group notional cap",
            last_order_rejection_market_id="m2",
            last_order_rejection_exposure_group_id="crypto:btc-reach-ladder",
            last_order_rejection_thesis_group_id="crypto:btc:reach",
            last_order_rejection_underlying_group_id="crypto:btc",
        )
    )

    assert "risk_action=review" in rendered
    assert "risk_decision=review:last_reject=exposure_group_cap" in rendered


def test_render_dashboard_includes_cap_utilization_when_trading_settings_are_provided() -> None:
    rendered = render_dashboard(
        DashboardState(
            total_equity=100.0,
            today_pnl=0.0,
            open_positions=(
                PositionState(
                    market_id="m1",
                    token_id="t1",
                    category=Category.CRYPTO,
                    strategy_id="crypto.surface",
                    notional=9.0,
                    opened_at=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
                    exposure_group_id="crypto:btc-reach-ladder",
                    thesis_group_id="crypto:btc:reach",
                    underlying_group_id="crypto:btc",
                ),
            ),
            pending_orders=(),
            status=RuntimeStatus.RUNNING,
            halt_reason=HaltReason.NONE,
            halt_message=None,
            last_alert=None,
            daily_order_count=0,
            daily_order_soft_limit_reached=False,
        ),
        trading_settings=TradingSettings(
            max_notional_per_category=10.0,
            max_notional_per_exposure_group=10.0,
            max_notional_per_thesis_group=10.0,
            max_notional_per_underlying_group=10.0,
            max_total_gross_notional=10.0,
        ),
    )

    assert "risk_action=review" in rendered
    assert "risk_decision=review:total_gross_near_cap" in rendered
    assert "portfolio_total_gross_utilization=used=9.00:cap=10.00:remaining=1.00:ratio=0.9000" in rendered
    assert "category_utilization=crypto:markets=1:used=9.00:cap=10.00:remaining=1.00:ratio=0.9000" in rendered
    assert "exposure_group_utilization=crypto:btc-reach-ladder:crypto:markets=1:used=9.00:cap=10.00:remaining=1.00:ratio=0.9000" in rendered
    assert "thesis_group_utilization=crypto:btc:reach:crypto:markets=1:used=9.00:cap=10.00:remaining=1.00:ratio=0.9000" in rendered
    assert "underlying_group_utilization=crypto:btc:crypto:markets=1:used=9.00:cap=10.00:remaining=1.00:ratio=0.9000" in rendered


def test_render_dashboard_marks_proceed_when_runtime_is_clear() -> None:
    rendered = render_dashboard(
        DashboardState(
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
        )
    )

    assert "risk_action=proceed" in rendered
    assert "risk_decision=proceed:clear" in rendered


def test_render_dashboard_with_promotion_summary_appends_summary(tmp_path: Path) -> None:
    summary_path = tmp_path / "promotion-summary.md"
    summary_path.write_text("# Promotion Operator Summary\n\n- ready: false\n", encoding="utf-8")

    rendered = render_dashboard_with_promotion_summary(
        DashboardState(
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
        promotion_summary_path=summary_path,
    )

    assert "runtime_dashboard" in rendered
    assert "promotion_summary" in rendered
    assert "# Promotion Operator Summary" in rendered


def test_render_dashboard_with_promotion_summary_prefers_structured_fields(tmp_path: Path) -> None:
    metrics_path = tmp_path / "metrics.json"
    state_path = tmp_path / "state.json"
    event_path = tmp_path / "events.jsonl"
    metrics_path.write_text('{"orders_submitted":2,"orders_filled":1}', encoding="utf-8")
    state_path.write_text(
        '{"starting_equity":100.0,"day_starting_equity":100.0,"open_positions":{},"pending_orders":{},"status":"running","halt_reason":"none","halt_message":null,"last_alert":null,"last_data_success_at":null,"last_data_error":null,"consecutive_data_failures":0,"orders_today":0,"consecutive_losses":0,"realized_pnl_today":0.0,"unrealized_pnl":0.0,"day_open_unrealized_pnl":0.0,"day_started_at":"2026-03-23T10:00:00+00:00","updated_at":"2026-03-23T10:00:00+00:00"}',
        encoding="utf-8",
    )
    event_path.write_text('{"event_type":"order.submitted"}\n', encoding="utf-8")
    review = build_promotion_artifact_review(
        stage="paper_to_sync_shadow",
        metrics_path=metrics_path,
        state_path=state_path,
        event_path=event_path,
    )
    readiness = PromotionReadinessReport(
        stage="paper_to_sync_shadow",
        ready=False,
        source_config_dir="configs/profiles/paper-baseline-v1",
        target_config_dir="configs/profiles/sync-promotion-shadow-v1",
        blockers=("missing operator note",),
        warnings=(),
        checks={},
        rollback_triggers=("runtime halted",),
        escalation_actions=("inspect artifacts",),
    )
    summary_path = write_promotion_operator_summary(
        path=tmp_path / "promotion-summary.md",
        readiness=readiness,
        review=review,
    )

    rendered = render_dashboard_with_promotion_summary(
        DashboardState(
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
        promotion_summary_path=summary_path,
    )

    assert "promotion_status" in rendered
    assert "promotion_action=pause" in rendered
    assert "promotion_decision=pause:ready=false:blockers=1:warnings=0" in rendered
    assert "promotion_ready=false" in rendered
    assert "promotion_immediate_action=pause: missing operator note" in rendered


def test_render_dashboard_with_combined_operator_summary_prefers_combined_fields(tmp_path: Path) -> None:
    from pm_bot.promotion_artifacts import write_combined_operator_summary

    summary_path = write_combined_operator_summary(
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

    rendered = render_dashboard_with_promotion_summary(
        DashboardState(
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
        combined_summary_path=summary_path,
    )

    assert "operator_summary" in rendered
    assert "overall_action=pause" in rendered
    assert "rollback_target=previous_stage" in rendered
    assert "alert_count=1" in rendered


def test_render_dashboard_with_ops_summary_prefers_structured_console(tmp_path: Path) -> None:
    ops_console = tmp_path / "ops-console.md"
    ops_console.write_text("# Unified Ops Console\n", encoding="utf-8")
    ops_console.with_suffix(".json").write_text(
        '{"overall_action":"review","overall_decision":"review:crypto=review,sports=proceed,weather=proceed","next_step":"review_cross_board_artifacts","rollback_target":"crypto","checklist_completion_ratio":0.5,"blocker_count":0,"warning_count":1,"boards":[{"board":"crypto","action":"review","decision":"review:crypto","reviewed_items":1,"actionable_items":0,"evidence_ready":false,"warnings":["evidence blocked"]}],"checklist":["[todo] crypto board status -> review:crypto"],"escalation_actions":["review crypto board scorecard and refresh supporting evidence"],"generated_reports":["crypto.md","sports.md","weather.md"]}',
        encoding="utf-8",
    )

    rendered = render_dashboard_with_ops_summary(
        DashboardState(
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
        ops_console_path=ops_console,
    )

    assert "ops_console" in rendered
    assert "ops_console_action=review" in rendered
    assert "ops_console_rollback_target=crypto" in rendered
    assert "ops_console_escalation_action=review crypto board scorecard and refresh supporting evidence" in rendered


def test_render_dashboard_with_ops_summary_prefers_ops_one_page(tmp_path: Path) -> None:
    ops_one_page = tmp_path / "ops-one-page.md"
    ops_decision = tmp_path / "ops-decision.md"
    ops_decision.write_text("# Ops Decision\n", encoding="utf-8")
    ops_decision.with_suffix(".json").write_text(
        '{"triage_action":"escalate","triage_reason":"escalating_issues=1","overall_action":"review","overall_decision":"review:crypto=review","next_step":"review_cross_board_artifacts","rollback_target":"crypto","recommended_attention":"escalate_review_streak","strategy_mode":"learn","strategy_primary_board":"weather","strategy_next_step":"focus weaker board","strategy_cycle_status":"learn","strategy_cycle_next_step":"refresh experiments"}',
        encoding="utf-8",
    )
    ops_one_page.write_text("# Ops One Page\n", encoding="utf-8")
    ops_one_page.with_suffix(".json").write_text(
        '{"runtime_rendered":"runtime_dashboard\\nrisk_action=review","triage_action":"escalate","triage_reason":"escalating_issues=1","console":{"overall_action":"review","overall_decision":"review:crypto=review","next_step":"review_cross_board_artifacts","rollback_target":"crypto","checklist_completion_ratio":0.5,"blocker_count":0,"warning_count":1,"boards":[],"checklist":[],"escalation_actions":["review crypto"],"generated_reports":[]},"control_panel":{"runtime_action":"review","runtime_decision":"review:clear","overall_action":"review","overall_decision":"review:crypto=review","next_step":"review_cross_board_artifacts","rollback_target":"crypto","blocker_count":0,"warning_count":1,"checklist_completion_ratio":0.5,"boards":[],"escalation_actions":["review crypto"],"checklist":[],"latest_ops_action":"review","recent_ops_actions":["review","review"],"review_streak":2,"pause_streak":0,"recommended_attention":"escalate_review_streak","recurring_issues":["crypto: evidence blocked=2"],"strategy_mode":"learn","strategy_primary_board":"weather","strategy_next_step":"focus weaker board","strategy_cycle_status":"learn","strategy_cycle_reason":"current evidence still points to tuning","strategy_cycle_next_step":"refresh experiments"},"strategy_loop_decision":{"recommended_mode":"learn","latest_action":"learn","primary_board":"weather","next_step":"focus weaker board"},"strategy_cycle_package":{"cycle_status":"learn","cycle_reason":"current evidence still points to tuning","next_step":"refresh experiments","strategy_mode":"learn","primary_board":"weather"},"history":{"total_runs":2,"latest_action":"review","recent_actions":["review","review"],"review_streak":2,"pause_streak":0,"proceed_streak":0,"recommended_attention":"escalate_review_streak","board_review_counts":["crypto=2"],"recurring_issues":["crypto: evidence blocked=2"],"recent_runs":[]},"followup_queue":{"generated_from":"scheduled_ops","overall_action":"review","recommended_attention":"escalate_review_streak","item_count":2,"lifecycle":{"open_items":[],"escalating_items":["crypto: evidence blocked"],"resolved_items":[]},"items":[]}}',
        encoding="utf-8",
    )

    rendered = render_dashboard_with_ops_summary(
        DashboardState(
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
        ops_one_page_path=ops_one_page,
    )

    assert "ops_one_page" in rendered
    assert "ops_decision" in rendered
    assert "ops_decision_triage_action=escalate" in rendered
    assert "ops_decision_next_step=review_cross_board_artifacts" in rendered
    assert "ops_decision_strategy_mode=learn" in rendered
    assert "ops_decision_strategy_primary_board=weather" in rendered
    assert "ops_decision_strategy_next_step=focus weaker board" in rendered
    assert "ops_decision_strategy_cycle_status=learn" in rendered
    assert "ops_decision_strategy_cycle_next_step=refresh experiments" in rendered
    assert "ops_one_page_overall_action=review" in rendered
    assert "ops_one_page_rollback_target=crypto" in rendered
    assert "ops_one_page_triage_action=escalate" in rendered
    assert "ops_one_page_triage_reason=escalating_issues=1" in rendered
    assert "ops_one_page_strategy_mode=learn" in rendered
    assert "ops_one_page_strategy_primary_board=weather" in rendered
    assert "ops_one_page_strategy_next_step=focus weaker board" in rendered
    assert "ops_one_page_strategy_cycle_status=learn" in rendered
    assert "ops_one_page_strategy_cycle_reason=current evidence still points to tuning" in rendered
    assert "ops_one_page_strategy_cycle_next_step=refresh experiments" in rendered
    assert "ops_one_page_review_streak=2" in rendered
    assert "ops_one_page_escalating_issue_count=1" in rendered
    assert "ops_one_page_resolved_issue_count=0" in rendered
    assert "ops_one_page_escalation_action=review crypto" in rendered
