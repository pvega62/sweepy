from __future__ import annotations

import pandas as pd

from engine.adapters.base import ScraperAdapter


class AtsAdapter(ScraperAdapter):
    """Run the native Greenhouse, Ashby, Lever, Workable, and Built In NYC readers.

    The work lives in ``engine.discovery`` so the existing source hooks and tests
    keep working. The import is lazy to avoid a circular module load.
    """

    name = "ats"
    library = None

    supports_proxies = False
    supports_user_agent = False
    supports_description_toggle = False

    default_concurrency = 1
    default_timeout = 900

    def preflight(self, config: dict) -> dict:
        cfg = dict(config or {})
        cfg.setdefault("sources", {})
        cfg.setdefault("platforms", {})
        return cfg

    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        from engine import discovery

        cfg = self.preflight(config)
        jobs, _counts = discovery._discover_sources_core(
            cfg["sources"],
            query.get("titles") or [],
            query.get("location", ""),
            query.get("remote_only", False),
            query.get("include_hybrid", True),
            query.get("min_salary", 0),
            platforms=cfg["platforms"],
        )
        return pd.DataFrame(jobs)
