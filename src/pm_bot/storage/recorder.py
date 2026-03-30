"""Runtime event recorders."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from pm_bot.execution.paper_metrics import PaperExecutionMetrics


class InMemoryRecorder:
    """Simple recorder for tests and development."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(self, event_type: str, payload: Mapping[str, object]) -> None:
        self.events.append({"event_type": event_type, "payload": dict(payload)})


class JsonlRecorder:
    """Append normalized runtime events to a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def record(self, event_type: str, payload: Mapping[str, object]) -> None:
        line = json.dumps({"event_type": event_type, "payload": dict(payload)}, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")


class FanoutRecorder:
    """Mirror normalized runtime events to multiple recorder backends."""

    def __init__(self, *recorders: InMemoryRecorder | JsonlRecorder | ComparableRuntimeRecorder | None) -> None:
        self.recorders = tuple(recorder for recorder in recorders if recorder is not None)

    async def record(self, event_type: str, payload: Mapping[str, object]) -> None:
        for recorder in self.recorders:
            await recorder.record(event_type=event_type, payload=payload)


class ComparableRuntimeRecorder:
    """Persist runtime events and a paper-comparable execution metrics artifact."""

    def __init__(
        self,
        *,
        event_path: str | Path | None = None,
        metrics_path: str | Path | None = None,
    ) -> None:
        self.events: list[dict[str, Any]] = []
        self.metrics = PaperExecutionMetrics()
        self._event_recorder = JsonlRecorder(event_path) if event_path is not None else None
        self._metrics_path = Path(metrics_path) if metrics_path is not None else None

    async def record(self, event_type: str, payload: Mapping[str, object]) -> None:
        event = {"event_type": event_type, "payload": dict(payload)}
        self.events.append(event)
        self.metrics.record_event(event_type=event_type, payload=dict(payload))
        if self._event_recorder is not None:
            await self._event_recorder.record(event_type=event_type, payload=dict(payload))
        self._persist_metrics()

    def note_snapshot(self, *, timestamp: datetime, payload: Mapping[str, object] | None = None) -> None:
        self.metrics.note_snapshot(timestamp)
        if payload is not None:
            self.metrics.updated_at = str(payload.get("updated_at", self.metrics.updated_at))
        self._persist_metrics()

    def _persist_metrics(self) -> None:
        if self._metrics_path is None:
            return
        self.metrics.write(self._metrics_path)


class PaperRuntimeRecorder(ComparableRuntimeRecorder):
    """Persist paper runtime events and derived metrics."""


class LiveRuntimeRecorder(ComparableRuntimeRecorder):
    """Persist live runtime events and paper-comparable execution metrics."""
