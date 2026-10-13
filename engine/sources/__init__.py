from __future__ import annotations

import os
from typing import List

from engine.sources.ashby import fetch_ashby_org
from engine.sources.builtinnyc import fetch_builtin
from engine.sources.workable import fetch_workable_slug

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(_ROOT, "data", "sources")


def _load_lines(filename: str) -> List[str]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    items: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(line)
    return items


def load_ashby_orgs() -> List[str]:
    return _load_lines("ashby_orgs.txt")


def load_workable_slugs() -> List[str]:
    return _load_lines("workable_slugs.txt")


def load_builtin_categories() -> List[str]:
    return _load_lines("builtin_categories.txt")


__all__ = [
    "fetch_ashby_org",
    "fetch_workable_slug",
    "fetch_builtin",
    "load_ashby_orgs",
    "load_workable_slugs",
    "load_builtin_categories",
]
