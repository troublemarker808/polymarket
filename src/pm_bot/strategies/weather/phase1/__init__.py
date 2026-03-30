"""Phase 1 weather research helpers."""

from pm_bot.strategies.weather.phase1.forecasts import build_forecast_run_calendar, ingest_forecast_runs
from pm_bot.strategies.weather.phase1.fusion import fuse_weather_fair_value, to_fair_value_estimate
from pm_bot.strategies.weather.phase1.models import WeatherLocationDefinition, WeatherMarketDefinition
from pm_bot.strategies.weather.phase1.normalization import (
    classify_weather_market,
    normalize_weather_market,
    normalize_weather_settlement,
)
from pm_bot.strategies.weather.phase1.pricing import (
    build_forecast_distribution,
    build_weather_peer_probability_map,
    estimate_strip_consistency,
    estimate_threshold_probability,
)
from pm_bot.strategies.weather.phase1.reports import (
    format_weather_market_selection_report,
    format_weather_run_scorecard_report,
    format_weather_settlement_audit_report,
    generate_weather_market_selection_report,
    generate_weather_run_scorecard_report,
    generate_weather_settlement_audit_report,
)
from pm_bot.strategies.weather.phase1.final_report import (
    format_weather_final_scorecard,
    generate_weather_final_scorecard,
)
from pm_bot.strategies.weather.phase1.learning_report import (
    build_weather_learning_report,
    format_weather_learning_report,
)
from pm_bot.strategies.weather.phase1.tuning_plan import (
    build_weather_candidate_preset_registry,
    build_weather_tuning_plan,
    format_weather_tuning_plan,
)
from pm_bot.strategies.weather.phase1.attribution import build_weather_attribution_rows
from pm_bot.strategies.weather.phase1.replay import (
    compute_weather_phase1_fair_values,
    run_weather_phase1_replay,
)
from pm_bot.strategies.weather.phase1.skill import apply_bias_correction, apply_bias_corrections, load_model_skill_store

__all__ = [
    "WeatherLocationDefinition",
    "WeatherMarketDefinition",
    "apply_bias_correction",
    "apply_bias_corrections",
    "build_forecast_run_calendar",
    "build_forecast_distribution",
    "build_weather_peer_probability_map",
    "build_weather_attribution_rows",
    "build_weather_candidate_preset_registry",
    "build_weather_learning_report",
    "build_weather_tuning_plan",
    "classify_weather_market",
    "compute_weather_phase1_fair_values",
    "estimate_strip_consistency",
    "estimate_threshold_probability",
    "format_weather_market_selection_report",
    "format_weather_final_scorecard",
    "format_weather_learning_report",
    "format_weather_tuning_plan",
    "format_weather_run_scorecard_report",
    "format_weather_settlement_audit_report",
    "fuse_weather_fair_value",
    "generate_weather_market_selection_report",
    "generate_weather_final_scorecard",
    "generate_weather_run_scorecard_report",
    "generate_weather_settlement_audit_report",
    "ingest_forecast_runs",
    "load_model_skill_store",
    "normalize_weather_market",
    "normalize_weather_settlement",
    "run_weather_phase1_replay",
    "to_fair_value_estimate",
]
