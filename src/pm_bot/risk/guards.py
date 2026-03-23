"""Risk guard helpers.

Risk logic stays isolated so limits can evolve without editing strategy code.
"""

from __future__ import annotations

from pm_bot.core.types import RiskDecision, SignalSide, StrategySignal


def basic_signal_guard(signal: StrategySignal, max_edge_floor_bps: float) -> RiskDecision:
    """Reject signals that do not clear a minimum edge threshold."""

    if signal.side in {SignalSide.SELL_YES, SignalSide.SELL_NO}:
        return RiskDecision(approved=True, reason="approved")
    if signal.edge_bps < max_edge_floor_bps:
        return RiskDecision(approved=False, reason="edge below configured floor")

    return RiskDecision(approved=True, reason="approved")
