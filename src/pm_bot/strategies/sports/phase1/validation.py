"""Validation helpers for Sports Phase 1 closing-line review."""

from __future__ import annotations

from pm_bot.strategies.sports.phase1.models import SportsClosingLineReview


def review_closing_line(
    *,
    market_id: str,
    open_probability: float,
    fair_probability: float,
    close_probability: float,
) -> SportsClosingLineReview:
    open_gap = abs(fair_probability - open_probability)
    close_gap = abs(fair_probability - close_probability)
    clv_bps = (close_gap - open_gap) * -10000
    return SportsClosingLineReview(
        market_id=market_id,
        open_probability=open_probability,
        fair_probability=fair_probability,
        close_probability=close_probability,
        clv_bps=clv_bps,
        moved_toward_fair=close_gap <= open_gap,
    )
