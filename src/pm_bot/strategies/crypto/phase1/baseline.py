"""Locked calibration baseline helpers for Crypto Phase 1/2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from pm_bot.strategies.crypto.phase1.models import CryptoBarrierModelConfig, CryptoFusionModelConfig


@dataclass(slots=True, frozen=True)
class CryptoCalibrationBaselinePreset:
    preset_id: str
    candidate_name: str
    locked_at: datetime
    barrier_model_config: CryptoBarrierModelConfig
    fusion_model_config: CryptoFusionModelConfig
    rationale: str


def get_locked_crypto_calibration_baseline_preset() -> CryptoCalibrationBaselinePreset:
    return CryptoCalibrationBaselinePreset(
        preset_id="crypto-calibration-baseline-20260328",
        candidate_name="btc-r1-s165-b35-s65",
        locked_at=datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc),
        barrier_model_config=CryptoBarrierModelConfig(steepness=1.65),
        fusion_model_config=CryptoFusionModelConfig(barrier_weight=0.35, surface_weight=0.65),
        rationale=(
            "Locked Phase B baseline after BTC/ETH validation converged on a shallower "
            "barrier model with a surface-heavier fusion mix."
        ),
    )


def resolve_crypto_calibration_model_configs(
    *,
    barrier_model_config: CryptoBarrierModelConfig | None = None,
    fusion_model_config: CryptoFusionModelConfig | None = None,
) -> tuple[CryptoCalibrationBaselinePreset, CryptoBarrierModelConfig, CryptoFusionModelConfig]:
    preset = get_locked_crypto_calibration_baseline_preset()
    return (
        preset,
        barrier_model_config or preset.barrier_model_config,
        fusion_model_config or preset.fusion_model_config,
    )
