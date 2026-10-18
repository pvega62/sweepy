from __future__ import annotations

import copy
import logging
from typing import Dict, List, Optional

from engine.adapters import ADAPTERS
from engine.engine_defaults import (
    DEFAULT_APIFY_ACTOR,
    DEFAULT_CACHE,
    DEFAULT_HIREHUNT_SOURCES,
    DEFAULT_JOBDROP_SITES,
    DEFAULT_JOBSPY_SITES,
    DEFAULT_OPENROLES_ATS,
    DEFAULT_ORCHESTRATOR,
    DEFAULT_USER_AGENT,
    ENGINE_ORDER,
    NATIVE_SOURCES,
    jobspy_sites,
)

log = logging.getLogger("sweepy.engine.sweep_config")

_ENGINE_ORDER = ENGINE_ORDER
_NATIVE_SOURCES = NATIVE_SOURCES


def default_engine_config(name: str) -> dict:
    if name == "jobspy":
        return {
            "sites": list(DEFAULT_JOBSPY_SITES),
            "proxies": [],
            "user_agent": DEFAULT_USER_AGENT,
            "fetch_descriptions": True,
            "results_per_title": 25,
        }
    if name == "hirehunt":
        return {"sources": list(DEFAULT_HIREHUNT_SOURCES), "proxies": []}
    if name == "openroles":
        return {"ats": list(DEFAULT_OPENROLES_ATS), "companies": []}
    if name == "jobdrop":
        return {
            "sites": list(DEFAULT_JOBDROP_SITES),
            "headless": True,
            "fetch_descriptions": True,
            "proxies": [],
        }
    if name == "apify":
        return {"token": None, "actor": DEFAULT_APIFY_ACTOR}
    if name == "ats":
        return {"sources": {}, "platforms": {}}
    return {}


def jobspy_sites_for_profile(config: Optional[dict]) -> List[str]:
    return jobspy_sites(config)


def _native_source_enabled(raw: dict, platforms: dict, key: str) -> bool:
    cfg = raw.get(key) or {}
    return bool(cfg.get("enabled", True)) and bool(platforms.get(key, True))


def _ats_enabled(raw: dict, platforms: dict) -> bool:
    if any(_native_source_enabled(raw, platforms, key) for key in _NATIVE_SOURCES):
        return True
    return bool((raw.get("builtinnyc") or {}).get("enabled", True))


def normalize_sources(profile: Optional[dict]) -> dict:
    """Resolve a profile into engine configs, the enabled list, cache, and orchestrator settings."""
    profile = profile or {}
    raw = copy.deepcopy(profile.get("sources") or {})
    platforms = copy.deepcopy(profile.get("platforms") or {})
    if isinstance(platforms, list):
        migrated = migrate_legacy_platforms(platforms)
        raw = {**migrated, **raw}
        platforms = {}

    jobspy_cfg = {**default_engine_config("jobspy"), **(raw.get("jobspy") or {})}
    jobspy_cfg["sites"] = jobspy_sites(raw.get("jobspy") or {})

    engines = {
        "jobspy": jobspy_cfg,
        "ats": {
            "sources": {key: copy.deepcopy(raw[key]) for key in (*_NATIVE_SOURCES, "builtinnyc") if key in raw},
            "platforms": platforms,
        },
        "hirehunt": {**default_engine_config("hirehunt"), **(raw.get("hirehunt") or {})},
        "openroles": {**default_engine_config("openroles"), **(raw.get("openroles") or {})},
        "jobdrop": {**default_engine_config("jobdrop"), **(raw.get("jobdrop") or {})},
        "apify": {**default_engine_config("apify"), **(raw.get("apify") or {})},
    }

    disabled = {
        name
        for name in engines
        if (raw.get(name) or {}).get("enabled") is False
    }

    explicit = raw.get("enabled")
    if explicit is None:
        enabled = []
        if jobspy_cfg.get("enabled", True) is not False and jobspy_cfg["sites"]:
            enabled.append("jobspy")
        if _ats_enabled(raw, platforms):
            enabled.append("ats")
        for name in ("hirehunt", "openroles", "jobdrop", "apify"):
            config = engines[name]
            if config.get("enabled") and _required_fields_present(name, config):
                enabled.append(name)
    else:
        if isinstance(explicit, str):
            explicit = [part for part in explicit.split(",") if part.strip()]
        enabled = []
        for name in explicit or []:
            key = str(name).strip().lower()
            if key not in ADAPTERS:
                log.warning("Unknown job engine %r ignored", name)
                continue
            enabled.append(key)
        for name in _ENGINE_ORDER:
            if name in ADAPTERS and name not in enabled and (raw.get(name) or {}).get("enabled"):
                enabled.append(name)

    enabled = [name for name in _ENGINE_ORDER if name in enabled and name not in disabled]
    for name in enabled:
        if name not in ADAPTERS:
            log.warning("Unknown job engine %r ignored", name)

    cache = {**DEFAULT_CACHE, **(profile.get("cache") or {})}
    orchestrator = {**DEFAULT_ORCHESTRATOR, **(profile.get("orchestrator") or {})}
    orchestrator["circuit_breaker"] = {
        **DEFAULT_ORCHESTRATOR["circuit_breaker"],
        **((profile.get("orchestrator") or {}).get("circuit_breaker") or {}),
    }

    return {
        "enabled": [name for name in enabled if name in ADAPTERS],
        "engines": engines,
        "cache": cache,
        "orchestrator": orchestrator,
        "legacy_platforms": "enabled" not in raw,
    }


def _required_fields_present(name: str, config: dict) -> bool:
    if name == "openroles":
        return bool(config.get("companies"))
    if name == "apify":
        return bool(config.get("token"))
    return True


def enabled_engine_names(profile: Optional[dict]) -> List[str]:
    return normalize_sources(profile)["enabled"]


def validate_sources(engine_configs: Dict[str, dict], *, check_installed: bool = False) -> List[str]:
    """Run every adapter's preflight and report the errors as readable lines."""
    errors: List[str] = []
    for name, cfg in engine_configs.items():
        adapter = ADAPTERS.get(name)
        if adapter is None:
            errors.append(f"{name}: unknown job engine")
            continue
        try:
            adapter.preflight(cfg or {})
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
        if check_installed:
            from engine.engines import engine_status

            status = engine_status(name)
            if not status["installed"]:
                errors.append(f"{name}: {status['detail']}")
    return errors


def migrate_legacy_platforms(platforms) -> dict:
    """Map an old list-style `platforms` field onto a JobSpy source block."""
    if not isinstance(platforms, list):
        return {}
    sites = [str(item).strip().lower() for item in platforms if str(item).strip()]
    return {
        "enabled": ["jobspy"],
        "jobspy": {"sites": sites or list(DEFAULT_JOBSPY_SITES)},
    }


def legacy_profile_notice(profile: Optional[dict]) -> Optional[str]:
    """Return a one-line migration note for profiles that predate engine blocks."""
    profile = profile or {}
    if "enabled" in (profile.get("sources") or {}):
        return None
    if isinstance(profile.get("platforms"), list):
        return (
            "Legacy `platforms` list detected - mapped to jobspy boards. "
            "Run `python swee.py --setup` to enable more engines."
        )
    return None
