from __future__ import annotations

import logging
from typing import Any, List

import pandas as pd

from engine.adapters.base import ScraperAdapter, supported_kwargs
from engine.engine_defaults import DEFAULT_OPENROLES_ATS

log = logging.getLogger("sweepy.engine.adapters.openroles")


def _row(job: Any) -> dict:
    if isinstance(job, dict):
        data = dict(job)
    elif hasattr(job, "to_dict"):
        data = job.to_dict()
    else:
        data = {
            "title": getattr(job, "title", ""),
            "location": getattr(job, "location", ""),
            "url": getattr(job, "url", ""),
            "description": getattr(job, "description", ""),
            "posted": getattr(job, "posted", ""),
        }
    data.setdefault("source", data.get("ats") or "openroles")
    return data


class OpenRolesAdapter(ScraperAdapter):
    name = "openroles"
    library = "openroles"
    library_hint = 'pip install "sweepy[engines]"'

    supports_proxies = False
    supports_user_agent = False
    supports_description_toggle = False

    default_concurrency = 5

    def preflight(self, config: dict) -> dict:
        cfg = super().preflight(config)
        cfg.setdefault("ats", list(DEFAULT_OPENROLES_ATS))
        companies = [str(company).strip() for company in cfg.get("companies") or [] if str(company).strip()]
        cfg["companies"] = companies
        if not companies:
            raise ValueError(
                "openroles.companies must list at least one company slug, "
                "such as figma, stripe, or notion"
            )
        return cfg

    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        self.require_library()
        import openroles

        cfg = self.preflight(config)
        rows: List[dict] = []
        for ats in cfg["ats"]:
            for company in cfg["companies"]:
                board = f"{ats}:{company}"
                kwargs = {
                    "query": query.get("keywords"),
                    "location": query.get("location") or None,
                }
                try:
                    jobs = openroles.fetch(board, **supported_kwargs(openroles.fetch, kwargs))
                except Exception as exc:  # one unreadable board must not stop the rest
                    log.warning("openroles board %s failed: %s", board, exc)
                    continue
                for job in jobs or []:
                    row = _row(job)
                    row.setdefault("board", board)
                    rows.append(row)
        return pd.DataFrame(rows)
