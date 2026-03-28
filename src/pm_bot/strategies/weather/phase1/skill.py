"""Forecast skill and bias correction helpers for Weather Phase 1 research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pm_bot.strategies.common import parse_float
from pm_bot.strategies.weather.phase1.models import (
    BiasCorrectedForecast,
    WeatherForecastRun,
    WeatherMarketDefinition,
    WeatherModelSkill,
)


def load_model_skill_store(
    *,
    market: WeatherMarketDefinition,
    skill_payloads: Sequence[Mapping[str, Any]],
) -> tuple[WeatherModelSkill, ...]:
    skills: list[WeatherModelSkill] = []
    for payload in skill_payloads:
        skill = _normalize_skill_record(market=market, payload=payload)
        if skill is not None:
            skills.append(skill)
    skills.sort(key=lambda item: (item.model_name, item.horizon_bucket_hours))
    return tuple(skills)


def apply_bias_corrections(
    *,
    market: WeatherMarketDefinition,
    forecast_runs: Sequence[WeatherForecastRun],
    skill_store: Sequence[WeatherModelSkill],
) -> tuple[BiasCorrectedForecast, ...]:
    return tuple(
        apply_bias_correction(market=market, forecast_run=forecast_run, skill_store=skill_store)
        for forecast_run in forecast_runs
    )


def apply_bias_correction(
    *,
    market: WeatherMarketDefinition,
    forecast_run: WeatherForecastRun,
    skill_store: Sequence[WeatherModelSkill],
) -> BiasCorrectedForecast:
    skill = _select_skill(
        forecast_run=forecast_run,
        skill_store=skill_store,
        station_id=market.location.station_id,
    )
    mean_bias_f = skill.mean_bias_f if skill is not None else 0.0
    mae_f = skill.mae_f if skill is not None else forecast_run.distribution_sigma_f
    skill_score = skill.skill_score if skill is not None else 0.5

    bias_adjustment_f = -mean_bias_f
    corrected_high_temp_f = forecast_run.predicted_high_temp_f + bias_adjustment_f
    corrected_sigma_f = max(forecast_run.distribution_sigma_f, mae_f)
    skill_weight = min(1.0, max(0.05, skill_score))

    return BiasCorrectedForecast(
        forecast_run=forecast_run,
        bias_adjustment_f=bias_adjustment_f,
        corrected_high_temp_f=corrected_high_temp_f,
        corrected_sigma_f=corrected_sigma_f,
        skill_weight=skill_weight,
    )


def _normalize_skill_record(
    *,
    market: WeatherMarketDefinition,
    payload: Mapping[str, Any],
) -> WeatherModelSkill | None:
    station_id = str(payload.get("station_id", "")).strip().upper()
    if not station_id or station_id != market.location.station_id:
        return None

    model_name = str(payload.get("model_name", "")).strip().lower()
    if not model_name:
        return None

    horizon_bucket_hours = int(parse_float(payload, "horizon_bucket_hours") or 0)
    if horizon_bucket_hours <= 0:
        return None

    mean_bias_f = parse_float(payload, "mean_bias_f") or 0.0
    mae_f = parse_float(payload, "mae_f") or 3.0
    skill_score = parse_float(payload, "skill_score") or 0.5

    return WeatherModelSkill(
        model_name=model_name,
        station_id=station_id,
        horizon_bucket_hours=horizon_bucket_hours,
        mean_bias_f=mean_bias_f,
        mae_f=mae_f,
        skill_score=min(1.0, max(0.05, skill_score)),
    )


def _select_skill(
    *,
    forecast_run: WeatherForecastRun,
    skill_store: Sequence[WeatherModelSkill],
    station_id: str,
) -> WeatherModelSkill | None:
    candidates = [
        skill
        for skill in skill_store
        if skill.model_name == forecast_run.model_name and skill.station_id == station_id
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda skill: abs(skill.horizon_bucket_hours - forecast_run.horizon_hours),
    )
