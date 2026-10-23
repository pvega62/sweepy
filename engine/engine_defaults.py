"""Shared engine defaults.

Kept free of imports from :mod:`engine.adapters` so adapters and the config
resolver can both read these values without a circular import.
"""

from __future__ import annotations

DEFAULT_JOBSPY_SITES = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]
DEFAULT_HIREHUNT_SOURCES = ["linkedin", "indeed", "naukri", "internshala", "shine"]
DEFAULT_JOBDROP_SITES = ["linkedin", "indeed", "google", "glassdoor"]
DEFAULT_OPENROLES_ATS = ["greenhouse", "lever", "ashby", "workday"]
DEFAULT_APIFY_ACTOR = "curious_coder/linkedin-jobs-scraper"
DEFAULT_USER_AGENT = None

DEFAULT_CACHE = {"enabled": True, "ttl_seconds": 3600, "path": None}
DEFAULT_HISTORY = {
    "enabled": True,
    "retention_days": 4,
    "match": "url+role",
    "path": None,
}
DEFAULT_ORCHESTRATOR = {
    "timeout_per_source_seconds": 180,
    "circuit_breaker": {"failure_threshold": 5, "cooldown_seconds": 30},
}

ENGINE_ORDER = ["jobspy", "ats", "hirehunt", "openroles", "jobdrop", "apify"]
NATIVE_SOURCES = ("greenhouse", "ashby", "lever", "workable")


def jobspy_sites(config) -> list:
    """Accept both the legacy board booleans and the newer ``sites`` list."""
    cfg = config or {}
    if cfg.get("sites"):
        return [str(site).strip().lower() for site in cfg["sites"] if str(site).strip()]
    return [site for site in DEFAULT_JOBSPY_SITES if cfg.get(site, True)]
