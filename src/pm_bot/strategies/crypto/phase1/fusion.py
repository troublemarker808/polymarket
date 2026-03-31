"""Fusion helpers for Crypto Phase 1 fair-value estimation."""

from __future__ import annotations

from pm_bot.core.research_types import FairValueEstimate
from pm_bot.core.types import Category
from pm_bot.strategies.crypto.phase1.models import (
    CryptoBarrierEstimate,
    CryptoFusedFairValue,
    CryptoFusionModelConfig,
    CryptoPricingInputs,
    CryptoResidualModelConfig,
    CryptoSurfaceEstimate,
)
from pm_bot.strategies.crypto.phase1.pricing import resolve_residual_correction


def fuse_crypto_fair_value(
    *,
    inputs: CryptoPricingInputs,
    barrier_estimate: CryptoBarrierEstimate,
    surface_estimate: CryptoSurfaceEstimate | None = None,
    observed_probability: float | None = None,
    model_config: CryptoFusionModelConfig | None = None,
    residual_model_config: CryptoResidualModelConfig | None = None,
) -> CryptoFusedFairValue:
    config = model_config or CryptoFusionModelConfig()
    rationale_tags: tuple[str, ...]
    if surface_estimate is None:
        fair_probability = barrier_estimate.fair_probability
        surface_probability = None
        rationale_tags = ("barrier_model",)
        confidence = _confidence_from_inputs(inputs=inputs, has_surface=False)
    else:
        total_weight = max(config.barrier_weight + config.surface_weight, 1e-9)
        fair_probability = (
            (barrier_estimate.fair_probability * config.barrier_weight)
            + (surface_estimate.fair_probability * config.surface_weight)
        ) / total_weight
        surface_probability = surface_estimate.fair_probability
        rationale_tags = ("barrier_model", "surface_consistency")
        confidence = _confidence_from_inputs(inputs=inputs, has_surface=True)

    residual = resolve_residual_correction(
        inputs=inputs,
        confidence=confidence,
        model_config=residual_model_config,
    )
    if residual.applied:
        fair_probability += residual.correction_bps / 10000.0
    fair_probability = max(config.probability_floor, min(config.probability_ceiling, fair_probability))
    half_life_seconds = _half_life_seconds(inputs=inputs, observed_probability=observed_probability, fair_probability=fair_probability)
    return CryptoFusedFairValue(
        fair_probability=fair_probability,
        confidence=confidence,
        half_life_seconds=half_life_seconds,
        barrier_probability=barrier_estimate.fair_probability,
        surface_probability=surface_probability,
        rationale_tags=rationale_tags,
        residual_bucket_key=residual.bucket_key,
        residual_correction_bps=residual.correction_bps,
        residual_applied=residual.applied,
        residual_diagnostic_tag=residual.diagnostic_tag,
    )


def to_fair_value_estimate(
    *,
    inputs: CryptoPricingInputs,
    fused: CryptoFusedFairValue,
    observed_probability: float | None = None,
) -> FairValueEstimate:
    return FairValueEstimate(
        market_id=inputs.market.normalized.market_id,
        category=Category.CRYPTO,
        fair_probability=fused.fair_probability,
        confidence=fused.confidence,
        half_life_seconds=fused.half_life_seconds,
        observed_probability=observed_probability,
        model_id="crypto.phase1.fused",
        rationale_tags=fused.rationale_tags,
        supporting_values={
            "barrier_probability": fused.barrier_probability,
            "surface_probability": fused.surface_probability,
            "distance_ratio": inputs.distance_ratio,
            "effective_horizon_days": inputs.effective_horizon_days,
            "residual_bucket_key": fused.residual_bucket_key,
            "residual_correction_bps": fused.residual_correction_bps,
            "residual_applied": fused.residual_applied,
            "residual_diagnostic_tag": fused.residual_diagnostic_tag,
        },
    )


def _confidence_from_inputs(*, inputs: CryptoPricingInputs, has_surface: bool) -> float:
    base = 0.58
    if has_surface:
        base += 0.08
    if inputs.volatility_regime.label == "normal":
        base += 0.06
    elif inputs.volatility_regime.label == "low":
        base += 0.03
    else:
        base -= 0.02
    if inputs.effective_horizon_days >= 30:
        base += 0.03
    return max(0.5, min(0.85, base))


def _half_life_seconds(
    *,
    inputs: CryptoPricingInputs,
    observed_probability: float | None,
    fair_probability: float,
) -> int:
    probability_gap = abs((observed_probability if observed_probability is not None else fair_probability) - fair_probability)
    if probability_gap >= 0.03:
        return 3600
    if inputs.effective_horizon_days <= 14:
        return 8 * 3600
    return 24 * 3600
