from __future__ import annotations

import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from engine.sources._common import USER_AGENT, html_to_text

log = logging.getLogger("sweepy.engine.sources.builtinnyc")

_BASE = "https://www.builtinnyc.com"
_HEADERS = {"User-Agent": USER_AGENT}

# URL fragments that mark an outbound application link (a real ATS board).
_ATS_HOSTS = ("ashbyhq.com", "workable.com", "greenhouse.io", "lever.co")

_CARD_CLASS = "job-bounded-responsive"
_DETAIL_WORKERS = 1
_DETAIL_DELAY = 1.0

_SALARY_RANGE_RE = re.compile(
    r"(\d[\d,.]*)\s*([KkMm]?)\s*(?:-|–|—|to)\s*(\d[\d,.]*)\s*([KkMm]?)"
)
_SALARY_PERIODS = (
    ("annually", "year"),
    ("annual", "year"),
    ("yearly", "year"),
    ("monthly", "month"),
    ("weekly", "week"),
    ("daily", "day"),
    ("hourly", "hour"),
)


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
    return path.startswith("/job/")


def _card_for(anchor) -> Optional[BeautifulSoup]:
    """Return the listing card that holds one job, falling back to nearby markup."""
    card = anchor.find_parent("div", class_=lambda c: c and _CARD_CLASS in c)
    if card is not None:
        return card
    card = anchor
    for _ in range(3):
        if card.parent is None:
            break
        card = card.parent
    return card


def _icon_text(card, icon: str) -> str:
    """Read the label printed beside a Font Awesome icon such as ``fa-location-dot``."""
    if card is None:
        return ""
    icon_el = card.select_one(f"i.fa-{icon}")
    if icon_el is None or icon_el.parent is None:
        return ""
    label = icon_el.parent.find_next_sibling()
    return label.get_text(" ", strip=True) if label is not None else ""


def _amount(value: str, suffix: str) -> float:
    number = float(value.replace(",", ""))
    multiplier = {"k": 1000, "m": 1_000_000}.get((suffix or "").lower(), 1)
    return number * multiplier


def _parse_salary(text: str) -> tuple[float, float, str]:
    """Read a Built In pay label such as ``99K-186K Annually``."""
    match = _SALARY_RANGE_RE.search(text or "")
    if not match:
        return 0.0, 0.0, "year"
    suffix = match.group(2) or match.group(4)
    first = _amount(match.group(1), match.group(2) or suffix)
    second = _amount(match.group(3), match.group(4) or suffix)
    lowered = (text or "").lower()
    period = "year"
    for word, unit in _SALARY_PERIODS:
        if word in lowered:
            period = unit
            break
    return min(first, second), max(first, second), period


def parse_jobs(html: str, base_url: str = _BASE) -> List[dict]:
    """Best-effort parse of a Built In NYC listing page into source job dicts.

    The parser is deliberately defensive: Built In's markup changes often, so a
    failed or empty parse never raises — callers treat it as a soft miss.
    """
    soup = BeautifulSoup(html, "html.parser")
    parsed_base = urlparse(base_url)
    root = (
        f"{parsed_base.scheme}://{parsed_base.netloc}" if parsed_base.netloc else _BASE
    )
    jobs: List[dict] = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not _looks_like_job(href):
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = root.rstrip("/") + href
        if href in seen:
            continue
        seen.add(href)

        title = anchor.get_text(" ", strip=True)
        if not title:
            continue

        card = _card_for(anchor)

        company = ""
        company_el = card.find(attrs={"data-id": "company-title"}) if card is not None else None
        if company_el is not None:
            company = company_el.get_text(" ", strip=True)
        if not company and card is not None:
            company_link = card.find("a", href=lambda h: bool(h) and "/company/" in h)
            if company_link is not None:
                company = company_link.get_text(" ", strip=True)
        if not company and card is not None:
            company_el = card.find(class_=lambda c: c and "company" in c.lower())
            if company_el is not None:
                company = company_el.get_text(" ", strip=True)

        location = _icon_text(card, "location-dot")
        if not location and card is not None:
            location_el = card.find(class_=lambda c: c and "location" in c.lower())
            if location_el is not None:
                location = location_el.get_text(" ", strip=True)

        workplace = _icon_text(card, "house-building")
        min_amount, max_amount, salary_period = _parse_salary(_icon_text(card, "sack-dollar"))

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
            "min_amount": min_amount,
            "max_amount": max_amount,
            "currency": "USD",
            "salary_period": salary_period,
            "department": "",
            "remote": "remote" in workplace.lower(),
            "workplace_type": workplace,
        })
    return jobs


def parse_detail(html: str) -> dict:
    """Return the JobPosting JSON-LD block from a Built In detail page."""
    soup = BeautifulSoup(html, "html.parser")
    for block in soup.find_all("script", type="application/ld+json"):
        raw = block.string or block.get_text() or ""
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            continue
        nodes = data.get("@graph") if isinstance(data, dict) else None
        for node in nodes or [data]:
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                return node
    return {}


def _posting_location(posting: dict) -> str:
    job_location = posting.get("jobLocation")
    if isinstance(job_location, list):
        job_location = job_location[0] if job_location else {}
    address = (job_location or {}).get("address") if isinstance(job_location, dict) else {}
    if not isinstance(address, dict):
        return ""
    locality = str(address.get("addressLocality") or "").strip()
    region = str(address.get("addressRegion") or "").strip()
    return ", ".join(part for part in (locality, region) if part)


def _posting_salary(posting: dict) -> tuple[float, float, str]:
    base_salary = posting.get("baseSalary")
    if isinstance(base_salary, list):
        base_salary = base_salary[0] if base_salary else {}
    value = (base_salary or {}).get("value") if isinstance(base_salary, dict) else {}
    if not isinstance(value, dict):
        return 0.0, 0.0, "year"
    try:
        low = float(value.get("minValue") or 0)
        high = float(value.get("maxValue") or 0)
    except (TypeError, ValueError):
        return 0.0, 0.0, "year"
    unit = str(value.get("unitText") or "").lower()
    period = {"hour": "hour", "month": "month", "week": "week", "day": "day"}.get(unit, "year")
    return min(low, high), max(low, high), period


def apply_detail(job: dict, html: str) -> dict:
    """Merge the JobPosting JSON-LD from a detail page into a listing job."""
    posting = parse_detail(html)
    if not posting:
        return job

    enriched = dict(job)
    description = html_to_text(posting.get("description") or "")
    if description.strip():
        enriched["description"] = description

    organization = posting.get("hiringOrganization") or {}
    if isinstance(organization, list):
        organization = organization[0] if organization else {}
    if not enriched.get("company") and isinstance(organization, dict):
        enriched["company"] = str(organization.get("name") or "").strip()

    location = _posting_location(posting)
    if not enriched.get("location") and location:
        enriched["location"] = location

    low, high, period = _posting_salary(posting)
    if not enriched.get("min_amount") and not enriched.get("max_amount") and (low or high):
        enriched["min_amount"] = low
        enriched["max_amount"] = high
        enriched["salary_period"] = period

    if not enriched.get("date_posted"):
        enriched["date_posted"] = str(posting.get("datePosted") or "")

    if not enriched.get("job_type"):
        employment = posting.get("employmentType") or ""
        if isinstance(employment, list):
            employment = ", ".join(str(item) for item in employment)
        enriched["job_type"] = str(employment)

    if str(posting.get("jobLocationType") or "").upper() == "TELECOMMUTE":
        enriched["remote"] = True
        if not enriched.get("workplace_type"):
            enriched["workplace_type"] = "Remote"

    return enriched


def _enrich_from_detail(job: dict, timeout: float) -> tuple[dict, bool]:
    """Fill posting text from the detail page.

    Returns the job plus whether Built In answered with a rate-limit or bot
    challenge, so the caller can stop asking for more detail pages.
    """
    if job.get("platform") != "Built In NYC":
        return job, False
    url = job.get("url", "")
    if _DETAIL_DELAY:
        time.sleep(_DETAIL_DELAY)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        log.debug("Built In detail fetch failed for %s: %s", url, exc)
        return job, False
    if resp.status_code in (429, 503):
        log.debug("Built In answered %s for %s", resp.status_code, url)
        return job, True
    try:
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.debug("Built In detail fetch failed for %s: %s", url, exc)
        return job, False
    try:
        return apply_detail(job, resp.text), False
    except Exception:
        log.debug("Built In detail parse failed for %s", url, exc_info=True)
        return job, False


def fetch_builtin(
    category: str, timeout: float = 20, *, detail_pages: bool = False
) -> List[dict]:
    """Fetch a Built In NYC category or search page and parse its listings.

    Set ``detail_pages=True`` to read each posting's ``JobPosting`` JSON-LD for
    the full text. Built In answers those pages with a bot challenge after a
    handful of requests, so the default keeps to listing data and stops as soon
    as a challenge appears.
    """
    url = category if category.startswith("http") else f"{_BASE}/{category.lstrip('/')}"
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    jobs = parse_jobs(resp.text, url)
    if not jobs or not detail_pages:
        return jobs

    blocked = threading.Event()

    def worker(job: dict) -> dict:
        if blocked.is_set():
            return job
        enriched, throttled = _enrich_from_detail(job, timeout)
        if throttled and not blocked.is_set():
            blocked.set()
            log.info(
                "Built In NYC stopped answering detail pages; keeping listing data for %d postings.",
                len(jobs),
            )
        return enriched

    with ThreadPoolExecutor(max_workers=min(_DETAIL_WORKERS, len(jobs))) as pool:
        return list(pool.map(worker, jobs))
