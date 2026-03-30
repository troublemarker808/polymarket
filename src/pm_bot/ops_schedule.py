"""Scheduled multi-board ops bundle generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import shutil
from pathlib import Path

from pm_bot.multi_board_ops import (
    build_multi_board_ops_report_from_specs,
    default_multi_board_input_specs,
    write_multi_board_ops_report,
)
from pm_bot.ops_automation import build_daily_ops_bundle_from_specs, write_daily_ops_bundle
from pm_bot.ops_decision import build_ops_decision, write_ops_decision
from pm_bot.ops_followup import build_ops_followup_queue, write_ops_followup_queue
from pm_bot.ops_history import build_ops_history_report, write_ops_history_report
from pm_bot.ops_console import build_unified_ops_console_from_specs, write_unified_ops_console
from pm_bot.ops_one_page import build_ops_one_page, write_ops_one_page
from pm_bot.promotion_evidence import build_promotion_evidence_report, write_promotion_evidence_report
from pm_bot.runtime.state import DashboardState, HaltReason, RuntimeStatus
from pm_bot.strategy_loop_decision import build_strategy_loop_decision, write_strategy_loop_decision
from pm_bot.strategy_loop_history import build_strategy_loop_history_report, write_strategy_loop_history_report
from pm_bot.strategy_cycle_package import build_strategy_cycle_package, write_strategy_cycle_package


@dataclass(slots=True, frozen=True)
class ScheduledOpsArtifacts:
    run_id: str
    run_date: str
    output_dir: str
    multi_board_report_path: str
    daily_bundle_path: str
    ops_console_path: str
    ops_history_path: str
    ops_one_page_path: str
    ops_followup_queue_path: str
    ops_decision_path: str
    promotion_evidence_path: str | None
    strategy_loop_history_path: str | None
    strategy_loop_decision_path: str | None
    strategy_cycle_package_path: str | None
    latest_multi_board_report_path: str
    latest_daily_bundle_path: str
    latest_ops_console_path: str
    latest_ops_history_path: str
    latest_ops_one_page_path: str
    latest_ops_followup_queue_path: str
    latest_ops_decision_path: str
    latest_promotion_evidence_path: str | None
    latest_strategy_loop_history_path: str | None
    latest_strategy_loop_decision_path: str | None
    latest_strategy_cycle_package_path: str | None


def run_scheduled_ops_bundle(
    *,
    crypto_operator_summary_path: str | Path,
    sports_scorecard_path: str | Path,
    weather_scorecard_path: str | Path,
    crypto_evidence_path: str | Path | None = None,
    promotion_evidence_stage: str | None = None,
    promotion_evidence_bundle_paths: list[str | Path] | None = None,
    strategy_feedback_loop_paths: list[str | Path] | None = None,
    output_root: str | Path,
    run_id: str | None = None,
    now: datetime | None = None,
    runtime_rendered: str | None = None,
) -> ScheduledOpsArtifacts:
    timestamp = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    effective_run_id = run_id or timestamp.strftime("%Y%m%dT%H%M%SZ")
    run_date = timestamp.strftime("%Y-%m-%d")
    target_dir = Path(output_root) / run_date / effective_run_id
    target_dir.mkdir(parents=True, exist_ok=True)

    specs = default_multi_board_input_specs(
        crypto_operator_summary_path=crypto_operator_summary_path,
        sports_scorecard_path=sports_scorecard_path,
        weather_scorecard_path=weather_scorecard_path,
        crypto_evidence_path=crypto_evidence_path,
    )
    multi_board_report = build_multi_board_ops_report_from_specs(specs)
    daily_bundle = build_daily_ops_bundle_from_specs(specs)
    ops_console = build_unified_ops_console_from_specs(specs)

    multi_board_path = target_dir / "multi-board-ops.md"
    daily_bundle_path = target_dir / "daily-ops-bundle.md"
    ops_console_path = target_dir / "ops-console.md"
    write_multi_board_ops_report(path=multi_board_path, report=multi_board_report)
    write_daily_ops_bundle(path=daily_bundle_path, bundle=daily_bundle)
    write_unified_ops_console(path=ops_console_path, console=ops_console)
    ops_history_path = Path(output_root) / "ops-history.md"
    history_report = build_ops_history_report(output_root=output_root)
    write_ops_history_report(
        path=ops_history_path,
        report=history_report,
    )
    strategy_loop_history_path: Path | None = None
    strategy_loop_decision_path: Path | None = None
    strategy_cycle_package_path: Path | None = None
    latest_strategy_loop_history_path: Path | None = None
    latest_strategy_loop_decision_path: Path | None = None
    latest_strategy_cycle_package_path: Path | None = None
    strategy_loop_decision = None
    if strategy_feedback_loop_paths:
        strategy_loop_history = build_strategy_loop_history_report(
            feedback_loop_paths=[str(Path(path)) for path in strategy_feedback_loop_paths],
        )
        strategy_loop_history_path = target_dir / "strategy-loop-history.md"
        write_strategy_loop_history_report(
            path=strategy_loop_history_path,
            report=strategy_loop_history,
        )
        strategy_loop_decision = build_strategy_loop_decision(strategy_loop_history)
        strategy_loop_decision_path = target_dir / "strategy-loop-decision.md"
        write_strategy_loop_decision(
            path=strategy_loop_decision_path,
            decision=strategy_loop_decision,
        )
        strategy_cycle_package = build_strategy_cycle_package(
            history_report=strategy_loop_history,
            loop_decision=strategy_loop_decision,
        )
        strategy_cycle_package_path = target_dir / "strategy-cycle-package.md"
        write_strategy_cycle_package(
            path=strategy_cycle_package_path,
            package=strategy_cycle_package,
        )
    ops_one_page_path = target_dir / "ops-one-page.md"
    rendered_runtime = runtime_rendered or "runtime_dashboard\nrisk_action=review\nrisk_decision=review:scheduled_ops_stub"
    initial_one_page = build_ops_one_page(
        dashboard=_scheduled_dashboard_stub(),
        runtime_rendered=rendered_runtime,
        console=ops_console,
        history=history_report,
        strategy_loop_decision=strategy_loop_decision,
    )
    write_ops_one_page(
        path=ops_one_page_path,
        page=initial_one_page,
    )
    promotion_evidence_path: Path | None = None
    latest_promotion_evidence_path: Path | None = None
    promotion_evidence = None
    if promotion_evidence_stage is not None and promotion_evidence_bundle_paths:
        effective_bundle_paths: list[str | Path] = [
            str(Path(path))
            for path in promotion_evidence_bundle_paths
        ]
        current_bundle_path = str(Path(crypto_operator_summary_path))
        if current_bundle_path not in effective_bundle_paths:
            effective_bundle_paths.append(current_bundle_path)
        promotion_evidence = build_promotion_evidence_report(
            stage=promotion_evidence_stage,  # type: ignore[arg-type]
            bundle_paths=effective_bundle_paths,
        )
        promotion_evidence_path = target_dir / "crypto-promotion-evidence.md"
        write_promotion_evidence_report(
            path=promotion_evidence_path,
            report=promotion_evidence,
        )
    ops_followup_queue = build_ops_followup_queue(
        latest_report=multi_board_report,
        history=history_report,
        promotion_evidence=promotion_evidence,
        strategy_loop_decision=strategy_loop_decision,
    )
    ops_followup_queue_path = target_dir / "ops-followup-queue.md"
    write_ops_followup_queue(
        path=ops_followup_queue_path,
        queue=ops_followup_queue,
    )
    final_one_page = build_ops_one_page(
        dashboard=_scheduled_dashboard_stub(),
        runtime_rendered=rendered_runtime,
        console=ops_console,
        history=history_report,
        followup_queue=ops_followup_queue,
        strategy_loop_decision=strategy_loop_decision,
    )
    write_ops_one_page(
        path=ops_one_page_path,
        page=final_one_page,
    )
    ops_decision_path = target_dir / "ops-decision.md"
    write_ops_decision(
        path=ops_decision_path,
        decision=build_ops_decision(final_one_page),
    )
    latest_multi_board_report_path = _refresh_latest_artifact(
        source_path=multi_board_path,
        target_path=Path(output_root) / "latest-multi-board-ops.md",
    )
    latest_daily_bundle_path = _refresh_latest_artifact(
        source_path=daily_bundle_path,
        target_path=Path(output_root) / "latest-daily-ops-bundle.md",
    )
    latest_ops_console_path = _refresh_latest_artifact(
        source_path=ops_console_path,
        target_path=Path(output_root) / "latest-ops-console.md",
    )
    latest_ops_history_path = _refresh_latest_artifact(
        source_path=ops_history_path,
        target_path=Path(output_root) / "latest-ops-history.md",
    )
    latest_ops_one_page_path = _refresh_latest_artifact(
        source_path=ops_one_page_path,
        target_path=Path(output_root) / "latest-ops-one-page.md",
    )
    latest_ops_followup_queue_path = _refresh_latest_artifact(
        source_path=ops_followup_queue_path,
        target_path=Path(output_root) / "latest-ops-followup-queue.md",
    )
    latest_ops_decision_path = _refresh_latest_artifact(
        source_path=ops_decision_path,
        target_path=Path(output_root) / "latest-ops-decision.md",
    )
    if promotion_evidence_path is not None:
        latest_promotion_evidence_path = _refresh_latest_artifact(
            source_path=promotion_evidence_path,
            target_path=Path(output_root) / "latest-crypto-promotion-evidence.md",
        )
    if strategy_loop_history_path is not None:
        latest_strategy_loop_history_path = _refresh_latest_artifact(
            source_path=strategy_loop_history_path,
            target_path=Path(output_root) / "latest-strategy-loop-history.md",
        )
    if strategy_loop_decision_path is not None:
        latest_strategy_loop_decision_path = _refresh_latest_artifact(
            source_path=strategy_loop_decision_path,
            target_path=Path(output_root) / "latest-strategy-loop-decision.md",
        )
    if strategy_cycle_package_path is not None:
        latest_strategy_cycle_package_path = _refresh_latest_artifact(
            source_path=strategy_cycle_package_path,
            target_path=Path(output_root) / "latest-strategy-cycle-package.md",
        )
    return ScheduledOpsArtifacts(
        run_id=effective_run_id,
        run_date=run_date,
        output_dir=str(target_dir),
        multi_board_report_path=str(multi_board_path),
        daily_bundle_path=str(daily_bundle_path),
        ops_console_path=str(ops_console_path),
        ops_history_path=str(ops_history_path),
        ops_one_page_path=str(ops_one_page_path),
        ops_followup_queue_path=str(ops_followup_queue_path),
        ops_decision_path=str(ops_decision_path),
        promotion_evidence_path=(str(promotion_evidence_path) if promotion_evidence_path is not None else None),
        strategy_loop_history_path=(str(strategy_loop_history_path) if strategy_loop_history_path is not None else None),
        strategy_loop_decision_path=(str(strategy_loop_decision_path) if strategy_loop_decision_path is not None else None),
        strategy_cycle_package_path=(str(strategy_cycle_package_path) if strategy_cycle_package_path is not None else None),
        latest_multi_board_report_path=str(latest_multi_board_report_path),
        latest_daily_bundle_path=str(latest_daily_bundle_path),
        latest_ops_console_path=str(latest_ops_console_path),
        latest_ops_history_path=str(latest_ops_history_path),
        latest_ops_one_page_path=str(latest_ops_one_page_path),
        latest_ops_followup_queue_path=str(latest_ops_followup_queue_path),
        latest_ops_decision_path=str(latest_ops_decision_path),
        latest_promotion_evidence_path=(
            str(latest_promotion_evidence_path) if latest_promotion_evidence_path is not None else None
        ),
        latest_strategy_loop_history_path=(
            str(latest_strategy_loop_history_path) if latest_strategy_loop_history_path is not None else None
        ),
        latest_strategy_loop_decision_path=(
            str(latest_strategy_loop_decision_path) if latest_strategy_loop_decision_path is not None else None
        ),
        latest_strategy_cycle_package_path=(
            str(latest_strategy_cycle_package_path) if latest_strategy_cycle_package_path is not None else None
        ),
    )


def _scheduled_dashboard_stub() -> DashboardState:
    return DashboardState(
        total_equity=0.0,
        today_pnl=0.0,
        open_positions=(),
        pending_orders=(),
        status=RuntimeStatus.RUNNING,
        halt_reason=HaltReason.NONE,
        halt_message=None,
        last_alert=None,
        daily_order_count=0,
        daily_order_soft_limit_reached=False,
    )


def _refresh_latest_artifact(*, source_path: Path, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target_path)
    source_json = source_path.with_suffix(".json")
    if source_json.exists():
        shutil.copyfile(source_json, target_path.with_suffix(".json"))
    return target_path
