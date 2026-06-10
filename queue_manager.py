"""Queue file manager: load, save, advance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from models import Task, TaskStatus


class QueueManager:
    """Reads/writes queue.json. In-memory state, persisted on every change."""

    def __init__(self, queue_path: str):
        self.queue_path = Path(queue_path)
        self._raw: dict = self._load()
        self.tasks: list[Task] = [Task.from_dict(t) for t in self._raw.get("tasks", [])]

    def _load(self) -> dict:
        with open(self.queue_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_next_pending(self) -> Optional[Task]:
        """Return the lowest-id task with status=pending, or None."""
        pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        if not pending:
            return None
        return sorted(pending, key=lambda t: t.id)[0]

    def save_task(self, task: Task) -> None:
        """Update a single task in the queue file. Preserves all other tasks and config."""
        for i, t in enumerate(self.tasks):
            if t.id == task.id:
                self.tasks[i] = task
                break
        else:
            raise ValueError(f"Task {task.id} not found in queue")
        self._persist()

    def _persist(self) -> None:
        self._raw["tasks"] = [t.to_dict() for t in self.tasks]
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self._raw, f, ensure_ascii=False, indent=2)

    def reset_in_flight(self) -> None:
        """Revert any PROCESSING/DOWNLOADING tasks back to PENDING.

        Called at startup to recover from a previous crash.
        """
        changed = False
        for t in self.tasks:
            if t.status in (TaskStatus.PROCESSING, TaskStatus.DOWNLOADING):
                t.status = TaskStatus.PENDING
                t.started_at = None
                changed = True
        if changed:
            self._persist()