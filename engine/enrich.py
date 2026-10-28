from __future__ import annotations

import html
import logging
import os
import re
from typing import Dict, List, Optional

from engine.portfolio import card_portfolio_fields, get_portfolio
from engine.session import stable_id

log = logging.getLogger("sweepy.engine.enrich")

_DEFAULT_COLOR = "#1D4ED8"
DEFAULT_DESCRIPTION_CHARS = 1000
NO_CONCERNS = "No missing keywords found in the posting."

_REQUIREMENT_MARKERS = (
    "requirement",
    "qualification",
    "what you bring",
    "what you ll bring",
    "what we re looking for",
    "who you are",
    "you have",
    "you bring",
    "about you",
    "must have",
)

_DUTY_MARKERS = (
    "about the role",
    "the role",
    "role overview",
    "position overview",
    "about the job",
    "job description",
    "what you ll do",
    "what you ll be doing",
    "responsibilities",
    "day to day",
    "role",
)

# A caption line such as "Day to day, this can mean:" ends a prose section.
_CAPTION_RE = re.compile(r"^\s*(?:#+\s*)?[^.!?]{1,70}[:.]?\s*$")
_LIST_ITEM_RE = re.compile(r"^(?:[\u2022*\-]|\d+[.)])\s+(.*)$")
_NORM_RE = re.compile(r"[^a-z0-9]+")
_CUE_RE = re.compile(
    r"(?i)\b(experience (?:with|in|building)|proficien\w*|familiar\w*|knowledge of"
    r"|ability to|must have|years of|background in|comfortable with)\b"
)

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_TAG_RE = re.compile(
    r"(?i)</?(?:p|div|br|li|ul|ol|tr|td|blockquote|h[1-6]|section|article)\b[^>]*>"
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_WS_RE = re.compile(r"\s+")
_HSPACE_RE = re.compile(r"[ \t\u00a0]+")


def _heading_text(line: str) -> str:
    return _NORM_RE.sub(" ", line.lower()).strip()


def _is_heading(line: str, markers: tuple) -> bool:
    """Match a caption such as "What you'll bring" against normalized markers."""
    if line.rstrip().endswith((".", "!", "?")):
        return False
    words = _heading_text(line)
    if not words or len(words.split()) > 8:
        return False
    return any(marker in words for marker in markers)


def _body_after(lines: List[str], markers: tuple, limit: int = 8) -> List[str]:
    """Collect the lines under the first caption that matches *markers*."""
    for index, line in enumerate(lines):
        if not _is_heading(line, markers):
            continue
        body: List[str] = []
        for candidate in lines[index + 1 :]:
            if _is_heading(candidate, _REQUIREMENT_MARKERS + _DUTY_MARKERS):
                break
            if _CAPTION_RE.match(candidate):
                break
            body.append(candidate)
            if len(body) >= limit:
                break
        if body:
            return body
    return []


def _join_items(body: List[str]) -> str:
    items = []
    for line in body:
        match = _LIST_ITEM_RE.match(line)
        items.append((match.group(1) if match else line).strip())
    return _WS_RE.sub(" ", " ".join(items)).strip()


def _strip_html(text: str) -> str:
    """Strip tags but keep line structure, so headings and bullets survive.

    Postings arrive as one flattened paragraph once whitespace collapses, and
    every section-aware scan then misses the parts that matter. Block-level tags
    become line breaks here; ``_excerpt`` flattens the text again for display.
    Boards that serve escaped markup need the entities decoded first, or the
    decoded tags survive as literal text.
    """
    text = text or ""
    for _ in range(2):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _BLOCK_TAG_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    lines = [_HSPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


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


def _description_limit(profile: dict) -> int:
    """Read ``export.description_chars``; zero or less keeps the whole posting."""
    raw = (profile.get("export", {}) or {}).get(
        "description_chars", DEFAULT_DESCRIPTION_CHARS
    )
    try:
        value = int(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return DEFAULT_DESCRIPTION_CHARS
    return max(0, value)


def _excerpt(text: str, limit: int) -> str:
    if limit <= 0:
        return _WS_RE.sub(" ", text).strip()
    return _trim(text, limit)


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_RE.split(_WS_RE.sub(" ", text)) if s.strip()]


def _role_body(text: str) -> str:
    """Return the prose under a role caption, skipping the opening company pitch."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return _join_items(_body_after(lines, _DUTY_MARKERS))


def _summary(text: str) -> str:
    """Summarize the posting from its role section, not from its opening pitch."""
    if not text:
        return ""
    body = _role_body(text) or text
    cleaned = [s.rstrip(".!?").strip() for s in _sentences(body)]
    summary = ". ".join(cleaned[:2])
    if summary and not summary.endswith((".", "!", "?")):
        summary += "."
    return _trim(summary, 220)


def _requirements(text: str) -> str:
    """Pull requirements from anywhere in the posting, keeping the result short."""
    if not text:
        return ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    section = _body_after(lines, _REQUIREMENT_MARKERS)
    if section:
        return _trim(_join_items(section))
    inline = re.search(
        r"\b(?i:requirements|qualifications)\s*:?\s+([A-Z][^\n]{0,300})", text
    )
    if inline:
        return _trim(inline.group(1).strip())
    items = [m.group(1).strip() for m in map(_LIST_ITEM_RE.match, lines) if m]
    if items:
        return _trim(" ".join(items[:4]))
    duties = _body_after(lines, _DUTY_MARKERS)
    if duties:
        return _trim(_join_items(duties))
    cues = [
        sentence
        for sentence in _sentences(text)
        if len(sentence) >= 40 and _CUE_RE.search(sentence)
    ]
    if cues:
        return _trim(" ".join(cues[:2]))
    sentences = _sentences(text)
    if sentences:
        return _trim(sentences[0])
    return _trim(text)


def _concerns(job: dict) -> str:
    """Name the posting keywords the resume misses; the only gap a keyword pass proves."""
    missing = [
        str(skill).strip()
        for skill in job.get("missing_skills") or []
        if str(skill).strip()
    ]
    if not missing:
        return NO_CONCERNS
    return f"Posting asks for {', '.join(missing)}, which the resume does not show."


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


def enrich_jobs(
    scored_jobs: List[dict],
    profile: dict,
    portfolio_cache: Optional[Dict[str, List[dict]]] = None,
) -> List[dict]:
    """Convert scored jobs into canonical card records using deterministic fallbacks."""
    tracks = get_tracks(profile)
    description_limit = _description_limit(profile)
    pieces_per_card = get_portfolio(profile)["pieces_per_card"]
    if portfolio_cache is None:
        portfolio_cache = {}
    cards = []
    for job in scored_jobs:
        # Boards double-escape titles ("Technical Writer &amp; …", "&#x2014;"), and the
        # card prints the title verbatim.
        title = html.unescape(str(job.get("title", "") or ""))
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
        match_value = int(job.get("match_score", 0))
        cards.append({
            "id": stable_id(url),
            "rank": 0,
            "title": title,
            "company": str(job.get("company", "") or ""),
            "platform": str(job.get("platform", "") or ""),
            "url": url,
            "location": _location(job),
            "match_value": match_value,
            "match_score": match_value,
            "match_kind": "overlap",
            "badge": str(job.get("badge") or "Slate"),
            "unverified": bool(job.get("unverified") or False),
            "resume_track": str(resume_track or ""),
            "resume_color": str(resume_color or _DEFAULT_COLOR),
            "has_extended_response": has_extended,
            "app_format": _app_format(has_extended),
            "domain": _domain(job, profile),
            "summary": _summary(description),
            "requirements": _requirements(description),
            "description": _excerpt(description, description_limit),
            # A board that returns no body leaves nothing to score or judge. The flag
            # lets the calling agent fetch the posting itself and supply the text.
            "needs_description": not bool(description.strip()),
            # A search-engine link is not a posting: the agent cannot read it, so say so.
            "url_unresolved": bool(job.get("url_unresolved") or False),
            "alignment": job.get("playbook", "") or "",
            "concerns": _concerns(job),
            "playbook": str(job.get("playbook", "") or ""),
            "comp": _comp(job),
            "min_amount": job.get("min_amount") or 0,
            "max_amount": job.get("max_amount") or 0,
            "currency": str(job.get("currency") or "USD"),
            "salary_period": str(job.get("salary_period") or "year"),
            "key_matches": list(job.get("key_matches") or []),
            "missing_skills": list(job.get("missing_skills") or []),
            "benefits": "Not disclosed",
            "page": 0,
            "page_theme": "",
            **card_portfolio_fields(
                profile, resume_track, portfolio_cache, pieces_per_card
            ),
            # An agent judgment survives a second pass over the same posting.
            "portfolio_highlight": str(job.get("portfolio_highlight") or ""),
            **({"portfolio_fit": job["portfolio_fit"]}
               if job.get("portfolio_fit") is not None else {}),
        })

    cards.sort(key=lambda c: c["match_value"], reverse=True)
    for i, card in enumerate(cards):
        card["rank"] = i + 1
    return cards
