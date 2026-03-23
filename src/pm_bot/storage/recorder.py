"""Runtime event recorders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class InMemoryRecorder:
    """Simple recorder for tests and development."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        self.events.append({"event_type": event_type, "payload": payload})


class JsonlRecorder:
    """Append normalized runtime events to a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def record(self, event_type: str, payload: dict[str, object]) -> None:
        line = json.dumps({"event_type": event_type, "payload": payload}, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

