"""Persistence helpers for runtime state."""

from __future__ import annotations

import json
from pathlib import Path

from pm_bot.runtime.state import RuntimeState, runtime_state_from_dict, runtime_state_to_dict


class JsonRuntimeStateStore:
    """Persist runtime state to a JSON file for recovery and inspection."""

    def __init__(self, path: str | Path = "data/runtime/runtime_state.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: RuntimeState) -> None:
        payload = runtime_state_to_dict(state)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)

    def load(self) -> RuntimeState | None:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Runtime state file must contain a JSON object")
        return runtime_state_from_dict(payload)
