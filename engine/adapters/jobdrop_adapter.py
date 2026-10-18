from __future__ import annotations

import pandas as pd

from engine.adapters.base import DEFAULT_USER_AGENT, ScraperAdapter, supported_kwargs
from engine.engine_defaults import DEFAULT_JOBDROP_SITES


class JobDropAdapter(ScraperAdapter):
    name = "jobdrop"
    library = "jobdrop"
    library_hint = 'pip install "sweepy[engines]"'

    supports_proxies = True
    supports_user_agent = True
    supports_description_toggle = True

    default_concurrency = 1
    expensive_boards = frozenset({"google", "glassdoor", "linkedin", "indeed"})

    def preflight(self, config: dict) -> dict:
        cfg = super().preflight(config)
        cfg.setdefault("sites", list(DEFAULT_JOBDROP_SITES))
        if not cfg["sites"]:
            raise ValueError("jobdrop.sites must list at least one board")
        cfg.setdefault("headless", True)
        cfg.setdefault("fetch_descriptions", True)
        cfg.setdefault("proxies", [])
        cfg.setdefault("user_agent", DEFAULT_USER_AGENT)
        return cfg

    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        self.require_library()
        from jobdrop import scrape_jobs

        cfg = self.preflight(config)
        sites = list(query.get("sites") or cfg["sites"])
        fetch_descriptions = bool(cfg.get("fetch_descriptions", True))

        kwargs = {
            "site_name": sites,
            "search_term": query["keywords"],
            "location": query.get("location", ""),
            "results_wanted": query.get("limit", 25),
            "hours_old": query.get("hours_old", 72),
            "is_remote": query.get("remote_only", False),
            "country_indeed": query.get("country_indeed", "usa"),
            "user_agent": cfg.get("user_agent") or DEFAULT_USER_AGENT,
            "proxies": self.split_proxies(cfg.get("proxies")),
            "headless": cfg.get("headless", True),
            "linkedin_fetch_description": fetch_descriptions and "linkedin" in sites,
            "fetch_description": fetch_descriptions,
        }
        return scrape_jobs(**supported_kwargs(scrape_jobs, kwargs))
