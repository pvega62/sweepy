"""Portfolio sources for a Sweepy profile.

A candidate points Sweepy at a portfolio once per resume track, as a local file or an
online URL. Sweepy lists the pieces that portfolio holds, and the calling agent chooses the
pieces to highlight for each role.

An empty or missing ``portfolio`` block leaves every card field blank, so a profile without
a portfolio renders exactly as it did before portfolio support existed.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from engine.documents import _read_text as _read_local_text
from engine.documents import text_blocks

log = logging.getLogger("sweepy.engine.portfolio")

PORTFOLIO_SUFFIXES = (
    ".pdf",
    ".docx",
    ".md",
    ".markdown",
    ".txt",
    ".text",
    ".html",
    ".htm",
)
SUPPORTED_LABEL = ", ".join(PORTFOLIO_SUFFIXES)

DEFAULT_PIECES_PER_CARD = 3
MAX_PIECES_PER_CARD = 10
MAX_PIECES_PER_SOURCE = 12
MAX_PIECE_TITLE = 90
FETCH_TIMEOUT_SECONDS = 10

_ENTRY_KEYS = ("track", "url", "path", "pieces")
_PIECE_KEYS = ("title", "name", "url", "tags")
_HTML_SUFFIXES = (".html", ".htm")
_BINARY_SUFFIXES = (".pdf", ".docx")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_TITLE_END_PUNCTUATION = (".", ",", ";", ":", "!")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
}

_EMPTY_FIELDS = {
    "portfolio_url": "",
    "portfolio_path": "",
    "portfolio_pieces": [],
    "portfolio_highlight": "",
}


class PortfolioError(ValueError):
    """Raised when a portfolio block cannot be used."""


def _clean(value) -> str:
    """Collapse whitespace in one value read from a profile or a caller."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def looks_like_url(value) -> bool:
    """Return True when ``value`` is an http or https URL."""
    return bool(_URL_RE.match(_clean(value)))


def _track_names(track_names) -> List[str]:
    return [_clean(name) for name in (track_names or []) if _clean(name)]


def _raw_entries(raw) -> List:
    """Return the source entries a portfolio block holds, without validating them."""
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict):
        if "sources" in raw:
            sources = raw.get("sources")
            return list(sources) if isinstance(sources, list) else []
        return [raw]
    return []


def _piece_errors(piece, label: str) -> List[str]:
    if isinstance(piece, str):
        return [] if _clean(piece) else [f"{label} must name a piece"]
    if not isinstance(piece, dict):
        return [f"{label} must be a title string or an object"]
    errors = []
    unknown = set(piece) - set(_PIECE_KEYS)
    if unknown:
        errors.append(f"{label} has unsupported field(s): " + ", ".join(sorted(unknown)))
    if not _clean(piece.get("title") or piece.get("name")):
        errors.append(f"{label}.title must be a non-empty string")
    url = piece.get("url")
    if url is not None and not looks_like_url(url):
        errors.append(f"{label}.url must start with http:// or https://")
    tags = piece.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"{label}.tags must be a list")
    return errors


def _entry_errors(entry, index: int, track_names=None) -> List[str]:
    label = f"portfolio.sources[{index}]"
    if not isinstance(entry, dict):
        return [f"{label} must be an object"]

    errors: List[str] = []
    unknown = set(entry) - set(_ENTRY_KEYS)
    if unknown:
        errors.append(f"{label} has unsupported field(s): " + ", ".join(sorted(unknown)))

    track = entry.get("track")
    if track not in (None, ""):
        name = _clean(track)
        known = None if track_names is None else _track_names(track_names)
        if not name:
            errors.append(f"{label}.track must be a non-empty string")
        elif known is not None and name.lower() not in {t.lower() for t in known}:
            valid = ", ".join(sorted(known)) if known else "this profile defines none"
            errors.append(
                f"{label}.track {name!r} matches no resume track ({valid})"
            )

    path = entry.get("path")
    if path not in (None, ""):
        if not _clean(path):
            errors.append(f"{label}.path must be a non-empty string")
        else:
            resolved = os.path.abspath(os.path.expanduser(_clean(path)))
            suffix = os.path.splitext(resolved)[1].lower()
            if not os.path.exists(resolved):
                errors.append(f"{label}.path not found: {path!r}")
            elif suffix not in PORTFOLIO_SUFFIXES:
                errors.append(f"{label}.path must be one of: {SUPPORTED_LABEL}")

    url = entry.get("url")
    if url not in (None, "") and not looks_like_url(url):
        errors.append(f"{label}.url must start with http:// or https://")

    pieces = entry.get("pieces")
    if pieces not in (None, []):
        if not isinstance(pieces, list):
            errors.append(f"{label}.pieces must be a list")
        else:
            for piece_index, piece in enumerate(pieces, start=1):
                errors.extend(_piece_errors(piece, f"{label}.pieces[{piece_index}]"))

    if not any(entry.get(key) for key in ("url", "path", "pieces")):
        errors.append(f"{label} needs a url, a path, or pieces")
    return errors


def portfolio_errors(raw, track_names=None) -> List[str]:
    """Return every problem in a portfolio block. An empty list means usable."""
    if raw in (None, {}, []):
        return []

    errors: List[str] = []
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        if "sources" in raw:
            sources = raw.get("sources")
            if not isinstance(sources, list):
                return ["portfolio.sources must be a list of entries"]
            entries = sources
        else:
            # Shorthand: one portfolio written directly under `portfolio`.
            entries = [{k: v for k, v in raw.items() if k in _ENTRY_KEYS}]
        unknown = set(raw) - {"sources", "pieces_per_card", *_ENTRY_KEYS}
        if unknown:
            errors.append("Unsupported portfolio field(s): " + ", ".join(sorted(unknown)))
        limit = raw.get("pieces_per_card")
        if limit is not None and (type(limit) is not int or not 1 <= limit <= MAX_PIECES_PER_CARD):
            errors.append(
                f"portfolio.pieces_per_card must be an integer from 1 to {MAX_PIECES_PER_CARD}"
            )
    else:
        return ["portfolio must be an object or a list of sources"]

    for index, entry in enumerate(entries, start=1):
        errors.extend(_entry_errors(entry, index, track_names))
    return errors


def _normalize_pieces(pieces) -> List[Dict]:
    normalized = []
    for piece in pieces or []:
        if isinstance(piece, str):
            title, url, tags = _clean(piece), "", []
        else:
            title = _clean(piece.get("title") or piece.get("name"))
            url = _clean(piece.get("url"))
            tags = [_clean(tag) for tag in (piece.get("tags") or []) if _clean(tag)]
        if title:
            normalized.append({"title": title, "url": url, "tags": tags})
    return normalized


def _normalize_entry(entry: Dict) -> Dict:
    path = _clean(entry.get("path"))
    normalized = {}
    if _clean(entry.get("track")):
        normalized["track"] = _clean(entry.get("track"))
    if _clean(entry.get("url")):
        normalized["url"] = _clean(entry.get("url"))
    if path:
        normalized["path"] = os.path.abspath(os.path.expanduser(path))
    pieces = _normalize_pieces(entry.get("pieces"))
    if pieces:
        normalized["pieces"] = pieces
    return normalized


def normalize_portfolio(raw, track_names=None) -> Dict:
    """Validate a portfolio block and return it in canonical form."""
    errors = portfolio_errors(raw, track_names)
    if errors:
        raise PortfolioError("; ".join(errors))

    limit = DEFAULT_PIECES_PER_CARD
    if isinstance(raw, dict):
        value = raw.get("pieces_per_card")
        if type(value) is int:
            limit = value
    return {
        "sources": [_normalize_entry(entry) for entry in _raw_entries(raw)],
        "pieces_per_card": limit,
    }


def get_portfolio(profile) -> Dict:
    """Read the portfolio block from a profile, dropping entries that cannot be used.

    A sweep must not fail because a hand-edited profile points at a file the user moved.
    The dropped entry is logged, and the remaining entries still work.
    """
    raw = (profile or {}).get("portfolio") if isinstance(profile, dict) else None
    limit = DEFAULT_PIECES_PER_CARD
    if isinstance(raw, dict):
        value = raw.get("pieces_per_card")
        if type(value) is int and 1 <= value <= MAX_PIECES_PER_CARD:
            limit = value

    sources = []
    for index, entry in enumerate(_raw_entries(raw), start=1):
        problems = portfolio_errors([entry])
        if problems:
            log.warning("Skipping portfolio source %d: %s", index, "; ".join(problems))
            continue
        sources.append(_normalize_entry(entry))
    return {"sources": sources, "pieces_per_card": limit}


def portfolio_for_track(profile, track_name: Optional[str]) -> Optional[Dict]:
    """Return the portfolio for one resume track, falling back to the default entry."""
    sources = get_portfolio(profile)["sources"]
    name = _clean(track_name).lower()
    if name:
        for source in sources:
            if _clean(source.get("track")).lower() == name:
                return source
    for source in sources:
        if not source.get("track"):
            return source
    return None


def _dedupe(pieces: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for piece in pieces:
        key = _clean(piece.get("title")).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(piece)
    return unique


def _lines_as_pieces(text: str) -> List[Dict]:
    """Treat short standalone lines as candidate piece titles."""
    pieces = []
    for raw_line in (text or "").splitlines():
        line = _clean(raw_line)
        if not line or len(line) > MAX_PIECE_TITLE:
            continue
        if len(line.split()) > 10 or line.endswith(_TITLE_END_PUNCTUATION):
            continue
        if not re.search(r"[A-Za-z]{3}", line):
            continue
        pieces.append({"title": line, "url": "", "tags": []})
    return pieces


def _text_pieces(text: str) -> List[Dict]:
    """Read Markdown or plain text: headings first, short lines as a fallback."""
    pieces = [
        {"title": _clean(body), "url": "", "tags": []}
        for kind, body in text_blocks(text or "")
        if kind == "heading" and _clean(body)
    ]
    return pieces or _lines_as_pieces(text)


def _html_pieces(markup: str, base_url: str = "") -> List[Dict]:
    """Read headings and links from an HTML page."""
    try:
        soup = BeautifulSoup(markup or "", "html.parser")
    except Exception as exc:  # noqa: BLE001 - a malformed page must not fail a sweep
        log.warning("Could not parse HTML portfolio %r: %s", base_url or "(text)", exc)
        return []

    pieces = []
    for tag in soup.find_all(["h1", "h2", "h3", "a"]):
        title = _clean(tag.get_text(" ", strip=True))
        if not title or len(title) > MAX_PIECE_TITLE:
            continue
        href = ""
        if tag.name == "a":
            href = _clean(tag.get("href"))
            if href and base_url:
                href = urljoin(base_url, href)
        pieces.append({"title": title, "url": href, "tags": []})
    return pieces


def _file_pieces(path: str) -> List[Dict]:
    suffix = os.path.splitext(path)[1].lower()
    try:
        if suffix in _BINARY_SUFFIXES:
            from engine.scorer import read_document_text

            return _text_pieces(read_document_text(path))
        text = _read_local_text(path)
    except Exception as exc:  # noqa: BLE001 - an unreadable file must not fail a sweep
        log.warning("Could not read portfolio file %r: %s", path, exc)
        return []
    return _html_pieces(text) if suffix in _HTML_SUFFIXES else _text_pieces(text)


def _url_pieces(url: str) -> List[Dict]:
    import requests

    try:
        response = requests.get(
            url, headers=_HEADERS, timeout=FETCH_TIMEOUT_SECONDS, allow_redirects=True
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - record the link, skip the piece list
        log.warning("Could not read portfolio URL %r: %s", url, exc)
        return []
    return _html_pieces(response.text, url)


def extract_pieces(entry: Dict, fetch: bool = True) -> List[Dict]:
    """List the pieces a portfolio holds.

    Explicit ``pieces`` win, because they cost nothing to read. Otherwise a local file
    supplies the list, and an online portfolio is fetched once. A failed fetch returns no
    pieces so the card keeps the link and the sweep keeps running.
    """
    pieces = _normalize_pieces(entry.get("pieces"))
    if not pieces and entry.get("path"):
        pieces = _file_pieces(entry["path"])
    if not pieces and fetch and entry.get("url"):
        pieces = _url_pieces(entry["url"])
    return _dedupe(pieces)[:MAX_PIECES_PER_SOURCE]


def card_portfolio_fields(
    profile,
    track_name: Optional[str],
    cache: Optional[Dict[str, List[Dict]]] = None,
    limit: int = DEFAULT_PIECES_PER_CARD,
) -> Dict:
    """Return the portfolio fields one card carries for its resume track.

    ``cache`` holds the extracted pieces per track so a sweep reads each portfolio once.
    """
    fields = dict(_EMPTY_FIELDS)
    entry = portfolio_for_track(profile, track_name)
    if not entry:
        return fields

    key = (_clean(entry.get("track")) or "__default__").lower()
    if cache is not None and key in cache:
        pieces = cache[key]
    else:
        pieces = extract_pieces(entry)
        if cache is not None:
            cache[key] = pieces

    count = limit if limit and limit > 0 else DEFAULT_PIECES_PER_CARD
    fields.update(
        portfolio_url=entry.get("url") or "",
        portfolio_path=entry.get("path") or "",
        portfolio_pieces=[piece["title"] for piece in pieces[:count]],
    )
    return fields


def portfolio_summary(profile) -> Dict:
    """Describe the configured portfolios for an MCP payload."""
    block = get_portfolio(profile)
    return {
        "configured": bool(block["sources"]),
        "pieces_per_card": block["pieces_per_card"],
        "sources": [
            {
                "track": source.get("track") or "",
                "url": source.get("url") or "",
                "path": source.get("path") or "",
                "pieces_declared": len(source.get("pieces") or []),
            }
            for source in block["sources"]
        ],
    }
