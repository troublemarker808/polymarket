"""Promotion readiness checks for crypto runtime stages."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal

from pm_bot.config.loader import load_settings_from_directory
from pm_bot.core.types import RuntimeMode
from pm_bot.execution import describe_execution_configuration
from pm_bot.runtime.state import RuntimeStatus, runtime_state_from_dict


PromotionStage = Literal["paper_to_sync_shadow", "sync_shadow_to_small_live_baseline"]


@dataclass(slots=True, frozen=True)
class PromotionReadinessReport:
    stage: PromotionStage
    ready: bool
    source_config_dir: str
    target_config_dir: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, str]
    rollback_triggers: tuple[str, ...]
    escalation_actions: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PromotionQuantitativeThresholds:
    min_processed_snapshots: int
    min_event_lines: int
    min_orders_submitted: int
    max_submission_count_drift: int = 1


def validate_promotion_readiness(
    *,
    stage: PromotionStage,
    source_config_dir: str | Path,
    target_config_dir: str | Path,
    metrics_path: str | Path,
    state_path: str | Path,
    event_path: str | Path,
    shadow_metrics_path: str | Path | None = None,
    shadow_state_path: str | Path | None = None,
    shadow_event_path: str | Path | None = None,
    note_path: str | Path | None = None,
) -> PromotionReadinessReport:
    blockers: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}
    target_profile_name = Path(target_config_dir).name.lower()
    source_profile_name = Path(source_config_dir).name.lower()

    source_dir = str(Path(source_config_dir))
    target_dir = str(Path(target_config_dir))
    source_settings = load_settings_from_directory(source_config_dir)
    target_settings = load_settings_from_directory(target_config_dir)
    source_execution = describe_execution_configuration(settings=source_settings, env={})
    target_execution = describe_execution_configuration(settings=target_settings, env={})
    metrics = _load_json(metrics_path)
    state = runtime_state_from_dict(_load_json(state_path))
    event_lines = _count_nonempty_lines(event_path)
    thresholds = _quantitative_thresholds(stage)

    _require(
        condition=source_settings.app.mode == RuntimeMode.PAPER if stage == "paper_to_sync_shadow" else source_settings.app.mode == RuntimeMode.LIVE,
        checks=checks,
        key="source_mode",
        ok_value=source_settings.app.mode.value,
        fail_value=f"unexpected:{source_settings.app.mode.value}",
        blockers=blockers,
        blocker_message=(
            "Source profile must be paper mode for paper_to_sync_shadow."
            if stage == "paper_to_sync_shadow"
            else "Source profile must be live mode for sync_shadow_to_small_live_baseline."
        ),
    )
    _require(
        condition=target_settings.app.mode == RuntimeMode.LIVE,
        checks=checks,
        key="target_mode",
        ok_value=target_settings.app.mode.value,
        fail_value=f"unexpected:{target_settings.app.mode.value}",
        blockers=blockers,
        blocker_message="Target profile must be live mode.",
    )
    _require(
        condition=not bool(source_execution.get("allow_live_orders", False)) if stage == "paper_to_sync_shadow" else bool(source_execution.get("allow_live_orders", False)),
        checks=checks,
        key="source_live_orders",
        ok_value=str(source_execution.get("allow_live_orders", False)).lower(),
        fail_value=str(source_execution.get("allow_live_orders", False)).lower(),
        blockers=blockers,
        blocker_message=(
            "Source paper profile must keep live orders disabled."
            if stage == "paper_to_sync_shadow"
            else "Source sync-shadow profile must keep live orders enabled."
        ),
    )
    _require(
        condition=bool(target_execution.get("allow_live_orders", False)),
        checks=checks,
        key="target_live_orders",
        ok_value=str(target_execution.get("allow_live_orders", False)).lower(),
        fail_value=str(target_execution.get("allow_live_orders", False)).lower(),
        blockers=blockers,
        blocker_message="Target live profile must allow live orders.",
    )
    _require(
        condition=bool(target_execution.get("ready", False)),
        checks=checks,
        key="target_live_ready",
        ok_value=str(target_execution.get("ready", False)).lower(),
        fail_value=str(target_execution.get("ready", False)).lower(),
        blockers=blockers,
        blocker_message="Target live profile is not execution-ready.",
    )
    _require(
        condition=("shadow" in target_profile_name if stage == "paper_to_sync_shadow" else "promotion" in target_profile_name and "baseline" not in target_profile_name),
        checks=checks,
        key="target_profile_role",
        ok_value=target_profile_name,
        fail_value=target_profile_name,
        blockers=blockers,
        blocker_message=(
            "Target profile for paper_to_sync_shadow must be a shadow profile."
            if stage == "paper_to_sync_shadow"
            else "Target profile for sync_shadow_to_small_live_baseline must be a dedicated promotion profile, not the baseline profile."
        ),
    )
    _warn(
        condition=("baseline" in source_profile_name if stage == "paper_to_sync_shadow" else "shadow" in source_profile_name),
        checks=checks,
        key="source_profile_role",
        ok_value=source_profile_name,
        warn_value=source_profile_name,
        warnings=warnings,
        warning_message="Source profile naming does not clearly communicate the current promotion stage.",
    )
    _require(
        condition=target_settings.risk.manual_resume_required,
        checks=checks,
        key="target_manual_resume_required",
        ok_value=str(target_settings.risk.manual_resume_required).lower(),
        fail_value=str(target_settings.risk.manual_resume_required).lower(),
        blockers=blockers,
        blocker_message="Target profile must require manual resume after a halt.",
    )
    _require(
        condition=target_settings.risk.halt_on_data_source_failure,
        checks=checks,
        key="target_halt_on_data_source_failure",
        ok_value=str(target_settings.risk.halt_on_data_source_failure).lower(),
        fail_value=str(target_settings.risk.halt_on_data_source_failure).lower(),
        blockers=blockers,
        blocker_message="Target profile must halt on data-source failure.",
    )
    _require(
        condition=target_settings.risk.kill_switch_on_stale_data_seconds <= 30,
        checks=checks,
        key="target_stale_data_kill_switch_seconds",
        ok_value=str(target_settings.risk.kill_switch_on_stale_data_seconds),
        fail_value=str(target_settings.risk.kill_switch_on_stale_data_seconds),
        blockers=blockers,
        blocker_message="Target profile stale-data kill switch is too loose.",
    )
    _require(
        condition=int(metrics.get("processed_snapshots", 0)) >= thresholds.min_processed_snapshots,
        checks=checks,
        key="processed_snapshots",
        ok_value=str(metrics.get("processed_snapshots", 0)),
        fail_value=str(metrics.get("processed_snapshots", 0)),
        blockers=blockers,
        blocker_message=(
            "Source runtime artifacts did not meet the minimum snapshot threshold "
            f"({thresholds.min_processed_snapshots})."
        ),
    )
    _require(
        condition=event_lines >= thresholds.min_event_lines,
        checks=checks,
        key="event_lines",
        ok_value=str(event_lines),
        fail_value=str(event_lines),
        blockers=blockers,
        blocker_message=(
            "Source event artifact did not meet the minimum event-line threshold "
            f"({thresholds.min_event_lines})."
        ),
    )
    _require(
        condition=state.status != RuntimeStatus.HALTED,
        checks=checks,
        key="source_status",
        ok_value=state.status.value,
        fail_value=state.status.value,
        blockers=blockers,
        blocker_message=f"Source runtime is halted with reason={state.halt_reason.value}.",
    )
    _require(
        condition=state.consecutive_data_failures == 0,
        checks=checks,
        key="source_data_failures",
        ok_value=str(state.consecutive_data_failures),
        fail_value=str(state.consecutive_data_failures),
        blockers=blockers,
        blocker_message="Source runtime state still shows unresolved data failures.",
    )
    _require(
        condition=int(metrics.get("market_data_failures", 0)) == 0,
        checks=checks,
        key="source_market_data_failures",
        ok_value=str(metrics.get("market_data_failures", 0)),
        fail_value=str(metrics.get("market_data_failures", 0)),
        blockers=blockers,
        blocker_message="Source runtime metrics still show market-data failures in the validation window.",
    )
    _warn(
        condition=len(state.pending_orders) == 0,
        checks=checks,
        key="source_pending_orders",
        ok_value="0",
        warn_value=str(len(state.pending_orders)),
        warnings=warnings,
        warning_message="Source runtime still has pending orders; handoff evidence is less clean.",
    )
    _warn(
        condition=len(state.open_positions) == 0,
        checks=checks,
        key="source_open_positions",
        ok_value="0",
        warn_value=str(len(state.open_positions)),
        warnings=warnings,
        warning_message="Source runtime still has open positions; handoff evidence is less clean.",
    )
    if stage == "paper_to_sync_shadow":
        _warn(
            condition=note_path is not None and Path(note_path).exists(),
            checks=checks,
            key="operator_note",
            ok_value="present",
            warn_value="missing",
            warnings=warnings,
            warning_message="Operator note is missing for the paper handoff window.",
        )
    else:
        _require(
            condition=note_path is not None and Path(note_path).exists(),
            checks=checks,
            key="operator_note",
            ok_value="present",
            fail_value="missing",
            blockers=blockers,
            blocker_message="Operator note is required before promoting from sync-shadow to small-live.",
        )

    if stage == "paper_to_sync_shadow":
        _warn(
            condition=target_settings.trading.default_order_notional <= 1.1,
            checks=checks,
            key="target_default_order_notional",
            ok_value=str(target_settings.trading.default_order_notional),
            warn_value=str(target_settings.trading.default_order_notional),
            warnings=warnings,
            warning_message="Shadow promotion profile notional is higher than the micro-order baseline target.",
        )
        _require(
            condition=int(metrics.get("orders_submitted", 0)) >= thresholds.min_orders_submitted,
            checks=checks,
            key="paper_activity",
            ok_value=f"signals={metrics.get('signals_generated', 0)},orders={metrics.get('orders_submitted', 0)}",
            fail_value=f"signals={metrics.get('signals_generated', 0)},orders={metrics.get('orders_submitted', 0)}",
            blockers=blockers,
            blocker_message=(
                "Paper artifacts do not have enough submitted orders for promotion evidence "
                f"({thresholds.min_orders_submitted} required)."
            ),
        )
    else:
        if shadow_metrics_path is None or shadow_state_path is None or shadow_event_path is None:
            blockers.append("Sync-shadow to small-live validation requires shadow metrics/state/event artifacts.")
            checks["shadow_artifacts"] = "missing"
        else:
            shadow_metrics = _load_json(shadow_metrics_path)
            shadow_state = runtime_state_from_dict(_load_json(shadow_state_path))
            shadow_event_lines = _count_nonempty_lines(shadow_event_path)
            _require(
                condition=int(shadow_metrics.get("processed_snapshots", 0)) >= thresholds.min_processed_snapshots,
                checks=checks,
                key="shadow_processed_snapshots",
                ok_value=str(shadow_metrics.get("processed_snapshots", 0)),
                fail_value=str(shadow_metrics.get("processed_snapshots", 0)),
                blockers=blockers,
                blocker_message=(
                    "Shadow runtime artifacts did not meet the minimum snapshot threshold "
                    f"({thresholds.min_processed_snapshots})."
                ),
            )
            _require(
                condition=shadow_event_lines >= thresholds.min_event_lines,
                checks=checks,
                key="shadow_event_lines",
                ok_value=str(shadow_event_lines),
                fail_value=str(shadow_event_lines),
                blockers=blockers,
                blocker_message=(
                    "Shadow event artifact did not meet the minimum event-line threshold "
                    f"({thresholds.min_event_lines})."
                ),
            )
            _require(
                condition=shadow_state.status != RuntimeStatus.HALTED,
                checks=checks,
                key="shadow_status",
                ok_value=shadow_state.status.value,
                fail_value=shadow_state.status.value,
                blockers=blockers,
                blocker_message=f"Shadow runtime is halted with reason={shadow_state.halt_reason.value}.",
            )
            _require(
                condition=(
                    int(metrics.get("orders_submitted", 0)) >= thresholds.min_orders_submitted
                    and int(shadow_metrics.get("orders_submitted", 0)) >= thresholds.min_orders_submitted
                ),
                checks=checks,
                key="paired_submissions",
                ok_value=f"live={metrics.get('orders_submitted', 0)},shadow={shadow_metrics.get('orders_submitted', 0)}",
                fail_value=f"live={metrics.get('orders_submitted', 0)},shadow={shadow_metrics.get('orders_submitted', 0)}",
                blockers=blockers,
                blocker_message=(
                    "Sync-shadow artifacts do not meet the minimum paired-submission threshold "
                    f"({thresholds.min_orders_submitted} per side required)."
                ),
            )
            _warn(
                condition=(
                    abs(int(metrics.get("orders_submitted", 0)) - int(shadow_metrics.get("orders_submitted", 0)))
                    <= thresholds.max_submission_count_drift
                ),
                checks=checks,
                key="submission_parity",
                ok_value="within_1",
                warn_value=f"live={metrics.get('orders_submitted', 0)},shadow={shadow_metrics.get('orders_submitted', 0)}",
                warnings=warnings,
                warning_message="Live and shadow submission counts are drifting.",
            )
            _require(
                condition=int(shadow_metrics.get("market_data_failures", 0)) == 0,
                checks=checks,
                key="shadow_market_data_failures",
                ok_value=str(shadow_metrics.get("market_data_failures", 0)),
                fail_value=str(shadow_metrics.get("market_data_failures", 0)),
                blockers=blockers,
                blocker_message="Shadow runtime metrics still show market-data failures in the validation window.",
            )

        _require(
            condition=target_settings.trading.max_notional_per_category <= 2.2,
            checks=checks,
            key="target_max_notional_per_category",
            ok_value=str(target_settings.trading.max_notional_per_category),
            fail_value=str(target_settings.trading.max_notional_per_category),
            blockers=blockers,
            blocker_message="Promotion live profile category notional cap is too loose.",
        )
        _require(
            condition=target_settings.trading.max_notional_per_thesis_group <= 1.1,
            checks=checks,
            key="target_max_notional_per_thesis_group",
            ok_value=str(target_settings.trading.max_notional_per_thesis_group),
            fail_value=str(target_settings.trading.max_notional_per_thesis_group),
            blockers=blockers,
            blocker_message="Promotion live profile thesis-group notional cap is too loose.",
        )
        _require(
            condition=target_settings.trading.max_notional_per_underlying_group <= 1.6,
            checks=checks,
            key="target_max_notional_per_underlying_group",
            ok_value=str(target_settings.trading.max_notional_per_underlying_group),
            fail_value=str(target_settings.trading.max_notional_per_underlying_group),
            blockers=blockers,
            blocker_message="Promotion live profile underlying-group notional cap is too loose.",
        )
        _require(
            condition=target_settings.risk.max_daily_drawdown_pct <= 20.0,
            checks=checks,
            key="target_max_daily_drawdown_pct",
            ok_value=str(target_settings.risk.max_daily_drawdown_pct),
            fail_value=str(target_settings.risk.max_daily_drawdown_pct),
            blockers=blockers,
            blocker_message="Promotion live profile drawdown cap is too loose.",
        )
        _require(
            condition=target_settings.risk.max_consecutive_losses <= 10,
            checks=checks,
            key="target_max_consecutive_losses",
            ok_value=str(target_settings.risk.max_consecutive_losses),
            fail_value=str(target_settings.risk.max_consecutive_losses),
            blockers=blockers,
            blocker_message="Promotion live profile consecutive-loss cap is too loose.",
        )
        _require(
            condition=target_settings.trading.daily_order_hard_limit <= 60,
            checks=checks,
            key="target_daily_order_hard_limit",
            ok_value=str(target_settings.trading.daily_order_hard_limit),
            fail_value=str(target_settings.trading.daily_order_hard_limit),
            blockers=blockers,
            blocker_message="Promotion live profile daily hard order limit is too loose.",
        )

    return PromotionReadinessReport(
        stage=stage,
        ready=not blockers,
        source_config_dir=source_dir,
        target_config_dir=target_dir,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        checks=checks,
        rollback_triggers=_rollback_triggers(stage),
        escalation_actions=_escalation_actions(stage),
    )


def format_promotion_readiness_report(report: PromotionReadinessReport) -> str:
    lines = [
        "# Promotion Readiness",
        "",
        f"- stage: {report.stage}",
        f"- ready: {str(report.ready).lower()}",
        f"- source_config_dir: {report.source_config_dir}",
        f"- target_config_dir: {report.target_config_dir}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(report.checks.items()))
    lines.extend(["", "## Blockers", ""])
    if report.blockers:
        lines.extend(f"- {item}" for item in report.blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {item}" for item in report.warnings)
    else:
        lines.append("- none")
    lines.extend(["", "## Rollback Triggers", ""])
    lines.extend(f"- {item}" for item in report.rollback_triggers)
    lines.extend(["", "## Escalation Actions", ""])
    lines.extend(f"- {item}" for item in report.escalation_actions)
    return "\n".join(lines) + "\n"


def _load_json(path: str | Path) -> dict[str, Any]:
    return dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _count_nonempty_lines(path: str | Path) -> int:
    return sum(1 for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip())


def _require(
    *,
    condition: bool,
    checks: dict[str, str],
    key: str,
    ok_value: str,
    fail_value: str,
    blockers: list[str],
    blocker_message: str,
) -> None:
    checks[key] = ok_value if condition else fail_value
    if not condition:
        blockers.append(blocker_message)


def _warn(
    *,
    condition: bool,
    checks: dict[str, str],
    key: str,
    ok_value: str,
    warn_value: str,
    warnings: list[str],
    warning_message: str,
) -> None:
    checks[key] = ok_value if condition else warn_value
    if not condition:
        warnings.append(warning_message)


def _rollback_triggers(stage: PromotionStage) -> tuple[str, ...]:
    if stage == "paper_to_sync_shadow":
        return (
            "halt_reason is not none on the source paper runtime",
            "market_data_failures or consecutive_data_failures become non-zero during promotion sampling",
            "sync-shadow target profile loses execution readiness",
        )
    return (
        "live or shadow runtime halts for stale_data or data_source_failure",
        "live and shadow submission counts drift materially during paired sampling",
        "open positions or pending orders remain after the validation window closes",
    )


def _escalation_actions(stage: PromotionStage) -> tuple[str, ...]:
    if stage == "paper_to_sync_shadow":
        return (
            "re-run bounded paper validation and keep live disabled until blockers clear",
            "inspect paper metrics/state/event artifacts before opening sync-shadow",
        )
    if stage == "sync_shadow_to_small_live_baseline":
        return (
            "pause promotion and continue only on sync-shadow until blockers clear",
            "review paired live/shadow artifacts and operator note before any new live window",
            "require manual resume after any halt before another small-live attempt",
        )
    return ()


def _quantitative_thresholds(stage: PromotionStage) -> PromotionQuantitativeThresholds:
    if stage == "paper_to_sync_shadow":
        return PromotionQuantitativeThresholds(
            min_processed_snapshots=10,
            min_event_lines=5,
            min_orders_submitted=1,
        )
    return PromotionQuantitativeThresholds(
        min_processed_snapshots=10,
        min_event_lines=5,
        min_orders_submitted=2,
        max_submission_count_drift=1,
    )
