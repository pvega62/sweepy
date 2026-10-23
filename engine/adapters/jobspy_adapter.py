from __future__ import annotations

import pandas as pd

from engine.adapters.base import DEFAULT_USER_AGENT, ScraperAdapter, supported_kwargs
from engine.engine_defaults import DEFAULT_JOBSPY_SITES, jobspy_sites


class JobSpyAdapter(ScraperAdapter):
    name = "jobspy"
    library = "jobspy"
    library_hint = 'pip install -r requirements.txt'

    supports_proxies = True
    supports_user_agent = True
    supports_description_toggle = True

    default_concurrency = 4
    expensive_boards = frozenset({"linkedin", "indeed", "glassdoor"})

    def preflight(self, config: dict) -> dict:
        cfg = super().preflight(config)
        cfg.setdefault("sites", list(DEFAULT_JOBSPY_SITES))
        cfg["sites"] = jobspy_sites(config) or list(DEFAULT_JOBSPY_SITES)
        cfg.setdefault("proxies", [])
        cfg.setdefault("user_agent", DEFAULT_USER_AGENT)
        cfg.setdefault("fetch_descriptions", True)
        if not isinstance(cfg["proxies"], list):
            raise ValueError("jobspy.proxies must be a list of proxy strings")
        return cfg

    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        self.require_library()
        from jobspy import scrape_jobs

        cfg = self.preflight(config)
        sites = list(query.get("sites") or cfg["sites"])
        fetch_descriptions = bool(cfg.get("fetch_descriptions", True))

        kwargs = {
            "site_name": sites,
            "search_term": query["keywords"],
            "location": query.get("location", ""),
            "results_wanted": query.get("limit", cfg.get("results_per_title", 25)),
            "hours_old": query.get("hours_old", 72),
            "is_remote": query.get("remote_only", False),
            "country_indeed": query.get("country_indeed", "usa"),
            "user_agent": cfg.get("user_agent") or DEFAULT_USER_AGENT,
            "fetch_description": fetch_descriptions,
            "linkedin_fetch_description": fetch_descriptions and "linkedin" in sites,
            "proxies": self.split_proxies(cfg.get("proxies")),
        }
        return scrape_jobs(**supported_kwargs(scrape_jobs, kwargs))
