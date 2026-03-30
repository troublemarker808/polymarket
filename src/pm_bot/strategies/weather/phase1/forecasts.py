"""Forecast ingestion helpers for Weather Phase 1 research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pm_bot.strategies.common import parse_float
from pm_bot.strategies.weather.phase1.models import WeatherForecastRun, WeatherMarketDefinition


def build_forecast_run_calendar(
    *,
    market: WeatherMarketDefinition,
    run_payloads: Sequence[Mapping[str, Any]],
) -> tuple[datetime, ...]:
    runs = ingest_forecast_runs(market=market, run_payloads=run_payloads)
    return tuple(run.issued_at for run in runs)


def ingest_forecast_runs(
    *,
    market: WeatherMarketDefinition,
    run_payloads: Sequence[Mapping[str, Any]],
) -> tuple[WeatherForecastRun, ...]:
    ingested: list[WeatherForecastRun] = []
    for payload in run_payloads:
        run = _normalize_forecast_run(market=market, payload=payload)
        if run is not None:
            ingested.append(run)
    ingested.sort(key=lambda run: run.issued_at)
    return tuple(ingested)


def _normalize_forecast_run(
    *,
    market: WeatherMarketDefinition,
    payload: Mapping[str, Any],
) -> WeatherForecastRun | None:
    station_id = str(payload.get("station_id", "")).strip().upper()
    if not station_id or station_id != market.location.station_id:
        return None

    issued_at = _parse_datetime_value(payload.get("issued_at"))
    target_date = _parse_datetime_value(payload.get("target_date")) or market.event_date
    if issued_at is None or target_date is None:
        return None

    predicted_high_temp_f = parse_float(payload, "predicted_high_temp_f", "forecast_high_temp_f")
    if predicted_high_temp_f is None:
        return None

    distribution_sigma_f = (
        parse_float(payload, "distribution_sigma_f", "sigma_f", "forecast_sigma_f") or 3.0
    )
    horizon_hours = max(0.0, (target_date - issued_at).total_seconds() / 3600)

    metadata: dict[str, float | str] = {}
    for key in ("ensemble_member_count", "run_cycle", "source"):
        value = payload.get(key)
        if value not in (None, ""):
            metadata[key] = str(value)

    return WeatherForecastRun(
        model_name=str(payload.get("model_name", "")).strip().lower(),
        station_id=station_id,
        issued_at=issued_at,
        target_date=target_date,
        horizon_hours=horizon_hours,
        predicted_high_temp_f=predicted_high_temp_f,
        distribution_sigma_f=max(0.5, distribution_sigma_f),
        metadata=metadata,
    )


def _parse_datetime_value(raw_value: Any) -> datetime | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, datetime):
        return raw_value if raw_value.tzinfo is not None else raw_value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
