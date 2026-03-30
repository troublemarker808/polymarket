from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategy_change_window import StrategyChangeWindow
from pm_bot.strategy_execute_window import execute_strategy_change_window
from pm_bot.strategy_governance import StrategyGovernanceBoardStatus, StrategyGovernanceReport


def test_execute_strategy_change_window_applies_ready_boards(tmp_path: Path) -> None:
    crypto_package = _write_json(
        tmp_path / "crypto-package.json",
        {
            "ready_to_apply": True,
            "next_working_preset": "btc-fast",
            "patch": {"btc-fast": {"match": {"underlying": "BTC"}}},
        },
    )
    sports_package = _write_json(
        tmp_path / "sports-package.json",
        {
            "ready_to_apply": False,
            "next_working_preset": "nba-tight",
            "patch": {},
        },
    )
    weather_package = _write_json(
        tmp_path / "weather-package.json",
        {
            "ready_to_apply": True,
            "next_working_preset": "wx-strip",
            "patch": {"wx-strip": {"match": {"event_family": "daily_high_temperature_threshold"}}},
        },
    )
    crypto_target = _write_text(
        tmp_path / "crypto.toml",
        "[strategy.phase2]\n[strategy.phase2.preset_registry]\n",
    )
    weather_target = _write_text(
        tmp_path / "weather.toml",
        "[strategy.threshold]\n[strategy.threshold.preset_registry]\n\n[strategy.ensemble]\n[strategy.ensemble.preset_registry]\n",
    )

    governance = StrategyGovernanceReport(
        overall_action="apply",
        overall_reason="ready",
        next_step="apply ready boards",
        apply_ready_boards=("crypto", "weather"),
        rollback_boards=(),
        boards=(
            _board("crypto", "apply"),
            _board("sports", "hold"),
            _board("weather", "apply"),
        ),
        warnings=(),
    )
    window = StrategyChangeWindow(
        window_action="apply",
        first_step="apply crypto",
        apply_order=("crypto", "weather"),
        rollback_order=(),
        observe_order=(),
        steps=("apply crypto", "apply weather"),
    )

    report = execute_strategy_change_window(
        governance_report=governance,
        change_window=window,
        crypto_change_package_path=crypto_package,
        sports_change_package_path=sports_package,
        weather_change_package_path=weather_package,
        crypto_target_config_path=crypto_target,
        weather_target_config_path=weather_target,
    )

    assert report.executed is True
    assert report.halted is False
    assert [item.board for item in report.board_results] == ["crypto", "weather"]
    assert all(item.success for item in report.board_results)


def test_execute_strategy_change_window_rolls_back_before_other_actions(tmp_path: Path) -> None:
    backup = _write_text(tmp_path / "sports.applied.backup.toml", "[strategy.anchor]\n[strategy.anchor.preset_registry]\n")
    apply_result = _write_json(
        tmp_path / "sports-apply-result.json",
        {
            "backup_config_path": str(backup),
            "target_config_path": str(tmp_path / "sports.toml"),
            "rollback_output_config_path": str(tmp_path / "sports.rollback.toml"),
            "applied": True,
        },
    )
    governance = StrategyGovernanceReport(
        overall_action="rollback",
        overall_reason="rollback sports first",
        next_step="rollback",
        apply_ready_boards=("weather",),
        rollback_boards=("sports",),
        boards=(
            _board("sports", "rollback"),
            _board("weather", "apply"),
        ),
        warnings=(),
    )
    window = StrategyChangeWindow(
        window_action="stabilize",
        first_step="rollback sports",
        apply_order=("weather",),
        rollback_order=("sports",),
        observe_order=(),
        steps=("rollback sports", "hold weather"),
    )

    report = execute_strategy_change_window(
        governance_report=governance,
        change_window=window,
        sports_apply_result_path=apply_result,
    )

    assert report.executed is True
    assert report.halted is False
    assert [item.board for item in report.board_results] == ["sports"]
    assert report.board_results[0].executed_action == "rollback"


def _board(board: str, action: str) -> StrategyGovernanceBoardStatus:
    return StrategyGovernanceBoardStatus(
        board=board,
        next_working_preset=f"{board}-next",
        promotion_decision="promote_candidate",
        ready_to_apply=(action == "apply"),
        apply_mode="review_then_apply",
        applied=None,
        verification_decision=None,
        rollback_recommended=None,
        action=action,
        reason=action,
        warnings=(),
    )


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
