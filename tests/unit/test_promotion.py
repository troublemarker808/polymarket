from __future__ import annotations

import json
from pathlib import Path

import pytest

from pm_bot.promotion import format_promotion_readiness_report, validate_promotion_readiness
from pm_bot.runtime.state import RuntimeState, RuntimeStatus, runtime_state_to_dict


def test_validate_promotion_readiness_for_paper_to_sync_shadow_passes_clean_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pm_bot.promotion.describe_execution_configuration",
        lambda settings, env: {"allow_live_orders": settings.polymarket.allow_live_orders, "ready": True},
    )
    metrics_path, state_path, event_path = _write_runtime_artifacts(
        tmp_path=tmp_path,
        orders_submitted=2,
        processed_snapshots=20,
        halted=False,
    )

    report = validate_promotion_readiness(
        stage="paper_to_sync_shadow",
        source_config_dir="configs/profiles/paper-baseline-v1",
        target_config_dir="configs/profiles/sync-normal-shadow-v1",
        metrics_path=metrics_path,
        state_path=state_path,
        event_path=event_path,
        note_path=tmp_path / "note.md",
    )

    assert report.ready is True
    assert not report.blockers
    assert report.checks["target_mode"] == "live"
    assert report.rollback_triggers
    assert report.escalation_actions
    assert "ready: true" in format_promotion_readiness_report(report)


def test_validate_promotion_readiness_for_sync_shadow_requires_shadow_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pm_bot.promotion.describe_execution_configuration",
        lambda settings, env: {"allow_live_orders": settings.polymarket.allow_live_orders, "ready": True},
    )
    metrics_path, state_path, event_path = _write_runtime_artifacts(
        tmp_path=tmp_path,
        orders_submitted=1,
        processed_snapshots=12,
        halted=False,
    )

    report = validate_promotion_readiness(
        stage="sync_shadow_to_small_live_baseline",
        source_config_dir="configs/profiles/sync-normal-shadow-v1",
        target_config_dir="configs/profiles/small-live-baseline-v1",
        metrics_path=metrics_path,
        state_path=state_path,
        event_path=event_path,
    )

    assert report.ready is False
    assert any("shadow metrics/state/event artifacts" in blocker.lower() for blocker in report.blockers)


def test_validate_promotion_readiness_for_sync_shadow_accepts_paired_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pm_bot.promotion.describe_execution_configuration",
        lambda settings, env: {"allow_live_orders": settings.polymarket.allow_live_orders, "ready": True},
    )
    live_metrics_path, live_state_path, live_event_path = _write_runtime_artifacts(
        tmp_path=tmp_path / "live",
        orders_submitted=2,
        processed_snapshots=10,
        halted=False,
    )
    shadow_metrics_path, shadow_state_path, shadow_event_path = _write_runtime_artifacts(
        tmp_path=tmp_path / "shadow",
        orders_submitted=2,
        processed_snapshots=10,
        halted=False,
    )

    note_path = tmp_path / "operator-note.md"
    note_path.write_text("# note\n", encoding="utf-8")

    report = validate_promotion_readiness(
        stage="sync_shadow_to_small_live_baseline",
        source_config_dir="configs/profiles/sync-normal-shadow-v1",
        target_config_dir="configs/profiles/small-live-promotion-v1",
        metrics_path=live_metrics_path,
        state_path=live_state_path,
        event_path=live_event_path,
        shadow_metrics_path=shadow_metrics_path,
        shadow_state_path=shadow_state_path,
        shadow_event_path=shadow_event_path,
        note_path=note_path,
    )

    assert report.ready is True
    assert report.checks["paired_submissions"] == "live=2,shadow=2"
    assert report.checks["target_profile_role"] == "small-live-promotion-v1"


def _write_runtime_artifacts(
    *,
    tmp_path: Path,
    orders_submitted: int,
    processed_snapshots: int,
    halted: bool,
) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    metrics_path = tmp_path / "metrics.json"
    state_path = tmp_path / "state.json"
    event_path = tmp_path / "events.jsonl"
    metrics_path.write_text(
        json.dumps(
            {
                "processed_snapshots": processed_snapshots,
                "signals_generated": orders_submitted,
                "orders_submitted": orders_submitted,
                "orders_filled": 0,
                "market_data_failures": 0,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    state = RuntimeState(starting_equity=100.0, day_starting_equity=100.0)
    if halted:
        state.status = RuntimeStatus.HALTED
    state_path.write_text(json.dumps(runtime_state_to_dict(state), ensure_ascii=True, indent=2), encoding="utf-8")
    event_path.write_text(
        "\n".join(
            json.dumps(
                {"event_type": "market.snapshot_processed", "payload": {"market_id": f"m{index}"}},
                ensure_ascii=True,
            )
            for index in range(5)
        )
        + "\n",
        encoding="utf-8",
    )
    return metrics_path, state_path, event_path
