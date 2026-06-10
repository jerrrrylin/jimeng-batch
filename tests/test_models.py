import json
from datetime import datetime
from models import Task, TaskStatus, TaskParams, load_config


def test_task_status_enum():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.PROCESSING == "processing"
    assert TaskStatus.DOWNLOADING == "downloading"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"


def test_task_params_defaults():
    params = TaskParams()
    assert params.model == "Seedance 2.0 Fast"
    assert params.reference_mode == "全能参考"
    assert params.aspect_ratio == "9:16"
    assert params.duration == "5s"
    assert params.count == 1


def test_task_from_dict():
    raw = {
        "id": "001",
        "references": ["inputs/001/ref1.jpg"],
        "prompt_file": "inputs/001/prompt.txt",
        "params": {"model": "Seedance 2.0 Fast"},
        "output": "outputs/001.mp4",
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "video_url": None,
        "retry_count": 0,
        "error": None,
    }
    task = Task.from_dict(raw)
    assert task.id == "001"
    assert task.status == TaskStatus.PENDING
    assert task.params.model == "Seedance 2.0 Fast"
    assert task.params.aspect_ratio == "9:16"  # default applied
    assert task.retry_count == 0


def test_task_to_dict_roundtrip():
    raw = {
        "id": "001",
        "references": ["inputs/001/ref1.jpg"],
        "prompt_file": "inputs/001/prompt.txt",
        "params": {"model": "Seedance 2.0 Fast", "count": 1, "reference_mode": "全能参考", "aspect_ratio": "9:16", "duration": "5s"},
        "output": "outputs/001.mp4",
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "video_url": None,
        "retry_count": 0,
        "error": None,
    }
    task = Task.from_dict(raw)
    roundtripped = task.to_dict()
    assert roundtripped == raw


def test_load_config_from_yaml(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "browser:\n  profile_dir: \"./p\"\n  headless: false\n  start_url: \"https://x\"\n"
        "timing:\n  poll_interval_seconds: 5\n  max_wait_minutes: 30\n  page_load_timeout_seconds: 60\n"
        "retries:\n  max_task_retries: 2\n  download_retries: 3\n"
        "paths:\n  queue_file: \"./q.json\"\n  inputs_dir: \"./in\"\n  outputs_dir: \"./out\"\n  logs_dir: \"./logs\"\n",
        encoding="utf-8",
    )
    cfg = load_config(str(config_yaml))
    assert cfg.browser.profile_dir == "./p"
    assert cfg.timing.poll_interval_seconds == 5
    assert cfg.retries.download_retries == 3