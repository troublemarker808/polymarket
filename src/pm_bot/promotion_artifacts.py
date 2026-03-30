"""Standardized operator-facing promotion artifacts."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pm_bot.core.settings import TradingSettings
from pm_bot.execution.portfolio import build_portfolio_cap_utilization, portfolio_state_from_dashboard
from pm_bot.promotion import PromotionReadinessReport
from pm_bot.runtime.runtime_alerts import build_runtime_alerts
from pm_bot.runtime.state import DashboardState, RuntimeStatus, runtime_state_from_dict
from pm_bot.strategies.crypto.phase2.management import summarize_execution_feedback_from_events


@dataclass(slots=True, frozen=True)
class PromotionArtifactReview:
    stage: str
    source_metrics_path: str
    source_state_path: str
    source_event_path: str
    note_path: str | None
    shadow_metrics_path: str | None
    shadow_state_path: str | None
    shadow_event_path: str | None
    source_orders_submitted: int
    source_orders_filled: int
    source_status: str
    source_halt_reason: str
    shadow_orders_submitted: int | None
    shadow_orders_filled: int | None
    shadow_status: str | None
    shadow_halt_reason: str | None
    source_event_lines: int
    shadow_event_lines: int | None
    note_present: bool


@dataclass(slots=True, frozen=True)
class PromotionOperatorSummary:
    stage: str
    ready: bool
    action: str
    blocker_count: int
    warning_count: int
    source_status: str
    source_halt_reason: str
    note_present: bool
    shadow_status: str | None
    shadow_halt_reason: str | None
    source_orders_submitted: int
    shadow_orders_submitted: int | None
    immediate_action: str
    rollback_triggers: tuple[str, ...]
    escalation_actions: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class CombinedOperatorSummary:
    runtime_action: str
    runtime_decision: str
    promotion_action: str | None
    promotion_decision: str | None
    overall_action: str
    overall_decision: str
    next_step: str
    rollback_target: str | None
    alert_count: int
    alert_codes: tuple[str, ...]
    last_rejection_reason: str | None


@dataclass(slots=True, frozen=True)
class ExecutionFeedbackSummary:
    maker_fill_rate: float
    taker_shortfall_bps: float
    repeated_expiration_rate: float
    repeated_stop_out_rate: float
    recommended_route_bias: str


@dataclass(slots=True, frozen=True)
class SessionArtifactManifest:
    session_label: str | None
    metrics_path: str | None
    state_path: str | None
    event_path: str | None
    note_path: str | None
    event_count: int
    orders_submitted: int | None
    orders_filled: int | None


@dataclass(slots=True, frozen=True)
class SessionOperatorBundle:
    combined: CombinedOperatorSummary
    artifacts: SessionArtifactManifest
    execution_feedback: ExecutionFeedbackSummary | None


def build_promotion_artifact_review(
    *,
    stage: str,
    metrics_path: str | Path,
    state_path: str | Path,
    event_path: str | Path,
    note_path: str | Path | None = None,
    shadow_metrics_path: str | Path | None = None,
    shadow_state_path: str | Path | None = None,
    shadow_event_path: str | Path | None = None,
) -> PromotionArtifactReview:
    metrics = _load_json(metrics_path)
    state = runtime_state_from_dict(_load_json(state_path))
    shadow_metrics = _load_json(shadow_metrics_path) if shadow_metrics_path is not None else None
    shadow_state = runtime_state_from_dict(_load_json(shadow_state_path)) if shadow_state_path is not None else None
    return PromotionArtifactReview(
        stage=stage,
        source_metrics_path=str(Path(metrics_path)),
        source_state_path=str(Path(state_path)),
        source_event_path=str(Path(event_path)),
        note_path=str(Path(note_path)) if note_path is not None else None,
        shadow_metrics_path=str(Path(shadow_metrics_path)) if shadow_metrics_path is not None else None,
        shadow_state_path=str(Path(shadow_state_path)) if shadow_state_path is not None else None,
        shadow_event_path=str(Path(shadow_event_path)) if shadow_event_path is not None else None,
        source_orders_submitted=int(metrics.get("orders_submitted", 0)),
        source_orders_filled=int(metrics.get("orders_filled", 0)),
        source_status=state.status.value,
        source_halt_reason=state.halt_reason.value,
        shadow_orders_submitted=int(shadow_metrics.get("orders_submitted", 0)) if shadow_metrics is not None else None,
        shadow_orders_filled=int(shadow_metrics.get("orders_filled", 0)) if shadow_metrics is not None else None,
        shadow_status=shadow_state.status.value if shadow_state is not None else None,
        shadow_halt_reason=shadow_state.halt_reason.value if shadow_state is not None else None,
        source_event_lines=_count_nonempty_lines(event_path),
        shadow_event_lines=_count_nonempty_lines(shadow_event_path) if shadow_event_path is not None else None,
        note_present=note_path is not None and Path(note_path).exists(),
    )


def format_promotion_artifact_review(review: PromotionArtifactReview) -> str:
    lines = [
        "# Promotion Artifact Review",
        "",
        f"- stage: {review.stage}",
        f"- source_metrics_path: {review.source_metrics_path}",
        f"- source_state_path: {review.source_state_path}",
        f"- source_event_path: {review.source_event_path}",
        f"- note_present: {str(review.note_present).lower()}",
        f"- note_path: {review.note_path or 'none'}",
        "",
        "## Source",
        "",
        f"- orders_submitted: {review.source_orders_submitted}",
        f"- orders_filled: {review.source_orders_filled}",
        f"- event_lines: {review.source_event_lines}",
        f"- status: {review.source_status}",
        f"- halt_reason: {review.source_halt_reason}",
    ]
    if review.shadow_metrics_path is not None:
        lines.extend(
            [
                "",
                "## Shadow",
                "",
                f"- shadow_metrics_path: {review.shadow_metrics_path}",
                f"- shadow_state_path: {review.shadow_state_path}",
                f"- shadow_event_path: {review.shadow_event_path}",
                f"- orders_submitted: {review.shadow_orders_submitted}",
                f"- orders_filled: {review.shadow_orders_filled}",
                f"- event_lines: {review.shadow_event_lines}",
                f"- status: {review.shadow_status}",
                f"- halt_reason: {review.shadow_halt_reason}",
            ]
        )
    return "\n".join(lines) + "\n"


def format_promotion_operator_summary(
    *,
    readiness: PromotionReadinessReport,
    review: PromotionArtifactReview,
) -> str:
    summary = build_promotion_operator_summary(readiness=readiness, review=review)
    lines = [
        "# Promotion Operator Summary",
        "",
        f"- stage: {summary.stage}",
        f"- ready: {str(summary.ready).lower()}",
        f"- blockers: {summary.blocker_count}",
        f"- warnings: {summary.warning_count}",
        f"- source_status: {summary.source_status}",
        f"- source_halt_reason: {summary.source_halt_reason}",
        f"- note_present: {str(summary.note_present).lower()}",
    ]
    if summary.shadow_status is not None:
        lines.extend(
            [
                f"- shadow_status: {summary.shadow_status}",
                f"- shadow_halt_reason: {summary.shadow_halt_reason}",
                f"- submission_parity: {summary.source_orders_submitted}/{summary.shadow_orders_submitted}",
            ]
        )
    lines.extend(["", "## Immediate Action", ""])
    lines.append(f"- {summary.immediate_action}")
    lines.extend(["", "## Rollback Triggers", ""])
    lines.extend(f"- {item}" for item in summary.rollback_triggers)
    lines.extend(["", "## Escalation Actions", ""])
    lines.extend(f"- {item}" for item in summary.escalation_actions)
    return "\n".join(lines) + "\n"


def write_operator_note_template(
    *,
    path: str | Path,
    stage: str,
    run_id: str,
    market_window: str,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(
            [
                f"# {stage} Operator Note",
                "",
                f"- run_id: {run_id}",
                f"- market_window: {market_window}",
                "- outcome: pending",
                "- exchange_anomalies: none",
                "- pause_resume_notes: none",
                "- next_action: pending_review",
                "",
                "## Review",
                "",
                "- summarize the validation window here",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def write_promotion_operator_summary(
    *,
    path: str | Path,
    readiness: PromotionReadinessReport,
    review: PromotionArtifactReview,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    summary = build_promotion_operator_summary(readiness=readiness, review=review)
    target.write_text(
        format_promotion_operator_summary(readiness=readiness, review=review),
        encoding="utf-8",
    )
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(summary)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def build_promotion_operator_summary(
    *,
    readiness: PromotionReadinessReport,
    review: PromotionArtifactReview,
) -> PromotionOperatorSummary:
    if readiness.blockers:
        action = "pause"
        immediate_action = f"pause: {readiness.blockers[0]}"
    elif readiness.warnings:
        action = "review"
        immediate_action = f"review: {readiness.warnings[0]}"
    else:
        action = "proceed"
        immediate_action = "proceed: no immediate blockers detected"
    return PromotionOperatorSummary(
        stage=readiness.stage,
        ready=readiness.ready,
        action=action,
        blocker_count=len(readiness.blockers),
        warning_count=len(readiness.warnings),
        source_status=review.source_status,
        source_halt_reason=review.source_halt_reason,
        note_present=review.note_present,
        shadow_status=review.shadow_status,
        shadow_halt_reason=review.shadow_halt_reason,
        source_orders_submitted=review.source_orders_submitted,
        shadow_orders_submitted=review.shadow_orders_submitted,
        immediate_action=immediate_action,
        rollback_triggers=readiness.rollback_triggers,
        escalation_actions=readiness.escalation_actions,
    )


def load_promotion_operator_summary(path: str | Path) -> PromotionOperatorSummary | None:
    summary_path = Path(path)
    json_path = summary_path.with_suffix(".json")
    if not json_path.exists():
        return None
    payload = _load_json(json_path)
    return PromotionOperatorSummary(
        stage=str(payload.get("stage", "")),
        ready=bool(payload.get("ready", False)),
        action=str(payload.get("action", "")),
        blocker_count=int(payload.get("blocker_count", 0)),
        warning_count=int(payload.get("warning_count", 0)),
        source_status=str(payload.get("source_status", "")),
        source_halt_reason=str(payload.get("source_halt_reason", "")),
        note_present=bool(payload.get("note_present", False)),
        shadow_status=str(payload["shadow_status"]) if payload.get("shadow_status") is not None else None,
        shadow_halt_reason=str(payload["shadow_halt_reason"]) if payload.get("shadow_halt_reason") is not None else None,
        source_orders_submitted=int(payload.get("source_orders_submitted", 0)),
        shadow_orders_submitted=int(payload["shadow_orders_submitted"]) if payload.get("shadow_orders_submitted") is not None else None,
        immediate_action=str(payload.get("immediate_action", "")),
        rollback_triggers=tuple(str(item) for item in payload.get("rollback_triggers", [])),
        escalation_actions=tuple(str(item) for item in payload.get("escalation_actions", [])),
    )


def build_combined_operator_summary(
    *,
    dashboard: DashboardState,
    trading_settings: TradingSettings | None = None,
    promotion_summary: PromotionOperatorSummary | None = None,
) -> CombinedOperatorSummary:
    runtime_action, runtime_decision = _runtime_summary(
        dashboard=dashboard,
        trading_settings=trading_settings,
    )
    promotion_action = promotion_summary.action if promotion_summary is not None else None
    promotion_decision = (
        f"{promotion_summary.action}:ready={str(promotion_summary.ready).lower()}:"
        f"blockers={promotion_summary.blocker_count}:warnings={promotion_summary.warning_count}"
        if promotion_summary is not None
        else None
    )
    overall_action = _merge_actions(runtime_action=runtime_action, promotion_action=promotion_action)
    alerts = build_runtime_alerts(
        dashboard=dashboard,
        trading_settings=trading_settings,
        promotion_ready=(promotion_summary.ready if promotion_summary is not None else None),
        promotion_action=promotion_action,
    )
    overall_decision = _merge_decision(
        runtime_decision=runtime_decision,
        promotion_decision=promotion_decision,
        overall_action=overall_action,
        alerts=alerts,
    )
    return CombinedOperatorSummary(
        runtime_action=runtime_action,
        runtime_decision=runtime_decision,
        promotion_action=promotion_action,
        promotion_decision=promotion_decision,
        overall_action=overall_action,
        overall_decision=overall_decision,
        next_step=_next_step(
            overall_action=overall_action,
            promotion_summary=promotion_summary,
            alerts=alerts,
        ),
        rollback_target=_rollback_target(alerts),
        alert_count=len(alerts),
        alert_codes=tuple(alert.code for alert in alerts),
        last_rejection_reason=dashboard.last_order_rejection_reason,
    )


def format_combined_operator_summary(summary: CombinedOperatorSummary) -> str:
    lines = [
        "# Combined Operator Summary",
        "",
        f"- overall_action: {summary.overall_action}",
        f"- overall_decision: {summary.overall_decision}",
        f"- next_step: {summary.next_step}",
        f"- rollback_target: {summary.rollback_target or 'none'}",
        f"- alert_count: {summary.alert_count}",
        f"- runtime_action: {summary.runtime_action}",
        f"- runtime_decision: {summary.runtime_decision}",
        f"- alert_codes: {','.join(summary.alert_codes)}",
        f"- last_rejection_reason: {summary.last_rejection_reason or 'none'}",
    ]
    if summary.promotion_action is not None:
        lines.extend(
            [
                f"- promotion_action: {summary.promotion_action}",
                f"- promotion_decision: {summary.promotion_decision}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_combined_operator_summary(
    *,
    path: str | Path,
    dashboard: DashboardState,
    trading_settings: TradingSettings | None = None,
    promotion_summary: PromotionOperatorSummary | None = None,
    metrics_path: str | Path | None = None,
    state_path: str | Path | None = None,
    event_path: str | Path | None = None,
    note_path: str | Path | None = None,
    session_label: str | None = None,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    bundle = build_session_operator_bundle(
        dashboard=dashboard,
        trading_settings=trading_settings,
        promotion_summary=promotion_summary,
        metrics_path=metrics_path,
        state_path=state_path,
        event_path=event_path,
        note_path=note_path,
        session_label=session_label,
    )
    target.write_text(format_session_operator_bundle(bundle), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(bundle)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_combined_operator_summary(path: str | Path) -> CombinedOperatorSummary | None:
    target = Path(path)
    json_path = target.with_suffix(".json")
    if not json_path.exists():
        return None
    payload = _load_json(json_path)
    if "combined" in payload and isinstance(payload["combined"], dict):
        payload = dict(payload["combined"])
    return CombinedOperatorSummary(
        runtime_action=str(payload.get("runtime_action", "")),
        runtime_decision=str(payload.get("runtime_decision", "")),
        promotion_action=(
            str(payload["promotion_action"])
            if payload.get("promotion_action") not in (None, "")
            else None
        ),
        promotion_decision=(
            str(payload["promotion_decision"])
            if payload.get("promotion_decision") not in (None, "")
            else None
        ),
        overall_action=str(payload.get("overall_action", "")),
        overall_decision=str(payload.get("overall_decision", "")),
        next_step=str(payload.get("next_step", "")),
        rollback_target=(
            str(payload["rollback_target"])
            if payload.get("rollback_target") not in (None, "")
            else None
        ),
        alert_count=int(payload.get("alert_count", 0)),
        alert_codes=tuple(str(item) for item in payload.get("alert_codes", [])),
        last_rejection_reason=(
            str(payload["last_rejection_reason"])
            if payload.get("last_rejection_reason") not in (None, "")
            else None
        ),
    )


def build_session_operator_bundle(
    *,
    dashboard: DashboardState,
    trading_settings: TradingSettings | None = None,
    promotion_summary: PromotionOperatorSummary | None = None,
    metrics_path: str | Path | None = None,
    state_path: str | Path | None = None,
    event_path: str | Path | None = None,
    note_path: str | Path | None = None,
    session_label: str | None = None,
) -> SessionOperatorBundle:
    combined = build_combined_operator_summary(
        dashboard=dashboard,
        trading_settings=trading_settings,
        promotion_summary=promotion_summary,
    )
    metrics = _load_json(metrics_path) if metrics_path is not None and Path(metrics_path).exists() else {}
    events = _load_events(event_path) if event_path is not None and Path(event_path).exists() else ()
    execution_feedback = None
    if events:
        feedback = summarize_execution_feedback_from_events(
            recent_events=events,
            pending_orders=dashboard.pending_orders,
        )
        execution_feedback = ExecutionFeedbackSummary(
            maker_fill_rate=feedback.maker_fill_rate,
            taker_shortfall_bps=feedback.taker_shortfall_bps,
            repeated_expiration_rate=feedback.repeated_expiration_rate,
            repeated_stop_out_rate=feedback.repeated_stop_out_rate,
            recommended_route_bias=feedback.recommended_route_bias,
        )
    return SessionOperatorBundle(
        combined=combined,
        artifacts=SessionArtifactManifest(
            session_label=session_label,
            metrics_path=str(Path(metrics_path)) if metrics_path is not None else None,
            state_path=str(Path(state_path)) if state_path is not None else None,
            event_path=str(Path(event_path)) if event_path is not None else None,
            note_path=str(Path(note_path)) if note_path is not None else None,
            event_count=len(events),
            orders_submitted=(
                int(metrics.get("orders_submitted", 0))
                if metrics_path is not None and metrics
                else None
            ),
            orders_filled=(
                int(metrics.get("orders_filled", 0))
                if metrics_path is not None and metrics
                else None
            ),
        ),
        execution_feedback=execution_feedback,
    )


def format_session_operator_bundle(bundle: SessionOperatorBundle) -> str:
    lines = [format_combined_operator_summary(bundle.combined).rstrip()]
    lines.extend(
        [
            "",
            "## Session Artifacts",
            "",
            f"- session_label: {bundle.artifacts.session_label or 'none'}",
            f"- metrics_path: {bundle.artifacts.metrics_path or 'none'}",
            f"- state_path: {bundle.artifacts.state_path or 'none'}",
            f"- event_path: {bundle.artifacts.event_path or 'none'}",
            f"- note_path: {bundle.artifacts.note_path or 'none'}",
            f"- event_count: {bundle.artifacts.event_count}",
            f"- orders_submitted: {_optional_int(bundle.artifacts.orders_submitted)}",
            f"- orders_filled: {_optional_int(bundle.artifacts.orders_filled)}",
        ]
    )
    if bundle.execution_feedback is not None:
        lines.extend(
            [
                "",
                "## Execution Feedback",
                "",
                f"- maker_fill_rate: {bundle.execution_feedback.maker_fill_rate:.4f}",
                f"- taker_shortfall_bps: {bundle.execution_feedback.taker_shortfall_bps:.4f}",
                f"- repeated_expiration_rate: {bundle.execution_feedback.repeated_expiration_rate:.4f}",
                f"- repeated_stop_out_rate: {bundle.execution_feedback.repeated_stop_out_rate:.4f}",
                f"- recommended_route_bias: {bundle.execution_feedback.recommended_route_bias}",
            ]
        )
    return "\n".join(lines) + "\n"


def _load_json(path: str | Path) -> dict[str, Any]:
    return dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _load_events(path: str | Path) -> tuple[dict[str, object], ...]:
    events: list[dict[str, object]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            events.append(payload)
    return tuple(events)


def _count_nonempty_lines(path: str | Path) -> int:
    return sum(1 for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip())


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value


def _optional_int(value: int | None) -> str:
    return str(value) if value is not None else "none"
def _merge_actions(*, runtime_action: str, promotion_action: str | None) -> str:
    actions = [runtime_action]
    if promotion_action is not None:
        actions.append(promotion_action)
    if "pause" in actions:
        return "pause"
    if "review" in actions:
        return "review"
    return "proceed"


def _merge_decision(
    *,
    runtime_decision: str,
    promotion_decision: str | None,
    overall_action: str,
    alerts: tuple[object, ...],
) -> str:
    alert_suffix = f":alerts={len(alerts)}" if alerts else ""
    if promotion_decision is None:
        return f"{overall_action}:runtime={runtime_decision}{alert_suffix}"
    return f"{overall_action}:runtime={runtime_decision}:promotion={promotion_decision}{alert_suffix}"


def _next_step(
    *,
    overall_action: str,
    promotion_summary: PromotionOperatorSummary | None,
    alerts: tuple[object, ...],
) -> str:
    if any(getattr(alert, "rollback_target", None) == "previous_stage" for alert in alerts):
        return "rollback_previous_stage"
    if any(getattr(alert, "rollback_target", None) == "current_stage" for alert in alerts):
        return "hold_current_stage"
    if overall_action == "pause":
        return "stop_and_investigate"
    if overall_action == "review":
        return "review_operator_artifacts"
    if promotion_summary is None:
        return "continue_current_window"
    if promotion_summary.stage == "paper_to_sync_shadow":
        return "proceed_sync_shadow"
    if promotion_summary.stage == "sync_shadow_to_small_live_baseline":
        return "proceed_small_live"
    return "continue_current_window"


def _rollback_target(alerts: tuple[object, ...]) -> str | None:
    for preferred in ("previous_stage", "current_stage"):
        if any(getattr(alert, "rollback_target", None) == preferred for alert in alerts):
            return preferred
    return None


def _runtime_summary(
    *,
    dashboard: DashboardState,
    trading_settings: TradingSettings | None,
) -> tuple[str, str]:
    if dashboard.status == RuntimeStatus.HALTED:
        halt_reason = dashboard.halt_reason.value if dashboard.halt_reason.value else "halted"
        return "pause", f"pause:halted:{halt_reason}"
    if dashboard.consecutive_data_failures > 0:
        return "review", f"review:data_failures={dashboard.consecutive_data_failures}"
    if trading_settings is not None:
        utilization = build_portfolio_cap_utilization(
            portfolio=portfolio_state_from_dashboard(dashboard),
            trading_settings=trading_settings,
        )
        if utilization.total_gross.utilization_ratio >= 1.0:
            return "pause", "pause:total_gross_cap_breached"
        if utilization.total_gross.utilization_ratio >= 0.9:
            return "review", "review:total_gross_near_cap"
        hot_group = next(
            (item for item in utilization.by_exposure_group if item.utilization_ratio >= 0.9),
            None,
        )
        if hot_group is not None:
            return "review", f"review:exposure_group_near_cap={hot_group.exposure_group_id}"
    rejection_reason = (dashboard.last_order_rejection_reason or "").strip()
    if rejection_reason:
        return "review", f"review:last_reject={rejection_reason}"
    if dashboard.daily_order_soft_limit_reached:
        return "review", "review:daily_soft_limit_reached"
    return "proceed", "proceed:clear"
