from __future__ import annotations

import logging
from typing import List, Optional

import requests

from engine.sources._common import USER_AGENT

log = logging.getLogger("sweepy.engine.sources.ashby")

_API = "https://api.ashbyhq.com/posting-api/job-board/{org}"
_HEADERS = {"User-Agent": USER_AGENT}

# Curated display names for seed orgs; unknown slugs fall back to title case.
_COMPANY_NAMES = {
    "modal": "Modal",
    "camunda": "Camunda",
    "wealthsimple": "Wealthsimple",
    "deepnote": "Deepnote",
    "aghanim": "Aghanim",
    "perplexity": "Perplexity AI",
    "optro": "Optro",
    "percona": "Percona",
    "nango": "Nango",
    "hume-ai": "Hume AI",
    "vals-ai": "Vals AI",
    "illumio": "Illumio",
    "ziina": "Ziina",
    "harvey": "Harvey",
    "deepgram": "Deepgram",
    "lovable": "Lovable",
    "replit": "Replit",
    "llamaindex": "LlamaIndex",
    "bruno": "Bruno",
    "afterquery": "AfterQuery",
    "stripe": "Stripe",
    "google-deepmind": "Google DeepMind",
    "braze": "Braze",
}


def _company_name(org: str) -> str:
    return _COMPANY_NAMES.get(org, org.replace("-", " ").title())


def _parse_compensation(comp: Optional[dict]) -> tuple:
    """Extract (min_amount, max_amount, currency) from an Ashby compensation object."""
    if not comp:
        return 0.0, 0.0, "USD"
    currency = "USD"
    min_amt = 0.0
    max_amt = 0.0
    for tier in comp.get("compensationTiers", []) or []:
        for component in tier.get("components", []) or []:
            if component.get("compensationType") == "Salary":
                if component.get("currencyCode"):
                    currency = component["currencyCode"]
                if component.get("minValue") is not None:
                    min_amt = float(component["minValue"])
                if component.get("maxValue") is not None:
                    max_amt = float(component["maxValue"])
    return min_amt, max_amt, currency


def normalize(job: dict, org: str) -> Optional[dict]:
    """Normalize one Ashby job payload into the shared source job dict."""
    url = job.get("jobUrl") or ""
    if not url:
        return None
    min_amt, max_amt, currency = _parse_compensation(job.get("compensation"))
    remote = bool(job.get("isRemote", False))
    workplace = str(job.get("workplaceType", "") or "")
    location = str(job.get("location", "") or "")
    if remote and workplace:
        location = f"{location} ({workplace})"
    return {
        "id": str(job.get("id", "")),
        "platform": "Ashby",
        "url": url,
        "apply_url": job.get("applyUrl", ""),
        "title": str(job.get("title", "") or ""),
        "company": _company_name(org),
        "location": location,
        "job_type": str(job.get("employmentType", "") or ""),
        "date_posted": str(job.get("publishedAt", "") or ""),
        "description": job.get("descriptionPlain", "") or "",
        "min_amount": min_amt,
        "max_amount": max_amt,
        "currency": currency,
        "department": str(job.get("department", "") or ""),
        "remote": remote,
        "workplace_type": workplace,
    }


def fetch_ashby_org(org: str, timeout: float = 20) -> List[dict]:
    """Fetch and normalize all listed jobs for an Ashby org."""
    url = _API.format(org=org)
    resp = requests.get(
        url, params={"includeCompensation": "true"}, headers=_HEADERS, timeout=timeout
    )
    # A 404 means the org slug no longer exists on Ashby's public board. Treat
    # it as an empty result so one stale seed org never fails the whole sweep.
    if resp.status_code == 404:
        log.warning("Ashby org %r not found (404): %s", org, url)
        return []
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for raw in data.get("jobs", []) or []:
        job = normalize(raw, org)
        if job:
            jobs.append(job)
    return jobs
