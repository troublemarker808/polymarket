"""Minimal local .env loading for development and operator workflows."""

from __future__ import annotations

from pathlib import Path
import os


def load_local_env() -> None:
    """Load .env files without overriding real environment variables."""

    for env_path in _candidate_env_files():
        _load_env_file(env_path)


def _candidate_env_files() -> tuple[Path, ...]:
    discovered: list[Path] = []
    seen: set[Path] = set()
    roots = [Path.cwd(), Path(__file__).resolve()]

    for root in roots:
        current = root if root.is_dir() else root.parent
        for directory in (current, *current.parents):
            for filename in (".env", ".env.local"):
                candidate = directory / filename
                if candidate in seen or not candidate.is_file():
                    continue
                seen.add(candidate)
                discovered.append(candidate)

    return tuple(discovered)


def _load_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_quotes(value)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
