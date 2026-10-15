from __future__ import annotations

import logging
import logging.handlers
import os
from typing import Optional

# The application directory is the repo root (one level above engine/).
_DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def default_log_dir() -> str:
    return _DEFAULT_LOG_DIR


def get_log_file(log_dir: Optional[str] = None) -> str:
    return os.path.join(log_dir or _DEFAULT_LOG_DIR, "sweepy.log")


def enable_debug_logging(log_dir: Optional[str] = None) -> str:
    """Attach a rotating file handler to the ``sweepy`` logger at DEBUG level.

    Idempotent: repeated calls keep a single file handler per path. Returns the
    resolved log file path.
    """
    root = logging.getLogger("sweepy")
    log_file = os.path.abspath(get_log_file(log_dir))

    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", "") == log_file:
            root.setLevel(logging.DEBUG)
            return log_file

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    return log_file


def recent_log_lines(log_dir: Optional[str] = None, lines: int = 50) -> list:
    """Return the trailing ``lines`` entries of the debug log ([] when absent)."""
    path = get_log_file(log_dir)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()[-lines:]
