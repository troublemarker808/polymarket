from __future__ import annotations

import json
from pathlib import Path

from pm_bot.promotion_evidence import (
    build_promotion_evidence_report,
    format_promotion_evidence_report,
    write_promotion_evidence_report,
)


def test_build_promotion_evidence_report_accepts_stable_small_live_bundles(tmp_path: Path) -> None:
    bundle_paths = [
        _write_bundle(tmp_path / f"bundle-{index}.md", session_label=f"small-live-{index}")
        for index in range(3)
    ]

    report = build_promotion_evidence_report(
        stage="small_live_stability",
        bundle_paths=bundle_paths,
    )

    assert report.ready is True
    assert report.session_count == 3
    assert not report.blockers
    rendered = format_promotion_evidence_report(report)
    assert "Promotion Evidence Report" in rendered
    assert "small-live-0" in rendered


def test_build_promotion_evidence_report_blocks_pause_sessions(tmp_path: Path) -> None:
    stable = _write_bundle(tmp_path / "stable.md", session_label="stable")
    paused = _write_bundle(
        tmp_path / "paused.md",
        session_label="paused",
        overall_action="pause",
        alert_codes=("runtime_halted:stale_data",),
    )

    report = build_promotion_evidence_report(
        stage="sync_shadow_stability",
        bundle_paths=[stable, paused],
    )

    assert report.ready is False
    assert any("pause" in blocker for blocker in report.blockers)


def test_write_promotion_evidence_report_writes_sidecar_json(tmp_path: Path) -> None:
    bundle_paths = [
        _write_bundle(tmp_path / "bundle-a.md", session_label="sync-1"),
        _write_bundle(tmp_path / "bundle-b.md", session_label="sync-2"),
    ]
    report = build_promotion_evidence_report(
        stage="sync_shadow_stability",
        bundle_paths=bundle_paths,
    )

    output = write_promotion_evidence_report(
        path=tmp_path / "evidence.md",
        report=report,
    )

    assert output.exists()
    assert output.with_suffix(".json").exists()


def _write_bundle(
    path: Path,
    *,
    session_label: str,
    overall_action: str = "proceed",
    alert_codes: tuple[str, ...] = (),
    recommended_route_bias: str = "stable",
) -> Path:
    path.write_text("# Combined Operator Summary\n", encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "combined": {
                    "runtime_action": overall_action,
                    "runtime_decision": f"{overall_action}:clear",
                    "promotion_action": overall_action,
                    "promotion_decision": f"{overall_action}:ready=true:blockers=0:warnings=0",
                    "overall_action": overall_action,
                    "overall_decision": f"{overall_action}:runtime={overall_action}:alerts={len(alert_codes)}",
                    "next_step": "continue_current_window",
                    "rollback_target": None,
                    "alert_count": len(alert_codes),
                    "alert_codes": list(alert_codes),
                    "last_rejection_reason": None,
                },
                "artifacts": {
                    "session_label": session_label,
                    "metrics_path": "metrics.json",
                    "state_path": "state.json",
                    "event_path": "events.jsonl",
                    "note_path": None,
                    "event_count": 10,
                    "orders_submitted": 1,
                    "orders_filled": 1,
                },
                "execution_feedback": {
                    "maker_fill_rate": 0.5,
                    "taker_shortfall_bps": 1.0,
                    "repeated_expiration_rate": 0.1,
                    "repeated_stop_out_rate": 0.1,
                    "recommended_route_bias": recommended_route_bias,
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
