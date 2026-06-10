"""Page object: all interactions with Jimeng's web UI.

Selectors marked with `# confirm via Inspector` MUST be verified against the
live site using Playwright Inspector (right-click → Inspect → copy selector).
The selectors below are educated guesses based on observed screenshots; they
will need adjustment after first integration test.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

from models import Task, TaskParams, TaskStatus

log = logging.getLogger("jimeng")

# -------------------------------------------------------------------
# Selector constants — UPDATE THESE after running integration test
# Use Playwright Inspector (browser devtools → "Pick inspector" icon)
# -------------------------------------------------------------------

# Input area
REFERENCE_UPLOAD_INPUT = "input[type='file']"  # file input is usually hidden
PROMPT_TEXTAREA = "textarea[placeholder*='上传最多12个参考素材']"  # confirm exact placeholder

# Parameter dropdowns (text content of the button)
PARAM_MODEL_BUTTON = "button:has-text('Seedance')"  # the model dropdown shows current model name
PARAM_ASPECT_BUTTON = "button:has-text('9:16')"
PARAM_DURATION_BUTTON = "button:has-text('5s')"

# Submit button (round button with up-arrow icon, bottom-right)
SUBMIT_BUTTON = "button[class*='submit']"  # confirm via Inspector

# Status indicators
STATUS_QUEUED_TEXT = "排队中"
STATUS_GENERATING_TEXT = "生成中"
# Video element when complete
VIDEO_ELEMENT = "video"


class JimengPage:
    """Wraps a Playwright page with Jimeng-specific interactions."""

    def __init__(self, context: BrowserContext, start_url: str):
        self.context = context
        self.start_url = start_url
        self.page: Page = context.pages[0] if context.pages else context.new_page()

    # ---- Task 7: Navigation ----

    def navigate_home(self) -> None:
        """Open Jimeng home, wait for input area to be ready."""
        log.info(f"Navigating to {self.start_url}")
        self.page.goto(self.start_url, wait_until="domcontentloaded")
        try:
            self.page.wait_for_selector(PROMPT_TEXTAREA, timeout=30000)
            log.info("Jimeng home loaded, input area ready")
        except PlaywrightTimeout:
            raise RuntimeError(
                "Jimeng home did not load prompt textarea within 30s. "
                "Check login status or selectors."
            )

    def is_logged_in(self) -> bool:
        """Heuristic: logged-in users see the prompt textarea."""
        try:
            self.page.wait_for_selector(PROMPT_TEXTAREA, timeout=5000)
            return True
        except PlaywrightTimeout:
            return False

    # ---- Task 8: Reference image upload ----

    def upload_references(self, image_paths: list[str]) -> None:
        """Upload reference images for the task."""
        if not image_paths:
            log.info("No reference images to upload")
            return

        log.info(f"Uploading {len(image_paths)} reference images")
        abs_paths = [str(Path(p).resolve()) for p in image_paths]

        file_input = self.page.locator(REFERENCE_UPLOAD_INPUT).first
        file_input.set_input_files(abs_paths)

        try:
            self.page.wait_for_function(
                f"document.querySelectorAll('img[src*=\"thumbnail\"], img[src*=\"preview\"]').length >= {len(abs_paths)}",
                timeout=30000,
            )
            log.info("All reference images uploaded and thumbnails visible")
        except PlaywrightTimeout:
            log.warning(
                "Could not confirm all thumbnails appeared within 30s. "
                "Upload may have partially failed — verify visually."
            )

    # ---- Task 9: Prompt fill + parameter setting ----

    def fill_prompt(self, prompt_text: str) -> None:
        """Fill the prompt textarea."""
        log.info(f"Filling prompt ({len(prompt_text)} chars)")
        textarea = self.page.locator(PROMPT_TEXTAREA).first
        textarea.click()
        textarea.fill("")
        if len(prompt_text) > 500:
            textarea.fill(prompt_text)
        else:
            textarea.type(prompt_text, delay=10)
        log.info("Prompt filled")

    def set_parameters(self, params: TaskParams) -> None:
        """Click each parameter dropdown and select the target value."""
        log.info(f"Setting parameters: {params}")
        self._select_dropdown("Seedance", params.model)
        self._select_dropdown_ratio(params.aspect_ratio)
        self._select_dropdown_duration(params.duration)
        log.info("All parameters set")

    def _select_dropdown(self, current_value_hint: str, target_value: str) -> None:
        """Click a dropdown that contains current_value_hint, then click target_value."""
        if not target_value:
            return
        try:
            btn = self.page.locator(f"button:has-text('{current_value_hint}')").first
            btn.click()
            self.page.wait_for_selector("[role='listbox'], [class*='menu'], [class*='dropdown']", timeout=5000)
            option = self.page.locator(f"[role='option']:has-text('{target_value}'), li:has-text('{target_value}')").first
            option.click()
            log.info(f"Selected {target_value} from {current_value_hint} dropdown")
            self.page.wait_for_timeout(300)
        except PlaywrightTimeout:
            log.warning(f"Could not select {target_value} from {current_value_hint} dropdown (timeout)")

    def _select_dropdown_ratio(self, target: str) -> None:
        """Aspect ratio dropdown — match by exact text content."""
        try:
            btn = self.page.locator(f"button:has-text(':')").first
            btn.click()
            self.page.wait_for_selector("[role='listbox'], [class*='menu']", timeout=5000)
            option = self.page.locator(f"[role='option']:has-text('{target}')").first
            option.click()
            log.info(f"Set aspect ratio to {target}")
            self.page.wait_for_timeout(300)
        except PlaywrightTimeout:
            log.warning(f"Could not set aspect ratio {target}")

    def _select_dropdown_duration(self, target: str) -> None:
        """Duration dropdown — match by pattern like '5s', '10s'."""
        try:
            btn = self.page.locator(f"button:has-text('s')").first
            btn.click()
            self.page.wait_for_selector("[role='listbox'], [class*='menu']", timeout=5000)
            option = self.page.locator(f"[role='option']:has-text('{target}')").first
            option.click()
            log.info(f"Set duration to {target}")
            self.page.wait_for_timeout(300)
        except PlaywrightTimeout:
            log.warning(f"Could not set duration {target}")

    # ---- Task 10: Submit + state detection ----

    def submit_generation(self, timeout_seconds: int = 30) -> None:
        """Click the submit button. Verifies it's enabled first."""
        log.info("Looking for submit button")
        btn = self.page.locator(SUBMIT_BUTTON).first
        try:
            self.page.wait_for_function(
                """() => {
                    const btn = document.querySelector("button[class*='submit']");
                    return btn && !btn.disabled && !btn.getAttribute('aria-disabled');
                }""",
                timeout=timeout_seconds * 1000,
            )
        except PlaywrightTimeout:
            raise RuntimeError(
                f"Submit button did not become enabled within {timeout_seconds}s. "
                "Check parameters / image upload / account credits."
            )
        btn.click()
        log.info("Clicked submit button")

    def wait_for_queue_accepted(self, timeout_seconds: int = 60) -> None:
        """After submit, wait for confirmation that the task entered the queue."""
        log.info("Waiting for queue acceptance")
        try:
            self.page.wait_for_function(
                f"""() => document.body.innerText.includes('{STATUS_QUEUED_TEXT}')""",
                timeout=timeout_seconds * 1000,
            )
            log.info("Task entered queue (排队中 confirmed)")
        except PlaywrightTimeout:
            textarea = self.page.locator(PROMPT_TEXTAREA).first
            if textarea.input_value() == "":
                log.info("Prompt cleared — assuming submit accepted")
                return
            raise RuntimeError("Could not confirm task entered queue within timeout")

    def wait_for_generation_complete(
        self, poll_interval_seconds: int = 10, max_wait_minutes: int = 30
    ) -> None:
        """Block until generation completes. Polls DOM for <video> element."""
        log.info(f"Waiting for generation to complete (max {max_wait_minutes}min)")
        deadline = time.time() + max_wait_minutes * 60
        last_status = None
        while time.time() < deadline:
            video = self.page.query_selector(VIDEO_ELEMENT)
            if video:
                src = video.get_attribute("src") or ""
                if src:
                    log.info(f"Video element detected — generation complete")
                    return

            body_text = self.page.locator("body").inner_text()
            if STATUS_GENERATING_TEXT in body_text and last_status != "generating":
                log.info("Status: 生成中")
                last_status = "generating"
            elif STATUS_QUEUED_TEXT in body_text and last_status != "queued":
                log.info("Status: 排队中")
                last_status = "queued"

            time.sleep(poll_interval_seconds)

        raise TimeoutError(f"Generation did not complete within {max_wait_minutes} minutes")

    # ---- Task 11: Extract video URL ----

    def extract_video_url(self, timeout_seconds: int = 30) -> str:
        """Get the URL of the generated video."""
        log.info("Extracting video URL")
        video = self.page.locator(VIDEO_ELEMENT).first
        try:
            video.wait_for(timeout=timeout_seconds * 1000)
        except PlaywrightTimeout:
            raise RuntimeError("No <video> element found within timeout")
        src = video.get_attribute("src") or ""
        if src and not src.startswith("blob:"):
            log.info(f"Got video URL from <video src>: {src[:80]}...")
            return src

        log.info("Video src is blob URL, falling back to download button")
        return self._extract_url_via_download_button()

    def _extract_url_via_download_button(self) -> str:
        """Hover the video area, find download button, extract its URL."""
        try:
            video = self.page.locator(VIDEO_ELEMENT).first
            video.hover()
            self.page.wait_for_timeout(500)
            download_btn = self.page.locator(
                "[aria-label*='下载'], button:has-text('下载'), [class*='download']"
            ).first
            download_btn.wait_for(timeout=5000)
            url = (
                download_btn.get_attribute("href")
                or download_btn.get_attribute("data-url")
                or download_btn.get_attribute("data-href")
            )
            if url:
                log.info(f"Got video URL from download button: {url[:80]}...")
                return url
            raise RuntimeError("Download button found but no URL attribute")
        except PlaywrightTimeout:
            raise RuntimeError(
                "Could not find download button. The video element may need different interaction."
            )
