"""Runtime providers for crypto underlying-state payloads."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.state_loader import load_underlying_states


class FileBackedUnderlyingStateProvider:
    def __init__(self, path: str | Path) -> None:
        self.path = resolve_underlying_state_path(path)
        self._cached_fingerprint: str | None = None
        self._cached_states: dict[str, CryptoUnderlyingState] = {}

    def current_states(self) -> dict[str, CryptoUnderlyingState]:
        fingerprint = _file_fingerprint(self.path)
        if self._cached_fingerprint != fingerprint:
            self._cached_states = load_underlying_states(self.path)
            self._cached_fingerprint = fingerprint
        return dict(self._cached_states)


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read())
    return digest.hexdigest()


def resolve_underlying_state_path(path: str | Path) -> Path:
    candidate = Path(path)
    direct_path = candidate if candidate.is_absolute() else (Path.cwd() / candidate)
    if direct_path.exists():
        return direct_path

    fallback = _latest_runtime_underlying_state_candidate(candidate.name)
    if fallback is not None:
        return fallback

    raise FileNotFoundError(f"Unable to resolve underlying-state path: {candidate}")


def _latest_runtime_underlying_state_candidate(filename: str) -> Path | None:
    runtime_root = Path.cwd() / "data" / "runtime"
    if not runtime_root.exists():
        return None
    candidates = _existing_candidates(runtime_root.rglob(filename))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def _existing_candidates(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.is_file()]
