from __future__ import annotations

import html
import logging
import os
import re
from typing import List

from engine.session import stable_id

log = logging.getLogger("sweepy.engine.enrich")

_DEFAULT_COLOR = "#1D4ED8"

_REQUIREMENT_HEADINGS = (
    r"requirements",
    r"qualifications",
    r"what you'?ll bring",
    r"what we'?re looking for",
    r"you have",
    r"you bring",
    r"about you",
)

_HEADING_RE = re.compile(
    r"(?i)^\s*(?:#+\s*)?(" + "|".join(_REQUIREMENT_HEADINGS) + r")\s*:?\s*$"
)

_TAG_RE = re.compile(r"<[^>]+>")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def get_tracks(profile: dict) -> List[dict]:
    """Return the named resume tracks, or a single implicit track from resume.path."""
    resume = profile.get("resume", {}) or {}
    tracks = resume.get("tracks") or []
    if tracks:
        return tracks
    path = resume.get("path", "") or ""
    name = os.path.splitext(os.path.basename(path))[0] if path else "Primary Resume"
    return [{"name": name or "Primary Resume", "color": _DEFAULT_COLOR, "route_keywords": []}]


def _track_overlap(track: dict, text: str) -> int:
    keywords = track.get("route_keywords") or []
    text_lower = text.lower()
    return sum(
        1
        for kw in keywords
        if kw and re.search(r"\b" + re.escape(str(kw).lower()) + r"\b", text_lower)
    )


def route_track(title: str, description: str, tracks: List[dict]) -> dict:
    """Pick the best resume track by keyword overlap; ties resolve to the first track."""
    if not tracks:
        return {"name": "Primary Resume", "color": _DEFAULT_COLOR, "route_keywords": []}
    text = f"{title} {description}"
    best = tracks[0]
    best_score = _track_overlap(best, text)
    for track in tracks[1:]:
        score = _track_overlap(track, text)
        if score > best_score:
            best = track
            best_score = score
    return best


def _trim(text: str, limit: int = 280) -> str:
    """Trim text to *limit* characters, cutting at the last sentence boundary when possible."""
    text = _WS_RE.sub(" ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_period = cut.rfind(". ")
    if last_period > limit * 0.5:
        return cut[: last_period + 1].strip()
    last_space = cut.rfind(" ")
    if last_space > limit * 0.7:
        return cut[:last_space].strip() + "…"
    return cut.rstrip() + "…"


def _strip_md(text: str) -> str:
    """Remove markdown bold/italic markers and stray heading hashes."""
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text or "")
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    return text.strip()


def _summary(text: str) -> str:
    if not text:
        return ""
    sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    cleaned = [s.rstrip(".!?").strip() for s in sentences]
    summary = ". ".join(cleaned[:2])
    if summary and not summary.endswith((".", "!", "?")):
        summary += "."
    return _trim(summary, 220)


def _requirements(text: str) -> str:
    if not text:
        return ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    for i, line in enumerate(lines):
        if _HEADING_RE.match(line) and i + 1 < len(lines):
            body = " ".join(lines[i + 1 : i + 3])
            return _trim(_WS_RE.sub(" ", body).strip())
    inline = re.search(r"(?i)\b(requirements|qualifications)\s*:?\s+([A-Z].{0,300})", text)
    if inline:
        return _trim(inline.group(2).strip())
    bullets = [ln.lstrip("•-*").strip() for ln in lines if ln.lstrip().startswith(("•", "-", "*"))]
    if bullets:
        return _trim(" ".join(bullets[:4]))
    # No structured requirements found — return the first sentence as a fallback.
    sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    if sentences:
        return _trim(sentences[0])
    return _trim(text)


def _fmt_amount(value: float) -> str:
    value = float(value or 0)
    if value >= 1000:
        return f"{int(round(value / 1000))}K"
    return str(int(value))


_PERIOD_SUFFIX = {"hour": " / hour", "day": " / day", "week": " / week", "month": " / month"}


def _comp(job: dict) -> str:
    min_amt = job.get("min_amount") or 0
    max_amt = job.get("max_amount") or 0
    currency = job.get("currency", "USD") or "USD"
    sym = "$" if currency == "USD" else currency + " "
    suffix = _PERIOD_SUFFIX.get(str(job.get("salary_period") or "year").lower(), "")
    if min_amt and max_amt and min_amt != max_amt:
        return f"{sym}{_fmt_amount(min_amt)} - {sym}{_fmt_amount(max_amt)}{suffix}"
    if max_amt or min_amt:
        return f"{sym}{_fmt_amount(max_amt or min_amt)}{suffix}"
    return "Not disclosed"


def _app_format(has_extended: bool) -> str:
    if has_extended:
        return "Extended Written Prompts (Written samples, portfolio, or assessment may be required)."
    return "Standard Application (Resume upload, portfolio URL, and standard candidate profile)."


def _location(job: dict) -> str:
    loc = str(job.get("location", "") or "").strip()
    if not loc:
        return "Location Not Specified"
    if job.get("remote") is True and "(Remote)" not in loc and "Remote" not in loc:
        return f"{loc} (Remote)"
    return loc


def _domain(job: dict, profile: dict) -> str:
    department = str(job.get("department", "") or "").strip()
    if department:
        return department
    domain_map = (profile.get("sources", {}) or {}).get("domain_map", {}) or {}
    company = str(job.get("company", "") or "")
    return str(domain_map.get(company, "") or "")


def enrich_jobs(scored_jobs: List[dict], profile: dict) -> List[dict]:
    """Convert scored jobs into canonical card records using deterministic fallbacks."""
    tracks = get_tracks(profile)
    cards = []
    for job in scored_jobs:
        title = str(job.get("title", "") or "")
        raw_description = job.get("description", "") or ""
        description = _strip_md(_strip_html(raw_description))
        has_extended = (job.get("badge", "Slate") == "Amber")
        if job.get("resume_track"):
            resume_track = job.get("resume_track")
            resume_color = job.get("resume_color") or _DEFAULT_COLOR
        else:
            track = route_track(title, raw_description, tracks)
            resume_track = track.get("name", "")
            resume_color = track.get("color", _DEFAULT_COLOR)
        url = job.get("url", "") or ""
        cards.append({
            "id": stable_id(url),
            "rank": 0,
            "title": title,
            "company": str(job.get("company", "") or ""),
            "platform": str(job.get("platform", "") or ""),
            "url": url,
            "location": _location(job),
            "match_value": int(job.get("match_score", 0)),
            "match_kind": "overlap",
            "resume_track": str(resume_track or ""),
            "resume_color": str(resume_color or _DEFAULT_COLOR),
            "has_extended_response": has_extended,
            "app_format": _app_format(has_extended),
            "domain": _domain(job, profile),
            "summary": _summary(description),
            "requirements": _requirements(description),
            "alignment": job.get("playbook", "") or "",
            "comp": _comp(job),
            "salary_period": str(job.get("salary_period") or "year"),
            "benefits": "Not disclosed",
            "page": 0,
            "page_theme": "",
        })

    cards.sort(key=lambda c: c["match_value"], reverse=True)
    for i, card in enumerate(cards):
        card["rank"] = i + 1
    return cards
