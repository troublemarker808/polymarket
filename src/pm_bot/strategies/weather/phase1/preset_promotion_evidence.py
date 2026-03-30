"""Evidence aggregation for weather preset promotion decisions."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class WeatherPresetPromotionEvidence:
    report_count: int
    winning_variant: str
    ready_to_apply: bool
    recurring_promotion_target: str
    recurring_promotion_count: int
    recurring_targeted_improvement: float
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


def build_weather_preset_promotion_evidence(
    *,
    auto_experiment_paths: list[str | Path],
) -> WeatherPresetPromotionEvidence:
    promotion_counter: Counter[str] = Counter()
    targeted_improvement_total = 0.0
    targeted_improvement_count = 0
    blockers: list[str] = []
    warnings: list[str] = []

    for path in auto_experiment_paths:
        payload = _load_payload(path)
        promotion_decision = str(payload.get("promotion_decision", "")).strip()
        promotion_target = str(payload.get("promotion_target", "")).strip()
        winner = payload.get("winner", {})
        winner_action = str(winner.get("recommended_action", "")).strip() if isinstance(winner, dict) else ""
        targeted_improvement = float(
            winner.get("targeted_loss_improvement", payload.get("targeted_loss_improvement", 0.0)) or 0.0
        ) if isinstance(winner, dict) else float(payload.get("targeted_loss_improvement", 0.0) or 0.0)
        if promotion_decision == "promote_candidate" and promotion_target:
            promotion_counter[promotion_target] += 1
            targeted_improvement_total += targeted_improvement
            targeted_improvement_count += 1
        elif promotion_decision:
            warnings.append(f"{Path(path).name}: {promotion_decision}")
        if winner_action and winner_action != "proceed":
            blockers.append(f"{Path(path).name}: winner_action={winner_action}")

    recurring_promotion_target = promotion_counter.most_common(1)[0][0] if promotion_counter else "none"
    recurring_promotion_count = promotion_counter.most_common(1)[0][1] if promotion_counter else 0
    recurring_targeted_improvement = round(
        targeted_improvement_total / targeted_improvement_count,
        4,
    ) if targeted_improvement_count > 0 else 0.0
    if len(auto_experiment_paths) < 2:
        blockers.append("need at least two auto-experiment reports")
    if recurring_promotion_count < 2:
        blockers.append("same weather candidate has not won enough repeated auto-experiments")
    if recurring_targeted_improvement < 0.03:
        blockers.append("targeted weather loss improvement is not strong enough across repeated auto-experiments")

    return WeatherPresetPromotionEvidence(
        report_count=len(auto_experiment_paths),
        winning_variant=recurring_promotion_target,
        ready_to_apply=(not blockers and recurring_promotion_target != "none"),
        recurring_promotion_target=recurring_promotion_target,
        recurring_promotion_count=recurring_promotion_count,
        recurring_targeted_improvement=recurring_targeted_improvement,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def format_weather_preset_promotion_evidence(evidence: WeatherPresetPromotionEvidence) -> str:
    lines = [
        "# Weather Preset Promotion Evidence",
        "",
        f"- report_count: {evidence.report_count}",
        f"- winning_variant: {evidence.winning_variant}",
        f"- ready_to_apply: {str(evidence.ready_to_apply).lower()}",
        f"- recurring_promotion_target: {evidence.recurring_promotion_target}",
        f"- recurring_promotion_count: {evidence.recurring_promotion_count}",
        f"- recurring_targeted_improvement: {evidence.recurring_targeted_improvement:.4f}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in evidence.blockers or ("none",))
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in evidence.warnings or ("none",))
    return "\n".join(lines) + "\n"


def write_weather_preset_promotion_evidence(
    *,
    evidence: WeatherPresetPromotionEvidence,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_weather_preset_promotion_evidence(evidence),
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(evidence)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_payload(path: str | Path) -> dict[str, Any]:
    decoded = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(decoded, dict):
        return decoded
    return {}


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
