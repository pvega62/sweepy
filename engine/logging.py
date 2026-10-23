from __future__ import annotations

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

# The application directory is the repo root (one level above engine/).
_DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_FILE_PREFIX = "sweepy_"

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def default_log_dir() -> str:
    return _DEFAULT_LOG_DIR


def get_log_file(log_dir: Optional[str] = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return os.path.join(log_dir or _DEFAULT_LOG_DIR, f"{_LOG_FILE_PREFIX}{timestamp}.log")


def enable_debug_logging(log_dir: Optional[str] = None) -> str:
    """Attach a rotating file handler to the ``sweepy`` logger at DEBUG level.

    Idempotent for each log directory. Returns the resolved log file path.
    """
    root = logging.getLogger("sweepy")
    log_directory = os.path.abspath(log_dir or _DEFAULT_LOG_DIR)

    for handler in root.handlers:
        if not isinstance(handler, logging.FileHandler):
            continue
        handler_path = os.path.abspath(getattr(handler, "baseFilename", ""))
        handler_name = os.path.basename(handler_path)
        if (
            os.path.dirname(handler_path) == log_directory
            and handler_name.startswith(_LOG_FILE_PREFIX)
            and handler_name.endswith(".log")
        ):
            root.setLevel(logging.DEBUG)
            return handler_path

    log_file = os.path.abspath(get_log_file(log_directory))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    return log_file


def recent_log_lines(log_dir: Optional[str] = None, lines: int = 50) -> list:
    """Return trailing entries from the newest debug log ([] when absent)."""
    directory = log_dir or _DEFAULT_LOG_DIR
    if not os.path.isdir(directory):
        return []
    paths = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name == "sweepy.log" or (name.startswith(_LOG_FILE_PREFIX) and name.endswith(".log"))
    ]
    if not paths:
        return []
    # Log names embed a sortable timestamp, which breaks the ties Windows
    # file times produce when two handlers are created within one clock tick.
    path = max(paths, key=lambda p: (os.path.getmtime(p), os.path.basename(p)))
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()[-lines:]
