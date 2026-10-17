from __future__ import annotations

import concurrent.futures
import logging
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

log = logging.getLogger("sweepy.engine.validator")

_MAX_WORKERS = 10

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

_SOFT_404_DOMAINS = ("ashbyhq.com", "greenhouse.io", "lever.co")

# Statuses that mean "cannot verify", never "dead". Rate limiting and bot protection
# answer with these codes while the posting stays live: a measured request returned
# HEAD 429 while a GET on the same URL returned 200 with the full 312 KB job page.
# LinkedIn, Indeed, and Glassdoor routinely answer HEAD with 403 or 429, so pruning
# on these codes silently deletes valid postings.
_UNVERIFIED_STATUSES = frozenset({403, 408, 425, 429, 500, 502, 503, 504})


def _content_length(response: requests.Response) -> int:
    raw = response.headers.get("content-length")
    try:
        return int(raw) if raw else 0
    except (TypeError, ValueError):
        return 0


def _soft_404(domain: str, text: str) -> bool:
    if "ashbyhq.com" in domain:
        return (
            "window.__appData.posting = null;" in text
            or "window.__appData.posting: null" in text
            or "window.__appData.posting=null" in text.replace(" ", "")
        )
    if "greenhouse.io" in domain and "Sorry, this job has been filled" in text:
        return True
    if "lever.co" in domain and "This job is no longer available" in text:
        return True
    return False


def _check(url: str) -> requests.Response:
    """
    HEAD-first URL check with GET fallback. Raises requests.Timeout on timeout and other
    requests.RequestException subclasses on connection errors.

    HEAD-first is safe because some CDNs return a different status for HEAD vs GET; the GET
    fallback covers those, plus platforms that only reveal a soft-404 in the response body.
    """
    response = requests.head(url, headers=_HEADERS, timeout=10, allow_redirects=True)

    domain = urlparse(url).netloc.lower()
    needs_body = any(d in domain for d in _SOFT_404_DOMAINS)
    content_len = _content_length(response)

    should_get = (
        response.status_code < 400
        and (
            response.status_code == 405
            or (response.status_code == 200 and content_len == 0)
            or needs_body
        )
    )
    if should_get:
        response = requests.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)

    return response


def _classify(url: str) -> Tuple[str, str]:
    """
    One network pass that classifies a URL into a state plus a log reason.

    The state is ``"valid"``, ``"unverified"``, or ``"dead"``. ``"unverified"`` means
    the host refused to answer (rate limit, bot protection, or a transient server
    error), so the posting must be kept instead of pruned.
    """
    try:
        response = _check(url)
    except requests.Timeout:
        return "unverified", "timeout"
    except requests.RequestException:
        return "dead", "connection error"

    if response.status_code in _UNVERIFIED_STATUSES:
        return "unverified", f"HTTP {response.status_code}"

    if response.status_code >= 400:
        return "dead", f"HTTP {response.status_code}"

    domain = urlparse(url).netloc.lower()
    if any(d in domain for d in _SOFT_404_DOMAINS):
        if _soft_404(domain, getattr(response, "text", "")):
            return "dead", "soft 404"

    return "valid", f"HTTP {response.status_code}"


def check_url(url: str) -> str:
    """
    Classify a job URL as ``"valid"``, ``"unverified"``, or ``"dead"``.

    Callers that prune postings must treat ``"unverified"`` as alive: a timeout, a
    rate limit, or a bot-protection block tells you nothing about the posting itself.
    """
    return _classify(url)[0]


def is_valid_url(url: str) -> bool:
    """
    Validate a job URL to ensure it is still active.
    Handles standard HTTP 404s and platform-specific dead pages (e.g., Ashby).
    Returns True for unverifiable responses (timeout, 403, 429, 5xx) so a transient
    code never prunes a live posting. Only a definite dead link returns False.
    """
    return check_url(url) != "dead"


def _classify_job(job: dict) -> Tuple[dict, str, str]:
    """Return ``(job, state, reason)`` where ``state`` matches ``check_url``."""
    url = job.get("url")
    if not url:
        return job, "dead", "missing url"
    state, reason = _classify(url)
    return job, state, reason


def filter_valid_jobs(
    jobs: list,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[list, int]:
    """
    Take a list of job dictionaries and return only those with valid URLs,
    plus the count of expired jobs. Preserves input order.
    """
    n = len(jobs)
    results: List[Optional[Tuple[dict, str, str]]] = [None] * n
    done = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_map = {executor.submit(_classify_job, job): idx for idx, job in enumerate(jobs)}
        for future in concurrent.futures.as_completed(future_map):
            idx = future_map[future]
            results[idx] = future.result()
            done += 1
            if progress is not None and done % 10 == 0:
                progress(done, n, "Validating URLs")

    valid_jobs = []
    expired_count = 0
    for job, state, reason in results:
        if state == "valid":
            valid_jobs.append(job)
        elif state == "unverified":
            job["unverified"] = True
            valid_jobs.append(job)
            log.info("Keeping unverified (%s): %s", reason, job.get("url"))
        else:
            expired_count += 1

    return valid_jobs, expired_count
