"""Persistent record of postings Sweepy already reported.

The scrape cache in :mod:`engine.cache` avoids re-fetching for an hour. This
module answers a different question: which postings has the user already seen,
so a daily sweep reports new roles instead of yesterday's list.

Rows travel as plain columns, never pickle, and any database problem degrades to
"no history" instead of failing a sweep.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import time
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

log = logging.getLogger("sweepy.engine.history")

_DEFAULT_DIR = os.path.join(os.path.expanduser("~"), ".sweepy")
_DEFAULT_NAME = "history.db"

_SECONDS_PER_DAY = 86400.0

MATCH_URL = "url"
MATCH_URL_OR_ROLE = "url+role"
_MATCH_MODES = (MATCH_URL, MATCH_URL_OR_ROLE)

# Parameters that identify a click path rather than a posting. Keeping the rest
# means a board's meaningful query string still separates two postings.
_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "gh_src",
    "icid",
    "lever-origin",
    "lever-source",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "refid",
    "source",
    "src",
    "trk",
    "trackingid",
    "tracking_id",
    "via",
    "yjsd",
}
_TRACKING_PREFIXES = ("utm_", "_hs", "hsa_")

_NON_ALNUM = re.compile(r"[\W_]+")


def default_history_path() -> str:
    return os.environ.get("SWEEPY_HISTORY_PATH") or os.path.join(_DEFAULT_DIR, _DEFAULT_NAME)


def _normalize_text(value: object) -> str:
    return _NON_ALNUM.sub("", str(value or "").casefold())


def canonical_url(url: object) -> str:
    """Return a stable identity for a posting URL.

    Scheme and host are lowercased, ``www.`` is dropped, fragments and common
    tracking parameters are removed, and the remaining query is sorted.
    """
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return raw.lower()
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"

    path = re.sub(r"/+$", "", parsed.path or "") or "/"

    pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lower = key.lower()
        if lower in _TRACKING_PARAMS or lower.startswith(_TRACKING_PREFIXES):
            continue
        pairs.append((key, value))
    pairs.sort()
    query = urlencode(pairs, doseq=True)

    return f"{scheme}://{netloc}{path}" + (f"?{query}" if query else "")


def url_key(url: object) -> str:
    """Hash a canonical URL so one posting can only produce one key."""
    canonical = canonical_url(url)
    if not canonical:
        return ""
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def role_key(title: object, company: object, location: object) -> str:
    """Hash a normalized title/company/location triple, matching ``dedupe_jobs``."""
    parts = [_normalize_text(value) for value in (title, company, location)]
    if not all(parts):
        return ""
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def history_scope(profile_stem: Optional[str]) -> str:
    """Turn a profile name into one stable history bucket."""
    scope = _NON_ALNUM.sub("_", str(profile_stem or "")).strip("_").lower()
    return scope or "default"


def build_history(runtime: Optional[dict]) -> Optional["SweepHistory"]:
    """Build the history store for a resolved profile, or ``None`` when disabled."""
    cfg = (runtime or {}).get("history") or {}
    if not cfg.get("enabled", True):
        return None
    return SweepHistory(
        path=cfg.get("path"),
        retention_days=cfg.get("retention_days", 4),
        match=cfg.get("match", MATCH_URL_OR_ROLE),
    )


class SweepHistory:
    """SQLite-backed store of postings already reported to the user.

    The retention window is a re-report cadence: a posting stays suppressed until
    ``retention_days`` have passed since it last reached a report. Postings that
    stay live refresh ``last_seen_at`` on every sweep, while postings that leave
    the boards stop refreshing and fall out of the table.
    """

    def __init__(
        self,
        path: Optional[str] = None,
        retention_days: float = 4,
        match: str = MATCH_URL_OR_ROLE,
    ):
        self.path = path or default_history_path()
        try:
            self.retention_days = max(0.0, float(retention_days))
        except (TypeError, ValueError):
            self.retention_days = 4.0
        self.match = match if match in _MATCH_MODES else MATCH_URL_OR_ROLE

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                scope TEXT NOT NULL,
                job_key TEXT NOT NULL,
                url_key TEXT,
                role_key TEXT,
                url TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                first_seen_at REAL NOT NULL,
                last_seen_at REAL NOT NULL,
                last_reported_at REAL NOT NULL,
                sweep_id TEXT,
                PRIMARY KEY (scope, job_key)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS seen_jobs_role ON seen_jobs(scope, role_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS seen_jobs_seen ON seen_jobs(last_seen_at)"
        )
        conn.commit()
        return conn

    def filter_new(
        self,
        jobs: Iterable[dict],
        scope: str,
        match: Optional[str] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """Split jobs into first-time and already-reported lists."""
        jobs = list(jobs or [])
        mode = match if match in _MATCH_MODES else self.match
        if not jobs or self.retention_days <= 0:
            return jobs, []

        cutoff = time.time() - self.retention_days * _SECONDS_PER_DAY
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT url_key, role_key FROM seen_jobs "
                    "WHERE scope = ? AND last_reported_at >= ?",
                    (scope, cutoff),
                ).fetchall()
        except (sqlite3.Error, OSError) as exc:
            log.warning("History read failed: %s", exc)
            return jobs, []

        seen_urls = {row[0] for row in rows if row[0]}
        seen_roles = {row[1] for row in rows if row[1]}

        fresh: List[dict] = []
        seen: List[dict] = []
        for job in jobs:
            ukey = url_key(job.get("url"))
            rkey = role_key(job.get("title"), job.get("company"), job.get("location"))
            reported = bool(ukey and ukey in seen_urls) or (
                mode == MATCH_URL_OR_ROLE and bool(rkey and rkey in seen_roles)
            )
            (seen if reported else fresh).append(job)

        self._touch(seen, scope, mode)
        return fresh, seen

    def _touch(self, jobs: List[dict], scope: str, mode: str) -> None:
        """Refresh ``last_seen_at`` for postings this sweep rediscovered."""
        if not jobs:
            return
        now = time.time()
        try:
            with self._connect() as conn:
                for job in jobs:
                    ukey = url_key(job.get("url"))
                    rkey = role_key(
                        job.get("title"), job.get("company"), job.get("location")
                    )
                    if mode == MATCH_URL_OR_ROLE and rkey:
                        conn.execute(
                            "UPDATE seen_jobs SET last_seen_at = ? "
                            "WHERE scope = ? AND (url_key = ? OR role_key = ?)",
                            (now, scope, ukey, rkey),
                        )
                    else:
                        conn.execute(
                            "UPDATE seen_jobs SET last_seen_at = ? "
                            "WHERE scope = ? AND url_key = ?",
                            (now, scope, ukey),
                        )
                conn.commit()
        except (sqlite3.Error, OSError) as exc:
            log.warning("History refresh failed: %s", exc)

    def record(
        self,
        jobs: Iterable[dict],
        scope: str,
        sweep_id: Optional[str] = None,
    ) -> int:
        """Mark jobs as reported now, preserving when each was first seen."""
        now = time.time()
        rows = []
        for job in jobs or []:
            ukey = url_key(job.get("url"))
            rkey = role_key(job.get("title"), job.get("company"), job.get("location"))
            if not (ukey or rkey):
                continue
            rows.append(
                (
                    scope,
                    ukey or rkey,
                    ukey,
                    rkey,
                    str(job.get("url") or ""),
                    str(job.get("title") or ""),
                    str(job.get("company") or ""),
                    str(job.get("location") or ""),
                    now,
                    now,
                    now,
                    sweep_id,
                )
            )
        if not rows:
            return 0
        try:
            with self._connect() as conn:
                conn.executemany(
                    """
                    INSERT INTO seen_jobs (
                        scope, job_key, url_key, role_key, url, title, company,
                        location, first_seen_at, last_seen_at, last_reported_at,
                        sweep_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(scope, job_key) DO UPDATE SET
                        url_key = excluded.url_key,
                        role_key = excluded.role_key,
                        url = excluded.url,
                        title = excluded.title,
                        company = excluded.company,
                        location = excluded.location,
                        last_seen_at = excluded.last_seen_at,
                        last_reported_at = excluded.last_reported_at,
                        sweep_id = excluded.sweep_id
                    """,
                    rows,
                )
                conn.commit()
                return len(rows)
        except (sqlite3.Error, OSError) as exc:
            log.warning("History write failed: %s", exc)
            return 0

    def prune(self) -> int:
        """Drop rows for postings that left the boards outside the retention window."""
        cutoff = time.time() - self.retention_days * _SECONDS_PER_DAY
        try:
            with self._connect() as conn:
                deleted = conn.execute(
                    "DELETE FROM seen_jobs WHERE last_seen_at < ?", (cutoff,)
                ).rowcount
                conn.commit()
                return deleted
        except (sqlite3.Error, OSError) as exc:
            log.warning("History prune failed: %s", exc)
            return 0

    def clear(self, scope: Optional[str] = None) -> int:
        """Forget every remembered posting, or just one scope's postings."""
        try:
            with self._connect() as conn:
                if scope is None:
                    deleted = conn.execute("DELETE FROM seen_jobs").rowcount
                else:
                    deleted = conn.execute(
                        "DELETE FROM seen_jobs WHERE scope = ?", (scope,)
                    ).rowcount
                conn.commit()
                return deleted
        except (sqlite3.Error, OSError) as exc:
            log.warning("History clear failed: %s", exc)
            return 0

    def stats(self, scope: Optional[str] = None) -> Dict[str, object]:
        """Return row counts and report timestamps for one scope."""
        try:
            with self._connect() as conn:
                if scope is None:
                    row = conn.execute(
                        "SELECT COUNT(*), MIN(last_reported_at), MAX(last_reported_at) "
                        "FROM seen_jobs"
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*), MIN(last_reported_at), MAX(last_reported_at) "
                        "FROM seen_jobs WHERE scope = ?",
                        (scope,),
                    ).fetchone()
        except (sqlite3.Error, OSError) as exc:
            log.warning("History stats failed: %s", exc)
            return {"scope": scope, "count": 0, "oldest": None, "newest": None}
        count, oldest, newest = row or (0, None, None)
        return {"scope": scope, "count": int(count or 0), "oldest": oldest, "newest": newest}
