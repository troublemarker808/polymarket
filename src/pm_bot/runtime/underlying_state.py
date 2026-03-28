"""Runtime providers for crypto underlying-state payloads."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState
from pm_bot.strategies.crypto.phase1.state_loader import load_underlying_states


class FileBackedUnderlyingStateProvider:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
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
