"""Job-tracking columns for the CSV export.

Every sweep writes a new CSV, so a status typed into yesterday's export would be
lost. This module reads the newest CSVs for one profile and carries those values
into the new export, matching postings by canonical URL with a
title/company/location fallback.
"""

from __future__ import annotations

import csv
import glob
import logging
import os
from typing import Dict, Iterable, List, Optional

from engine.history import role_key, url_key

log = logging.getLogger("sweepy.engine.tracking")

TRACKING_COLUMNS = [
    "date_applied",
    "status",
    "interview_stage",
    "offer_amount",
    "offer_date",
    "follow_up_date",
    "contact",
    "notes",
]

DEFAULT_EXPORT_LIMIT = 20


def tracking_enabled(export_config: Optional[dict]) -> bool:
    """Return whether a profile wants tracking columns. New profiles start opted in."""
    if not export_config:
        return True
    value = export_config.get("tracking", True)
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off")
    return bool(value)


def _export_paths(
    results_dir: str,
    profile_stem: Optional[str],
    limit: int,
    exclude: Optional[str],
) -> List[str]:
    """Return the newest CSVs for one profile, newest first."""
    if not results_dir or not os.path.isdir(results_dir):
        return []
    pattern = os.path.join(results_dir, f"{profile_stem}_*.csv" if profile_stem else "*.csv")
    skip = os.path.realpath(exclude) if exclude else ""
    candidates = []
    for path in glob.glob(pattern):
        if skip and os.path.realpath(path) == skip:
            continue
        try:
            candidates.append((os.path.getmtime(path), path))
        except OSError:
            continue
    candidates.sort(reverse=True)
    return [path for _, path in candidates[: max(1, limit)]]


def _read_tracking_rows(path: str) -> Iterable[Dict[str, str]]:
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            yield from csv.DictReader(handle)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        log.warning("Could not read earlier export %s: %s", path, exc)


def _row_keys(row: Dict) -> List[str]:
    keys = []
    url = url_key(row.get("url"))
    if url:
        keys.append(f"url:{url}")
    role = role_key(row.get("title"), row.get("company"), row.get("location"))
    if role:
        keys.append(f"role:{role}")
    return keys


def _values_for_row(row: Dict, previous: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    for key in _row_keys(row):
        values = previous.get(key)
        if values:
            return values
    return {}


def load_previous(
    results_dir: str,
    profile_stem: Optional[str],
    *,
    limit: int = DEFAULT_EXPORT_LIMIT,
    exclude: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    """Collect tracking values from earlier exports of one profile.

    The newest export wins: files are read newest first and the first non-empty
    value for a column is the one kept.
    """
    previous: Dict[str, Dict[str, str]] = {}
    for path in _export_paths(results_dir, profile_stem, limit, exclude):
        for row in _read_tracking_rows(path):
            if not any(str(row.get(col) or "").strip() for col in TRACKING_COLUMNS):
                continue
            for key in _row_keys(row):
                bucket = previous.setdefault(key, {})
                for col in TRACKING_COLUMNS:
                    value = str(row.get(col) or "").strip()
                    if value and col not in bucket:
                        bucket[col] = value
    return previous


def backfill(rows: List[Dict], previous: Optional[Dict[str, Dict[str, str]]]) -> int:
    """Fill blank tracking cells from ``previous`` and return the value count."""
    if not previous:
        return 0
    filled = 0
    for row in rows:
        for col, value in _values_for_row(row, previous).items():
            if not str(row.get(col) or "").strip():
                row[col] = value
                filled += 1
    return filled


def carried_count(rows: List[Dict], previous: Optional[Dict[str, Dict[str, str]]]) -> int:
    """Count rows that have earlier tracking values waiting for them."""
    if not previous:
        return 0
    return sum(1 for row in rows if _values_for_row(row, previous))
