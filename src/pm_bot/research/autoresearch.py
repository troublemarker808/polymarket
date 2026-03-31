"""Autoresearch helpers for artifact-driven tuning loops."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from pm_bot.execution.metrics_report import load_metrics_file
from pm_bot.runtime.state import RuntimeState, runtime_state_from_dict

_CAPACITY_REJECTION_REASONS = frozenset(
    {
        "daily order hard limit reached",
        "daily order soft limit reached",
        "max concurrent positions reached",
        "market already has a pending order",
        "max open orders reached",
    }
)
_DAILY_LIMIT_REASONS = frozenset(
    {
        "daily order hard limit reached",
        "daily order soft limit reached",
    }
)
_CONCURRENCY_REASONS = frozenset(
    {
        "max concurrent positions reached",
        "market already has a pending order",
        "max open orders reached",
    }
)
_LOCKED_PARAMETERS = (
    "polymarket.allow_live_orders",
    "trading.live_allowed_categories",
    "trading.max_notional_per_market",
    "trading.max_notional_per_category",
    "trading.max_concurrent_positions",
    "trading.max_positions_per_market",
    "trading.daily_order_soft_limit",
    "trading.daily_order_hard_limit",
    "risk.max_daily_drawdown_pct",
    "risk.max_consecutive_losses",
    "risk.max_open_orders",
    "risk.kill_switch_on_stale_data_seconds",
    "risk.manual_resume_required",
    "risk.halt_on_data_source_failure",
    "polymarket.post_only_live_orders",
    "polymarket.private_key_env",
    "polymarket.api_key_env",
    "polymarket.api_secret_env",
    "polymarket.api_passphrase_env",
    "polymarket.funder_env",
)
_TUNABLE_PARAMETERS = (
    "strategy.maker.min_spread_bps",
    "strategy.maker.inventory_skew_strength",
    "strategy.maker.quote_ttl_seconds",
    "strategy.maker.global_cooldown_seconds",
    "strategy.maker.market_cooldown_seconds",
    "strategy.maker.failure_cooldown_seconds",
    "strategy.maker.min_requote_edge_improvement_bps",
    "strategy.maker.failure_reentry_edge_improvement_bps",
    "risk.open_order_replacement_min_edge_improvement_bps",
    "strategy.surface.min_edge_bps",
    "strategy.surface.max_curve_mispricing_bps",
    "strategy.surface.exit_edge_bps",
    "strategy.surface.stop_loss_bps",
            "strategy.phase2.maker_min_edge_bps",
            "strategy.phase2.resolution_maker_min_edge_bps",
            "strategy.phase2.maker_aggressiveness",
            "strategy.phase2.high_edge_taker_min_edge_bps",
    "strategy.phase2.high_edge_taker_max_spread_bps",
    "strategy.phase2.taker_max_entry_premium_bps",
    "strategy.phase2.maker_quote_ttl_seconds",
    "strategy.phase2.resolution_maker_quote_ttl_seconds",
    "strategy.phase2.entry_repost_cooldown_seconds",
    "strategy.phase2.exit_edge_bps",
    "strategy.phase2.min_holding_seconds_before_exit",
    "strategy.phase2.adverse_fill_exit_bps",
    "strategy.phase2.adverse_fill_max_remaining_edge_bps",
)
_SCORE_FORMULA = """score =
  + 8.0 * effective_closed_trade_net_pnl
  + 3.0 * effective_trades_closed
  + 10.0 * effective_fill_rate
  - 6.0 * cancel_rate
  - 8.0 * rejected_ratio
  - 10.0 * capacity_bound_rejection_ratio
  - 3.0 * market_data_failures
  - 0.05 * abs(avg_fill_price_vs_mid_bps)
"""


@dataclass(slots=True, frozen=True)
class ExperimentSuggestion:
    name: str
    parameters: tuple[str, ...]
    rationale: str
    expected_effect: str


@dataclass(slots=True, frozen=True)
class EventDiagnostics:
    event_counts: dict[str, int]
    rejection_reasons: dict[str, int]
    fill_sources: dict[str, int]
    closed_trade_net_pnl: float
    session_rejection_reasons: dict[str, int]
    session_fill_sources: dict[str, int]
    session_fill_event_count: int
    session_submitted_order_count: int
    session_filled_order_count: int
    session_closed_trade_count: int
    session_closed_trade_net_pnl: float
    recovered_closed_trade_count: int
    recovered_closed_trade_net_pnl: float

    @property
    def has_session_scope(self) -> bool:
        return any(
            (
                self.session_submitted_order_count > 0,
                self.session_filled_order_count > 0,
                self.session_fill_event_count > 0,
                self.session_closed_trade_count > 0,
                bool(self.session_rejection_reasons),
                bool(self.session_fill_sources),
            )
        )

    @property
    def effective_rejection_reasons(self) -> dict[str, int]:
        if self.has_session_scope:
            return self.session_rejection_reasons
        return self.rejection_reasons

    @property
    def effective_fill_sources(self) -> dict[str, int]:
        if self.has_session_scope:
            return self.session_fill_sources
        return self.fill_sources

    @property
    def effective_closed_trade_net_pnl(self) -> float:
        if self.has_session_scope:
            return self.session_closed_trade_net_pnl
        return self.closed_trade_net_pnl

    def effective_orders_submitted(self, metrics: dict[str, Any]) -> int:
        if self.has_session_scope and self.session_submitted_order_count > 0:
            return self.session_submitted_order_count
        return int(metrics.get("orders_submitted", 0) or 0)

    def effective_orders_rejected(self, metrics: dict[str, Any]) -> int:
        effective_rejections = sum(self.effective_rejection_reasons.values())
        if effective_rejections > 0:
            return effective_rejections
        return int(metrics.get("orders_rejected", 0) or 0)

    def effective_filled_orders(self, metrics: dict[str, Any]) -> int:
        metric_fills = int(metrics.get("orders_filled", 0) or 0) + int(
            metrics.get("orders_partially_filled", 0) or 0
        )
        if not self.has_session_scope:
            return metric_fills
        if self.session_filled_order_count > 0:
            return self.session_filled_order_count
        if self.session_fill_event_count <= 0:
            return metric_fills
        submitted = self.effective_orders_submitted(metrics)
        if submitted > 0:
            return min(self.session_fill_event_count, submitted)
        return self.session_fill_event_count

    def effective_closed_trade_count(self, metrics: dict[str, Any]) -> int:
        if self.has_session_scope:
            return self.session_closed_trade_count
        return int(metrics.get("trades_closed", 0) or 0)

    def effective_fill_rate(self, metrics: dict[str, Any]) -> float:
        submitted = self.effective_orders_submitted(metrics)
        if submitted <= 0:
            return 0.0
        return min(1.0, self.effective_filled_orders(metrics) / submitted)

    @property
    def dominant_rejection_reason(self) -> str | None:
        rejection_reasons = self.effective_rejection_reasons
        if not rejection_reasons:
            return None
        return max(rejection_reasons.items(), key=lambda item: (item[1], item[0]))[0]

    @property
    def capacity_bound_rejection_count(self) -> int:
        return sum(
            count
            for reason, count in self.effective_rejection_reasons.items()
            if reason in _CAPACITY_REJECTION_REASONS
        )

    @property
    def daily_limit_rejection_count(self) -> int:
        return sum(
            count
            for reason, count in self.effective_rejection_reasons.items()
            if reason in _DAILY_LIMIT_REASONS
        )

    @property
    def concurrency_rejection_count(self) -> int:
        return sum(
            count
            for reason, count in self.effective_rejection_reasons.items()
            if reason in _CONCURRENCY_REASONS
        )

    @property
    def capacity_bound_rejection_ratio(self) -> float:
        rejected = sum(self.effective_rejection_reasons.values())
        if rejected <= 0:
            rejected = self.event_counts.get("order.rejected", 0)
        if rejected <= 0:
            return 0.0
        return self.capacity_bound_rejection_count / rejected


@dataclass(slots=True, frozen=True)
class AutoresearchReport:
    generated_at: datetime
    metrics_path: str
    event_path: str | None
    state_path: str | None
    classification: str
    score: float
    rewritten_objective: str
    score_formula: str
    dominant_rejection_reasons: tuple[tuple[str, int], ...]
    fill_source_mix: tuple[tuple[str, int], ...]
    locked_parameters: tuple[str, ...]
    tunable_parameters: tuple[str, ...]
    experiment_matrix: tuple[ExperimentSuggestion, ...]
    next_follow_up_experiments: tuple[str, ...]
    effective_orders_submitted: int
    effective_orders_rejected: int
    effective_orders_filled: int
    effective_trades_closed: int
    effective_fill_rate: float
    effective_closed_trade_net_pnl: float
    recovered_closed_trade_count: int
    recovered_closed_trade_net_pnl: float
    state_status: str | None
    total_equity: float | None
    today_pnl: float | None
    metrics: dict[str, Any]
    event_diagnostics: EventDiagnostics


def generate_autoresearch_report(
    *,
    metrics_path: str | Path,
    event_path: str | Path | None = None,
    state_path: str | Path | None = None,
) -> AutoresearchReport:
    metrics = load_metrics_file(metrics_path)
    diagnostics = _summarize_event_log(event_path)
    runtime_state = _load_runtime_state(state_path)
    classification = _classify_baseline(metrics=metrics, diagnostics=diagnostics)
    score = _compute_score(metrics=metrics, diagnostics=diagnostics)
    effective_orders_submitted = diagnostics.effective_orders_submitted(metrics)
    effective_orders_rejected = diagnostics.effective_orders_rejected(metrics)
    effective_orders_filled = diagnostics.effective_filled_orders(metrics)
    effective_trades_closed = diagnostics.effective_closed_trade_count(metrics)
    effective_fill_rate = diagnostics.effective_fill_rate(metrics)
    effective_closed_trade_net_pnl = diagnostics.effective_closed_trade_net_pnl
    return AutoresearchReport(
        generated_at=datetime.now(tz=timezone.utc),
        metrics_path=str(Path(metrics_path)),
        event_path=(str(Path(event_path)) if event_path is not None else None),
        state_path=(str(Path(state_path)) if state_path is not None else None),
        classification=classification,
        score=score,
        rewritten_objective=_rewritten_objective(classification=classification, metrics=metrics),
        score_formula=_SCORE_FORMULA,
        dominant_rejection_reasons=tuple(_top_items(diagnostics.rejection_reasons, limit=5)),
        fill_source_mix=tuple(_top_items(diagnostics.fill_sources, limit=5)),
        locked_parameters=_LOCKED_PARAMETERS,
        tunable_parameters=_TUNABLE_PARAMETERS,
        experiment_matrix=_experiment_matrix(classification=classification, metrics=metrics),
        next_follow_up_experiments=_follow_up_experiments(classification=classification, metrics=metrics),
        effective_orders_submitted=effective_orders_submitted,
        effective_orders_rejected=effective_orders_rejected,
        effective_orders_filled=effective_orders_filled,
        effective_trades_closed=effective_trades_closed,
        effective_fill_rate=effective_fill_rate,
        effective_closed_trade_net_pnl=effective_closed_trade_net_pnl,
        recovered_closed_trade_count=diagnostics.recovered_closed_trade_count,
        recovered_closed_trade_net_pnl=diagnostics.recovered_closed_trade_net_pnl,
        state_status=(runtime_state.status.value if runtime_state is not None else None),
        total_equity=(runtime_state.total_equity if runtime_state is not None else None),
        today_pnl=(runtime_state.today_pnl if runtime_state is not None else None),
        metrics=metrics,
        event_diagnostics=diagnostics,
    )


def format_autoresearch_report(report: AutoresearchReport) -> str:
    lines = [
        "# Autoresearch Report",
        "",
        f"- generated_at: {report.generated_at.isoformat()}",
        f"- classification: {report.classification}",
        f"- score: {report.score:.4f}",
        f"- metrics_path: {report.metrics_path}",
        f"- event_path: {report.event_path or ''}",
        f"- state_path: {report.state_path or ''}",
        "",
        "## Objective",
        "",
        f"- {report.rewritten_objective}",
        "",
        "## Baseline",
        "",
        f"- signals_generated: {int(report.metrics.get('signals_generated', 0))}",
        f"- orders_submitted: {report.effective_orders_submitted}",
        f"- orders_rejected: {report.effective_orders_rejected}",
        f"- orders_filled: {report.effective_orders_filled}",
        f"- orders_partially_filled: {int(report.metrics.get('orders_partially_filled', 0))}",
        f"- orders_expired: {int(report.metrics.get('orders_expired', 0))}",
        f"- trades_closed: {report.effective_trades_closed}",
        f"- fill_rate: {report.effective_fill_rate:.4f}",
        f"- cancel_rate: {float(report.metrics.get('cancel_rate', 0.0)):.4f}",
        f"- avg_fill_price_vs_mid_bps: {float(report.metrics.get('avg_fill_price_vs_mid_bps', 0.0)):.2f}",
        f"- capacity_bound_rejection_ratio: {report.event_diagnostics.capacity_bound_rejection_ratio:.4f}",
        f"- closed_trade_net_pnl: {report.effective_closed_trade_net_pnl:.6f}",
    ]
    if report.event_diagnostics.has_session_scope:
        lines.append("- session_scoped_baseline: true")
        if report.recovered_closed_trade_count > 0:
            lines.append(f"- recovered_closed_trades: {report.recovered_closed_trade_count}")
            lines.append(
                f"- recovered_closed_trade_net_pnl: {report.recovered_closed_trade_net_pnl:.6f}"
            )
    if report.state_status is not None:
        lines.extend(
            [
                f"- runtime_status: {report.state_status}",
                f"- total_equity: {report.total_equity:.4f}" if report.total_equity is not None else "- total_equity: ",
                f"- today_pnl: {report.today_pnl:.4f}" if report.today_pnl is not None else "- today_pnl: ",
            ]
        )
    lines.extend(
        [
            "",
            "## Dominant Rejection Reasons",
            "",
        ]
    )
    if report.dominant_rejection_reasons:
        for reason, count in report.dominant_rejection_reasons:
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Fill Sources",
            "",
        ]
    )
    if report.fill_source_mix:
        for source, count in report.fill_source_mix:
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- none")

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
    for experiment in report.experiment_matrix:
        lines.append(f"- {experiment.name}: {', '.join(experiment.parameters)}")
        lines.append(f"  rationale: {experiment.rationale}")
        lines.append(f"  expected_effect: {experiment.expected_effect}")

    lines.extend(
        [
            "",
            "## Next Follow-Ups",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report.next_follow_up_experiments)
    return "\n".join(lines)


def write_autoresearch_report(report: AutoresearchReport, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_autoresearch_report(report), encoding="utf-8")


def _summarize_event_log(path: str | Path | None) -> EventDiagnostics:
    event_counts: Counter[str] = Counter()
    rejection_reasons: Counter[str] = Counter()
    fill_sources: Counter[str] = Counter()
    closed_trade_net_pnl = 0.0
    session_rejection_reasons: Counter[str] = Counter()
    session_fill_sources: Counter[str] = Counter()
    session_fill_event_count = 0
    session_submitted_order_ids: set[str] = set()
    session_filled_order_ids: set[str] = set()
    session_closed_trade_count = 0
    session_closed_trade_net_pnl = 0.0
    recovered_closed_trade_count = 0
    recovered_closed_trade_net_pnl = 0.0
    if path is None:
        return EventDiagnostics(
            event_counts={},
            rejection_reasons={},
            fill_sources={},
            closed_trade_net_pnl=0.0,
            session_rejection_reasons={},
            session_fill_sources={},
            session_fill_event_count=0,
            session_submitted_order_count=0,
            session_filled_order_count=0,
            session_closed_trade_count=0,
            session_closed_trade_net_pnl=0.0,
            recovered_closed_trade_count=0,
            recovered_closed_trade_net_pnl=0.0,
        )

    event_path = Path(path)
    if not event_path.exists():
        raise FileNotFoundError(event_path)

    with event_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            event = json.loads(line)
            event_type = str(event.get("event_type", "")).strip()
            if not event_type:
                continue
            event_counts[event_type] += 1
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            strategy_id = str(payload.get("strategy_id", "")).strip()
            is_recovered = strategy_id == "recovered.live"
            if event_type == "order.submitted" and not is_recovered:
                order_id = str(payload.get("order_id", "")).strip()
                if order_id:
                    session_submitted_order_ids.add(order_id)
            if event_type == "order.rejected":
                reason = str(payload.get("reason", "")).strip()
                if reason:
                    rejection_reasons[reason] += 1
                    if not is_recovered:
                        session_rejection_reasons[reason] += 1
            elif event_type in {"order.filled", "order.partially_filled"}:
                fill_source = str(payload.get("fill_source", "")).strip() or "unknown"
                fill_sources[fill_source] += 1
                if not is_recovered:
                    session_fill_sources[fill_source] += 1
                    session_fill_event_count += 1
                    order_id = str(payload.get("order_id", "")).strip()
                    if order_id:
                        session_filled_order_ids.add(order_id)
            elif event_type == "trade.closed":
                net_pnl = float(payload.get("net_pnl", 0.0) or 0.0)
                closed_trade_net_pnl += net_pnl
                if is_recovered:
                    recovered_closed_trade_count += 1
                    recovered_closed_trade_net_pnl += net_pnl
                else:
                    session_closed_trade_count += 1
                    session_closed_trade_net_pnl += net_pnl

    return EventDiagnostics(
        event_counts=dict(sorted(event_counts.items())),
        rejection_reasons=dict(sorted(rejection_reasons.items())),
        fill_sources=dict(sorted(fill_sources.items())),
        closed_trade_net_pnl=closed_trade_net_pnl,
        session_rejection_reasons=dict(sorted(session_rejection_reasons.items())),
        session_fill_sources=dict(sorted(session_fill_sources.items())),
        session_fill_event_count=session_fill_event_count,
        session_submitted_order_count=len(session_submitted_order_ids),
        session_filled_order_count=len(session_filled_order_ids),
        session_closed_trade_count=session_closed_trade_count,
        session_closed_trade_net_pnl=session_closed_trade_net_pnl,
        recovered_closed_trade_count=recovered_closed_trade_count,
        recovered_closed_trade_net_pnl=recovered_closed_trade_net_pnl,
    )


def _load_runtime_state(path: str | Path | None) -> RuntimeState | None:
    if path is None:
        return None
    state_path = Path(path)
    if not state_path.exists():
        raise FileNotFoundError(state_path)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Runtime state payload must be a JSON object")
    return runtime_state_from_dict(payload)


def _classify_baseline(*, metrics: dict[str, Any], diagnostics: EventDiagnostics) -> str:
    signals_generated = int(metrics.get("signals_generated", 0) or 0)
    orders_submitted = diagnostics.effective_orders_submitted(metrics)
    orders_rejected = diagnostics.effective_orders_rejected(metrics)
    fills = diagnostics.effective_filled_orders(metrics)
    expired = int(metrics.get("orders_expired", 0) or 0) + int(metrics.get("orders_canceled", 0) or 0)
    trades_closed = diagnostics.effective_closed_trade_count(metrics)
    market_data_failures = int(metrics.get("market_data_failures", 0) or 0)

    submission_rate = _safe_ratio(orders_submitted, signals_generated)
    if (
        signals_generated >= 100
        and orders_rejected >= max(orders_submitted * 5, 25)
        and diagnostics.capacity_bound_rejection_ratio >= 0.5
        and submission_rate <= 0.05
    ):
        return "capacity-bound"

    if market_data_failures > 0 and orders_submitted == 0 and fills == 0:
        return "data-bound"

    if signals_generated == 0 and orders_submitted == 0 and orders_rejected == 0 and fills == 0:
        return "alpha-bound"

    if orders_submitted > 0 and fills <= max(1, orders_submitted // 10) and expired >= max(1, orders_submitted // 2):
        return "execution-bound"

    if trades_closed > 0 and diagnostics.effective_closed_trade_net_pnl <= 0:
        return "alpha-bound"

    if market_data_failures > 0 and diagnostics.capacity_bound_rejection_ratio < 0.25:
        return "data-bound"

    if fills > 0 and trades_closed > 0:
        return "alpha-bound"

    if orders_submitted > 0:
        return "execution-bound"
    return "capacity-bound"


def _compute_score(*, metrics: dict[str, Any], diagnostics: EventDiagnostics) -> float:
    orders_submitted = diagnostics.effective_orders_submitted(metrics)
    orders_rejected = diagnostics.effective_orders_rejected(metrics)
    rejected_ratio = _safe_ratio(orders_rejected, orders_rejected + orders_submitted)
    effective_fill_rate = diagnostics.effective_fill_rate(metrics)
    effective_trades_closed = diagnostics.effective_closed_trade_count(metrics)
    return (
        (8.0 * diagnostics.effective_closed_trade_net_pnl)
        + (3.0 * float(effective_trades_closed))
        + (10.0 * effective_fill_rate)
        - (6.0 * float(metrics.get("cancel_rate", 0.0) or 0.0))
        - (8.0 * rejected_ratio)
        - (10.0 * diagnostics.capacity_bound_rejection_ratio)
        - (3.0 * float(metrics.get("market_data_failures", 0) or 0))
        - (0.05 * abs(float(metrics.get("avg_fill_price_vs_mid_bps", 0.0) or 0.0)))
    )


def _rewritten_objective(*, classification: str, metrics: dict[str, Any]) -> str:
    if classification == "capacity-bound":
        return (
            "Increase useful submissions and fills per fixed safety budget by reducing low-value "
            "signal generation before daily limits and concurrency gates saturate."
        )
    if classification == "execution-bound":
        return (
            "Increase fill quality and completed trade count for approved orders without changing "
            "account-level risk caps."
        )
    if classification == "data-bound":
        return "Reduce data interruptions and stale execution inputs before tuning strategy parameters."
    if _is_zero_activity_alpha_bound(metrics):
        return (
            "Find replay windows and ladder series with demonstrable tradable alpha before further "
            "execution tuning, because the current baseline produces no useful submissions."
        )
    return "Improve closed-trade quality and downside behavior on the existing opportunity set."


def _experiment_matrix(*, classification: str, metrics: dict[str, Any]) -> tuple[ExperimentSuggestion, ...]:
    if classification == "capacity-bound":
        return (
            ExperimentSuggestion(
                name="Tighten maker spread floor",
                parameters=("strategy.maker.min_spread_bps",),
                rationale="Maker dominates signal volume and is burning the fixed order budget on low-selectivity opportunities.",
                expected_effect="Lower signal pressure and fewer hard-limit rejects before the first useful fills.",
            ),
            ExperimentSuggestion(
                name="Throttle failed markets before global churn",
                parameters=(
                    "strategy.maker.failure_cooldown_seconds",
                    "strategy.maker.min_requote_edge_improvement_bps",
                    "strategy.maker.failure_reentry_edge_improvement_bps",
                ),
                rationale="Capacity-bound runs usually need maker to stop revisiting the same recently failed market unless the next quote is materially better.",
                expected_effect="Lower repeated intent pressure on churn-heavy markets without suppressing the rest of the book.",
            ),
            ExperimentSuggestion(
                name="Lengthen maker quote lifetime",
                parameters=("strategy.maker.quote_ttl_seconds",),
                rationale="Recent paper runs show high expiry counts relative to fills, which suggests quotes are churning faster than they convert.",
                expected_effect="Fewer expiries and better chance that submitted quotes survive long enough to fill.",
            ),
        )
    if classification == "execution-bound":
        return (
            ExperimentSuggestion(
                name="Adjust maker quote lifetime and spread together",
                parameters=("strategy.maker.quote_ttl_seconds", "strategy.maker.min_spread_bps"),
                rationale="Execution-bound runs usually need a better balance between quote persistence and adverse-selection risk.",
                expected_effect="Higher fill rate with lower expiry churn.",
            ),
            ExperimentSuggestion(
                name="Tune market-local failure cooldown",
                parameters=(
                    "strategy.maker.failure_cooldown_seconds",
                    "strategy.maker.min_requote_edge_improvement_bps",
                    "strategy.maker.failure_reentry_edge_improvement_bps",
                ),
                rationale="Once execution is the bottleneck, recently expired or replaced markets need a local pause instead of a strategy-wide brake.",
                expected_effect="Better fill opportunity coverage outside churn-heavy markets.",
            ),
            ExperimentSuggestion(
                name="Tune maker inventory skew",
                parameters=("strategy.maker.inventory_skew_strength",),
                rationale="Inventory skew changes whether fills accumulate into positions that can be exited cleanly.",
                expected_effect="Less inventory drag and better exit quality.",
            ),
        )
    if classification == "data-bound":
        return (
            ExperimentSuggestion(
                name="Stabilize data collection before tuning",
                parameters=(),
                rationale="Data-bound runs invalidate parameter search because strategy comparisons are contaminated by missing or stale inputs.",
                expected_effect="Cleaner baseline artifacts for future train/validation loops.",
            ),
            ExperimentSuggestion(
                name="Shorten candidate windows until data is stable",
                parameters=(),
                rationale="Smaller verified windows are more useful than long noisy windows when recovery behavior is still under investigation.",
                expected_effect="Faster iteration with trustworthy baselines.",
            ),
            ExperimentSuggestion(
                name="Re-run fixed-window paper after data fixes",
                parameters=(),
                rationale="Do not search strategy space until data-bound symptoms stop dominating the artifact set.",
                expected_effect="Prevents tuning around infrastructure noise.",
            ),
        )
    if _is_zero_activity_alpha_bound(metrics):
        return (
            ExperimentSuggestion(
                name="Mine eventful fixed windows",
                parameters=(),
                rationale="Zero-activity alpha-bound runs should first isolate windows with fills, closes, or meaningful order lifecycle events before searching execution parameters.",
                expected_effect="Higher-signal train/validation windows that can distinguish missing alpha from missing execution opportunities.",
            ),
            ExperimentSuggestion(
                name="Recalibrate ladder fair value",
                parameters=("strategy.surface.min_edge_bps", "strategy.surface.max_curve_mispricing_bps"),
                rationale="When no trades are even attempted, the likely bottleneck is fair-value conservatism or series selection, not exit plumbing.",
                expected_effect="Restores a non-empty opportunity set on windows where repricing actually occurs.",
            ),
            ExperimentSuggestion(
                name="Tighten runtime market selection separately from pricing",
                parameters=("strategy.phase2.maker_min_edge_bps", "strategy.phase2.resolution_maker_min_edge_bps"),
                rationale="Selection should exclude structurally bad ladders without collapsing every runtime window to zero activity.",
                expected_effect="Cleaner surviving ladders and clearer evidence about whether any family still contains alpha.",
            ),
        )
    return (
        ExperimentSuggestion(
            name="Tighten surface entries",
            parameters=("strategy.surface.min_edge_bps", "strategy.surface.max_curve_mispricing_bps"),
            rationale="Alpha-bound runs need a cleaner opportunity set before changing safety behavior.",
            expected_effect="Fewer low-quality entries and better per-trade expectancy.",
        ),
        ExperimentSuggestion(
            name="Tune surface exits and stop-loss",
            parameters=("strategy.surface.exit_edge_bps", "strategy.surface.stop_loss_bps"),
            rationale="Closed-trade quality is already observable, so exits are the highest-leverage local control.",
            expected_effect="Improved closed-trade PnL and downside containment.",
        ),
        ExperimentSuggestion(
            name="Tune maker inventory skew",
            parameters=("strategy.maker.inventory_skew_strength",),
            rationale="Inventory pressure often leaks alpha through slow exits and overexposure to one side.",
            expected_effect="Cleaner inventory normalization and less forced-loss behavior.",
        ),
    )


def _follow_up_experiments(*, classification: str, metrics: dict[str, Any]) -> tuple[str, ...]:
    if classification == "capacity-bound":
        return (
            "Build a score wrapper that penalizes capacity-bound rejection ratio directly on timestamped paper-session artifacts.",
            "Split fixed windows by day and compare signal-to-submission efficiency before and after maker selectivity changes.",
            "Only move to replay/backtest after useful submissions rise without touching hard limits.",
        )
    if classification == "execution-bound":
        return (
            "Replay deterministic book windows that contain expiries and compare fill-rate changes across narrow TTL/spread moves.",
            "Track maker versus taker fill-source mix per candidate, not just aggregate fill rate.",
            "Reject any candidate that raises fill rate only by worsening avg_fill_price_vs_mid_bps materially.",
        )
    if classification == "data-bound":
        return (
            "Instrument data-failure windows and verify whether failures cluster around bootstrap or websocket recovery.",
            "Keep candidate tuning paused until market_data_failures stop dominating the run narrative.",
            "After data fixes, regenerate a fresh timestamped baseline before any parameter search.",
        )
    if _is_zero_activity_alpha_bound(metrics):
        return (
            "Run mine-fixed-windows on the latest long paper-session snapshot and event captures, then promote only fill-bearing windows with strong edge_after_cost_proxy/fill_density into the fixed-window experiment set.",
            "Compare ETH and BTC ladders separately so overpriced yearly strips do not drown out shorter-lived repricing windows.",
            "Do not spend more iterations on maker TTL or taker premium until at least one replay window shows non-zero useful submissions under the current fair-value stack.",
        )
    return (
        "Build train/validation/holdout replay windows around the strategy that produced the losing closed trades.",
        "Compare alpha candidates with the repo-local score first, then with replay/backtest confirmation.",
        "Do not widen scope beyond one strategy until closed-trade quality improves on validation windows.",
    )


def _is_zero_activity_alpha_bound(metrics: dict[str, Any]) -> bool:
    return (
        int(metrics.get("signals_generated", 0) or 0) == 0
        and int(metrics.get("orders_submitted", 0) or 0) == 0
        and int(metrics.get("orders_rejected", 0) or 0) == 0
        and int(metrics.get("orders_filled", 0) or 0) == 0
        and int(metrics.get("orders_partially_filled", 0) or 0) == 0
        and int(metrics.get("trades_closed", 0) or 0) == 0
    )


def _top_items(counter: dict[str, int], *, limit: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)
