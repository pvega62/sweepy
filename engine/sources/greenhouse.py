from __future__ import annotations

import logging
import re
from typing import List, Optional

import requests

from engine.sources._common import USER_AGENT, html_to_text, title_matches

log = logging.getLogger("sweepy.engine.sources.greenhouse")

_API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
_HEADERS = {"User-Agent": USER_AGENT}

# Metadata fields that may carry a pay range, matched case-insensitively.
_PAY_FIELD_HINTS = ("salary", "pay", "compensation", "comp")
_PAY_RE = re.compile(r"([$€£])?\s*(\d[\d,]*(?:\.\d+)?)\s*([kK])?")


def _company_name(board: str) -> str:
    return board.replace("-", " ").title()


def _parse_pay_range(value) -> tuple:
    """Best-effort (min_amount, max_amount, currency) from a metadata value."""
    if isinstance(value, (list, tuple)):
        text = " ".join(str(v) for v in value)
    else:
        text = str(value or "")
    currency = "USD"
    if "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    amounts: List[float] = []
    for match in _PAY_RE.finditer(text):
        symbol, digits, suffix = match.group(1), match.group(2), match.group(3)
        plain = digits.replace(",", "")
        if not symbol and not suffix and len(plain.split(".")[0]) < 5:
            continue
        if suffix and not symbol and len(plain.split(".")[0]) < 2:
            continue
        amount = float(plain)
        if suffix:
            amount *= 1000
        if 1000 <= amount <= 10_000_000:
            amounts.append(amount)
    if not amounts:
        return 0.0, 0.0, currency
    return min(amounts), max(amounts), currency


def _metadata_pay(job: dict) -> tuple:
    for entry in job.get("metadata", []) or []:
        name = str(entry.get("name", "") or "").lower()
        if any(hint in name for hint in _PAY_FIELD_HINTS):
            min_amt, max_amt, currency = _parse_pay_range(entry.get("value"))
            if min_amt or max_amt:
                return min_amt, max_amt, currency
    return 0.0, 0.0, "USD"


def normalize(job: dict, board: str) -> Optional[dict]:
    """Normalize one Greenhouse board job into the shared source job dict."""
    url = job.get("absolute_url") or ""
    if not url:
        return None
    location = str((job.get("location") or {}).get("name", "") or "")
    remote = "remote" in location.lower()
    departments = job.get("departments") or []
    department = str(departments[0].get("name", "") or "") if departments else ""
    min_amt, max_amt, currency = _metadata_pay(job)
    return {
        "id": str(job.get("id", "") or ""),
        "platform": "Greenhouse",
        "url": url,
        "apply_url": "",
        "title": str(job.get("title", "") or ""),
        "company": str(job.get("company_name", "") or _company_name(board)),
        "location": location,
        "job_type": "",
        "date_posted": str(job.get("first_published") or job.get("updated_at") or ""),
        "description": html_to_text(job.get("content", "") or "", unescape=True),
        "min_amount": min_amt,
        "max_amount": max_amt,
        "currency": currency,
        "department": department,
        "remote": remote,
        "workplace_type": "Remote" if remote else "",
    }


def fetch_greenhouse_board(board: str, titles: Optional[List[str]] = None, timeout: float = 20) -> List[dict]:
    """Fetch and normalize all listed jobs for a Greenhouse board.

    Requests full content (`content=true`) so descriptions and departments are
    present for scoring; roles whose title cannot match `titles` are skipped
    during normalization to bound memory and time.
    """
    url = _API.format(board=board)
    resp = requests.get(url, params={"content": "true"}, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for raw in data.get("jobs", []) or []:
        if not title_matches(str(raw.get("title", "") or ""), titles or []):
            continue
        job = normalize(raw, board)
        if job:
            jobs.append(job)
    return jobs
