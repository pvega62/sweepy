from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import sqlite3
import time
from typing import Iterable, Optional

import pandas as pd

log = logging.getLogger("sweepy.engine.cache")

_SCHEMA_VERSION = "2"
_DEFAULT_DIR = os.path.join(os.path.expanduser("~"), ".sweepy")
_DEFAULT_NAME = "cache.db"


def default_cache_path() -> str:
    return os.environ.get("SWEEPY_CACHE_PATH") or os.path.join(_DEFAULT_DIR, _DEFAULT_NAME)


def cache_key(query: dict, sources: Iterable[str], engine_configs: Optional[dict] = None) -> str:
    """Hash the query, the enabled sources, and their config so runs never collide."""
    payload = json.dumps(
        {
            "v": _SCHEMA_VERSION,
            "query": query,
            "sources": sorted(sources),
            "config": engine_configs or {},
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResultCache:
    """SQLite-backed store for normalized results.

    Frames travel as JSON, never pickle, so a cache row cannot execute code.
    A missing or unreadable database degrades to "no cache" instead of failing a sweep.
    """

    def __init__(self, path: Optional[str] = None, ttl: float = 3600):
        self.path = path or default_cache_path()
        self.ttl = ttl

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, ts REAL, payload TEXT)"
        )
        conn.commit()
        return conn

    def load(self, key: str) -> Optional[pd.DataFrame]:
        if self.ttl <= 0:
            return None
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT ts, payload FROM cache WHERE key = ?", (key,)
                ).fetchone()
        except sqlite3.Error as exc:
            log.warning("Cache read failed: %s", exc)
            return None
        if not row:
            return None
        ts, payload = row
        if time.time() - float(ts) >= self.ttl:
            return None
        try:
            frame = pd.read_json(io.StringIO(payload), orient="split")
        except (ValueError, TypeError) as exc:
            log.warning("Cache row could not be decoded: %s", exc)
            return None
        # JSON turns an all-empty object column into float NaN; restore it so a
        # cached frame matches a fresh one.
        for column in frame.columns:
            if frame[column].isna().all():
                frame[column] = pd.Series([None] * len(frame), dtype=object)
        return frame

    def save(self, key: str, frame: pd.DataFrame) -> None:
        try:
            payload = frame.to_json(orient="split", default_handler=str)
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, ts, payload) VALUES (?, ?, ?)",
                    (key, time.time(), payload),
                )
                conn.commit()
        except (sqlite3.Error, ValueError, TypeError) as exc:
            log.warning("Cache write failed: %s", exc)

    def clear(self) -> int:
        try:
            with self._connect() as conn:
                deleted = conn.execute("DELETE FROM cache").rowcount
                conn.commit()
                return deleted
        except sqlite3.Error as exc:
            log.warning("Cache clear failed: %s", exc)
            return 0
