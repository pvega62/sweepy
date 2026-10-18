from __future__ import annotations

import os

import pandas as pd

from engine.adapters.base import ScraperAdapter
from engine.engine_defaults import DEFAULT_APIFY_ACTOR


class ApifyAdapter(ScraperAdapter):
    name = "apify"
    library = "apify_client"
    library_hint = 'pip install "sweepy[apify]"'

    supports_proxies = False
    supports_user_agent = False
    supports_description_toggle = False

    default_concurrency = 2

    def preflight(self, config: dict) -> dict:
        cfg = super().preflight(config)
        token = cfg.get("token") or os.environ.get("APIFY_TOKEN")
        if not token:
            raise ValueError("APIFY_TOKEN is not set; apify stays disabled")
        cfg["token"] = token
        cfg.setdefault("actor", DEFAULT_APIFY_ACTOR)
        return cfg

    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        self.require_library()
        from apify_client import ApifyClient

        cfg = self.preflight(config)
        client = ApifyClient(cfg["token"])
        run = client.actor(cfg["actor"]).call(
            run_input={
                "keywords": query["keywords"],
                "location": query.get("location", ""),
                "maxResults": query.get("limit", 25),
            }
        )
        if not run:
            raise ValueError(f"Apify actor {cfg['actor']} returned no run")
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        frame = pd.DataFrame(items)
        if not frame.empty:
            frame["source"] = "apify"
        return frame
