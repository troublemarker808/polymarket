"""Fixed-window experiment helpers for replay-driven tuning."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.settings import BotSettings, CategoryRuntimeConfig
from pm_bot.core.types import MarketSnapshot
from pm_bot.research.autoresearch import (
    AutoresearchReport,
    generate_autoresearch_report,
    write_autoresearch_report,
)
from pm_bot.research.engine import load_market_snapshots, run_replay_snapshots
from pm_bot.research.window_mining import WindowMiningReport, mine_fixed_windows_from_snapshots

if TYPE_CHECKING:
    from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState


@dataclass(slots=True, frozen=True)
class DatasetSplit:
    name: str
    snapshot_count: int
    started_at: datetime | None
    ended_at: datetime | None
    source: str
    source_name: str
    labels: tuple[str, ...]
    score: float | None
    source_snapshot_path: str
    source_event_path: str | None
    btc_family_labels: tuple[str, ...]
    expiry_bucket: str


@dataclass(slots=True, frozen=True)
class _PreparedDatasetSplit:
    metadata: DatasetSplit
    snapshots: tuple[MarketSnapshot, ...]


@dataclass(slots=True, frozen=True)
class ExperimentCandidate:
    name: str
    overrides: tuple[tuple[str, Any], ...]
    rationale: str


@dataclass(slots=True, frozen=True)
class ExperimentRunArtifact:
    split_name: str
    candidate_name: str
    overrides: tuple[tuple[str, Any], ...]
    classification: str
    score: float
    metrics_path: str
    event_path: str
    autoresearch_path: str
    signals_generated: int
    orders_submitted: int
    orders_rejected: int
    orders_filled: int
    orders_expired: int
    orders_canceled: int
    fill_rate: float
    cancel_rate: float
    dominant_rejection_reasons: tuple[tuple[str, int], ...]

    @property
    def useful_submissions(self) -> int:
        return max(0, self.orders_submitted - self.orders_expired - self.orders_canceled)

    @property
    def submission_coverage(self) -> float:
        if self.signals_generated <= 0:
            return 0.0
        return self.orders_submitted / self.signals_generated


@dataclass(slots=True, frozen=True)
class FixedWindowExperimentReport:
    generated_at: datetime
    mode: str
    snapshot_path: str
    output_dir: str
    summary_path: str
    window_selection_mode: str
    window_selection_reason: str
    mining_summary_path: str | None
    dataset_splits: tuple[DatasetSplit, ...]
    baseline_classification: str
    rewritten_objective: str
    score_formula: str
    locked_parameters: tuple[str, ...]
    tunable_parameters: tuple[str, ...]
    experiment_matrix: tuple[ExperimentCandidate, ...]
    finalists: tuple[str, ...]
    validation_winner: str
    promoted_winner: str
    decision_reason: str
    train_results: tuple[ExperimentRunArtifact, ...]
    validation_results: tuple[ExperimentRunArtifact, ...]
    holdout_results: tuple[ExperimentRunArtifact, ...]


async def run_fixed_window_experiments(
    *,
    snapshot_path: str | Path,
    config_dir: str = "configs",
    output_dir: str | Path | None = None,
    mode: str = "replay",
    limit: int | None = None,
    underlying_state_path: str | Path | None = None,
    event_path: str | Path | None = None,
    window_snapshots: int = 30,
    top_windows: int = 3,
) -> FixedWindowExperimentReport:
    snapshots = load_market_snapshots(snapshot_path)
    if limit is not None:
        snapshots = snapshots[: max(limit, 0)]
    if len(snapshots) < 3:
        raise ValueError("Fixed-window experiments require at least 3 snapshots")
    snapshots = _chronological_snapshots(snapshots)

    output_root = _resolve_output_dir(output_dir)
    settings = load_settings_from_directory(config_dir)
    underlying_states = None
    if _has_strategy_config(settings, "phase2"):
        if underlying_state_path is None:
            raise ValueError("Phase 2 fixed-window experiments require underlying_state_path")
        from pm_bot.strategies.crypto.phase1.state_loader import load_underlying_states

        underlying_states = load_underlying_states(underlying_state_path)
    prepared_splits, window_selection_mode, window_selection_reason, mining_summary_path = await _prepare_dataset_splits(
        snapshots=snapshots,
        snapshot_path=snapshot_path,
        event_path=event_path,
        output_dir=output_root,
        window_snapshots=window_snapshots,
        top_windows=top_windows,
    )
    split_payloads = {prepared.metadata.name: list(prepared.snapshots) for prepared in prepared_splits}

    baseline_candidate = ExperimentCandidate(
        name="baseline",
        overrides=(),
        rationale="Unmodified config baseline for the captured fixed window.",
    )

    train_baseline = await _run_candidate(
        base_settings=settings,
        candidate=baseline_candidate,
        split_name="train",
        snapshots=split_payloads["train"],
        output_dir=output_root,
        mode=mode,
        underlying_states=underlying_states,
    )
    baseline_train_report = generate_autoresearch_report(
        metrics_path=train_baseline.metrics_path,
        event_path=train_baseline.event_path,
    )
    candidates = (baseline_candidate,) + _default_candidates(
        classification=baseline_train_report.classification,
        settings=settings,
    )

    train_results = [train_baseline]
    for candidate in candidates[1:]:
        train_results.append(
            await _run_candidate(
                base_settings=settings,
                candidate=candidate,
                split_name="train",
                snapshots=split_payloads["train"],
                output_dir=output_root,
                mode=mode,
                tunable_parameters=baseline_train_report.tunable_parameters,
                underlying_states=underlying_states,
            )
        )

    finalists = _select_finalists(train_results)
    validation_results = []
    for candidate_name in finalists:
        candidate = next(item for item in candidates if item.name == candidate_name)
        validation_results.append(
            await _run_candidate(
                base_settings=settings,
                candidate=candidate,
                split_name="validation",
                snapshots=split_payloads["validation"],
                output_dir=output_root,
                mode=mode,
                tunable_parameters=baseline_train_report.tunable_parameters,
                underlying_states=underlying_states,
            )
        )

    validation_winner, validation_reason = _pick_validation_winner(validation_results)
    holdout_names = ("baseline",) if validation_winner == "baseline" else ("baseline", validation_winner)
    holdout_results = []
    for candidate_name in holdout_names:
        candidate = next(item for item in candidates if item.name == candidate_name)
        holdout_results.append(
            await _run_candidate(
                base_settings=settings,
                candidate=candidate,
                split_name="holdout",
                snapshots=split_payloads["holdout"],
                output_dir=output_root,
                mode=mode,
                tunable_parameters=baseline_train_report.tunable_parameters,
                underlying_states=underlying_states,
            )
        )

    promoted_winner, decision_reason = _promote_winner(
        validation_winner=validation_winner,
        validation_reason=validation_reason,
        holdout_results=holdout_results,
    )

    report = FixedWindowExperimentReport(
        generated_at=datetime.now(tz=timezone.utc),
        mode=mode,
        snapshot_path=str(Path(snapshot_path)),
        output_dir=str(output_root),
        summary_path=str(output_root / "summary.md"),
        window_selection_mode=window_selection_mode,
        window_selection_reason=window_selection_reason,
        mining_summary_path=mining_summary_path,
        dataset_splits=tuple(prepared.metadata for prepared in prepared_splits),
        baseline_classification=baseline_train_report.classification,
        rewritten_objective=baseline_train_report.rewritten_objective,
        score_formula=baseline_train_report.score_formula,
        locked_parameters=baseline_train_report.locked_parameters,
        tunable_parameters=baseline_train_report.tunable_parameters,
        experiment_matrix=candidates,
        finalists=finalists,
        validation_winner=validation_winner,
        promoted_winner=promoted_winner,
        decision_reason=decision_reason,
        train_results=tuple(train_results),
        validation_results=tuple(validation_results),
        holdout_results=tuple(holdout_results),
    )
    write_fixed_window_report(report, report.summary_path)
    return report


def format_fixed_window_report(report: FixedWindowExperimentReport) -> str:
    return "\n".join(
        [
            f"mode={report.mode}",
            f"snapshot_path={report.snapshot_path}",
            f"output_dir={report.output_dir}",
            f"window_selection_mode={report.window_selection_mode}",
            f"window_selection_reason={report.window_selection_reason}",
            f"mining_summary_path={report.mining_summary_path or ''}",
            f"dataset_split_sources={_format_split_sources(report.dataset_splits)}",
            f"baseline_classification={report.baseline_classification}",
            f"validation_winner={report.validation_winner}",
            f"promoted_winner={report.promoted_winner}",
            f"finalists={','.join(report.finalists)}",
            f"train_scores={_format_score_line(report.train_results)}",
            f"train_promotion_scores={_format_promotion_score_line(report.train_results)}",
            f"validation_scores={_format_score_line(report.validation_results)}",
            f"validation_promotion_scores={_format_promotion_score_line(report.validation_results)}",
            f"holdout_scores={_format_score_line(report.holdout_results)}",
            f"holdout_promotion_scores={_format_promotion_score_line(report.holdout_results)}",
            f"summary_path={report.summary_path}",
        ]
    )


def write_fixed_window_report(report: FixedWindowExperimentReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_render_fixed_window_report(report), encoding="utf-8")


async def _run_candidate(
    *,
    base_settings: BotSettings,
    candidate: ExperimentCandidate,
    split_name: str,
    snapshots: list[MarketSnapshot],
    output_dir: Path,
    mode: str,
    tunable_parameters: tuple[str, ...] | None = None,
    underlying_states: dict[str, CryptoUnderlyingState] | None = None,
) -> ExperimentRunArtifact:
    if tunable_parameters is not None:
        _validate_overrides(candidate.overrides, tunable_parameters)

    settings = _apply_overrides(base_settings, candidate.overrides)
    candidate_slug = _slug(candidate.name)
    split_dir = output_dir / split_name
    split_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = split_dir / f"{candidate_slug}.metrics.json"
    event_path = split_dir / f"{candidate_slug}.events.jsonl"
    autoresearch_path = split_dir / f"{candidate_slug}.autoresearch.md"

    if _has_strategy_config(settings, "phase2") and mode == "replay":
        if underlying_states is None:
            raise ValueError("Phase 2 candidate runs require underlying_states")
        from pm_bot.strategies.crypto.phase2.replay import run_crypto_phase2_replay_snapshots

        candidate_output_dir = split_dir / candidate_slug
        await run_crypto_phase2_replay_snapshots(
            snapshots=snapshots,
            underlying_states=underlying_states,
            settings=settings,
            config_dir="fixed-window-phase2",
            output_dir=candidate_output_dir,
            run_id=f"{split_name}-{candidate_slug}",
            snapshot_path=f"{split_name}:{candidate_slug}",
        )
        metrics_path = candidate_output_dir / "engine.metrics.json"
        event_path = candidate_output_dir / "events.jsonl"
        autoresearch_path = candidate_output_dir / "autoresearch.md"
    else:
        await run_replay_snapshots(
            mode=mode,
            snapshots=snapshots,
            settings=settings,
            recorder_path=event_path,
            metrics_path=metrics_path,
        )
    report = generate_autoresearch_report(metrics_path=metrics_path, event_path=event_path)
    write_autoresearch_report(report, autoresearch_path)
    return _artifact_from_report(
        split_name=split_name,
        candidate=candidate,
        report=report,
        metrics_path=metrics_path,
        event_path=event_path,
        autoresearch_path=autoresearch_path,
    )


def _artifact_from_report(
    *,
    split_name: str,
    candidate: ExperimentCandidate,
    report: AutoresearchReport,
    metrics_path: Path,
    event_path: Path,
    autoresearch_path: Path,
) -> ExperimentRunArtifact:
    metrics = report.metrics
    return ExperimentRunArtifact(
        split_name=split_name,
        candidate_name=candidate.name,
        overrides=candidate.overrides,
        classification=report.classification,
        score=report.score,
        metrics_path=str(metrics_path),
        event_path=str(event_path),
        autoresearch_path=str(autoresearch_path),
        signals_generated=int(metrics.get("signals_generated", 0) or 0),
        orders_submitted=int(metrics.get("orders_submitted", 0) or 0),
        orders_rejected=int(metrics.get("orders_rejected", 0) or 0),
        orders_filled=int(metrics.get("orders_filled", 0) or 0),
        orders_expired=int(metrics.get("orders_expired", 0) or 0),
        orders_canceled=int(metrics.get("orders_canceled", 0) or 0),
        fill_rate=float(metrics.get("fill_rate", 0.0) or 0.0),
        cancel_rate=float(metrics.get("cancel_rate", 0.0) or 0.0),
        dominant_rejection_reasons=report.dominant_rejection_reasons,
    )


def _split_snapshots(snapshots: list[MarketSnapshot]) -> dict[str, list[MarketSnapshot]]:
    total = len(snapshots)
    train_count = max(1, (total * 60) // 100)
    validation_count = max(1, (total * 20) // 100)
    holdout_count = total - train_count - validation_count
    if holdout_count < 1:
        if train_count > validation_count and train_count > 1:
            train_count -= 1
        else:
            validation_count -= 1
        holdout_count = total - train_count - validation_count
    return {
        "train": list(snapshots[:train_count]),
        "validation": list(snapshots[train_count : train_count + validation_count]),
        "holdout": list(snapshots[train_count + validation_count : train_count + validation_count + holdout_count]),
    }


async def _prepare_dataset_splits(
    *,
    snapshots: list[MarketSnapshot],
    snapshot_path: str | Path,
    event_path: str | Path | None,
    output_dir: Path,
    window_snapshots: int,
    top_windows: int,
) -> tuple[tuple[_PreparedDatasetSplit, ...], str, str, str | None]:
    chronological = _chronological_prepared_splits(
        snapshots=snapshots,
        snapshot_path=snapshot_path,
        event_path=event_path,
    )
    if event_path is None:
        return (
            chronological,
            "chronological_baseline",
            "No event log was provided, so fixed-window experiments use a chronological split of the full capture.",
            None,
        )

    resolved_window_snapshots = max(3, min(window_snapshots, len(snapshots)))
    try:
        mining_report = await mine_fixed_windows_from_snapshots(
            snapshots=snapshots,
            snapshot_label=str(Path(snapshot_path)),
            event_path=event_path,
            output_dir=output_dir / "mined-windows",
            window_snapshots=resolved_window_snapshots,
            top_windows=top_windows,
        )
    except ValueError as exc:
        return (
            chronological,
            "chronological_baseline_fallback",
            f"Eventful-window mining could not promote any fixed window: {exc}",
            None,
        )

    mined = _mined_prepared_splits(mining_report=mining_report)
    if len(mined) >= 3:
        return (
            mined[:3],
            "eventful_mined",
            "Train, validation, and holdout splits were promoted from mined eventful windows.",
            mining_report.summary_path,
        )

    mixed = list(mined)
    used_names = {item.metadata.name for item in mixed}
    for baseline in chronological:
        if baseline.metadata.name in used_names:
            continue
        mixed.append(baseline)
        if len(mixed) >= 3:
            break
    mixed.sort(key=lambda item: ("train", "validation", "holdout").index(item.metadata.name))
    return (
        tuple(mixed[:3]),
        "eventful_mined_mixed",
        "Mined eventful windows were used where available, with chronological baseline fallbacks for the remaining splits.",
        mining_report.summary_path,
    )


def _chronological_prepared_splits(
    *,
    snapshots: list[MarketSnapshot],
    snapshot_path: str | Path,
    event_path: str | Path | None,
) -> tuple[_PreparedDatasetSplit, ...]:
    split_payloads = _split_snapshots(snapshots)
    prepared: list[_PreparedDatasetSplit] = []
    for name in ("train", "validation", "holdout"):
        split_snapshots = tuple(split_payloads[name])
        prepared.append(
            _PreparedDatasetSplit(
                metadata=_dataset_split_metadata(
                    name=name,
                    snapshots=split_snapshots,
                    source="chronological_baseline",
                    source_name="chronological-baseline",
                    labels=("baseline-chronological",),
                    score=None,
                    source_snapshot_path=str(Path(snapshot_path)),
                    source_event_path=(str(Path(event_path)) if event_path is not None else None),
                    btc_family_labels=("unknown",),
                    expiry_bucket="unknown",
                ),
                snapshots=split_snapshots,
            )
        )
    return tuple(prepared)


def _mined_prepared_splits(*, mining_report: WindowMiningReport) -> tuple[_PreparedDatasetSplit, ...]:
    prepared: list[_PreparedDatasetSplit] = []
    split_names = ("train", "validation", "holdout")
    for name, window in zip(split_names, mining_report.mined_windows, strict=False):
        split_snapshots = tuple(load_market_snapshots(window.snapshot_path))
        prepared.append(
            _PreparedDatasetSplit(
                metadata=_dataset_split_metadata(
                    name=name,
                    snapshots=split_snapshots,
                    source="mined_window",
                    source_name=window.name,
                    labels=window.labels,
                    score=window.score,
                    source_snapshot_path=window.snapshot_path,
                    source_event_path=window.event_path,
                    btc_family_labels=window.btc_family_labels,
                    expiry_bucket=window.expiry_bucket,
                ),
                snapshots=split_snapshots,
            )
        )
    return tuple(prepared)


def _dataset_split_metadata(
    *,
    name: str,
    snapshots: Sequence[MarketSnapshot],
    source: str,
    source_name: str,
    labels: tuple[str, ...],
    score: float | None,
    source_snapshot_path: str,
    source_event_path: str | None,
    btc_family_labels: tuple[str, ...],
    expiry_bucket: str,
) -> DatasetSplit:
    return DatasetSplit(
        name=name,
        snapshot_count=len(snapshots),
        started_at=(snapshots[0].timestamp if snapshots else None),
        ended_at=(snapshots[-1].timestamp if snapshots else None),
        source=source,
        source_name=source_name,
        labels=labels,
        score=score,
        source_snapshot_path=source_snapshot_path,
        source_event_path=source_event_path,
        btc_family_labels=btc_family_labels,
        expiry_bucket=expiry_bucket,
    )


def _default_candidates(*, classification: str, settings: BotSettings) -> tuple[ExperimentCandidate, ...]:
    if _has_strategy_config(settings, "phase2"):
        return _default_phase2_candidates(classification=classification, settings=settings)

    maker = _strategy_config(settings, "maker")
    spread = int(float(maker.get("min_spread_bps", 100)))
    quote_ttl = int(maker.get("quote_ttl_seconds", 10))
    failure_cooldown = int(maker.get("failure_cooldown_seconds", 0))
    requote = int(float(maker.get("min_requote_edge_improvement_bps", 50)))
    failure_reentry = int(float(maker.get("failure_reentry_edge_improvement_bps", requote)))
    replacement = int(float(settings.risk.open_order_replacement_min_edge_improvement_bps))
    surface = _strategy_config(settings, "surface")
    surface_min_edge = int(float(surface.get("min_edge_bps", 250)))
    surface_exit_edge = int(float(surface.get("exit_edge_bps", 75)))
    surface_stop_loss = int(float(surface.get("stop_loss_bps", 250)))

    if classification == "capacity-bound":
        return (
            ExperimentCandidate(
                name="maker_failure_plus20_requote_plus50",
                overrides=(
                    ("strategy.maker.failure_cooldown_seconds", failure_cooldown + 20),
                    ("strategy.maker.min_requote_edge_improvement_bps", requote + 50),
                ),
                rationale="Pause only churn-heavy markets longer and demand a stronger re-quote improvement before burning more order budget.",
            ),
            ExperimentCandidate(
                name="maker_spread_plus25_failure_plus20",
                overrides=(
                    ("strategy.maker.min_spread_bps", spread + 25),
                    ("strategy.maker.failure_cooldown_seconds", failure_cooldown + 20),
                ),
                rationale="Trim weak maker entries while pausing only the markets that just failed to convert.",
            ),
            ExperimentCandidate(
                name="maker_failure_plus20_reentry_plus50",
                overrides=(
                    ("strategy.maker.failure_cooldown_seconds", failure_cooldown + 20),
                    ("strategy.maker.failure_reentry_edge_improvement_bps", failure_reentry + 50),
                ),
                rationale="Keep failed markets on the bench unless the next quote is materially better than the failed one.",
            ),
        )
    if classification == "execution-bound":
        return (
            ExperimentCandidate(
                name="maker_ttl_plus5_failure_plus20",
                overrides=(
                    ("strategy.maker.quote_ttl_seconds", quote_ttl + 5),
                    ("strategy.maker.failure_cooldown_seconds", failure_cooldown + 20),
                ),
                rationale="Let quotes live slightly longer while backing off only the markets that just expired or got replaced.",
            ),
            ExperimentCandidate(
                name="maker_spread_plus25_failure_plus20",
                overrides=(
                    ("strategy.maker.min_spread_bps", spread + 25),
                    ("strategy.maker.failure_cooldown_seconds", failure_cooldown + 20),
                ),
                rationale="Require slightly better spread capture while keeping the cooldown local to churn-heavy markets.",
            ),
            ExperimentCandidate(
                name="maker_failure_plus20_requote_plus50",
                overrides=(
                    ("strategy.maker.failure_cooldown_seconds", failure_cooldown + 20),
                    ("strategy.maker.min_requote_edge_improvement_bps", requote + 50),
                    ("risk.open_order_replacement_min_edge_improvement_bps", replacement + 50),
                ),
                rationale="Raise the bar for revisiting a failed market and replacing live quotes, without suppressing unrelated markets.",
            ),
        )
    if classification == "data-bound":
        return ()
    return (
        ExperimentCandidate(
            name="surface_min_edge_plus50",
            overrides=(("strategy.surface.min_edge_bps", surface_min_edge + 50),),
            rationale="Tighten surface entries to reject marginal mispricings.",
        ),
        ExperimentCandidate(
            name="surface_exit_plus25_stop_loss_minus25",
            overrides=(
                ("strategy.surface.exit_edge_bps", surface_exit_edge + 25),
                ("strategy.surface.stop_loss_bps", max(25, surface_stop_loss - 25)),
            ),
            rationale="Test a faster exit threshold with a slightly tighter stop to improve closed-trade quality.",
        ),
        ExperimentCandidate(
            name="maker_inventory_skew_plus25bp_replace_plus50",
            overrides=(
                ("strategy.maker.inventory_skew_strength", round(float(maker.get("inventory_skew_strength", 0.5)) + 0.25, 2)),
                ("risk.open_order_replacement_min_edge_improvement_bps", replacement + 50),
            ),
            rationale="Reduce inventory drag without reopening easy order replacement.",
        ),
    )


def _default_phase2_candidates(*, classification: str, settings: BotSettings) -> tuple[ExperimentCandidate, ...]:
    phase2 = _strategy_config(settings, "phase2")
    maker_ttl = int(phase2.get("maker_quote_ttl_seconds", 60))
    resolution_ttl = int(phase2.get("resolution_maker_quote_ttl_seconds", 180))
    maker_edge = float(phase2.get("maker_min_edge_bps", 100.0))
    resolution_edge = float(phase2.get("resolution_maker_min_edge_bps", 150.0))
    maker_aggressiveness = float(phase2.get("maker_aggressiveness", 1.0))
    taker_premium = float(phase2.get("taker_max_entry_premium_bps", 750.0))
    entry_cooldown = float(phase2.get("entry_repost_cooldown_seconds", 120.0))

    if classification == "execution-bound":
        return (
            ExperimentCandidate(
                name="phase2_resolution_ttl_plus45",
                overrides=(
                    ("strategy.phase2.resolution_maker_quote_ttl_seconds", resolution_ttl + 45),
                    ("strategy.phase2.entry_repost_cooldown_seconds", max(15.0, entry_cooldown + 15.0)),
                ),
                rationale="Let long-horizon maker quotes rest longer before expiring, while backing off slightly after a miss.",
            ),
            ExperimentCandidate(
                name="phase2_resolution_edge_minus25_ttl_plus45",
                overrides=(
                    ("strategy.phase2.resolution_maker_min_edge_bps", max(75.0, resolution_edge - 25.0)),
                    ("strategy.phase2.resolution_maker_quote_ttl_seconds", resolution_ttl + 45),
                ),
                rationale="Probe whether the family is under-trading thin but still positive resolution edges that need more time on the book.",
            ),
            ExperimentCandidate(
                name="phase2_maker_aggr_plus075_ttl_plus15",
                overrides=(
                    ("strategy.phase2.maker_aggressiveness", round(maker_aggressiveness + 0.75, 2)),
                    ("strategy.phase2.maker_quote_ttl_seconds", maker_ttl + 15),
                ),
                rationale="Make passive quotes one notch more aggressive while keeping them non-crossing and letting them rest slightly longer.",
            ),
            ExperimentCandidate(
                name="phase2_resolution_edge_minus25_aggr_plus075_ttl_plus45",
                overrides=(
                    ("strategy.phase2.resolution_maker_min_edge_bps", max(75.0, resolution_edge - 25.0)),
                    ("strategy.phase2.resolution_maker_quote_ttl_seconds", resolution_ttl + 45),
                    ("strategy.phase2.maker_aggressiveness", round(maker_aggressiveness + 0.75, 2)),
                ),
                rationale="Combine slightly thinner resolution entry gating with longer-lived, more aggressive passive quotes to test whether the family is stalled just inside the spread.",
            ),
        )
    return (
        ExperimentCandidate(
            name="phase2_resolution_edge_plus15",
            overrides=(("strategy.phase2.resolution_maker_min_edge_bps", resolution_edge + 15.0),),
            rationale="Tighten long-horizon phase2 entries when closed-trade quality, not fill scarcity, is the problem.",
        ),
        ExperimentCandidate(
            name="phase2_maker_edge_plus10",
            overrides=(("strategy.phase2.maker_min_edge_bps", maker_edge + 10.0),),
            rationale="Trim marginal phase2 entries before widening any execution route.",
        ),
        ExperimentCandidate(
            name="phase2_taker_premium_minus25",
            overrides=(("strategy.phase2.taker_max_entry_premium_bps", max(25.0, taker_premium - 25.0)),),
            rationale="Reduce phase2 taker aggressiveness when alpha quality is the issue.",
        ),
    )


def _apply_overrides(settings: BotSettings, overrides: tuple[tuple[str, Any], ...]) -> BotSettings:
    updated = settings.model_copy(deep=True)
    for parameter, value in overrides:
        parts = parameter.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid parameter override: {parameter}")
        if parts[0] == "strategy" and len(parts) == 3:
            strategy_name = parts[1]
            field_name = parts[2]
            category_config = _category_config_for_strategy(updated, strategy_name)
            strategy_map = dict(category_config.strategy)
            strategy_values = dict(strategy_map.get(strategy_name, {}))
            strategy_values[field_name] = value
            strategy_map[strategy_name] = strategy_values
            category_config.strategy = strategy_map
            continue
        if len(parts) != 2:
            raise ValueError(f"Unsupported parameter override path: {parameter}")
        section = getattr(updated, parts[0], None)
        if section is None or not hasattr(section, parts[1]):
            raise ValueError(f"Unknown parameter override path: {parameter}")
        setattr(section, parts[1], value)
    return updated


def _validate_overrides(overrides: tuple[tuple[str, Any], ...], tunable_parameters: tuple[str, ...]) -> None:
    allowed = set(tunable_parameters)
    for parameter, _ in overrides:
        if parameter not in allowed:
            raise ValueError(f"Override is outside the tunable whitelist: {parameter}")


def _category_config_for_strategy(settings: BotSettings, strategy_name: str) -> CategoryRuntimeConfig:
    for category_config in settings.category_configs.values():
        if strategy_name in category_config.strategy:
            return category_config
        suffix = f".{strategy_name}"
        if any(strategy_id.endswith(suffix) for strategy_id in category_config.enabled_strategies):
            return category_config
    raise ValueError(f"Strategy config not found: {strategy_name}")


def _strategy_config(settings: BotSettings, strategy_name: str) -> dict[str, Any]:
    category_config = _category_config_for_strategy(settings, strategy_name)
    return dict(category_config.strategy.get(strategy_name, {}))


def _has_strategy_config(settings: BotSettings, strategy_name: str) -> bool:
    try:
        _category_config_for_strategy(settings, strategy_name)
    except ValueError:
        return False
    return True


def _select_finalists(train_results: list[ExperimentRunArtifact], finalist_count: int = 2) -> tuple[str, ...]:
    baseline = next(item for item in train_results if item.candidate_name == "baseline")
    ranked = sorted(
        train_results,
        key=lambda item: (
            -_promotion_score(candidate=item, baseline=baseline),
            -item.score,
            item.candidate_name,
        ),
    )
    finalists = ["baseline"]
    for artifact in ranked:
        if artifact.candidate_name == "baseline":
            continue
        finalists.append(artifact.candidate_name)
        if len(finalists) >= finalist_count + 1:
            break
    return tuple(finalists)


def _pick_validation_winner(validation_results: list[ExperimentRunArtifact]) -> tuple[str, str]:
    baseline = next(item for item in validation_results if item.candidate_name == "baseline")
    challengers = [
        item
        for item in validation_results
        if item.candidate_name != "baseline" and _preserves_activity(candidate=item, baseline=baseline)
    ]
    if not challengers:
        return "baseline", "No non-baseline candidate survived validation without collapsing activity."
    winner = max(
        challengers,
        key=lambda item: (
            _promotion_score(candidate=item, baseline=baseline),
            item.score,
            item.orders_filled,
            -item.cancel_rate,
            item.candidate_name,
        ),
    )
    if _promotion_score(candidate=winner, baseline=baseline) <= _promotion_score(candidate=baseline, baseline=baseline):
        return "baseline", "No non-baseline candidate beat the baseline on validation promotion score."
    return winner.candidate_name, f"{winner.candidate_name} beat the baseline on validation promotion score."


def _promote_winner(
    *,
    validation_winner: str,
    validation_reason: str,
    holdout_results: list[ExperimentRunArtifact],
) -> tuple[str, str]:
    if validation_winner == "baseline":
        return "baseline", validation_reason
    baseline_holdout = next(item for item in holdout_results if item.candidate_name == "baseline")
    candidate_holdout = next(item for item in holdout_results if item.candidate_name == validation_winner)
    if not _preserves_activity(candidate=candidate_holdout, baseline=baseline_holdout):
        return (
            "baseline",
            f"{validation_winner} won validation but collapsed activity on holdout.",
        )
    if _promotion_score(candidate=candidate_holdout, baseline=baseline_holdout) <= _promotion_score(
        candidate=baseline_holdout,
        baseline=baseline_holdout,
    ):
        return (
            "baseline",
            f"{validation_winner} won validation but failed to beat baseline on holdout promotion score.",
        )
    return validation_winner, f"{validation_winner} beat baseline on validation and holdout."


def _render_fixed_window_report(report: FixedWindowExperimentReport) -> str:
    lines = [
        "# Fixed Window Experiment Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- mode: {report.mode}",
        f"- snapshot_path: {report.snapshot_path}",
        f"- output_dir: {report.output_dir}",
        f"- window_selection_mode: {report.window_selection_mode}",
        f"- window_selection_reason: {report.window_selection_reason}",
        f"- mining_summary_path: {report.mining_summary_path or ''}",
        f"- baseline_classification: {report.baseline_classification}",
        f"- validation_winner: {report.validation_winner}",
        f"- promoted_winner: {report.promoted_winner}",
        f"- decision_reason: {report.decision_reason}",
        "",
        "## Objective",
        "",
        f"- {report.rewritten_objective}",
        "",
        "## Dataset Split",
        "",
    ]
    for split in report.dataset_splits:
        lines.append(
            f"- {split.name}: {split.snapshot_count} snapshots ({_format_dt(split.started_at)} -> {_format_dt(split.ended_at)}), "
            f"source={split.source}, source_name={split.source_name}, score={_format_optional_score(split.score)}, labels={','.join(split.labels) or 'none'}, "
            f"btc_family={'+'.join(split.btc_family_labels) or 'unknown'}, expiry_bucket={split.expiry_bucket}"
        )
        lines.append(f"  source_snapshot_path: {split.source_snapshot_path}")
        lines.append(f"  source_event_path: {split.source_event_path or ''}")

    lines.extend(
        [
            "",
            "## Locked Parameters",
            "",
        ]
    )
    lines.extend(f"- {parameter}" for parameter in report.locked_parameters)
    lines.extend(
        [
            "",
            "## Tunable Whitelist",
            "",
        ]
    )
    lines.extend(f"- {parameter}" for parameter in report.tunable_parameters)
    lines.extend(
        [
            "",
            "## Score Formula",
            "",
            "```text",
            report.score_formula.rstrip(),
            "```",
            "",
            "## Experiment Matrix",
            "",
        ]
    )
    for candidate in report.experiment_matrix:
        lines.append(f"- {candidate.name}: {_format_overrides(candidate.overrides)}")
        lines.append(f"  rationale: {candidate.rationale}")
    lines.extend(
        [
            "",
            "## Train",
            "",
        ]
    )
    lines.extend(_render_result_lines(report.train_results))
    lines.extend(
        [
            "",
            "## Validation",
            "",
        ]
    )
    lines.extend(_render_result_lines(report.validation_results))
    lines.extend(
        [
            "",
            "## Holdout",
            "",
        ]
    )
    lines.extend(_render_result_lines(report.holdout_results))
    return "\n".join(lines)


def _render_result_lines(results: tuple[ExperimentRunArtifact, ...]) -> list[str]:
    lines: list[str] = []
    baseline = next((item for item in results if item.candidate_name == "baseline"), None)
    if baseline is None and results:
        baseline = results[0]
    for result in sorted(
        results,
        key=lambda item: (
            -_promotion_score(candidate=item, baseline=baseline),
            -item.score,
            item.candidate_name,
        ),
    ):
        lines.append(
            f"- {result.candidate_name}: score={result.score:.4f}, promotion_score={_promotion_score(candidate=result, baseline=baseline):.4f}, "
            f"classification={result.classification}, useful_submissions={result.useful_submissions}, "
            f"submission_coverage={result.submission_coverage:.4f}, submitted={result.orders_submitted}, filled={result.orders_filled}, expired={result.orders_expired}, "
            f"canceled={result.orders_canceled}, rejected={result.orders_rejected}, fill_rate={result.fill_rate:.4f}, "
            f"cancel_rate={result.cancel_rate:.4f}"
        )
        lines.append(f"  metrics_path: {result.metrics_path}")
        lines.append(f"  event_path: {result.event_path}")
        lines.append(f"  autoresearch_path: {result.autoresearch_path}")
        if result.overrides:
            lines.append(f"  overrides: {_format_overrides(result.overrides)}")
        if result.dominant_rejection_reasons:
            reason, count = result.dominant_rejection_reasons[0]
            lines.append(f"  dominant_rejection_reason: {reason} ({count})")
    if not lines:
        lines.append("- none")
    return lines


def _resolve_output_dir(output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        resolved = Path(output_dir)
    else:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        resolved = Path("data/runtime") / f"fixed-window-experiments-{timestamp}"
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _chronological_snapshots(snapshots: list[MarketSnapshot]) -> list[MarketSnapshot]:
    indexed = list(enumerate(snapshots))
    indexed.sort(key=lambda item: (item[1].timestamp, item[0]))
    return [snapshot for _, snapshot in indexed]


def _preserves_activity(*, candidate: ExperimentRunArtifact, baseline: ExperimentRunArtifact) -> bool:
    if baseline.orders_submitted <= 0:
        return True
    if candidate.orders_filled > baseline.orders_filled:
        return True
    minimum_submissions = max(1, (baseline.orders_submitted + 1) // 2)
    return candidate.orders_submitted >= minimum_submissions


def _promotion_score(*, candidate: ExperimentRunArtifact, baseline: ExperimentRunArtifact | None) -> float:
    if baseline is None:
        return candidate.score + (3.0 * candidate.useful_submissions)
    activity_gap = max(0, baseline.orders_submitted - candidate.orders_submitted)
    stalled_penalty = 1.0 if baseline.orders_submitted > 0 and candidate.orders_submitted == 0 else 0.0
    return candidate.score + (3.0 * candidate.useful_submissions) - (2.0 * activity_gap) - stalled_penalty


def _slug(name: str) -> str:
    letters = [ch.lower() if ch.isalnum() else "-" for ch in name]
    slug = "".join(letters)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "candidate"


def _format_overrides(overrides: tuple[tuple[str, Any], ...]) -> str:
    if not overrides:
        return "none"
    return ", ".join(f"{parameter}={value}" for parameter, value in overrides)


def _format_score_line(results: tuple[ExperimentRunArtifact, ...]) -> str:
    if not results:
        return ""
    ranked = sorted(results, key=lambda item: item.candidate_name)
    return ",".join(f"{item.candidate_name}:{item.score:.4f}" for item in ranked)


def _format_promotion_score_line(results: tuple[ExperimentRunArtifact, ...]) -> str:
    if not results:
        return ""
    baseline = next((item for item in results if item.candidate_name == "baseline"), None)
    ranked = sorted(results, key=lambda item: item.candidate_name)
    return ",".join(
        f"{item.candidate_name}:{_promotion_score(candidate=item, baseline=baseline):.4f}"
        for item in ranked
    )


def _format_dt(value: datetime | None) -> str:
    return "" if value is None else value.isoformat()


def _format_optional_score(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def _format_split_sources(splits: tuple[DatasetSplit, ...]) -> str:
    if not splits:
        return ""
    return ",".join(
        f"{split.name}:{split.source}:{split.source_name}:{_format_optional_score(split.score)}:"
        f"{'+'.join(split.labels) or 'none'}:{'+'.join(split.btc_family_labels) or 'unknown'}:{split.expiry_bucket}"
        for split in splits
    )
