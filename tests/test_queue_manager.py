import json
import pytest
import tempfile

from models import Task, TaskStatus
from queue_manager import QueueManager


@pytest.fixture
def queue_file(tmp_path):
    p = tmp_path / "queue.json"
    p.write_text(
        json.dumps({
            "config": {},
            "tasks": [
                {"id": "001", "references": [], "prompt_file": "p1.txt",
                 "params": {}, "output": "o1.mp4", "status": "pending",
                 "started_at": None, "completed_at": None, "video_url": None,
                 "retry_count": 0, "error": None},
                {"id": "002", "references": [], "prompt_file": "p2.txt",
                 "params": {}, "output": "o2.mp4", "status": "completed",
                 "started_at": None, "completed_at": None, "video_url": None,
                 "retry_count": 0, "error": None},
                {"id": "003", "references": [], "prompt_file": "p3.txt",
                 "params": {}, "output": "o3.mp4", "status": "pending",
                 "started_at": None, "completed_at": None, "video_url": None,
                 "retry_count": 0, "error": None},
            ],
        }),
        encoding="utf-8",
    )
    return str(p)


def test_load_all_tasks(queue_file):
    qm = QueueManager(queue_file)
    assert len(qm.tasks) == 3


def test_get_next_pending_returns_oldest_pending(queue_file):
    qm = QueueManager(queue_file)
    task = qm.get_next_pending()
    assert task is not None
    assert task.id == "001"  # before 003


def test_get_next_pending_returns_none_if_no_pending(tmp_path):
    p = tmp_path / "queue.json"
    p.write_text(json.dumps({"config": {}, "tasks": []}), encoding="utf-8")
    qm = QueueManager(str(p))
    assert qm.get_next_pending() is None


def test_update_task_status_persists(queue_file):
    qm = QueueManager(queue_file)
    task = qm.get_next_pending()
    task.mark(TaskStatus.PROCESSING)
    qm.save_task(task)
    # Reload and check
    qm2 = QueueManager(queue_file)
    reloaded = next(t for t in qm2.tasks if t.id == "001")
    assert reloaded.status == TaskStatus.PROCESSING
    assert reloaded.started_at is not None


def test_save_task_preserves_other_tasks(queue_file):
    qm = QueueManager(queue_file)
    task = qm.get_next_pending()
    task.mark(TaskStatus.COMPLETED)
    task.video_url = "https://example.com/v.mp4"
    qm.save_task(task)
    qm2 = QueueManager(queue_file)
    assert len(qm2.tasks) == 3
    completed = next(t for t in qm2.tasks if t.id == "001")
    assert completed.status == TaskStatus.COMPLETED
    assert completed.video_url == "https://example.com/v.mp4"


def test_reset_in_flight_marks_processing_back_to_pending(queue_file):
    qm = QueueManager(queue_file)
    task = qm.get_next_pending()
    task.mark(TaskStatus.PROCESSING)
    qm.save_task(task)
    # Simulate crash — on restart, reset_in_flight rolls back PROCESSING → PENDING
    qm2 = QueueManager(queue_file)
    qm2.reset_in_flight()
    qm3 = QueueManager(queue_file)
    t = next(t for t in qm3.tasks if t.id == "001")
    assert t.status == TaskStatus.PENDING
    assert t.started_at is None