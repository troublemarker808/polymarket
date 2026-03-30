"""Repository validation entry point.

This module gives contributors one explicit command path for the core quality
gate and fails loudly when optional dev tools have not been installed yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
import subprocess
import sys


REQUIRED_DEV_TOOLS: dict[str, str] = {
    "pytest": "pytest>=8.3.3",
    "ruff": "ruff>=0.6.9",
    "mypy": "mypy>=1.11.2",
}


@dataclass(slots=True, frozen=True)
class ValidationCommand:
    label: str
    argv: tuple[str, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def missing_dev_tools() -> tuple[str, ...]:
    missing = [name for name in REQUIRED_DEV_TOOLS if find_spec(name) is None]
    return tuple(sorted(missing))


def validation_commands(*, python_executable: str | None = None) -> tuple[ValidationCommand, ...]:
    python_bin = python_executable or sys.executable
    return (
        ValidationCommand("tests", (python_bin, "-m", "pytest", "-q")),
        ValidationCommand("lint", (python_bin, "-m", "ruff", "check", "src", "tests")),
        ValidationCommand("type-check", (python_bin, "-m", "mypy", "src")),
    )


def print_missing_tools(missing: tuple[str, ...], *, python_executable: str | None = None) -> None:
    python_bin = python_executable or sys.executable
    requirement_specs = ", ".join(REQUIRED_DEV_TOOLS[name] for name in missing)
    print(f"[validate] missing dev tools: {', '.join(missing)}")
    print(f"[validate] expected optional dependencies: {requirement_specs}")
    print(f"[validate] install with: {python_bin} -m pip install -e .[dev]")


def run_validation(*, commands: tuple[ValidationCommand, ...], cwd: Path) -> int:
    for command in commands:
        formatted = " ".join(command.argv)
        print(f"[validate] running {command.label}: {formatted}")
        completed = subprocess.run(command.argv, cwd=cwd, check=False)
        if completed.returncode != 0:
            print(f"[validate] {command.label} failed with exit code {completed.returncode}")
            return completed.returncode
    print("[validate] all checks passed")
    return 0


def main() -> int:
    missing = missing_dev_tools()
    if missing:
        print_missing_tools(missing)
        return 2
    return run_validation(commands=validation_commands(), cwd=repo_root())


if __name__ == "__main__":
    raise SystemExit(main())
