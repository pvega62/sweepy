from __future__ import annotations

from typing import Dict, List

from engine.adapters.apify_adapter import ApifyAdapter
from engine.adapters.ats_adapter import AtsAdapter
from engine.adapters.base import DEFAULT_USER_AGENT, ScraperAdapter
from engine.adapters.hirehunt_adapter import HireHuntAdapter
from engine.adapters.jobdrop_adapter import JobDropAdapter
from engine.adapters.jobspy_adapter import JobSpyAdapter
from engine.adapters.openroles_adapter import OpenRolesAdapter

ADAPTERS: Dict[str, ScraperAdapter] = {
    "jobspy": JobSpyAdapter(),
    "ats": AtsAdapter(),
    "hirehunt": HireHuntAdapter(),
    "openroles": OpenRolesAdapter(),
    "jobdrop": JobDropAdapter(),
    "apify": ApifyAdapter(),
}


def get_adapter(name: str) -> ScraperAdapter:
    adapter = ADAPTERS.get(str(name or "").strip().lower())
    if adapter is None:
        raise ValueError(f"Unknown job engine: {name}")
    return adapter


def adapter_names() -> List[str]:
    return list(ADAPTERS)


__all__ = [
    "ADAPTERS",
    "ScraperAdapter",
    "DEFAULT_USER_AGENT",
    "AtsAdapter",
    "ApifyAdapter",
    "HireHuntAdapter",
    "JobDropAdapter",
    "JobSpyAdapter",
    "OpenRolesAdapter",
    "adapter_names",
    "get_adapter",
]
