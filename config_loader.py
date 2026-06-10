"""High-level config loader: combines YAML config + queue.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from models import Config, Task, load_config


@dataclass
class FullConfig:
    config: Config
    tasks: list[Task]


def load_full_config(yaml_path: str, queue_path: Optional[str] = None) -> FullConfig:
    """Load YAML config and queue.json. If queue_path is None, uses default from YAML."""
    cfg = load_config(yaml_path)
    q_path = queue_path or cfg.paths.queue_file
    with open(q_path, "r", encoding="utf-8") as f:
        q_data = json.load(f)
    tasks = [Task.from_dict(t) for t in q_data.get("tasks", [])]
    return FullConfig(config=cfg, tasks=tasks)