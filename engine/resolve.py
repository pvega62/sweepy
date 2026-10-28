"""Resolve aggregator search links into real posting URLs.

Google Jobs returns a search query as the posting URL, and jobdrop stores it
verbatim, so the card cannot be opened or read. This module turns such a link into
the employer's own posting by asking the employer's ATS board for a title match.

Only boards Sweepy can already read are probed (Greenhouse, Ashby, Lever, Workable),
so resolution costs a handful of requests and returns an exact posting URL or nothing.
An unresolved row keeps its search link, and the card records that fact rather than
pretending the link is a posting.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

log = logging.getLogger("sweepy.engine.resolve")

# Hosts that serve a search result, never a posting.
SEARCH_HOSTS = (
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "search.yahoo.com",
    "ask.com",
)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Sweepy/2.4 (+https://github.com/pvega62/sweepy)"
TIMEOUT_SECONDS = 8.0
MAX_COMPANIES_PER_RUN = 40

_CACHE: Dict[Tuple[str, str], Optional[str]] = {}
_ATTEMPTS = {"companies": 0}


def is_search_url(url: str) -> bool:
    """True when the link is an aggregator search query rather than a posting."""
    try:
        parsed = urlparse(url or "")
    except ValueError:
        return False
    host = parsed.netloc.lower()
    if not host:
        return False
    if not any(host == search or host.endswith("." + search) for search in SEARCH_HOSTS):
        return False
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    return path.startswith("/search") or "q=" in query or "udm=" in query


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _titles_match(candidate: str, wanted: str) -> bool:
    """True when one title contains the other, ignoring punctuation and case."""
    left, right = _normalize(candidate), _normalize(wanted)
    if not left or not right:
        return False
    if left == right:
        return True
    if len(right) >= 8 and right in left:
        return True
    return len(left) >= 8 and left in right


def _slugs(company: str) -> List[str]:
    """Slug guesses for one company name, most likely first."""
    base = re.sub(r"[^a-z0-9]", "", (company or "").lower())
    dashed = re.sub(r"[^a-z0-9]+", "-", (company or "").lower()).strip("-")
    guesses = [base, dashed]
    for suffix in ("inc", "llc", "ltd", "group", "corp", "company"):
        trimmed = re.sub(rf"{suffix}$", "", base)
        if trimmed and trimmed != base:
            guesses.append(trimmed)
    return list(dict.fromkeys(guess for guess in guesses if guess))


def _get_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def _greenhouse(slug: str) -> List[Tuple[str, str]]:
    payload = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [(str(job.get("title") or ""), str(job.get("absolute_url") or "")) for job in jobs]


def _ashby(slug: str) -> List[Tuple[str, str]]:
    payload = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [
        (str(job.get("title") or ""), str(job.get("jobUrl") or job.get("applyUrl") or ""))
        for job in jobs
    ]


def _lever(slug: str) -> List[Tuple[str, str]]:
    payload = _get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    jobs = payload if isinstance(payload, list) else []
    return [(str(job.get("text") or ""), str(job.get("hostedUrl") or "")) for job in jobs]


def _workable(slug: str) -> List[Tuple[str, str]]:
    payload = _get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    urls = {
        str(job.get("shortcode") or ""): str(job.get("url") or "")
        for job in jobs
    }
    pairs = []
    for job in jobs:
        url = urls.get(str(job.get("shortcode") or "")) or str(job.get("url") or "")
        if not url and job.get("shortcode"):
            url = f"https://apply.workable.com/j/{job['shortcode']}"
        pairs.append((str(job.get("title") or ""), url))
    return pairs


READERS: Sequence[Tuple[str, object]] = (
    ("greenhouse", _greenhouse),
    ("ashby", _ashby),
    ("lever", _lever),
    ("workable", _workable),
)


_TITLE_NOISE = {
    "senior", "staff", "lead", "principal", "junior", "head", "director", "manager",
    "technical", "writer", "writers", "writing", "content", "documentation", "docs",
    "strategist", "strategy", "designer", "specialist", "editor", "editorial",
    "freelance", "contract", "remote", "hybrid", "onsite", "full", "part", "time",
    "temporary", "assistant", "associate", "coordinator", "camera", "creator",
    "the", "and", "for", "with", "job", "jobs", "usa", "new", "york", "city",
}


def _company_candidates(company: str, title: str) -> List[str]:
    """Company names to probe: the listed employer first, then names found in the title.

    Google and jobdrop sometimes list the posting under an agency or board name while
    the employer appears inside the title, so the title tokens are worth one probe.
    """
    names = [company] if (company or "").strip() else []
    for token in re.findall(r"[A-Z][A-Za-z0-9&.]{2,}", title or ""):
        lowered = token.lower()
        if lowered in _TITLE_NOISE:
            continue
        if lowered not in [name.lower() for name in names]:
            names.append(token)
    return names[:6]


def resolve_posting_url(title: str, company: str) -> Optional[str]:
    """Return the employer's posting URL for one role, or None when it cannot be found.

    The lookup probes each supported ATS with slug guesses and stubs the whole
    company once it answers, so a company that is not on any of them costs one
    round of requests per sweep, not per posting.
    """
    wanted_title = _normalize(title)
    wanted_company = _normalize(company)
    if not wanted_title:
        return None

    key = (wanted_company, wanted_title)
    if key in _CACHE:
        return _CACHE[key]

    if _ATTEMPTS["companies"] >= MAX_COMPANIES_PER_RUN:
        return None
    _ATTEMPTS["companies"] += 1

    for name in _company_candidates(company, title):
        for slug in _slugs(name):
            for reader_name, reader in READERS:
                try:
                    postings = reader(slug)
                except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError, OSError):
                    continue
                except Exception as exc:  # noqa: BLE001 - a bad board must not stop a sweep
                    log.debug("Resolver probe %s:%s failed: %s", reader_name, slug, exc)
                    continue
                for posting_title, posting_url in postings:
                    if posting_url and _titles_match(posting_title, title):
                        log.info("Resolved %r at %s to %s", title, company, posting_url)
                        _CACHE[key] = posting_url
                        return posting_url

    _CACHE[key] = None
    return None


def reset_cache() -> None:
    """Clear the per-run cache and attempt budget. Tests and repeated sweeps use this."""
    _CACHE.clear()
    _ATTEMPTS["companies"] = 0
