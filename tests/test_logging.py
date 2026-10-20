import logging
import os
import re
from pathlib import Path

from engine.logging import enable_debug_logging, get_log_file, recent_log_lines


def _cleanup_file_handlers():
    root = logging.getLogger("sweepy")
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler)
            handler.close()


def test_get_log_file_defaults_to_logs_dir():
    path = get_log_file()
    assert re.fullmatch(r"sweepy_\d{8}_\d{6}_\d{6}\.log", os.path.basename(path))


def test_enable_debug_logging_writes_and_reads(tmp_path):
    try:
        log_file = enable_debug_logging(str(tmp_path))
        assert enable_debug_logging(str(tmp_path)) == log_file
        assert os.path.exists(log_file)

        logging.getLogger("sweepy").debug("debug marker")
        lines = recent_log_lines(str(tmp_path))
        assert any("debug marker" in line for line in lines)
    finally:
        _cleanup_file_handlers()


def test_enable_debug_logging_uses_separate_files_across_runs(tmp_path):
    try:
        first_log = enable_debug_logging(str(tmp_path))
        logging.getLogger("sweepy").debug("first run marker")
        _cleanup_file_handlers()

        second_log = enable_debug_logging(str(tmp_path))
        logging.getLogger("sweepy").debug("second run marker")

        assert first_log != second_log
        assert "first run marker" in Path(first_log).read_text(encoding="utf-8")
        assert "second run marker" in Path(second_log).read_text(encoding="utf-8")
        assert any("second run marker" in line for line in recent_log_lines(str(tmp_path)))
    finally:
        _cleanup_file_handlers()


def test_recent_log_lines_prefers_the_newest_name_on_equal_mtimes(tmp_path):
    older = tmp_path / "sweepy_20260101_000000_000000.log"
    newer = tmp_path / "sweepy_20260101_000001_000000.log"
    older.write_text("old\n", encoding="utf-8")
    newer.write_text("new\n", encoding="utf-8")
    stamp = 1_800_000_000
    os.utime(older, (stamp, stamp))
    os.utime(newer, (stamp, stamp))

    assert recent_log_lines(str(tmp_path)) == ["new\n"]


def test_recent_log_lines_missing_file_returns_empty(tmp_path):
    assert recent_log_lines(str(tmp_path)) == []
