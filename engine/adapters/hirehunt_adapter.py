from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from engine.adapters.base import ScraperAdapter, supported_kwargs
from engine.engine_defaults import DEFAULT_HIREHUNT_SOURCES

log = logging.getLogger("sweepy.engine.adapters.hirehunt")


def _field(job: Any, name: str, default=None):
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _money(job: Any, name: str):
    salary = _field(job, "salary")
    value = getattr(salary, name, None)
    if value is None:
        value = _field(job, name)
    return value


def _to_row(job: Any) -> dict:
    work_mode = str(_field(job, "work_mode") or "").lower()
    return {
        "title": _field(job, "title") or "",
        "company": _field(job, "company") or "",
        "location": _field(job, "location") or _field(job, "city") or "",
        "job_url": _field(job, "job_url") or _field(job, "url") or "",
        "description": _field(job, "description") or "",
        "date_posted": _field(job, "date_posted") or "",
        "min_amount": _money(job, "min_amount"),
        "max_amount": _money(job, "max_amount"),
        "currency": _money(job, "currency"),
        "job_type": _field(job, "job_kind") or "",
        "is_remote": work_mode == "remote",
        "site": _field(job, "source") or "hirehunt",
        "skills": _field(job, "skills") or [],
        "experience_min": _field(job, "experience_min"),
        "experience_max": _field(job, "experience_max"),
    }


class HireHuntAdapter(ScraperAdapter):
    name = "hirehunt"
    library = "hirehunt"
    library_hint = 'pip install "sweepy[engines]"'

    supports_proxies = False
    supports_user_agent = False
    supports_description_toggle = False

    default_concurrency = 3

    def preflight(self, config: dict) -> dict:
        cfg = super().preflight(config)
        cfg.setdefault("sources", list(DEFAULT_HIREHUNT_SOURCES))
        if not cfg["sources"]:
            raise ValueError("hirehunt.sources must list at least one source")
        return cfg

    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        self.require_library()
        from hirehunt import scrape_jobs

        cfg = self.preflight(config)
        location = query.get("location", "")
        hours_old = int(query.get("hours_old", 72) or 72)
        kwargs = {
            "search_term": query["keywords"],
            "sources": cfg["sources"],
            "location": location or None,
            "city": location or None,
            "country": query.get("country"),
            "results_wanted": query.get("limit", 25),
            "posted_within_days": max(1, hours_old // 24),
            "remote": True if query.get("remote_only") else None,
            "job_kind": "job",
        }
        result = scrape_jobs(**supported_kwargs(scrape_jobs, kwargs))

        for error in getattr(result, "errors", None) or []:
            log.warning("hirehunt source error: %s", error)

        jobs = getattr(result, "jobs", result)
        return pd.DataFrame([_to_row(job) for job in jobs or []])
