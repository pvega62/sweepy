from __future__ import annotations

import logging
import os
import re
import time
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
from jobspy import scrape_jobs

from engine.sources import (
    fetch_ashby_org,
    fetch_builtin,
    fetch_workable_slug,
    load_ashby_orgs,
    load_builtin_categories,
    load_workable_slugs,
)

log = logging.getLogger("sweepy.engine.discovery")

_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)

_REQUEST_DELAY = float(os.environ.get("SWEEPY_SOURCE_DELAY", "0.2"))

_DEFAULT_JOBSPY_SITES = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]


def classify_platform(url: str, default_site: str, custom_platforms: Optional[List[Dict]] = None) -> str:
    """Classify the target ATS or board platform based on URL and site name, including custom platforms."""
    url_lower = url.lower()

    if custom_platforms:
        for custom in custom_platforms:
            c_domain = str(custom.get("domain", "")).lower().strip()
            if c_domain and c_domain in url_lower:
                return str(custom.get("name", "Custom"))

    if "greenhouse.io" in url_lower:
        return "Greenhouse"
    if "ashbyhq.com" in url_lower:
        return "Ashby"
    if "lever.co" in url_lower:
        return "Lever"
    if "workable.com" in url_lower:
        return "Workable"

    site_clean = default_site.title() if default_site else "Aggregator"
    return site_clean


def discover_jobs(
    titles: List[str],
    location: str,
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    platforms: Optional[Dict] = None,
    results_wanted: int = 25,
    progress: Optional[Callable[[int, int, str], None]] = None,
    sites: Optional[List[str]] = None,
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Scrapes jobs across configured platforms and job boards via jobspy,
    classifying ATS endpoints, handling custom platforms, and filtering hybrid/remote/salary.
    """
    if platforms is None:
        platforms = {"greenhouse": True, "ashby": True, "lever": True, "workable": True, "aggregators": False}

    custom_platforms = platforms.get("custom", [])

    all_jobs = []
    platform_counts = {
        "Greenhouse": 0,
        "Ashby": 0,
        "Lever": 0,
        "Workable": 0,
    }
    if platforms.get("aggregators", False):
        platform_counts["Aggregators"] = 0

    for cp in custom_platforms:
        cp_name = cp.get("name", "Custom")
        if cp.get("enabled", True):
            platform_counts[cp_name] = 0

    sites_to_query = [s for s in (sites or _DEFAULT_JOBSPY_SITES) if s in _DEFAULT_JOBSPY_SITES] or _DEFAULT_JOBSPY_SITES

    for idx, title in enumerate(titles):
        try:
            jobs_df: pd.DataFrame = scrape_jobs(
                site_name=sites_to_query,
                search_term=title,
                location=location,
                results_wanted=results_wanted,
                hours_old=72,
                is_remote=remote_only,
                # `country_indeed` is the Indeed country filter in python-jobspy (default "usa").
                country_indeed="usa",
                # LinkedIn returns postings without a description unless this is set, which
                # would leave every description empty and score every role 0%.
                linkedin_fetch_description=True,
            )

            if not jobs_df.empty:
                jobs_df = jobs_df.fillna("")

                for _, row in jobs_df.iterrows():
                    raw_url = str(row.get("job_url", "")).strip()
                    if not raw_url:
                        continue

                    raw_site = str(row.get("site", "Aggregator"))
                    detected_platform = classify_platform(raw_url, raw_site, custom_platforms)

                    plat_key = detected_platform.lower()
                    if plat_key in platforms and not platforms[plat_key]:
                        continue

                    custom_disabled = False
                    for cp in custom_platforms:
                        if cp.get("name", "").lower() == plat_key and not cp.get("enabled", True):
                            custom_disabled = True
                            break
                    if custom_disabled:
                        continue

                    job_title = str(row.get("title", ""))
                    job_desc = str(row.get("description", ""))
                    job_loc = str(row.get("location", location))

                    # Hybrid detection: word-boundary match on title and location only.
                    is_hybrid_role = bool(_HYBRID_RE.search(job_title) or _HYBRID_RE.search(job_loc))
                    if not include_hybrid and is_hybrid_role:
                        continue

                    min_amt = row.get("min_amount") or 0
                    max_amt = row.get("max_amount") or 0
                    try:
                        min_amt = float(min_amt) if min_amt else 0
                        max_amt = float(max_amt) if max_amt else 0
                    except (ValueError, TypeError):
                        min_amt, max_amt = 0, 0

                    if min_salary > 0 and max_amt > 0 and max_amt < min_salary:
                        continue

                    job_data = {
                        "id": str(row.get("id", "")),
                        "platform": detected_platform,
                        "url": raw_url,
                        "title": job_title,
                        "company": str(row.get("company", "")),
                        "location": job_loc,
                        "job_type": str(row.get("job_type", "")),
                        "date_posted": str(row.get("date_posted", "")),
                        "description": job_desc,
                        "min_amount": min_amt,
                        "max_amount": max_amt,
                        "currency": str(row.get("currency", "USD"))
                    }
                    all_jobs.append(job_data)
        except Exception as e:
            log.warning("Discovery failed for %r: %s", title, e)
        finally:
            if progress is not None:
                progress(idx + 1, len(titles), f"Discovering roles: {title}")

    # Deduplicate by URL
    unique_jobs = {job["url"]: job for job in all_jobs if job.get("url")}
    final_jobs = list(unique_jobs.values())

    for job in final_jobs:
        plat = job["platform"]
        if plat in platform_counts:
            platform_counts[plat] += 1
        elif "Aggregators" in platform_counts:
            platform_counts["Aggregators"] += 1
        else:
            platform_counts[plat] = 1

    return final_jobs, platform_counts


def _matches_titles(title: str, titles: List[str]) -> bool:
    if not titles:
        return True
    lowered = title.lower()
    return any(t and str(t).lower() in lowered for t in titles)


def _source_job_matches_filters(
    job: dict,
    titles: List[str],
    remote_only: bool,
    include_hybrid: bool,
    min_salary: int,
) -> bool:
    if not _matches_titles(str(job.get("title", "") or ""), titles):
        return False
    if remote_only and not job.get("remote"):
        return False
    workplace = str(job.get("workplace_type", "") or "").lower()
    if not include_hybrid and "hybrid" in workplace:
        return False
    max_amt = job.get("max_amount") or 0
    if min_salary > 0 and max_amt > 0 and float(max_amt) < min_salary:
        return False
    return True


def _add_source_jobs(
    jobs: List[dict],
    all_jobs: List[dict],
    counts: Dict[str, int],
    titles: List[str],
    remote_only: bool,
    include_hybrid: bool,
    min_salary: int,
) -> None:
    for job in jobs:
        if not _source_job_matches_filters(job, titles, remote_only, include_hybrid, min_salary):
            continue
        all_jobs.append(job)
        plat = job.get("platform", "Direct")
        counts[plat] = counts.get(plat, 0) + 1


def discover_sources(
    sources_config: Optional[Dict] = None,
    titles: Optional[List[str]] = None,
    location: str = "",
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Discover jobs from the deterministic (no-key) Ashby / Workable / Built In NYC sources.

    Each org/slug/category is fetched independently; a failure is logged and skipped
    so one bad org never kills the sweep.
    """
    sources_config = sources_config or {}
    titles = titles or []
    all_jobs: List[dict] = []
    counts: Dict[str, int] = {}

    ashby_cfg = sources_config.get("ashby", {}) or {}
    workable_cfg = sources_config.get("workable", {}) or {}
    builtin_cfg = sources_config.get("builtinnyc", {}) or {}

    ashby_orgs = list(ashby_cfg.get("orgs") or []) or load_ashby_orgs()
    for org in ashby_orgs:
        try:
            jobs = fetch_ashby_org(org)
        except Exception as e:
            log.warning("Ashby source %r failed: %s", org, e)
            continue
        _add_source_jobs(jobs, all_jobs, counts, titles, remote_only, include_hybrid, min_salary)
        if _REQUEST_DELAY:
            time.sleep(_REQUEST_DELAY)

    workable_slugs = list(workable_cfg.get("slugs") or []) or load_workable_slugs()
    for slug in workable_slugs:
        try:
            jobs = fetch_workable_slug(slug)
        except Exception as e:
            log.warning("Workable source %r failed: %s", slug, e)
            continue
        _add_source_jobs(jobs, all_jobs, counts, titles, remote_only, include_hybrid, min_salary)
        if _REQUEST_DELAY:
            time.sleep(_REQUEST_DELAY)

    if builtin_cfg.get("enabled", True):
        categories = list(builtin_cfg.get("categories") or []) or load_builtin_categories()
        for category in categories:
            try:
                jobs = fetch_builtin(category)
            except Exception as e:
                log.warning("Built In NYC source %r failed: %s", category, e)
                continue
            _add_source_jobs(jobs, all_jobs, counts, titles, remote_only, include_hybrid, min_salary)
            if _REQUEST_DELAY:
                time.sleep(_REQUEST_DELAY)

    unique = {job["url"]: job for job in all_jobs if job.get("url")}
    return list(unique.values()), counts
