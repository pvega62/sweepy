from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from engine.adapters import ADAPTERS
from engine.cache import ResultCache, cache_key
from engine.circuit_breaker import CircuitBreaker
from engine.engine_defaults import DEFAULT_JOBSPY_SITES
from engine.normalize import normalize_all
from engine.salary import annual_max_amount, extract_pay
from engine.sources import (
    fetch_ashby_org,
    fetch_builtin,
    fetch_greenhouse_board,
    fetch_lever_company,
    fetch_workable_slug,
    load_ashby_orgs,
    load_builtin_categories,
    load_greenhouse_boards,
    load_lever_companies,
    load_workable_slugs,
)
from engine.sources._common import title_matches
from engine.sweep_config import normalize_sources

log = logging.getLogger("sweepy.engine.discovery")

_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)

# Pay intervals that aggregator feeds report alongside a numeric range.
_PERIOD_ALIASES = {
    "yearly": "year",
    "annual": "year",
    "annually": "year",
    "monthly": "month",
    "weekly": "week",
    "daily": "day",
    "hourly": "hour",
}

_REQUEST_DELAY = float(os.environ.get("SWEEPY_SOURCE_DELAY", "0.2"))

_DEFAULT_JOBSPY_SITES = list(DEFAULT_JOBSPY_SITES)

CIRCUIT = CircuitBreaker()


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


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def _run_one(adapter, query, config, timeout, pool, semaphore, circuit):
    if circuit.is_open(adapter.name):
        log.warning("Skipping %s: circuit open after repeated failures", adapter.name)
        return adapter.name, None, "circuit_open"

    loop = asyncio.get_running_loop()
    try:
        async with semaphore:
            future = loop.run_in_executor(pool, adapter.scrape, query, config)
            raw = await (asyncio.wait_for(future, timeout) if timeout else future)
        circuit.record_success(adapter.name)
        return adapter.name, adapter.normalize(raw, query), None
    except asyncio.TimeoutError:
        circuit.record_failure(adapter.name)
        log.warning("Source %s timed out after %ss", adapter.name, timeout)
        return adapter.name, None, "timeout"
    except Exception as exc:  # failure isolation: one engine never kills the run
        circuit.record_failure(adapter.name)
        log.warning("Source %s failed: %s", adapter.name, exc)
        log.debug("Source %s traceback", adapter.name, exc_info=True)
        return adapter.name, None, str(exc)


async def scrape_all(
    query: dict,
    enabled_sources: Optional[List[str]] = None,
    engine_configs: Optional[Dict[str, dict]] = None,
    *,
    timeout_per_source: Optional[float] = 180,
    use_cache: bool = True,
    deduplicate: bool = True,
    cache: Optional[ResultCache] = None,
    circuit: Optional[CircuitBreaker] = None,
) -> Tuple[pd.DataFrame, List[dict]]:
    """Run every enabled engine concurrently and return normalized, deduped results.

    Returns the merged frame and a list of ``{"name", "reason"}`` entries for
    engines that were skipped, timed out, or failed.
    """
    engine_configs = engine_configs or {}
    circuit = circuit or CIRCUIT
    names = [name for name in (enabled_sources or []) if name]
    skipped: List[dict] = []
    key = None

    if use_cache and cache is not None:
        key = cache_key({**query, "deduplicate": deduplicate}, names, engine_configs)
        cached = cache.load(key)
        if cached is not None:
            log.info("Cache hit for %s", ", ".join(names))
            return cached, skipped

    runnable = []
    for name in names:
        adapter = ADAPTERS.get(name)
        if adapter is None:
            log.warning("Unknown source %r ignored", name)
            skipped.append({"name": name, "reason": "unknown source"})
            continue
        if circuit.is_open(name):
            skipped.append({"name": name, "reason": "circuit_open"})
            continue
        runnable.append(adapter)

    if not runnable:
        return pd.DataFrame(), skipped

    pool = ThreadPoolExecutor(max_workers=max(4, len(runnable) * 2))
    semaphores = {
        adapter.name: asyncio.Semaphore(max(1, adapter.default_concurrency))
        for adapter in runnable
    }
    try:
        tasks = [
            asyncio.create_task(
                _run_one(
                    adapter,
                    query,
                    engine_configs.get(adapter.name, {}),
                    adapter.effective_timeout(timeout_per_source),
                    pool,
                    semaphores[adapter.name],
                    circuit,
                )
            )
            for adapter in runnable
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        # A timed-out library call cannot be killed, so do not block the sweep
        # waiting for its thread to unwind.
        pool.shutdown(wait=False, cancel_futures=True)

    clean = []
    for result in results:
        if isinstance(result, BaseException):
            log.warning("Source task failed: %s", result)
            skipped.append({"name": "unknown", "reason": str(result)})
            continue
        name, frame, error = result
        if error:
            skipped.append({"name": name, "reason": error})
        if frame is not None:
            clean.append(result)

    frame = normalize_all(clean, deduplicate=deduplicate)
    if use_cache and cache is not None and key and clean:
        cache.save(key, frame)
    return frame, skipped


def scrape_all_sync(*args, **kwargs) -> Tuple[pd.DataFrame, List[dict]]:
    """Blocking wrapper for callers outside an event loop."""
    return asyncio.run(scrape_all(*args, **kwargs))


def build_cache(runtime: dict) -> Optional[ResultCache]:
    cache_cfg = runtime.get("cache") or {}
    if not cache_cfg.get("enabled", True):
        return None
    return ResultCache(path=cache_cfg.get("path"), ttl=float(cache_cfg.get("ttl_seconds", 3600)))


def build_circuit(runtime: dict) -> CircuitBreaker:
    breaker = (runtime.get("orchestrator") or {}).get("circuit_breaker") or {}
    return CircuitBreaker(
        failure_threshold=int(breaker.get("failure_threshold", 5)),
        cooldown=float(breaker.get("cooldown_seconds", 30)),
    )


def _timeout(runtime: dict) -> float:
    return float((runtime.get("orchestrator") or {}).get("timeout_per_source_seconds", 180))


# ---------------------------------------------------------------------------
# Frame conversion and filters
# ---------------------------------------------------------------------------


def _first(record: dict, *names, default=None):
    for name in names:
        if name in record:
            value = record[name]
            if value is None:
                continue
            if isinstance(value, float) and pd.isna(value):
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return default


def _amount(value) -> float:
    try:
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0


def _salary_period(value) -> str:
    """Normalize a pay interval such as ``hourly`` or ``yearly`` into a unit."""
    text = str(value or "").strip().lower()
    return _PERIOD_ALIASES.get(text, text or "year")


def _as_bool(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "remote"):
        return True
    if text in ("false", "0", "no", "onsite", "on-site"):
        return False
    return None


def _platform_disabled(platform: str, platforms: dict, custom_platforms: List[dict]) -> bool:
    key = platform.lower()
    if key in platforms and not platforms.get(key):
        return True
    for custom in custom_platforms:
        if str(custom.get("name", "")).lower() == key and not custom.get("enabled", True):
            return True
    return False


def _frame_to_jobs(
    frame: Optional[pd.DataFrame],
    *,
    location: str,
    platforms: Optional[dict] = None,
    custom_platforms: Optional[List[dict]] = None,
    titles: Optional[List[str]] = None,
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    filter_titles: bool = False,
    salary_from_description: bool = True,
) -> List[dict]:
    """Convert a normalized frame into Sweepy's job dictionaries and apply filters."""
    if frame is None or frame.empty:
        return []

    platforms = platforms or {}
    custom_platforms = custom_platforms or []
    jobs: List[dict] = []
    for record in frame.to_dict("records"):
        url = str(_first(record, "url", "job_url", "apply_url") or "").strip()
        if not url:
            continue

        title = str(_first(record, "title") or "")
        if filter_titles and not _matches_titles(title, titles or []):
            continue

        source = str(_first(record, "source", "site") or "Aggregator")
        board = str(_first(record, "site", "board") or source)
        platform = str(_first(record, "platform") or "") or classify_platform(
            url, board, custom_platforms
        )
        if _platform_disabled(platform, platforms, custom_platforms):
            continue

        job_location = str(_first(record, "location") or location)
        is_hybrid = bool(_HYBRID_RE.search(title) or _HYBRID_RE.search(job_location))
        if not include_hybrid and is_hybrid:
            continue

        min_amount = _amount(_first(record, "salary_min", "min_amount"))
        max_amount = _amount(_first(record, "salary_max", "max_amount"))
        currency = str(_first(record, "salary_currency", "currency") or "USD")
        salary_period = _salary_period(_first(record, "salary_period", "period", "interval"))
        description = str(_first(record, "description") or "")
        if salary_from_description and not min_amount and not max_amount and description:
            pay = extract_pay(description)
            if pay:
                min_amount = pay["min_amount"]
                max_amount = pay["max_amount"]
                currency = pay["currency"]
                salary_period = pay["period"]
        if min_salary > 0 and max_amount > 0 and annual_max_amount(max_amount, salary_period) < min_salary:
            continue

        remote = _as_bool(_first(record, "remote", "is_remote"))
        if remote_only and remote is False:
            continue

        jobs.append(
            {
                "id": str(_first(record, "id") or ""),
                "platform": platform,
                "url": url,
                "apply_url": str(_first(record, "apply_url") or ""),
                "title": title,
                "company": str(_first(record, "company") or ""),
                "location": job_location,
                "job_type": str(_first(record, "employment_type", "job_type") or ""),
                "date_posted": str(_first(record, "posted_at", "date_posted") or ""),
                "description": description,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "currency": currency,
                "salary_period": salary_period,
                "remote": bool(remote),
                "workplace_type": str(
                    _first(record, "workplace_type") or ("remote" if remote else "")
                ),
                "source": source,
                "skills": _first(record, "skills") or [],
            }
        )
    return jobs


def dedupe_jobs(jobs: List[dict], *, enabled: bool = True) -> List[dict]:
    """Keep one copy of URL duplicates and same-role listings from different boards."""
    if not enabled:
        return [job for job in jobs if str(job.get("url") or "").strip()]

    unique_urls = set()
    role_boards: Dict[Tuple[str, str, str], set] = {}
    unique: List[dict] = []
    for job in jobs:
        url = str(job.get("url") or "").strip()
        if not url:
            continue
        if url in unique_urls:
            continue
        unique_urls.add(url)

        title = re.sub(r"[\W_]+", "", str(job.get("title") or "").casefold())
        company = re.sub(r"[\W_]+", "", str(job.get("company") or "").casefold())
        location = re.sub(r"[\W_]+", "", str(job.get("location") or "").casefold())
        board = str(job.get("platform") or job.get("source") or "").strip().casefold()
        if title and company and location and board:
            role_key = (title, company, location)
            boards = role_boards.setdefault(role_key, set())
            if boards and board not in boards:
                continue
            boards.add(board)
        unique.append(job)
    return unique


def _record_skips(skipped: Optional[List[dict]], skips: List[dict]) -> None:
    if skipped is None:
        return
    seen = {(entry.get("name"), entry.get("reason")) for entry in skipped}
    for entry in skips:
        key = (entry.get("name"), entry.get("reason"))
        if key not in seen:
            skipped.append(entry)
            seen.add(key)


# ---------------------------------------------------------------------------
# JobSpy discovery
# ---------------------------------------------------------------------------


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
    *,
    sources_config: Optional[Dict] = None,
    runtime: Optional[Dict] = None,
    deduplicate: bool = True,
    cache: Optional[ResultCache] = None,
    circuit: Optional[CircuitBreaker] = None,
    skipped: Optional[List[dict]] = None,
    salary_from_description: bool = True,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Scrape JobSpy boards per title through the adapter orchestrator."""
    if platforms is None:
        platforms = {"greenhouse": True, "ashby": True, "lever": True, "workable": True, "aggregators": False}
    if isinstance(platforms, list):
        platforms = {}

    custom_platforms = platforms.get("custom", [])

    platform_counts: Dict[str, int] = {
        "Greenhouse": 0,
        "Ashby": 0,
        "Lever": 0,
        "Workable": 0,
    }
    if platforms.get("aggregators", False):
        platform_counts["Aggregators"] = 0

    for custom in custom_platforms:
        if custom.get("enabled", True):
            platform_counts[custom.get("name", "Custom")] = 0

    runtime = runtime or normalize_sources(
        {"sources": sources_config or {}, "platforms": platforms}
    )
    if "jobspy" not in runtime["enabled"]:
        return [], platform_counts

    config = dict(runtime["engines"]["jobspy"])
    if sites:
        filtered = [site for site in sites if site in _DEFAULT_JOBSPY_SITES]
        config["sites"] = filtered or _DEFAULT_JOBSPY_SITES

    cache = cache if cache is not None else build_cache(runtime)
    circuit = circuit or build_circuit(runtime)
    frames = []

    for idx, title in enumerate(titles):
        query = {
            "keywords": title,
            "location": location,
            "limit": results_wanted,
            "remote_only": remote_only,
            "hours_old": 72,
            "country_indeed": "usa",
            "sites": config["sites"],
        }
        try:
            frame, skips = scrape_all_sync(
                query,
                ["jobspy"],
                {"jobspy": config},
                timeout_per_source=_timeout(runtime),
                deduplicate=deduplicate,
                cache=cache,
                circuit=circuit,
            )
            frames.append(frame)
            _record_skips(skipped, skips)
        except Exception as exc:
            log.warning("Discovery failed for %r: %s", title, exc)
        finally:
            if progress is not None:
                progress(idx + 1, len(titles), f"Discovering roles: {title}")

    merged = pd.concat(frames, ignore_index=True) if frames else None
    jobs = dedupe_jobs(
        _frame_to_jobs(
            merged,
            location=location,
            platforms=platforms,
            custom_platforms=custom_platforms,
            remote_only=remote_only,
            include_hybrid=include_hybrid,
            min_salary=min_salary,
            salary_from_description=salary_from_description,
        ),
        enabled=deduplicate,
    )

    for job in jobs:
        platform = job["platform"]
        if platform in platform_counts:
            platform_counts[platform] += 1
        elif "Aggregators" in platform_counts:
            platform_counts["Aggregators"] += 1
        else:
            platform_counts[platform] = 1

    return jobs, platform_counts


# ---------------------------------------------------------------------------
# Native ATS discovery
# ---------------------------------------------------------------------------


def _matches_titles(title: str, titles: List[str]) -> bool:
    return title_matches(title, titles)


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


def _discover_sources_core(
    sources_config: Optional[Dict] = None,
    titles: Optional[List[str]] = None,
    location: str = "",
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    platforms: Optional[Dict] = None,
    deduplicate: bool = True,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Discover jobs from the deterministic (no-key) ATS sources.

    Fetches Ashby, Workable, Greenhouse, Lever, and Built In NYC. Each
    org/slug/board/company/category is fetched independently; a failure is logged
    and skipped so one bad source never kills the sweep.

    Every source honors ``sources.<x>.enabled`` (default ``True``) and, where a
    matching key exists, ``platforms.<x>`` (default ``True``). Built In NYC has no
    ``platforms`` counterpart, so it gates on ``enabled`` only.
    """
    sources_config = sources_config or {}
    titles = titles or []
    platforms = platforms or {}
    all_jobs: List[dict] = []
    counts: Dict[str, int] = {}

    ashby_cfg = sources_config.get("ashby", {}) or {}
    workable_cfg = sources_config.get("workable", {}) or {}
    greenhouse_cfg = sources_config.get("greenhouse", {}) or {}
    lever_cfg = sources_config.get("lever", {}) or {}
    builtin_cfg = sources_config.get("builtinnyc", {}) or {}

    if ashby_cfg.get("enabled", True) and platforms.get("ashby", True):
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

    if workable_cfg.get("enabled", True) and platforms.get("workable", True):
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

    if greenhouse_cfg.get("enabled", True) and platforms.get("greenhouse", True):
        greenhouse_boards = list(greenhouse_cfg.get("boards") or []) or load_greenhouse_boards()
        for board in greenhouse_boards:
            try:
                jobs = fetch_greenhouse_board(board, titles=titles)
            except Exception as e:
                log.warning("Greenhouse source %r failed: %s", board, e)
                continue
            _add_source_jobs(jobs, all_jobs, counts, titles, remote_only, include_hybrid, min_salary)
            if _REQUEST_DELAY:
                time.sleep(_REQUEST_DELAY)

    if lever_cfg.get("enabled", True) and platforms.get("lever", True):
        lever_companies = list(lever_cfg.get("companies") or []) or load_lever_companies()
        for company in lever_companies:
            try:
                jobs = fetch_lever_company(company, titles=titles)
            except Exception as e:
                log.warning("Lever source %r failed: %s", company, e)
                continue
            _add_source_jobs(jobs, all_jobs, counts, titles, remote_only, include_hybrid, min_salary)
            if _REQUEST_DELAY:
                time.sleep(_REQUEST_DELAY)

    if builtin_cfg.get("enabled", True):
        categories = list(builtin_cfg.get("categories") or []) or load_builtin_categories()
        detail_pages = bool(builtin_cfg.get("detail_pages", False))
        for category in categories:
            try:
                jobs = fetch_builtin(category, detail_pages=detail_pages)
            except Exception as e:
                log.warning("Built In NYC source %r failed: %s", category, e)
                continue
            _add_source_jobs(jobs, all_jobs, counts, titles, remote_only, include_hybrid, min_salary)
            if _REQUEST_DELAY:
                time.sleep(_REQUEST_DELAY)

    if deduplicate:
        all_jobs = dedupe_jobs(all_jobs)
    return all_jobs, counts


def discover_sources(
    sources_config: Optional[Dict] = None,
    titles: Optional[List[str]] = None,
    location: str = "",
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    platforms: Optional[Dict] = None,
    progress: Optional[Callable[[int, int, str], None]] = None,
    *,
    runtime: Optional[Dict] = None,
    deduplicate: bool = True,
    cache: Optional[ResultCache] = None,
    circuit: Optional[CircuitBreaker] = None,
    skipped: Optional[List[dict]] = None,
    salary_from_description: bool = True,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Run the native ATS readers through the orchestrator."""
    platforms = platforms or {}
    runtime = runtime or normalize_sources(
        {"sources": sources_config or {}, "platforms": platforms}
    )
    if "ats" not in runtime["enabled"]:
        return [], {}

    query = {
        "titles": list(titles or []),
        "location": location,
        "remote_only": remote_only,
        "include_hybrid": include_hybrid,
        "min_salary": min_salary,
        "deduplicate": deduplicate,
    }
    cache = cache if cache is not None else build_cache(runtime)
    circuit = circuit or build_circuit(runtime)
    frame, skips = scrape_all_sync(
        query,
        ["ats"],
        {"ats": runtime["engines"]["ats"]},
        timeout_per_source=_timeout(runtime),
        deduplicate=deduplicate,
        cache=cache,
        circuit=circuit,
    )
    _record_skips(skipped, skips)

    jobs = dedupe_jobs(
        _frame_to_jobs(
            frame,
            location=location,
            platforms=platforms,
            remote_only=remote_only,
            include_hybrid=include_hybrid,
            min_salary=min_salary,
            salary_from_description=salary_from_description,
        ),
        enabled=deduplicate,
    )
    counts: Dict[str, int] = {}
    for job in jobs:
        platform = job.get("platform", "Direct")
        counts[platform] = counts.get(platform, 0) + 1
    return jobs, counts


# ---------------------------------------------------------------------------
# Optional engines
# ---------------------------------------------------------------------------


def discover_engines(
    engine_names: Optional[List[str]],
    titles: Optional[List[str]],
    location: str = "",
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    *,
    runtime: Optional[Dict] = None,
    deduplicate: bool = True,
    cache: Optional[ResultCache] = None,
    circuit: Optional[CircuitBreaker] = None,
    progress: Optional[Callable[[int, int, str], None]] = None,
    skipped: Optional[List[dict]] = None,
    salary_from_description: bool = True,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Run the optional engines (hirehunt, openroles, jobdrop, apify) if enabled."""
    names = [name for name in (engine_names or []) if name in ADAPTERS]
    if not names or runtime is None:
        return [], {}

    configs = {name: runtime["engines"].get(name, {}) for name in names}
    cache = cache if cache is not None else build_cache(runtime)
    circuit = circuit or build_circuit(runtime)
    search_titles = list(titles or [])
    frames = []

    for idx, title in enumerate(search_titles or [""]):
        query = {
            "keywords": title,
            "location": location,
            "limit": 25,
            "remote_only": remote_only,
            "hours_old": 72,
            "country_indeed": "usa",
            "deduplicate": deduplicate,
        }
        try:
            frame, skips = scrape_all_sync(
                query,
                names,
                configs,
                timeout_per_source=_timeout(runtime),
                deduplicate=deduplicate,
                cache=cache,
                circuit=circuit,
            )
            frames.append(frame)
            _record_skips(skipped, skips)
        except Exception as exc:
            log.warning("Engine discovery failed for %r: %s", title, exc)
        finally:
            if progress is not None:
                progress(idx + 1, len(search_titles), f"Searching {', '.join(names)}: {title}")

    merged = pd.concat(frames, ignore_index=True) if frames else None
    jobs = dedupe_jobs(
        _frame_to_jobs(
            merged,
            location=location,
            titles=search_titles,
            remote_only=remote_only,
            include_hybrid=include_hybrid,
            min_salary=min_salary,
            filter_titles=True,
            salary_from_description=salary_from_description,
        ),
        enabled=deduplicate,
    )
    counts: Dict[str, int] = {}
    for job in jobs:
        platform = job.get("platform", "Direct")
        counts[platform] = counts.get(platform, 0) + 1
    return jobs, counts
