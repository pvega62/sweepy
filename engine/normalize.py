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


def dedupe(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop repeated postings, matching on the URL first and role details second."""
    if frame is None or frame.empty:
        return frame if frame is not None else pd.DataFrame(columns=COMMON_COLUMNS)

    url = frame["url"].fillna("").astype(str).str.strip()
    details = (
        frame["title"].fillna("").astype(str).str.lower().str.strip()
        + "|"
        + frame["company"].fillna("").astype(str).str.lower().str.strip()
        + "|"
        + frame["location"].fillna("").astype(str).str.lower().str.strip()
    )
    keys = url.where(url != "", details)
    return frame.loc[~keys.duplicated(keep="first")].reset_index(drop=True)


def normalize_all(
    results: Iterable[Tuple[str, Optional[pd.DataFrame], Optional[str]]],
) -> pd.DataFrame:
    """Merge every successful engine frame into one deduped common-schema frame."""
    frames = [to_common(frame, name) for name, frame, _error in results if frame is not None]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    return dedupe(pd.concat(frames, ignore_index=True))
