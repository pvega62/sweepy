from __future__ import annotations

import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd

log = logging.getLogger("sweepy.engine.adapters")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def supported_kwargs(func, kwargs: dict) -> dict:
    """Drop keys the installed library version does not accept.

    Optional engines pin version ranges, but the published APIs still drift between
    releases. Filtering by signature keeps one missing argument from killing a sweep.
    """
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return dict(kwargs)
    if any(param.kind is param.VAR_KEYWORD for param in params.values()):
        return {key: value for key, value in kwargs.items() if value is not None}
    return {
        key: value
        for key, value in kwargs.items()
        if key in params and value is not None
    }



class ScraperAdapter(ABC):
    """One scraper library behind a uniform contract.

    Adapters return a raw DataFrame from ``scrape``. The orchestrator maps every
    frame onto the common schema in ``engine.normalize`` before caching or scoring.
    """

    name: str = "unknown"
    library: Optional[str] = None
    library_hint: str = 'pip install "sweepy[engines]"'

    supports_proxies: bool = False
    supports_user_agent: bool = False
    supports_description_toggle: bool = False

    default_concurrency: int = 1
    default_timeout: Optional[float] = None
    expensive_boards: frozenset[str] = frozenset()

    @property
    def label(self) -> str:
        return self.name.capitalize()

    @abstractmethod
    def scrape(self, query: dict, config: dict) -> pd.DataFrame:
        """Run the scrape and return a raw DataFrame with any column names."""

    def normalize(self, raw: pd.DataFrame, query: dict) -> pd.DataFrame:
        """Map the raw frame onto the common schema. The default is a passthrough."""
        return raw

    def preflight(self, config: dict) -> dict:
        """Fill defaults, validate, and drop capabilities the engine cannot honor."""
        cfg = dict(config or {})
        if cfg.get("proxies") and not self.supports_proxies:
            log.warning(
                "%s has no proxy support: ignoring %d configured prox%s",
                self.name,
                len(cfg["proxies"]),
                "y" if len(cfg["proxies"]) == 1 else "ies",
            )
            cfg["proxies"] = []
        if cfg.get("user_agent") and not self.supports_user_agent:
            log.warning("%s cannot override the User-Agent: ignoring the value", self.name)
            cfg.pop("user_agent", None)
        if cfg.get("fetch_descriptions") and not self.supports_description_toggle:
            log.warning("%s always fetches every description it can", self.name)
            cfg.pop("fetch_descriptions", None)
        return cfg

    def require_library(self) -> None:
        """Import the backing library or raise a message a user can act on."""
        if not self.library:
            return
        try:
            importlib.import_module(self.library)
        except ImportError as exc:
            raise ValueError(
                f"The {self.name} engine needs the {self.library!r} package. "
                f"Install it with: {self.library_hint}"
            ) from exc

    def effective_timeout(self, global_timeout: Optional[float]) -> Optional[float]:
        """Prefer the adapter's own bound so long native sweeps are not cut short."""
        if self.default_timeout is not None:
            return self.default_timeout
        return global_timeout

    def split_proxies(self, proxies: Optional[List[str]]) -> List[str]:
        return [p.strip() for p in (proxies or []) if str(p).strip()]
