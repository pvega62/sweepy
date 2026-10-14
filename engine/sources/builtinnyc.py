from __future__ import annotations

import logging
from typing import List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from engine.sources._common import USER_AGENT

log = logging.getLogger("sweepy.engine.sources.builtinnyc")

_BASE = "https://www.builtinnyc.com"
_HEADERS = {"User-Agent": USER_AGENT}

# URL fragments that mark an outbound application link (a real ATS board).
_ATS_HOSTS = ("ashbyhq.com", "workable.com", "greenhouse.io", "lever.co")


def _platform_for(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "ashbyhq.com" in host:
        return "Ashby"
    if "workable.com" in host:
        return "Workable"
    if "greenhouse.io" in host:
        return "Greenhouse"
    if "lever.co" in host:
        return "Lever"
    return "Built In NYC"


def _looks_like_job(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if any(h in host for h in _ATS_HOSTS):
        return True
    return "/job" in path


def parse_jobs(html: str, base_url: str = _BASE) -> List[dict]:
    """Best-effort parse of a Built In NYC listing page into source job dicts.

    The parser is deliberately defensive: Built In's markup changes often, so a
    failed or empty parse never raises — callers treat it as a soft miss.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs: List[dict] = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = base_url.rstrip("/") + href
        if not _looks_like_job(href):
            continue
        if href in seen:
            continue
        seen.add(href)

        title = anchor.get_text(" ", strip=True)
        if not title:
            continue

        card = anchor
        for _ in range(3):
            card = card.parent if card.parent else card

        company = ""
        location = ""
        company_el = card.find(class_=lambda c: c and "company" in c.lower())
        if company_el is not None:
            company = company_el.get_text(" ", strip=True)
        location_el = card.find(class_=lambda c: c and "location" in c.lower())
        if location_el is not None:
            location = location_el.get_text(" ", strip=True)

        jobs.append({
            "id": "",
            "platform": _platform_for(href),
            "url": href,
            "apply_url": "",
            "title": title,
            "company": company,
            "location": location,
            "job_type": "",
            "date_posted": "",
            "description": "",
            "min_amount": 0.0,
            "max_amount": 0.0,
            "currency": "USD",
            "department": "",
            "remote": False,
            "workplace_type": "",
        })
    return jobs


def fetch_builtin(category: str, timeout: float = 20) -> List[dict]:
    """Fetch a Built In NYC category or search page and parse its listings."""
    url = category if category.startswith("http") else f"{_BASE}/{category.lstrip('/')}"
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return parse_jobs(resp.text, url)
