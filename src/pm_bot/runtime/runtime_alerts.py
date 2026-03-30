"""Operator-facing runtime alerts and rollback suggestions."""

from __future__ import annotations

from dataclasses import dataclass

from pm_bot.core.settings import TradingSettings
from pm_bot.execution.portfolio import build_portfolio_cap_utilization, portfolio_state_from_dashboard
from pm_bot.runtime.state import DashboardState, RuntimeStatus


@dataclass(slots=True, frozen=True)
class RuntimeAlert:
    code: str
    severity: str
    action: str
    rollback_target: str | None
    message: str


def build_runtime_alerts(
    *,
    dashboard: DashboardState,
    trading_settings: TradingSettings | None = None,
    promotion_ready: bool | None = None,
    promotion_action: str | None = None,
) -> tuple[RuntimeAlert, ...]:
    alerts: list[RuntimeAlert] = []
    if dashboard.status == RuntimeStatus.HALTED:
        alerts.append(
            RuntimeAlert(
                code=f"runtime_halted:{dashboard.halt_reason.value}",
                severity="critical",
                action="pause",
                rollback_target="previous_stage",
                message=dashboard.halt_message or f"runtime halted: {dashboard.halt_reason.value}",
            )
        )
    if dashboard.consecutive_data_failures > 0:
        alerts.append(
            RuntimeAlert(
                code="data_failures_active",
                severity="high",
                action="review",
                rollback_target="paper" if promotion_action == "pause" else None,
                message=f"unresolved data failures={dashboard.consecutive_data_failures}",
            )
        )
    rejection_reason = (dashboard.last_order_rejection_reason or "").strip()
    if rejection_reason:
        alerts.append(
            RuntimeAlert(
                code="recent_risk_reject",
                severity="medium",
                action="review",
                rollback_target=None,
                message=rejection_reason,
            )
        )
    if dashboard.daily_order_soft_limit_reached:
        alerts.append(
            RuntimeAlert(
                code="daily_soft_limit_reached",
                severity="medium",
                action="review",
                rollback_target=None,
                message="daily soft order limit reached",
            )
        )
    if trading_settings is not None:
        utilization = build_portfolio_cap_utilization(
            portfolio=portfolio_state_from_dashboard(dashboard),
            trading_settings=trading_settings,
        )
        if utilization.total_gross.utilization_ratio >= 0.9:
            alerts.append(
                RuntimeAlert(
                    code="total_gross_near_cap",
                    severity="high" if utilization.total_gross.utilization_ratio >= 1.0 else "medium",
                    action="review" if utilization.total_gross.utilization_ratio < 1.0 else "pause",
                    rollback_target=None,
                    message=(
                        "total gross cap used="
                        f"{utilization.total_gross.used_notional:.2f}/{utilization.total_gross.cap_notional:.2f}"
                    ),
                )
            )
        hot_thesis = next((item for item in utilization.by_thesis_group if item.utilization_ratio >= 0.9), None)
        if hot_thesis is not None:
            alerts.append(
                RuntimeAlert(
                    code=f"thesis_group_near_cap:{hot_thesis.exposure_group_id}",
                    severity="medium",
                    action="review",
                    rollback_target=None,
                    message=(
                        f"thesis group near cap {hot_thesis.exposure_group_id} "
                        f"{hot_thesis.used_notional:.2f}/{hot_thesis.cap_notional:.2f}"
                    ),
                )
            )
        hot_underlying = next((item for item in utilization.by_underlying_group if item.utilization_ratio >= 0.9), None)
        if hot_underlying is not None:
            alerts.append(
                RuntimeAlert(
                    code=f"underlying_group_near_cap:{hot_underlying.exposure_group_id}",
                    severity="medium",
                    action="review",
                    rollback_target=None,
                    message=(
                        f"underlying group near cap {hot_underlying.exposure_group_id} "
                        f"{hot_underlying.used_notional:.2f}/{hot_underlying.cap_notional:.2f}"
                    ),
                )
            )
    if promotion_ready is False:
        alerts.append(
            RuntimeAlert(
                code="promotion_blocked",
                severity="high" if promotion_action == "pause" else "medium",
                action=promotion_action or "review",
                rollback_target="current_stage",
                message="promotion readiness is blocked",
            )
        )
    return tuple(alerts)
