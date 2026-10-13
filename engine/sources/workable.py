from __future__ import annotations

import logging
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("sweepy.engine.sources.workable")

_WIDGET_API = "https://apply.workable.com/api/v1/widget/accounts/{slug}"
_HEADERS = {"User-Agent": "Sweepy/1.5 (+https://github.com/pvega62/sweepy)"}


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    try:
        return BeautifulSoup(html, "html.parser").get_text("\n")
    except Exception:
        return html


def normalize(job: dict, company: str) -> Optional[dict]:
    """Normalize one Workable widget job into the shared source job dict."""
    url = job.get("url") or job.get("shortlink") or ""
    if not url:
        return None
    remote = bool(job.get("telecommuting", False))
    city = str(job.get("city", "") or "")
    state = str(job.get("state", "") or "")
    location = city
    if state and state.lower() != city.lower():
        location = f"{city}, {state}" if city else state
    if remote:
        location = f"{location} (Remote)" if location else "Remote"
    return {
        "id": str(job.get("shortcode", "") or ""),
        "platform": "Workable",
        "url": url,
        "apply_url": job.get("application_url", ""),
        "title": str(job.get("title", "") or ""),
        "company": company,
        "location": location,
        "job_type": str(job.get("employment_type", "") or ""),
        "date_posted": str(job.get("published_on", "") or ""),
        "description": _html_to_text(job.get("description", "") or ""),
        "min_amount": 0.0,
        "max_amount": 0.0,
        "currency": "USD",
        "department": str(job.get("department", "") or ""),
        "remote": remote,
        "workplace_type": "",
    }


def fetch_workable_slug(slug: str, timeout: float = 20) -> List[dict]:
    """Fetch and normalize all listed jobs for a Workable account slug."""
    url = _WIDGET_API.format(slug=slug)
    resp = requests.get(url, params={"details": "true"}, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    company = data.get("name") or slug.replace("-", " ").title()
    jobs = []
    for raw in data.get("jobs", []) or []:
        job = normalize(raw, company)
        if job:
            jobs.append(job)
    return jobs
