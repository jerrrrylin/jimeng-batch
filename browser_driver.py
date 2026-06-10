"""Playwright browser lifecycle: persistent context for login reuse."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Playwright, sync_playwright

from models import BrowserConfig


class BrowserDriver:
    """Wraps Playwright with a persistent user profile (cookies survive restarts)."""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> BrowserContext:
        """Launch Playwright + persistent context. Returns the context."""
        if self._context is not None:
            return self._context
        self._playwright = sync_playwright().start()
        profile_dir = Path(self.config.profile_dir).resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.config.headless,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled"],
        )
        return self._context

    def new_page(self):
        """Convenience: get a fresh page from the context."""
        ctx = self.start()
        # Reuse existing page if present (Jimeng is a SPA — fewer tabs is cleaner)
        if ctx.pages:
            return ctx.pages[0]
        return ctx.new_page()

    def stop(self) -> None:
        """Close browser + stop Playwright."""
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()