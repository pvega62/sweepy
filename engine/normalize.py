from __future__ import annotations

import logging
from typing import Iterable, Optional, Sequence, Tuple

import pandas as pd

log = logging.getLogger("sweepy.engine.normalize")

COMMON_COLUMNS = [
    "title",
    "company",
    "location",
    "url",
    "source",
    "posted_at",
    "salary_min",
    "salary_max",
    "salary_currency",
    "description",
    "remote",
    "employment_type",
    "raw",
]

_ALIASES = {
    "title": ("title", "job_title", "name"),
    "company": ("company", "company_name", "employer"),
    "location": ("location", "city"),
    "url": ("url", "job_url", "apply_url", "link"),
    "posted_at": ("posted_at", "date_posted", "posted", "published_at"),
    "salary_min": ("salary_min", "min_amount"),
    "salary_max": ("salary_max", "max_amount"),
    "salary_currency": ("salary_currency", "currency"),
    "description": ("description", "job_description"),
    "remote": ("remote", "is_remote"),
    "employment_type": ("employment_type", "job_type"),
}


def _column(frame: pd.DataFrame, names: Sequence[str]) -> pd.Series:
    for name in names:
        if name in frame.columns:
            return frame[name]
    return pd.Series([None] * len(frame), index=frame.index, dtype=object)


def to_common(frame: Optional[pd.DataFrame], source: str) -> pd.DataFrame:
    """Map one engine's frame onto the common schema, keeping its extra columns."""
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=COMMON_COLUMNS)

    raw = frame.to_dict("records")
    out = pd.DataFrame(index=frame.index)
    for column, aliases in _ALIASES.items():
        out[column] = _column(frame, aliases)
    out["source"] = _column(frame, ("source",)).where(
        _column(frame, ("source",)).notna(), source
    )
    out["raw"] = raw

    extras = [c for c in frame.columns if c not in out.columns]
    return pd.concat([out[COMMON_COLUMNS], frame[extras]], axis=1)


def dedupe(frame: pd.DataFrame, *, enabled: bool = True) -> pd.DataFrame:
    """Drop repeated postings by URL and cross-board role details."""
    if frame is None or frame.empty:
        return frame if frame is not None else pd.DataFrame(columns=COMMON_COLUMNS)
    if not enabled:
        return frame.reset_index(drop=True)

    url = frame["url"].fillna("").astype(str).str.strip()
    details = (
        frame["title"].fillna("").astype(str).str.lower().str.strip()
        + "|"
        + frame["company"].fillna("").astype(str).str.lower().str.strip()
        + "|"
        + frame["location"].fillna("").astype(str).str.lower().str.strip()
    )
    seen_urls = set()
    seen_board_details = {}
    seen_unlinked_details = set()
    keep = []
    for position in range(len(frame)):
        row = frame.iloc[position]
        row_url = url.iloc[position]
        detail_key = details.iloc[position]
        if row_url and row_url in seen_urls:
            keep.append(False)
            continue
        if row_url:
            seen_urls.add(row_url)
        else:
            if detail_key in seen_unlinked_details:
                keep.append(False)
                continue
            seen_unlinked_details.add(detail_key)

        title = "" if pd.isna(row.get("title")) else str(row.get("title")).strip()
        company = "" if pd.isna(row.get("company")) else str(row.get("company")).strip()
        location = "" if pd.isna(row.get("location")) else str(row.get("location")).strip()
        if title and company and location:
            board = tuple(
                str(row.get(column)).strip().casefold()
                for column in ("platform", "site", "board", "source")
                if not pd.isna(row.get(column)) and str(row.get(column)).strip()
            )
            if row_url and board:
                matching_boards = seen_board_details.setdefault(detail_key, set())
                if matching_boards and board not in matching_boards:
                    keep.append(False)
                    continue
                matching_boards.add(board)
        keep.append(True)

    return frame.loc[keep].reset_index(drop=True)


def normalize_all(
    results: Iterable[Tuple[str, Optional[pd.DataFrame], Optional[str]]],
    *,
    deduplicate: bool = True,
) -> pd.DataFrame:
    """Merge every successful engine frame, optionally removing duplicate postings."""
    frames = [to_common(frame, name) for name, frame, _error in results if frame is not None]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    return dedupe(pd.concat(frames, ignore_index=True), enabled=deduplicate)
