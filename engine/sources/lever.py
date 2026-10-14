from __future__ import annotations

import datetime
import logging
from typing import List, Optional

import requests

from engine.sources._common import USER_AGENT, html_to_text, title_matches

log = logging.getLogger("sweepy.engine.sources.lever")

_API = "https://api.lever.co/v0/postings/{company}"
_HEADERS = {"User-Agent": USER_AGENT}

# Curated display names for seed companies; unknown slugs fall back to title case.
_COMPANY_NAMES = {
    "leverdemo": "Lever",
    "spotify": "Spotify",
}


def _company_name(company: str) -> str:
    return _COMPANY_NAMES.get(company, company.replace("-", " ").title())


def _epoch_ms_to_iso(value) -> str:
    """Convert a Lever `createdAt` epoch-millisecond value into an ISO-8601 string."""
    try:
        millis = float(value)
    except (TypeError, ValueError):
        return ""
    if millis <= 0:
        return ""
    try:
        moment = datetime.datetime.fromtimestamp(millis / 1000, tz=datetime.timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_salary(salary_range: Optional[dict]) -> tuple:
    if not salary_range:
        return 0.0, 0.0, "USD"
    try:
        min_amt = float(salary_range.get("min") or 0)
        max_amt = float(salary_range.get("max") or 0)
    except (TypeError, ValueError):
        min_amt, max_amt = 0.0, 0.0
    currency = str(salary_range.get("currency") or "USD")
    if max_amt and not min_amt:
        min_amt = max_amt
    if min_amt and not max_amt:
        max_amt = min_amt
    return min_amt, max_amt, currency


def normalize(job: dict, company: str) -> Optional[dict]:
    """Normalize one Lever posting into the shared source job dict."""
    url = job.get("hostedUrl") or job.get("applyUrl") or ""
    if not url:
        return None
    categories = job.get("categories") or {}
    workplace = str(job.get("workplaceType", "") or "")
    remote = workplace.lower() == "remote"
    location = str(categories.get("location", "") or "")
    if remote and location and "(Remote)" not in location:
        location = f"{location} (Remote)"
    description = job.get("descriptionPlain")
    if not description:
        description = html_to_text(job.get("description", "") or "")
    min_amt, max_amt, currency = _parse_salary(job.get("salaryRange"))
    department = str(categories.get("department") or categories.get("team") or "")
    return {
        "id": str(job.get("id", "") or ""),
        "platform": "Lever",
        "url": url,
        "apply_url": job.get("applyUrl", "") or "",
        "title": str(job.get("text", "") or ""),
        "company": _company_name(company),
        "location": location,
        "job_type": str(categories.get("commitment", "") or ""),
        "date_posted": _epoch_ms_to_iso(job.get("createdAt")),
        "description": description or "",
        "min_amount": min_amt,
        "max_amount": max_amt,
        "currency": currency,
        "department": department,
        "remote": remote,
        "workplace_type": workplace,
    }


def fetch_lever_company(company: str, titles: Optional[List[str]] = None, timeout: float = 20) -> List[dict]:
    """Fetch and normalize all listed postings for a Lever company.

    The Lever postings endpoint returns a bare JSON array with descriptions and
    salary ranges inline. Roles whose title cannot match `titles` are skipped
    during normalization to bound memory and time.
    """
    url = _API.format(company=company)
    resp = requests.get(url, params={"mode": "json"}, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for raw in data or []:
        if not isinstance(raw, dict):
            continue
        if not title_matches(str(raw.get("text", "") or ""), titles or []):
            continue
        job = normalize(raw, company)
        if job:
            jobs.append(job)
    return jobs
