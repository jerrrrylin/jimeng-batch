"""Main orchestrator: load config, drive browser, process queue."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from browser_driver import BrowserDriver
from config_loader import load_full_config
from jimeng_page import JimengPage
from logger_setup import setup_logger
from models import Task, TaskStatus
from queue_manager import QueueManager
from video_downloader import download_video_http, download_video_via_ui


def process_one_task(
    task: Task,
    queue: QueueManager,
    jimeng: JimengPage,
    config,
) -> bool:
    """Run one task end-to-end. Returns True on success, False on failure."""
    log = setup_logger(config.paths.logs_dir)
    log.info(f"Task {task.id}: start processing")

    # Pre-flight validation
    prompt_path = Path(task.prompt_file)
    if not prompt_path.exists():
        task.mark(TaskStatus.FAILED, f"Prompt file not found: {task.prompt_file}")
        queue.save_task(task)
        log.error(f"Task {task.id}: prompt file missing, marked failed")
        return False
    for ref in task.references:
        if not Path(ref).exists():
            task.mark(TaskStatus.FAILED, f"Reference not found: {ref}")
            queue.save_task(task)
            log.error(f"Task {task.id}: reference missing, marked failed")
            return False

    try:
        # Mark processing
        task.mark(TaskStatus.PROCESSING)
        queue.save_task(task)

        # Drive UI
        jimeng.navigate_home()
        jimeng.upload_references(task.references)
        prompt_text = prompt_path.read_text(encoding="utf-8")
        jimeng.fill_prompt(prompt_text)
        jimeng.set_parameters(task.params)
        jimeng.submit_generation()
        jimeng.wait_for_queue_accepted()
        jimeng.wait_for_generation_complete(
            poll_interval_seconds=config.timing.poll_interval_seconds,
            max_wait_minutes=config.timing.max_wait_minutes,
        )

        # Extract URL and download
        video_url = jimeng.extract_video_url()
        task.video_url = video_url
        task.mark(TaskStatus.DOWNLOADING)
        queue.save_task(task)

        # Try HTTP first
        cookies_list = jimeng.context.cookies()
        cookies_dict = {c["name"]: c["value"] for c in cookies_list}
        success = download_video_http(video_url, task.output, cookies_dict)

        # Fallback to UI
        if not success:
            log.warning(f"Task {task.id}: HTTP download failed, trying UI fallback")
            success = download_video_via_ui(
                jimeng.context, config.browser.start_url, task.output
            )

        if not success:
            raise RuntimeError("Both HTTP and UI download failed")

        task.mark(TaskStatus.COMPLETED)
        queue.save_task(task)
        log.info(f"Task {task.id}: completed successfully")
        return True

    except Exception as e:
        log.error(f"Task {task.id}: failed — {e}")
        task.retry_count += 1
        if task.retry_count > config.retries.max_task_retries:
            task.mark(TaskStatus.FAILED, str(e))
            queue.save_task(task)
            log.error(f"Task {task.id}: retries exhausted, marked failed")
            return False
        # Re-queue for retry
        task.status = TaskStatus.PENDING
        task.started_at = None
        queue.save_task(task)
        log.info(
            f"Task {task.id}: re-queued for retry "
            f"({task.retry_count}/{config.retries.max_task_retries})"
        )
        return False


def main(config_yaml: str = "config.yaml") -> int:
    cfg = load_full_config(config_yaml)
    log = setup_logger(cfg.config.paths.logs_dir)

    queue = QueueManager(cfg.config.paths.queue_file)
    queue.reset_in_flight()  # Recover from previous crash

    pending_count = sum(1 for t in queue.tasks if t.status == TaskStatus.PENDING)
    log.info(f"Starting Jimeng batch: {pending_count} pending tasks")

    with BrowserDriver(cfg.config.browser) as driver:
        context = driver.start()
        jimeng = JimengPage(context, cfg.config.browser.start_url)

        # Sanity check: logged in?
        jimeng.navigate_home()
        if not jimeng.is_logged_in():
            log.error("Not logged in. Please run with headless=False and scan QR code.")
            return 1

        while True:
            task = queue.get_next_pending()
            if task is None:
                log.info("All tasks done. Exiting.")
                break
            process_one_task(task, queue, jimeng, cfg.config)
            # Small breather between tasks
            time.sleep(3)

    return 0


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    sys.exit(main(config_path))
