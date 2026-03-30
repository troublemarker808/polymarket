from __future__ import annotations

import subprocess

from pm_bot.validation import ValidationCommand, main, missing_dev_tools, run_validation, validation_commands


def test_missing_dev_tools_returns_sorted_names(monkeypatch) -> None:
    monkeypatch.setattr(
        "pm_bot.validation.find_spec",
        lambda name: None if name in {"ruff", "mypy"} else object(),
    )

    assert missing_dev_tools() == ("mypy", "ruff")


def test_validation_commands_use_requested_python_executable() -> None:
    commands = validation_commands(python_executable="python-bin")

    assert commands == (
        ValidationCommand("tests", ("python-bin", "-m", "pytest", "-q")),
        ValidationCommand("lint", ("python-bin", "-m", "ruff", "check", "src", "tests")),
        ValidationCommand("type-check", ("python-bin", "-m", "mypy", "src")),
    )


def test_run_validation_stops_after_first_failed_command(monkeypatch, tmp_path, capsys) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv: tuple[str, ...], cwd, check: bool) -> subprocess.CompletedProcess[str]:
        del cwd, check
        calls.append(argv)
        returncode = 1 if argv[2] == "ruff" else 0
        return subprocess.CompletedProcess(argv, returncode=returncode)

    monkeypatch.setattr("pm_bot.validation.subprocess.run", fake_run)

    exit_code = run_validation(
        commands=(
            ValidationCommand("tests", ("python", "-m", "pytest", "-q")),
            ValidationCommand("lint", ("python", "-m", "ruff", "check", "src", "tests")),
            ValidationCommand("type-check", ("python", "-m", "mypy", "src")),
        ),
        cwd=tmp_path,
    )

    captured = capsys.readouterr().out
    assert exit_code == 1
    assert calls == [
        ("python", "-m", "pytest", "-q"),
        ("python", "-m", "ruff", "check", "src", "tests"),
    ]
    assert "[validate] lint failed with exit code 1" in captured


def test_main_returns_missing_tools_exit_code(monkeypatch, capsys) -> None:
    monkeypatch.setattr("pm_bot.validation.missing_dev_tools", lambda: ("mypy", "ruff"))

    exit_code = main()

    captured = capsys.readouterr().out
    assert exit_code == 2
    assert "missing dev tools: mypy, ruff" in captured
    assert "pip install -e .[dev]" in captured


def test_main_runs_validation_when_tools_exist(monkeypatch) -> None:
    monkeypatch.setattr("pm_bot.validation.missing_dev_tools", lambda: ())
    monkeypatch.setattr(
        "pm_bot.validation.validation_commands",
        lambda: (ValidationCommand("tests", ("python", "-m", "pytest", "-q")),),
    )
    monkeypatch.setattr("pm_bot.validation.run_validation", lambda *, commands, cwd: 0)

    assert main() == 0
