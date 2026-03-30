"""Follow-up queue generation for repeated reviews, pauses, and blockers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pm_bot.multi_board_ops import MultiBoardOpsReport, load_multi_board_ops_report
from pm_bot.ops_history import OpsHistoryReport, load_ops_history_report
from pm_bot.promotion_evidence import PromotionEvidenceReport, load_promotion_evidence_report
from pm_bot.strategy_loop_decision import StrategyLoopDecision, load_strategy_loop_decision


@dataclass(slots=True, frozen=True)
class OpsFollowUpItem:
    priority: str
    owner: str
    item: str
    reason: str


@dataclass(slots=True, frozen=True)
class OpsIssueLifecycle:
    open_items: tuple[str, ...]
    escalating_items: tuple[str, ...]
    resolved_items: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class OpsFollowUpQueue:
    generated_from: str
    overall_action: str
    recommended_attention: str
    item_count: int
    lifecycle: OpsIssueLifecycle
    items: tuple[OpsFollowUpItem, ...]


def build_ops_followup_queue(
    *,
    latest_report: MultiBoardOpsReport,
    history: OpsHistoryReport | None = None,
    promotion_evidence: PromotionEvidenceReport | None = None,
    strategy_loop_decision: StrategyLoopDecision | None = None,
    generated_from: str = "scheduled_ops",
) -> OpsFollowUpQueue:
    items: list[OpsFollowUpItem] = []
    lifecycle = _build_issue_lifecycle(latest_report=latest_report, history=history)
    if latest_report.overall_action == "pause":
        items.append(
            OpsFollowUpItem(
                priority="critical",
                owner=latest_report.rollback_target or "operator",
                item="stabilize paused board before next session",
                reason=latest_report.overall_decision,
            )
        )
    if history is not None and history.review_streak >= 2:
        items.append(
            OpsFollowUpItem(
                priority="high",
                owner="operator",
                item="resolve repeated review streak before promotion",
                reason=f"review_streak={history.review_streak}",
            )
        )
    for blocker in latest_report.blockers:
        items.append(
            OpsFollowUpItem(
                priority="high",
                owner="operator",
                item="clear blocker",
                reason=blocker,
            )
        )
    for warning in latest_report.warnings[:3]:
        items.append(
            OpsFollowUpItem(
                priority="medium",
                owner="operator",
                item="inspect recurring warning",
                reason=warning,
            )
        )
    if history is not None:
        for review_count in history.board_review_counts:
            board, _, count = review_count.partition("=")
            if int(count or "0") >= 2:
                items.append(
                    OpsFollowUpItem(
                        priority="medium",
                        owner=board,
                        item="reduce repeated board reviews",
                        reason=review_count,
                    )
                )
    if strategy_loop_decision is not None:
        if strategy_loop_decision.recommended_mode == "stabilize":
            items.append(
                OpsFollowUpItem(
                    priority="high",
                    owner=strategy_loop_decision.primary_board or "operator",
                    item="freeze repeated strategy promotions and re-baseline the board",
                    reason=strategy_loop_decision.next_step,
                )
            )
        elif strategy_loop_decision.recommended_mode == "learn":
            items.append(
                OpsFollowUpItem(
                    priority="medium",
                    owner=strategy_loop_decision.primary_board or "operator",
                    item="focus the next experiment cycle on the weaker board",
                    reason=strategy_loop_decision.next_step,
                )
            )
        elif strategy_loop_decision.recommended_mode == "verify":
            items.append(
                OpsFollowUpItem(
                    priority="medium",
                    owner=strategy_loop_decision.primary_board or "operator",
                    item="finish pending strategy verification before the next promotion window",
                    reason=strategy_loop_decision.next_step,
                )
            )
    if promotion_evidence is not None:
        if not promotion_evidence.ready:
            items.append(
                OpsFollowUpItem(
                    priority="high",
                    owner="crypto",
                    item="close crypto promotion-evidence blockers before next promotion step",
                    reason="; ".join(promotion_evidence.blockers) or f"stage={promotion_evidence.stage}:ready=false",
                )
            )
        for warning in promotion_evidence.warnings[:3]:
            items.append(
                OpsFollowUpItem(
                    priority="medium",
                    owner="crypto",
                    item="inspect crypto promotion-evidence warning",
                    reason=warning,
                )
            )
    if not items:
        items.append(
            OpsFollowUpItem(
                priority="low",
                owner="operator",
                item="continue current monitoring cadence",
                reason=latest_report.overall_decision,
            )
        )
    return OpsFollowUpQueue(
        generated_from=generated_from,
        overall_action=latest_report.overall_action,
        recommended_attention=_recommended_attention(
            history=history,
            strategy_loop_decision=strategy_loop_decision,
        ),
        item_count=len(items),
        lifecycle=lifecycle,
        items=tuple(items),
    )


def format_ops_followup_queue(queue: OpsFollowUpQueue) -> str:
    lines = [
        "# Ops Follow-Up Queue",
        "",
        f"- generated_from: {queue.generated_from}",
        f"- overall_action: {queue.overall_action}",
        f"- recommended_attention: {queue.recommended_attention}",
        f"- item_count: {queue.item_count}",
        "",
        "## Lifecycle",
        "",
        f"- open_items: {','.join(queue.lifecycle.open_items) if queue.lifecycle.open_items else 'none'}",
        f"- escalating_items: {','.join(queue.lifecycle.escalating_items) if queue.lifecycle.escalating_items else 'none'}",
        f"- resolved_items: {','.join(queue.lifecycle.resolved_items) if queue.lifecycle.resolved_items else 'none'}",
        "",
        "## Items",
        "",
    ]
    for item in queue.items:
        lines.append(
            "- "
            + f"priority={item.priority}:owner={item.owner}:"
            + f"item={item.item}:reason={item.reason}"
        )
    return "\n".join(lines) + "\n"


def write_ops_followup_queue(
    *,
    path: str | Path,
    queue: OpsFollowUpQueue,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_ops_followup_queue(queue), encoding="utf-8")
    target.with_suffix(".json").write_text(
        json.dumps(
            {
                "generated_from": queue.generated_from,
                "overall_action": queue.overall_action,
                "recommended_attention": queue.recommended_attention,
                "item_count": queue.item_count,
                "lifecycle": {
                    "open_items": list(queue.lifecycle.open_items),
                    "escalating_items": list(queue.lifecycle.escalating_items),
                    "resolved_items": list(queue.lifecycle.resolved_items),
                },
                "items": [asdict(item) for item in queue.items],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return target


def load_ops_followup_queue(path: str | Path) -> OpsFollowUpQueue | None:
    json_path = Path(path).with_suffix(".json")
    if not json_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    lifecycle_payload = payload.get("lifecycle", {})
    return OpsFollowUpQueue(
        generated_from=str(payload.get("generated_from", "")),
        overall_action=str(payload.get("overall_action", "")),
        recommended_attention=str(payload.get("recommended_attention", "")),
        item_count=int(payload.get("item_count", 0)),
        lifecycle=OpsIssueLifecycle(
            open_items=tuple(str(item) for item in lifecycle_payload.get("open_items", [])),
            escalating_items=tuple(str(item) for item in lifecycle_payload.get("escalating_items", [])),
            resolved_items=tuple(str(item) for item in lifecycle_payload.get("resolved_items", [])),
        ),
        items=tuple(
            OpsFollowUpItem(
                priority=str(item.get("priority", "")),
                owner=str(item.get("owner", "")),
                item=str(item.get("item", "")),
                reason=str(item.get("reason", "")),
            )
            for item in payload.get("items", [])
        ),
    )


def build_ops_followup_queue_from_paths(
    *,
    latest_report_path: str | Path,
    history_path: str | Path | None = None,
    promotion_evidence_path: str | Path | None = None,
    strategy_loop_decision_path: str | Path | None = None,
    generated_from: str = "scheduled_ops",
) -> OpsFollowUpQueue:
    latest_report = load_multi_board_ops_report(latest_report_path)
    if latest_report is None:
        raise FileNotFoundError(f"Missing multi-board ops report JSON sidecar for {latest_report_path}")
    history = load_ops_history_report(history_path) if history_path is not None else None
    promotion_evidence = load_promotion_evidence_report(promotion_evidence_path) if promotion_evidence_path is not None else None
    strategy_loop_decision = load_strategy_loop_decision(strategy_loop_decision_path) if strategy_loop_decision_path is not None else None
    return build_ops_followup_queue(
        latest_report=latest_report,
        history=history,
        promotion_evidence=promotion_evidence,
        strategy_loop_decision=strategy_loop_decision,
        generated_from=generated_from,
    )


def _recommended_attention(
    *,
    history: OpsHistoryReport | None,
    strategy_loop_decision: StrategyLoopDecision | None,
) -> str:
    if strategy_loop_decision is not None:
        if strategy_loop_decision.recommended_mode == "stabilize":
            board = strategy_loop_decision.primary_board or "strategy"
            return f"stabilize_{board}"
        if strategy_loop_decision.recommended_mode == "verify":
            board = strategy_loop_decision.primary_board or "strategy"
            return f"verify_{board}"
        if strategy_loop_decision.recommended_mode == "learn":
            board = strategy_loop_decision.primary_board or "strategy"
            return f"learn_{board}"
    if history is not None:
        return history.recommended_attention
    return "collect_more_runs"


def _build_issue_lifecycle(
    *,
    latest_report: MultiBoardOpsReport,
    history: OpsHistoryReport | None,
) -> OpsIssueLifecycle:
    current_items = sorted(set(latest_report.blockers) | set(latest_report.warnings))
    recurring_counts: dict[str, int] = {}
    if history is not None:
        for item in history.recurring_issues:
            issue, _, count = item.rpartition("=")
            if issue and count.isdigit():
                recurring_counts[issue] = int(count)
    escalating_items = tuple(
        item
        for item in current_items
        if recurring_counts.get(item, 0) >= 2
    )
    open_items = tuple(
        item
        for item in current_items
        if item not in escalating_items
    )
    resolved_items: tuple[str, ...] = ()
    if history is not None and len(history.recent_runs) >= 2:
        previous_items = set(history.recent_runs[1].blockers) | set(history.recent_runs[1].warnings)
        resolved_items = tuple(
            item
            for item in sorted(previous_items)
            if item not in current_items and recurring_counts.get(item, 0) >= 2
        )
    return OpsIssueLifecycle(
        open_items=open_items,
        escalating_items=escalating_items,
        resolved_items=resolved_items,
    )
