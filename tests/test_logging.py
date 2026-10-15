import logging
import os

from engine.logging import enable_debug_logging, get_log_file, recent_log_lines


def _cleanup_file_handlers():
    root = logging.getLogger("sweepy")
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler)
            handler.close()


def test_get_log_file_defaults_to_logs_dir():
    path = get_log_file()
    assert os.path.basename(path) == "sweepy.log"


def test_enable_debug_logging_writes_and_reads(tmp_path):
    try:
        log_file = enable_debug_logging(str(tmp_path))
        assert os.path.exists(log_file)

        logging.getLogger("sweepy").debug("debug marker")
        lines = recent_log_lines(str(tmp_path))
        assert any("debug marker" in line for line in lines)
    finally:
        _cleanup_file_handlers()


def test_recent_log_lines_missing_file_returns_empty(tmp_path):
    assert recent_log_lines(str(tmp_path)) == []
