import json
from pathlib import Path

import pytest

from config_loader import load_full_config, FullConfig
from models import Task


@pytest.fixture
def setup_files(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "browser:\n  profile_dir: \"./p\"\n  headless: false\n  start_url: \"https://x\"\n"
        "timing:\n  poll_interval_seconds: 5\n  max_wait_minutes: 30\n  page_load_timeout_seconds: 60\n"
        "retries:\n  max_task_retries: 2\n  download_retries: 3\n"
        "paths:\n  queue_file: \"./q.json\"\n  inputs_dir: \"./in\"\n  outputs_dir: \"./out\"\n  logs_dir: \"./logs\"\n",
        encoding="utf-8",
    )
    queue_json = tmp_path / "q.json"
    queue_json.write_text(
        json.dumps({
            "config": {"poll_interval_seconds": 5, "max_wait_minutes": 30, "max_retries": 2, "download_retries": 3},
            "tasks": [
                {"id": "001", "references": [], "prompt_file": "p.txt",
                 "params": {}, "output": "o.mp4", "status": "pending",
                 "started_at": None, "completed_at": None, "video_url": None,
                 "retry_count": 0, "error": None},
            ],
        }),
        encoding="utf-8",
    )
    return config_yaml, queue_json


def test_load_full_config_merges_yaml_and_queue(setup_files):
    config_yaml, queue_json = setup_files
    full = load_full_config(str(config_yaml), str(queue_json))
    assert isinstance(full, FullConfig)
    assert full.config.browser.start_url == "https://x"
    assert len(full.tasks) == 1
    assert isinstance(full.tasks[0], Task)
    assert full.tasks[0].id == "001"


def test_load_full_config_uses_default_queue_path(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "browser:\n  profile_dir: \"./p\"\n  headless: false\n  start_url: \"https://x\"\n"
        "timing:\n  poll_interval_seconds: 5\n  max_wait_minutes: 30\n  page_load_timeout_seconds: 60\n"
        "retries:\n  max_task_retries: 2\n  download_retries: 3\n"
        "paths:\n  queue_file: \"./q.json\"\n  inputs_dir: \"./in\"\n  outputs_dir: \"./out\"\n  logs_dir: \"./logs\"\n",
        encoding="utf-8",
    )
    queue_json = tmp_path / "q.json"
    queue_json.write_text(
        json.dumps({"config": {}, "tasks": []}),
        encoding="utf-8",
    )
    full = load_full_config(str(config_yaml), str(queue_json))
    assert full.tasks == []