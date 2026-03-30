"""Version comparison artifacts for crypto phase2 presets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.strategies.crypto.phase2.auto_experiments import CryptoPhase2AutoExperimentsReport
from pm_bot.strategies.crypto.phase2.preset_promotion_evidence import CryptoPhase2PresetPromotionEvidence


@dataclass(slots=True, frozen=True)
class CryptoPhase2VersionComparison:
    current_version: str
    candidate_version: str
    recommendation: str
    strategy_state: str
    metric_wins: dict[str, str]
    targeted_improvement: float
    readiness_delta: float
    total_profit_loss_delta: float
    filtered_pnl_delta: float
    edge_capture_delta: float
    pnl_per_notional_delta: float
    average_loss_trade_pnl_delta: float
    large_notional_share_delta: float
    trade_execution_drag_delta: float
    trade_realized_pnl_bps_delta: float
    exit_family_balance_delta: float
    large_bucket_pnl_per_notional_delta: float
    reasons: tuple[str, ...]


def build_crypto_phase2_version_comparison(
    *,
    report: CryptoPhase2AutoExperimentsReport,
    evidence: CryptoPhase2PresetPromotionEvidence | None = None,
) -> CryptoPhase2VersionComparison:
    baseline = report.baseline
    winner = report.winner
    targeted_improvement = float(getattr(winner, "targeted_loss_improvement", 0.0))
    readiness_delta = round(winner.readiness_score - baseline.readiness_score, 4)
    total_profit_loss_delta = round(baseline.total_profit_loss - winner.total_profit_loss, 4)
    filtered_pnl_delta = round(winner.filtered_pnl - baseline.filtered_pnl, 6)
    edge_capture_delta = round(
        float(getattr(winner, "edge_capture_ratio", 0.0))
        - float(getattr(baseline, "edge_capture_ratio", 0.0)),
        4,
    )
    pnl_per_notional_delta = round(
        float(getattr(winner, "pnl_per_notional", 0.0))
        - float(getattr(baseline, "pnl_per_notional", 0.0)),
        6,
    )
    average_loss_trade_pnl_delta = round(
        abs(float(getattr(baseline, "average_loss_trade_pnl", 0.0)))
        - abs(float(getattr(winner, "average_loss_trade_pnl", 0.0))),
        6,
    )
    large_notional_share_delta = round(
        float(getattr(baseline, "large_notional_share", 0.0))
        - float(getattr(winner, "large_notional_share", 0.0)),
        4,
    )
    trade_execution_drag_delta = round(
        float(getattr(baseline, "average_trade_execution_drag_bps", 0.0))
        - float(getattr(winner, "average_trade_execution_drag_bps", 0.0)),
        4,
    )
    trade_realized_pnl_bps_delta = round(
        float(getattr(winner, "average_trade_realized_pnl_bps", 0.0))
        - float(getattr(baseline, "average_trade_realized_pnl_bps", 0.0)),
        4,
    )
    exit_family_balance_delta = round(
        float(getattr(winner, "exit_family_balance_score", 0.0))
        - float(getattr(baseline, "exit_family_balance_score", 0.0)),
        4,
    )
    large_bucket_pnl_per_notional_delta = round(
        float(getattr(winner, "large_bucket_pnl_per_notional", 0.0))
        - float(getattr(baseline, "large_bucket_pnl_per_notional", 0.0)),
        6,
    )
    metric_wins = {
        "readiness": winner.variant_name if winner.readiness_score > baseline.readiness_score else baseline.variant_name,
        "profit_loss": winner.variant_name if winner.total_profit_loss < baseline.total_profit_loss else baseline.variant_name,
        "filtered_pnl": winner.variant_name if winner.filtered_pnl > baseline.filtered_pnl else baseline.variant_name,
        "targeted_loss": winner.variant_name if targeted_improvement > 0 else baseline.variant_name,
        "edge_capture": winner.variant_name if edge_capture_delta > 0 else baseline.variant_name,
        "pnl_efficiency": winner.variant_name if pnl_per_notional_delta > 0 else baseline.variant_name,
        "exit_asymmetry": winner.variant_name if average_loss_trade_pnl_delta > 0 else baseline.variant_name,
        "size_concentration": winner.variant_name if large_notional_share_delta > 0 else baseline.variant_name,
        "trade_execution_drag": winner.variant_name if trade_execution_drag_delta > 0 else baseline.variant_name,
        "trade_realized_pnl_bps": winner.variant_name if trade_realized_pnl_bps_delta > 0 else baseline.variant_name,
        "exit_family_balance": winner.variant_name if exit_family_balance_delta > 0 else baseline.variant_name,
        "large_bucket_pnl_per_notional": winner.variant_name if large_bucket_pnl_per_notional_delta > 0 else baseline.variant_name,
    }
    reasons: list[str] = []
    if baseline.recommended_action == "pause" or winner.recommended_action == "pause":
        recommendation = "quarantine"
        strategy_state = "quarantined"
        reasons.append("baseline or winner remains paused after experiments")
    elif (
        targeted_improvement <= 0
        and total_profit_loss_delta <= 0
        and filtered_pnl_delta <= 0
        and edge_capture_delta <= 0
        and average_loss_trade_pnl_delta <= 0
        and trade_execution_drag_delta <= 0
        and trade_realized_pnl_bps_delta <= 0
        and exit_family_balance_delta <= 0
    ):
        recommendation = "quarantine"
        strategy_state = "quarantined"
        reasons.append("candidate fails to improve losses, pnl, edge capture, or loss-trade asymmetry")
    elif report.promotion_decision == "promote_candidate":
        recommendation = "promote"
        strategy_state = "candidate"
        reasons.append("candidate clears crypto promotion conditions")
    elif report.promotion_decision == "keep_baseline" and baseline.recommended_action == "proceed":
        recommendation = "keep_current"
        strategy_state = "stable"
        reasons.append("baseline remains the strongest stable crypto preset")
    elif targeted_improvement > 0 and (
        edge_capture_delta > 0
        or pnl_per_notional_delta > 0
        or average_loss_trade_pnl_delta > 0
        or large_notional_share_delta > 0
    ):
        recommendation = "keep_current"
        strategy_state = "candidate"
        reasons.append("candidate is improving target losses but still needs more repeated evidence")
    elif (
        total_profit_loss_delta < 0
        or filtered_pnl_delta < 0
        or pnl_per_notional_delta < 0
        or average_loss_trade_pnl_delta < 0
        or trade_execution_drag_delta < 0
        or trade_realized_pnl_bps_delta < 0
        or large_bucket_pnl_per_notional_delta < 0
    ):
        recommendation = "keep_current"
        strategy_state = "degraded"
        reasons.append("candidate degrades aggregate profitability, pnl efficiency, or exit asymmetry despite partial gains")
    else:
        recommendation = "keep_current"
        strategy_state = "degraded"
        reasons.append("candidate does not yet improve the recurring crypto loss stack")
    if evidence is not None and not evidence.ready_to_apply and strategy_state == "candidate":
        recommendation = "keep_current"
        strategy_state = "degraded"
        reasons.append("promotion evidence is not yet strong enough to apply the candidate")
    return CryptoPhase2VersionComparison(
        current_version=baseline.variant_name,
        candidate_version=winner.variant_name,
        recommendation=recommendation,
        strategy_state=strategy_state,
        metric_wins=metric_wins,
        targeted_improvement=targeted_improvement,
        readiness_delta=readiness_delta,
        total_profit_loss_delta=total_profit_loss_delta,
        filtered_pnl_delta=filtered_pnl_delta,
        edge_capture_delta=edge_capture_delta,
        pnl_per_notional_delta=pnl_per_notional_delta,
        average_loss_trade_pnl_delta=average_loss_trade_pnl_delta,
        large_notional_share_delta=large_notional_share_delta,
        trade_execution_drag_delta=trade_execution_drag_delta,
        trade_realized_pnl_bps_delta=trade_realized_pnl_bps_delta,
        exit_family_balance_delta=exit_family_balance_delta,
        large_bucket_pnl_per_notional_delta=large_bucket_pnl_per_notional_delta,
        reasons=tuple(reasons),
    )


def format_crypto_phase2_version_comparison(report: CryptoPhase2VersionComparison) -> str:
    lines = [
        "# Crypto Phase 2 Version Comparison",
        "",
        f"- current_version: {report.current_version}",
        f"- candidate_version: {report.candidate_version}",
        f"- recommendation: {report.recommendation}",
        f"- strategy_state: {report.strategy_state}",
        f"- targeted_improvement: {report.targeted_improvement:.4f}",
        f"- readiness_delta: {report.readiness_delta:.4f}",
        f"- total_profit_loss_delta: {report.total_profit_loss_delta:.4f}",
        f"- filtered_pnl_delta: {report.filtered_pnl_delta:.6f}",
        f"- edge_capture_delta: {report.edge_capture_delta:.4f}",
        f"- pnl_per_notional_delta: {report.pnl_per_notional_delta:.6f}",
        f"- average_loss_trade_pnl_delta: {report.average_loss_trade_pnl_delta:.6f}",
        f"- large_notional_share_delta: {report.large_notional_share_delta:.4f}",
        f"- trade_execution_drag_delta: {report.trade_execution_drag_delta:.4f}",
        f"- trade_realized_pnl_bps_delta: {report.trade_realized_pnl_bps_delta:.4f}",
        f"- exit_family_balance_delta: {report.exit_family_balance_delta:.4f}",
        f"- large_bucket_pnl_per_notional_delta: {report.large_bucket_pnl_per_notional_delta:.6f}",
        "",
        "## Metric Wins",
        "",
    ]
    for metric, winner in report.metric_wins.items():
        lines.append(f"- {metric}: {winner}")
    lines.extend(["", "## Reasons", ""])
    lines.extend(f"- {reason}" for reason in report.reasons or ("none",))
    return "\n".join(lines) + "\n"


def write_crypto_phase2_version_comparison(
    *,
    report: CryptoPhase2VersionComparison,
    output_path: str | Path,
) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_crypto_phase2_version_comparison(report), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(report)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
