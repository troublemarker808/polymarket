"""Operator-facing dashboard rendering helpers."""

from __future__ import annotations

from pm_bot.runtime.state import DashboardState, dashboard_state_to_lines


def render_dashboard(dashboard: DashboardState) -> str:
    lines = [
        "runtime_dashboard",
        *dashboard_state_to_lines(dashboard),
    ]
    return "\n".join(lines)
