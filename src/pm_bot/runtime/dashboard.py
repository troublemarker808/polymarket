"""Operator-facing dashboard rendering helpers."""

from __future__ import annotations

from pathlib import Path

from pm_bot.core.settings import TradingSettings
from pm_bot.multi_board_ops import load_multi_board_ops_report
from pm_bot.ops_console import load_unified_ops_console
from pm_bot.ops_decision import load_ops_decision
from pm_bot.ops_one_page import load_ops_one_page
from pm_bot.execution.portfolio import (
    PortfolioCapUtilization,
    build_portfolio_cap_utilization,
    portfolio_state_from_dashboard,
)
from pm_bot.promotion_artifacts import (
    CombinedOperatorSummary,
    load_combined_operator_summary,
    load_promotion_operator_summary,
)
from pm_bot.runtime.state import DashboardState, RuntimeStatus, dashboard_state_to_lines


def render_dashboard(
    dashboard: DashboardState,
    *,
    trading_settings: TradingSettings | None = None,
) -> str:
    portfolio = portfolio_state_from_dashboard(dashboard)
    utilization = (
        build_portfolio_cap_utilization(portfolio=portfolio, trading_settings=trading_settings)
        if trading_settings is not None
        else None
    )
    risk_action, risk_reason = _risk_decision_summary(
        dashboard=dashboard,
        utilization=utilization,
    )
    lines = [
        "runtime_dashboard",
        f"risk_action={risk_action}",
        f"risk_decision={risk_action}:{risk_reason}",
        *dashboard_state_to_lines(dashboard),
        f"portfolio_total_open_notional={portfolio.total_open_notional:.2f}",
        f"portfolio_total_pending_notional={portfolio.total_pending_notional:.2f}",
        f"portfolio_total_gross_notional={portfolio.total_gross_notional:.2f}",
        f"portfolio_exposure_groups={len(portfolio.by_exposure_group)}",
        f"portfolio_thesis_groups={len(portfolio.by_thesis_group)}",
        f"portfolio_underlying_groups={len(portfolio.by_underlying_group)}",
    ]
    for exposure_group in portfolio.by_exposure_group[:5]:
        lines.append(
            "exposure_group="
            + f"{exposure_group.exposure_group_id}:{exposure_group.category.value}:"
            + f"markets={exposure_group.market_count}:"
            + f"open={exposure_group.open_notional:.2f}:"
            + f"pending={exposure_group.pending_notional:.2f}:"
            + f"gross={exposure_group.gross_notional:.2f}"
        )
    for thesis_group in portfolio.by_thesis_group[:3]:
        lines.append(
            "thesis_group="
            + f"{thesis_group.thesis_group_id}:{thesis_group.category.value}:"
            + f"markets={thesis_group.market_count}:"
            + f"open={thesis_group.open_notional:.2f}:"
            + f"pending={thesis_group.pending_notional:.2f}:"
            + f"gross={thesis_group.gross_notional:.2f}"
        )
    for underlying_group in portfolio.by_underlying_group[:3]:
        lines.append(
            "underlying_group="
            + f"{underlying_group.underlying_group_id}:{underlying_group.category.value}:"
            + f"markets={underlying_group.market_count}:"
            + f"open={underlying_group.open_notional:.2f}:"
            + f"pending={underlying_group.pending_notional:.2f}:"
            + f"gross={underlying_group.gross_notional:.2f}"
        )
    if utilization is not None:
        lines.extend(_portfolio_cap_lines(utilization))
    return "\n".join(lines)


def render_dashboard_with_promotion_summary(
    dashboard: DashboardState,
    *,
    trading_settings: TradingSettings | None = None,
    promotion_summary_path: str | Path | None = None,
    combined_summary_path: str | Path | None = None,
) -> str:
    rendered = render_dashboard(dashboard, trading_settings=trading_settings)
    if combined_summary_path is not None:
        combined = load_combined_operator_summary(combined_summary_path)
        if combined is not None:
            return "\n".join([rendered, "", *_combined_summary_lines(combined)])
    if promotion_summary_path is None:
        return rendered
    summary_path = Path(promotion_summary_path)
    if not summary_path.exists():
        return rendered
    structured = load_promotion_operator_summary(summary_path)
    if structured is not None:
        lines = [
            rendered,
            "",
            "promotion_status",
            f"promotion_action={structured.action}",
            (
                "promotion_decision="
                + f"{structured.action}:ready={str(structured.ready).lower()}:"
                + f"blockers={structured.blocker_count}:warnings={structured.warning_count}"
            ),
            f"promotion_stage={structured.stage}",
            f"promotion_ready={str(structured.ready).lower()}",
            f"promotion_blockers={structured.blocker_count}",
            f"promotion_warnings={structured.warning_count}",
            f"promotion_note_present={str(structured.note_present).lower()}",
            f"promotion_source_status={structured.source_status}",
            f"promotion_source_halt_reason={structured.source_halt_reason}",
            f"promotion_immediate_action={structured.immediate_action}",
        ]
        if structured.shadow_status is not None:
            lines.extend(
                [
                    f"promotion_shadow_status={structured.shadow_status}",
                    f"promotion_shadow_halt_reason={structured.shadow_halt_reason or ''}",
                ]
            )
        return "\n".join(lines)
    summary = summary_path.read_text(encoding="utf-8").strip()
    if not summary:
        return rendered
    return f"{rendered}\n\npromotion_summary\n{summary}"


def render_dashboard_with_ops_summary(
    dashboard: DashboardState,
    *,
    trading_settings: TradingSettings | None = None,
    promotion_summary_path: str | Path | None = None,
    combined_summary_path: str | Path | None = None,
    ops_summary_path: str | Path | None = None,
    ops_console_path: str | Path | None = None,
    ops_one_page_path: str | Path | None = None,
) -> str:
    rendered = render_dashboard_with_promotion_summary(
        dashboard,
        trading_settings=trading_settings,
        promotion_summary_path=promotion_summary_path,
        combined_summary_path=combined_summary_path,
    )
    if ops_one_page_path is not None:
        one_page = load_ops_one_page(ops_one_page_path)
        if one_page is not None:
            decision_lines: list[str] = []
            decision_path = Path(ops_one_page_path).with_name("ops-decision.md")
            decision = load_ops_decision(decision_path)
            if decision is not None:
                decision_lines = _ops_decision_lines(decision)
            return "\n".join([rendered, "", *decision_lines, *_ops_one_page_lines(one_page)])
    if ops_console_path is not None:
        console = load_unified_ops_console(ops_console_path)
        if console is not None:
            return "\n".join([rendered, "", *_ops_console_lines(console)])
    if ops_summary_path is not None:
        ops_report = load_multi_board_ops_report(ops_summary_path)
        if ops_report is not None:
            return "\n".join([rendered, "", *_multi_board_ops_lines(ops_report)])
        summary_path = Path(ops_summary_path)
        if summary_path.exists():
            content = summary_path.read_text(encoding="utf-8").strip()
            if content:
                return f"{rendered}\n\nmulti_board_ops\n{content}"
    return rendered


def _risk_decision_summary(
    *,
    dashboard: DashboardState,
    utilization: PortfolioCapUtilization | None,
) -> tuple[str, str]:
    if dashboard.status == RuntimeStatus.HALTED:
        halt_reason = dashboard.halt_reason.value if dashboard.halt_reason.value else "halted"
        return "pause", f"halted:{halt_reason}"
    if dashboard.consecutive_data_failures > 0:
        return "review", f"data_failures={dashboard.consecutive_data_failures}"
    if utilization is not None:
        total_ratio = utilization.total_gross.utilization_ratio
        if total_ratio >= 1.0:
            return "pause", "total_gross_cap_breached"
        if total_ratio >= 0.9:
            return "review", "total_gross_near_cap"
        hot_group = next(
            (item for item in utilization.by_exposure_group if item.utilization_ratio >= 0.9),
            None,
        )
        if hot_group is not None:
            return "review", f"exposure_group_near_cap={hot_group.exposure_group_id}"
        hot_thesis = next(
            (item for item in utilization.by_thesis_group if item.utilization_ratio >= 0.9),
            None,
        )
        if hot_thesis is not None:
            return "review", f"thesis_group_near_cap={hot_thesis.exposure_group_id}"
        hot_underlying = next(
            (item for item in utilization.by_underlying_group if item.utilization_ratio >= 0.9),
            None,
        )
        if hot_underlying is not None:
            return "review", f"underlying_group_near_cap={hot_underlying.exposure_group_id}"
        hot_category = next(
            (item for item in utilization.by_category if item.utilization_ratio >= 0.9),
            None,
        )
        if hot_category is not None:
            return "review", f"category_near_cap={hot_category.category.value}"
    rejection_reason = (dashboard.last_order_rejection_reason or "").strip()
    if rejection_reason:
        if "exposure-group" in rejection_reason:
            return "review", "last_reject=exposure_group_cap"
        if "total gross" in rejection_reason:
            return "review", "last_reject=total_gross_cap"
        if "per-category" in rejection_reason:
            return "review", "last_reject=category_cap"
        if "per-market" in rejection_reason:
            return "review", "last_reject=market_cap"
        return "review", "last_reject=other"
    if dashboard.daily_order_soft_limit_reached:
        return "review", "daily_soft_limit_reached"
    return "proceed", "clear"


def _portfolio_cap_lines(utilization: PortfolioCapUtilization) -> list[str]:
    lines = [
        (
            "portfolio_total_gross_utilization="
            + f"used={utilization.total_gross.used_notional:.2f}:"
            + f"cap={utilization.total_gross.cap_notional:.2f}:"
            + f"remaining={utilization.total_gross.remaining_notional:.2f}:"
            + f"ratio={utilization.total_gross.utilization_ratio:.4f}"
        )
    ]
    for category in utilization.by_category[:3]:
        lines.append(
            "category_utilization="
            + f"{category.category.value}:"
            + f"markets={category.market_count}:"
            + f"used={category.used_notional:.2f}:"
            + f"cap={category.cap_notional:.2f}:"
            + f"remaining={category.remaining_notional:.2f}:"
            + f"ratio={category.utilization_ratio:.4f}"
        )
    for exposure_group in utilization.by_exposure_group[:5]:
        lines.append(
            "exposure_group_utilization="
            + f"{exposure_group.exposure_group_id}:"
            + f"{exposure_group.category.value}:"
            + f"markets={exposure_group.market_count}:"
            + f"used={exposure_group.used_notional:.2f}:"
            + f"cap={exposure_group.cap_notional:.2f}:"
            + f"remaining={exposure_group.remaining_notional:.2f}:"
            + f"ratio={exposure_group.utilization_ratio:.4f}"
        )
    for thesis_group in utilization.by_thesis_group[:3]:
        lines.append(
            "thesis_group_utilization="
            + f"{thesis_group.exposure_group_id}:"
            + f"{thesis_group.category.value}:"
            + f"markets={thesis_group.market_count}:"
            + f"used={thesis_group.used_notional:.2f}:"
            + f"cap={thesis_group.cap_notional:.2f}:"
            + f"remaining={thesis_group.remaining_notional:.2f}:"
            + f"ratio={thesis_group.utilization_ratio:.4f}"
        )
    for underlying_group in utilization.by_underlying_group[:3]:
        lines.append(
            "underlying_group_utilization="
            + f"{underlying_group.exposure_group_id}:"
            + f"{underlying_group.category.value}:"
            + f"markets={underlying_group.market_count}:"
            + f"used={underlying_group.used_notional:.2f}:"
            + f"cap={underlying_group.cap_notional:.2f}:"
            + f"remaining={underlying_group.remaining_notional:.2f}:"
            + f"ratio={underlying_group.utilization_ratio:.4f}"
        )
    return lines


def _combined_summary_lines(summary: CombinedOperatorSummary) -> list[str]:
    lines = [
        "operator_summary",
        f"overall_action={summary.overall_action}",
        f"overall_decision={summary.overall_decision}",
        f"next_step={summary.next_step}",
        f"rollback_target={summary.rollback_target or ''}",
        f"alert_count={summary.alert_count}",
        f"runtime_action={summary.runtime_action}",
        f"runtime_decision={summary.runtime_decision}",
    ]
    if summary.promotion_action is not None:
        lines.extend(
            [
                f"promotion_action={summary.promotion_action}",
                f"promotion_decision={summary.promotion_decision or ''}",
            ]
        )
    lines.extend(
        [
            f"alert_codes={','.join(summary.alert_codes)}",
            f"last_rejection_reason={summary.last_rejection_reason or ''}",
        ]
    )
    return lines


def _multi_board_ops_lines(report: object) -> list[str]:
    from pm_bot.multi_board_ops import MultiBoardOpsReport

    typed = report if isinstance(report, MultiBoardOpsReport) else None
    if typed is None:
        return []
    lines = [
        "multi_board_ops",
        f"multi_board_action={typed.overall_action}",
        f"multi_board_decision={typed.overall_decision}",
        f"multi_board_next_step={typed.next_step}",
        f"multi_board_rollback_target={typed.rollback_target or ''}",
        f"multi_board_blockers={len(typed.blockers)}",
        f"multi_board_warnings={len(typed.warnings)}",
    ]
    lines.extend(f"multi_board_escalation_action={item}" for item in typed.escalation_actions)
    lines.extend(
        "multi_board_board="
        + f"{board.board}:action={board.action}:reviewed={board.reviewed_items}:actionable={board.actionable_items}"
        for board in typed.boards
    )
    return lines


def _ops_console_lines(console: object) -> list[str]:
    from pm_bot.ops_console import UnifiedOpsConsole

    typed = console if isinstance(console, UnifiedOpsConsole) else None
    if typed is None:
        return []
    lines = [
        "ops_console",
        f"ops_console_action={typed.overall_action}",
        f"ops_console_decision={typed.overall_decision}",
        f"ops_console_next_step={typed.next_step}",
        f"ops_console_rollback_target={typed.rollback_target or ''}",
        f"ops_console_blockers={typed.blocker_count}",
        f"ops_console_warnings={typed.warning_count}",
        f"ops_console_checklist_completion={typed.checklist_completion_ratio:.2f}",
    ]
    lines.extend(
        "ops_console_board="
        + f"{board.board}:action={board.action}:reviewed={board.reviewed_items}:actionable={board.actionable_items}"
        for board in typed.boards
    )
    lines.extend(f"ops_console_escalation_action={item}" for item in typed.escalation_actions)
    return lines


def _ops_one_page_lines(page: dict[str, object]) -> list[str]:
    control_panel = page.get("control_panel", {})
    history = page.get("history", {})
    if not isinstance(control_panel, dict):
        control_panel = {}
    if history is None or not isinstance(history, dict):
        history = {}
    lines = [
        "ops_one_page",
        f"ops_one_page_overall_action={control_panel.get('overall_action', '')}",
        f"ops_one_page_overall_decision={control_panel.get('overall_decision', '')}",
        f"ops_one_page_next_step={control_panel.get('next_step', '')}",
        f"ops_one_page_rollback_target={control_panel.get('rollback_target', '') or ''}",
        f"ops_one_page_triage_action={page.get('triage_action', '')}",
        f"ops_one_page_triage_reason={page.get('triage_reason', '')}",
        f"ops_one_page_recommended_attention={control_panel.get('recommended_attention', '')}",
        f"ops_one_page_strategy_mode={control_panel.get('strategy_mode', '')}",
        f"ops_one_page_strategy_primary_board={control_panel.get('strategy_primary_board', '')}",
        f"ops_one_page_strategy_next_step={control_panel.get('strategy_next_step', '')}",
        f"ops_one_page_strategy_cycle_status={control_panel.get('strategy_cycle_status', '')}",
        f"ops_one_page_strategy_cycle_reason={control_panel.get('strategy_cycle_reason', '')}",
        f"ops_one_page_strategy_cycle_next_step={control_panel.get('strategy_cycle_next_step', '')}",
        f"ops_one_page_latest_action={control_panel.get('latest_ops_action', '')}",
        f"ops_one_page_review_streak={control_panel.get('review_streak', 0)}",
        f"ops_one_page_pause_streak={control_panel.get('pause_streak', 0)}",
    ]
    followup_queue = page.get("followup_queue", {})
    if isinstance(followup_queue, dict):
        lifecycle = followup_queue.get("lifecycle", {})
        if isinstance(lifecycle, dict):
            open_items = lifecycle.get("open_items", [])
            escalating_items = lifecycle.get("escalating_items", [])
            resolved_items = lifecycle.get("resolved_items", [])
            if isinstance(open_items, list):
                lines.append(f"ops_one_page_open_issue_count={len(open_items)}")
            if isinstance(escalating_items, list):
                lines.append(f"ops_one_page_escalating_issue_count={len(escalating_items)}")
            if isinstance(resolved_items, list):
                lines.append(f"ops_one_page_resolved_issue_count={len(resolved_items)}")
    recent_actions = history.get("recent_actions", ())
    if isinstance(recent_actions, list):
        lines.append(f"ops_one_page_recent_actions={','.join(str(item) for item in recent_actions)}")
    escalation_actions = control_panel.get("escalation_actions", ())
    if isinstance(escalation_actions, list):
        lines.extend(f"ops_one_page_escalation_action={item}" for item in escalation_actions)
    return lines


def _ops_decision_lines(decision: object) -> list[str]:
    from pm_bot.ops_decision import OpsDecision

    typed = decision if isinstance(decision, OpsDecision) else None
    if typed is None:
        return []
    return [
        "ops_decision",
        f"ops_decision_triage_action={typed.triage_action}",
        f"ops_decision_triage_reason={typed.triage_reason}",
        f"ops_decision_overall_action={typed.overall_action}",
        f"ops_decision_next_step={typed.next_step}",
        f"ops_decision_rollback_target={typed.rollback_target or ''}",
        f"ops_decision_recommended_attention={typed.recommended_attention}",
        f"ops_decision_strategy_mode={typed.strategy_mode}",
        f"ops_decision_strategy_primary_board={typed.strategy_primary_board or ''}",
        f"ops_decision_strategy_next_step={typed.strategy_next_step}",
        f"ops_decision_strategy_cycle_status={typed.strategy_cycle_status}",
        f"ops_decision_strategy_cycle_next_step={typed.strategy_cycle_next_step}",
    ]
