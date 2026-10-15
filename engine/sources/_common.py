from __future__ import annotations

import html
from typing import List

from bs4 import BeautifulSoup

# Shared User-Agent for every deterministic source fetcher. Bump the version
# here when the engine version changes so outbound requests stay identifiable.
USER_AGENT = "Sweepy/2.3 (+https://github.com/pvega62/sweepy)"


def title_matches(title: str, titles: List[str]) -> bool:
    """Substring match used to pre-filter source roles by title.

    An empty ``titles`` list matches everything, so callers can skip the filter.
    ``discovery._matches_titles`` delegates here so the pre-filter and the
    post-fetch filter can never drift apart.
    """
    if not titles:
        return True
    lowered = (title or "").lower()
    return any(t and str(t).lower() in lowered for t in titles)


def html_to_text(value: str, unescape: bool = False) -> str:
    """Strip HTML tags into plain text.

    Set ``unescape=True`` for source fields that deliver HTML-escaped HTML
    (Greenhouse `content`); other sources deliver real HTML.
    """
    if not value:
        return ""
    text = html.unescape(str(value)) if unescape else str(value)
    try:
        return BeautifulSoup(text, "html.parser").get_text("\n")
    except Exception:
        return text
