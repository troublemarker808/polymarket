from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategy_loop_history import build_strategy_loop_history_report


def test_build_strategy_loop_history_report_detects_recurring_stabilize_and_learn(tmp_path: Path) -> None:
    one = _write_feedback(
        tmp_path / "one.json",
        overall_loop_action="stabilize",
        boards=[
            {"board": "sports", "loop_action": "stabilize"},
            {"board": "weather", "loop_action": "learn"},
        ],
    )
    two = _write_feedback(
        tmp_path / "two.json",
        overall_loop_action="learn",
        boards=[
            {"board": "sports", "loop_action": "stabilize"},
            {"board": "weather", "loop_action": "learn"},
        ],
    )

    report = build_strategy_loop_history_report(feedback_loop_paths=[one, two])

    assert report.window_count == 2
    assert report.recurring_stabilize_boards == ("sports",)
    assert report.recurring_learn_boards == ("weather",)
    assert report.recommended_mode == "stabilize"


def _write_feedback(path: Path, *, overall_loop_action: str, boards: list[dict[str, str]]) -> Path:
    path.write_text(
        json.dumps(
            {
                "overall_loop_action": overall_loop_action,
                "next_step": "continue",
                "boards": boards,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
