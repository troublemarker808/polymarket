"""Phase 1 sports research helpers."""

from pm_bot.strategies.sports.phase1.anchors import apply_anchor_adjustments, estimate_odds_anchor
from pm_bot.strategies.sports.phase1.attribution import build_sports_attribution_rows
from pm_bot.strategies.sports.phase1.features import build_pregame_features, estimate_pregame_adjustments
from pm_bot.strategies.sports.phase1.final_report import (
    build_sports_final_scorecard,
    format_sports_final_scorecard,
    generate_sports_final_scorecard,
)
from pm_bot.strategies.sports.phase1.learning_report import (
    build_sports_learning_report,
    format_sports_learning_report,
)
from pm_bot.strategies.sports.phase1.tuning_plan import (
    build_sports_candidate_preset_registry,
    build_sports_tuning_plan,
    format_sports_tuning_plan,
)
from pm_bot.strategies.sports.phase1.models import SportsEventDefinition, SportsEventGroup
from pm_bot.strategies.sports.phase1.normalization import (
    build_sports_event_schedule,
    classify_sports_market,
    normalize_sports_market,
)
from pm_bot.strategies.sports.phase1.pricing import (
    estimate_line_dislocation,
    estimate_pregame_fair_value,
    to_fair_value_estimate,
)
from pm_bot.strategies.sports.phase1.reports import (
    format_sports_closing_line_report,
    format_sports_event_scorecard_report,
    format_sports_market_selection_report,
    generate_sports_closing_line_report,
    generate_sports_event_scorecard_report,
    generate_sports_market_selection_report,
)
from pm_bot.strategies.sports.phase1.replay import compute_sports_phase1_fair_values, run_sports_phase1_replay
from pm_bot.strategies.sports.phase1.validation import review_closing_line

__all__ = [
    "SportsEventDefinition",
    "SportsEventGroup",
    "apply_anchor_adjustments",
    "build_sports_attribution_rows",
    "build_sports_event_schedule",
    "build_pregame_features",
    "build_sports_final_scorecard",
    "build_sports_candidate_preset_registry",
    "build_sports_learning_report",
    "build_sports_tuning_plan",
    "classify_sports_market",
    "compute_sports_phase1_fair_values",
    "estimate_line_dislocation",
    "estimate_odds_anchor",
    "estimate_pregame_fair_value",
    "estimate_pregame_adjustments",
    "format_sports_final_scorecard",
    "format_sports_learning_report",
    "format_sports_tuning_plan",
    "format_sports_closing_line_report",
    "format_sports_event_scorecard_report",
    "format_sports_market_selection_report",
    "generate_sports_closing_line_report",
    "generate_sports_event_scorecard_report",
    "generate_sports_final_scorecard",
    "generate_sports_market_selection_report",
    "normalize_sports_market",
    "review_closing_line",
    "run_sports_phase1_replay",
    "to_fair_value_estimate",
]
