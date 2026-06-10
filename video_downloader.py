"""Video download: HTTP primary + UI fallback."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import requests
from playwright.sync_api import BrowserContext, TimeoutError as PlaywrightTimeout

log = logging.getLogger("jimeng")

MIN_VIDEO_SIZE = 100 * 1024  # 100KB — anything smaller is suspect


def download_video_http(
    url: str,
    output_path: str,
    cookies: dict,
    min_size_bytes: int = MIN_VIDEO_SIZE,
    timeout: int = 300,
) -> bool:
    """Download video via direct HTTP. Returns True on success."""
    log.info(f"HTTP download: {url[:80]}... → {output_path}")
    try:
        response = requests.get(
            url,
            cookies=cookies,
            stream=True,
            timeout=timeout,
        )
        response.raise_for_status()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        size = out.stat().st_size
        if size < min_size_bytes:
            log.warning(
                f"Downloaded file is only {size} bytes (min {min_size_bytes}). "
                "Likely an error page — treating as failure."
            )
            out.unlink()
            return False
        log.info(f"Downloaded {size / 1024 / 1024:.2f} MB → {output_path}")
        return True
    except (requests.RequestException, OSError) as e:
        log.error(f"HTTP download failed: {e}")
        try:
            Path(output_path).unlink(missing_ok=True)
        except OSError:
            pass
        return False


def download_video_via_ui(
    context: BrowserContext,
    page_url: str,
    output_path: str,
    timeout_seconds: int = 60,
) -> bool:
    """Fallback: trigger download via UI hover+click, capture with expect_download."""
    log.info(f"UI download fallback from {page_url}")
    page = context.new_page()
    try:
        page.goto(page_url)
        try:
            video = page.locator("video").first
            video.wait_for(timeout=10000)
            video.hover()
            page.wait_for_timeout(500)
            download_btn = page.locator(
                "[aria-label*='下载'], button:has-text('下载'), [class*='download']"
            ).first
            with page.expect_download(timeout=timeout_seconds * 1000) as dl_info:
                download_btn.click()
            download = dl_info.value
            download.save_as(output_path)
            size = Path(output_path).stat().st_size
            log.info(f"UI download saved {size / 1024 / 1024:.2f} MB → {output_path}")
            return True
        except PlaywrightTimeout as e:
            log.error(f"UI download timed out: {e}")
            return False
    finally:
        page.close()