"""Data models for the Jimeng batch generator."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskParams:
    model: str = "Seedance 2.0 Fast"
    reference_mode: str = "全能参考"
    aspect_ratio: str = "9:16"
    duration: str = "5s"
    count: int = 1

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "reference_mode": self.reference_mode,
            "aspect_ratio": self.aspect_ratio,
            "duration": self.duration,
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskParams":
        return cls(
            model=data.get("model", "Seedance 2.0 Fast"),
            reference_mode=data.get("reference_mode", "全能参考"),
            aspect_ratio=data.get("aspect_ratio", "9:16"),
            duration=data.get("duration", "5s"),
            count=data.get("count", 1),
        )


@dataclass
class Task:
    id: str
    references: list[str]
    prompt_file: str
    params: TaskParams
    output: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    video_url: Optional[str] = None
    retry_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "references": list(self.references),
            "prompt_file": self.prompt_file,
            "params": self.params.to_dict(),
            "output": self.output,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "video_url": self.video_url,
            "retry_count": self.retry_count,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            references=list(data.get("references", [])),
            prompt_file=data["prompt_file"],
            params=TaskParams.from_dict(data.get("params", {})),
            output=data["output"],
            status=TaskStatus(data.get("status", "pending")),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            video_url=data.get("video_url"),
            retry_count=data.get("retry_count", 0),
            error=data.get("error"),
        )

    def mark(self, status: TaskStatus, error: Optional[str] = None) -> None:
        """Update status and timestamps."""
        self.status = status
        now = datetime.now().isoformat(timespec="seconds")
        if status == TaskStatus.PROCESSING:
            self.started_at = now
        elif status == TaskStatus.COMPLETED:
            self.completed_at = now
        if error is not None:
            self.error = error


@dataclass
class BrowserConfig:
    profile_dir: str
    headless: bool
    start_url: str


@dataclass
class TimingConfig:
    poll_interval_seconds: int
    max_wait_minutes: int
    page_load_timeout_seconds: int


@dataclass
class RetriesConfig:
    max_task_retries: int
    download_retries: int


@dataclass
class PathsConfig:
    queue_file: str
    inputs_dir: str
    outputs_dir: str
    logs_dir: str


@dataclass
class Config:
    browser: BrowserConfig
    timing: TimingConfig
    retries: RetriesConfig
    paths: PathsConfig


def load_config(yaml_path: str) -> Config:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(
        browser=BrowserConfig(**data["browser"]),
        timing=TimingConfig(**data["timing"]),
        retries=RetriesConfig(**data["retries"]),
        paths=PathsConfig(**data["paths"]),
    )