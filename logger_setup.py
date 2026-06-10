"""Logging configuration: file + console, daily rotation."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(logs_dir: str, name: str = "jimeng") -> logging.Logger:
    """Configure root logger with file + console handlers.

    Returns the configured logger. Idempotent — safe to call multiple times.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler — daily rotation by filename
    log_path = Path(logs_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        log_path / f"run-{today}.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger