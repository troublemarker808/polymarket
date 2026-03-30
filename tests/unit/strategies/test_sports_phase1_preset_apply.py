from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.sports.phase1.preset_apply import apply_sports_preset_change_package
from pm_bot.strategies.sports.phase1.preset_apply_plan import build_sports_preset_apply_plan


def test_build_sports_preset_apply_plan_reviews_when_ready() -> None:
    package = type(
        "Package",
        (),
        {
            "next_working_preset": "selection_higher_edge_gate",
            "ready_to_apply": True,
            "patch": {"selection_higher_edge_gate": {"match": {}, "overrides": {}}},
        },
    )()
    plan = build_sports_preset_apply_plan(package=package)
    assert plan.apply_mode == "review_then_apply"
    assert not plan.blockers


def test_apply_sports_preset_change_package_writes_applied_config(tmp_path: Path) -> None:
    package_path = tmp_path / "sports-change-package.json"
    target_path = tmp_path / "sports.v1.toml"
    output_path = tmp_path / "sports.applied.toml"
    package_path.write_text(
        json.dumps(
            {
                "ready_to_apply": True,
                "next_working_preset": "selection_higher_edge_gate",
                "patch": {
                    "selection_higher_edge_gate": {
                        "match": {"league": "nba", "market_family": "moneyline"},
                        "overrides": {"min_edge_bps": 85.0},
                        "rationale": ["tighten selection"],
                        "focus": "selection",
                    }
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    target_path.write_text(
        'category = "sports"\n\n[strategy.anchor]\nmin_edge_bps = 300\n',
        encoding="utf-8",
    )

    result = apply_sports_preset_change_package(
        change_package_path=package_path,
        target_config_path=target_path,
        output_config_path=output_path,
    )

    assert result.applied is True
    assert result.next_working_preset == "selection_higher_edge_gate"
    rendered = output_path.read_text(encoding="utf-8")
    assert "[strategy.anchor.preset_registry.selection_higher_edge_gate.match]" in rendered
    assert "[strategy.live.preset_registry.selection_higher_edge_gate.match]" in rendered
    assert result.rollback_output_config_path.endswith("sports.applied.rollback.toml")
