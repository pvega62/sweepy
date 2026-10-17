from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple

import pymupdf

from engine.enrich import _strip_html, _strip_md, route_track

log = logging.getLogger("sweepy.engine.scorer")

AMBER_KEYWORDS = [
    r"cover letter",
    r"portfolio",
    r"writing sample",
    r"assessment",
    r"take[- ]?home",
    r"challenge",
    r"case study",
    r"essay"
]

COMMON_DOMAIN_KEYWORDS = [
    # Legal & Compliance
    "westlaw", "lexisnexis", "e-discovery", "ediscovery", "contract review",
    "legal research", "document management", "case management", "litigation support",
    "relativity", "court filings", "docketing", "subpoena", "cite checking", "bluebook",
    # Tech & Design
    "python", "react", "typescript", "javascript", "sql", "css", "html", "git",
    "docker", "kubernetes", "aws", "rest api", "graphql", "figma", "node.js"
]

# Terms that appear in almost every resume and posting but carry no signal.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "as", "at", "by", "in", "of", "on", "to",
    "for", "with", "you", "your", "are", "have", "has", "had", "that", "this", "these",
    "those", "from", "will", "can", "could", "would", "should", "our", "their", "they",
    "them", "was", "were", "been", "being", "is", "am", "be", "do", "does", "did",
    "get", "got", "we", "he", "she", "it", "i", "not", "also", "into", "about", "each",
    "other", "such", "more", "most", "than", "then", "when", "what", "which", "who",
    "how", "all", "any", "new", "within", "across", "using", "use", "used", "include",
    "including", "years", "year", "experience", "work", "team", "job", "role", "roles",
    "company", "requirements", "qualifications", "responsibilities", "skills", "ability",
    "candidate", "position", "etc",
}

_SKILLS_START_HEADINGS = {
    "skills", "core skills", "technical skills", "key skills", "competencies",
    "technologies", "tools",
}

# Lines that end a Skills block instead of extending it. A heading such as
# "experience" or "languages" marks the next section, so collection stops there.
_HEADING_STOPWORDS = _STOPWORDS | {
    "additional", "additional skills", "additional information", "languages",
    "certifications", "education", "projects", "references", "awards",
    "volunteer", "interests", "summary", "profile", "publications", "training",
}
_SKILLS_HEADINGS = _SKILLS_START_HEADINGS | _HEADING_STOPWORDS

# Months, month tokens, and years carry dates, never skills.
_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep", "oct",
    "nov", "dec",
}
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")

# A leading conjunction, preposition, résumé label, or proficiency word makes
# the rest of the fragment a sentence, not a skill.
_LEADING_JUNK = {
    "and", "or", "the", "with", "for", "plus", "including", "etc", "additional",
    "other", "languages", "language", "experience", "skills", "remote", "hybrid",
    "freelance", "present", "fluent", "proficient", "intermediate", "beginner",
    "advanced", "bilingual", "native",
}

_BULLETS = "•●▪◦‣·-*"
_TRIM_CHARS = _BULLETS + " \t,;:|/#\"'`<>{}[]"
_URL_PREFIXES = ("http", "www", "//")

_SKILL_SEPARATORS = ",;|·\t•●▪‣>"

_CAPITALIZED_PHRASE_RE = re.compile(r"\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+){1,2}\b")
_WORD_RE = re.compile(r"[a-z][a-z0-9+#.-]{1,20}")

_MAX_KEYWORDS = 60
_MAX_SKILL_LEN = 40
_MAX_JOB_KEYWORDS = 25

# Matching accepts these common acronym expansions in either direction.
_KEYWORD_ALIASES = {
    "api": ("application programming interface",),
    "application programming interface": ("api",),
    "cms": ("content management system",),
    "content management system": ("cms",),
    "seo": ("search engine optimization",),
    "search engine optimization": ("seo",),
    "ui": ("user interface",),
    "user interface": ("ui",),
    "ux": ("user experience",),
    "user experience": ("ux",),
    "wcag": ("web content accessibility guidelines",),
    "web content accessibility guidelines": ("wcag",),
}

# Headings a posting uses to label what it wants. Terms inside such a block
# outrank terms from the surrounding marketing copy.
_JOB_SECTION_STARTS = _SKILLS_START_HEADINGS | {
    "requirements", "requirement", "required", "required skills",
    "minimum qualifications", "basic qualifications", "preferred qualifications",
    "qualifications", "qualification", "requirements and qualifications",
    "what you'll bring", "what you will bring", "what you need",
    "what we're looking for", "what we are looking for", "we're looking for",
    "who you are", "you have", "you bring", "about you", "must have", "must haves",
    "nice to have", "your experience", "experience required",
}

_REQUIRED_JOB_HEADINGS = {
    "requirements", "requirement", "required", "required skills",
    "minimum qualifications", "basic qualifications", "qualifications",
    "qualification", "requirements and qualifications", "must have", "must haves",
    "what you'll bring", "what you will bring", "what you need",
    "what we're looking for", "what we are looking for", "we're looking for",
    "who you are", "you have", "you bring", "about you", "your experience",
    "experience required",
}
_PREFERRED_JOB_HEADINGS = {
    "preferred qualifications", "preferred skills", "nice to have", "nice to haves",
}

# Headings that end a requirements block.
_JOB_SECTION_BREAKS = _JOB_SECTION_STARTS | {
    "responsibilities", "what you'll do", "what you will do", "duties",
    "the role", "about the role", "about us", "about the team", "our team",
    "benefits", "perks", "compensation", "salary", "how to apply", "why join us",
    "what we offer", "we offer", "equal opportunity", "equal opportunities",
    "equal employment opportunity",
}

_BLOCK_TAG_RE = re.compile(
    r"(?i)</(?:p|div|li|ul|ol|h[1-6]|section|tr|td|blockquote)\s*>|<br\s*/?>"
)

_SMART_PUNCTUATION = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-",
}


def _clean_keyword(term: str, max_len: int = 60) -> Optional[str]:
    """Return ``term`` as a usable keyword, or None when it carries no signal.

    Rejects unbalanced parenthetical fragments, dates, stopword-led phrases,
    punctuation-only strings, initials such as ``n.y.``, and length outliers,
    and strips parenthetical qualifiers from the terms it keeps.
    """
    if not term:
        return None
    text = re.sub(r"\s+", " ", str(term)).strip()
    text = text.strip(_TRIM_CHARS).strip()
    # Drop parenthetical qualifiers. "(Concepts, IA)" and "(rest, openapi)" are
    # asides the résumé makes, not words a posting repeats, and the fragment
    # left behind reads as the skill itself: "api documentation".
    text = re.sub(r"\s*\([^()]*\)", "", text).strip()
    if not text:
        return None
    if text.count("(") != text.count(")"):
        # A stray half of a parentheses group, e.g. "(indesign" or "acrobat)".
        return None
    # Checks run against a lower-case copy so an acronym such as SQL keeps its
    # display form without dodging the month, stopword, and date rules.
    lowered = text.lower()
    if not re.search(r"[a-z]", lowered):
        return None
    tokens = [token for token in re.split(r"[^a-z0-9+#./-]+", lowered) if token]
    if not tokens:
        return None
    if any(token in _MONTHS for token in tokens):
        return None
    if _YEAR_RE.search(text):
        return None
    if tokens[0] in _LEADING_JUNK or tokens[0] in _STOPWORDS:
        return None
    if re.fullmatch(r"[a-z](\.[a-z])+\.?", lowered):
        return None
    if not 2 <= len(text) <= max_len:
        return None
    if lowered.startswith(_URL_PREFIXES):
        return None
    return text


def _split_skill_fragments(line: str) -> list:
    """Split a skills line on separators that sit outside parentheses.

    ``Research (Concepts, IA), Figma`` yields two fragments, not three, so the
    parentheses stay attached to their term.
    """
    fragments = []
    buf = []
    depth = 0
    for char in line:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if depth <= 0 and char in _SKILL_SEPARATORS:
            fragments.append("".join(buf))
            buf = []
            continue
        buf.append(char)
    fragments.append("".join(buf))
    return fragments


def _heading_key(line: str) -> str:
    """Normalize a line into a comparable section-heading key."""
    text = line.strip()
    for source, target in _SMART_PUNCTUATION.items():
        text = text.replace(source, target)
    text = re.sub(r"^[\s#*•·\-]+", "", text)
    text = re.sub(r"[\s:#*•·\-]+$", "", text)
    return re.sub(r"\s+", " ", text).lower()


def _section_terms(body: str, max_len: int = _MAX_SKILL_LEN) -> list:
    """Pull separated terms out of a block of text, in first-seen order."""
    terms: Dict[str, str] = {}
    for line in body.splitlines():
        for fragment in _split_skill_fragments(line):
            cleaned = _clean_keyword(fragment, max_len=max_len)
            if cleaned is not None:
                terms.setdefault(cleaned.lower(), cleaned)
    return list(terms.values())


def _extract_skills_section(full_text_lower: str) -> list:
    """Pull terms from a dedicated Skills section, in first-seen order."""
    body: List[str] = []
    lines = full_text_lower.splitlines()
    for i, line in enumerate(lines):
        if _heading_key(line) not in _SKILLS_START_HEADINGS:
            continue
        for following in lines[i + 1 : i + 14]:
            if _heading_key(following) in _SKILLS_HEADINGS:
                break
            body.append(following)
        break
    return _section_terms("\n".join(body))


def _domain_terms(full_text_lower: str) -> list:
    """Return the COMMON_DOMAIN_KEYWORDS present in the text, in list order."""
    return [
        kw.title() if len(kw) > 3 else kw.upper()
        for kw in COMMON_DOMAIN_KEYWORDS
        if re.search(r"\b" + re.escape(kw) + r"\b", full_text_lower)
    ]


def _read_resume_text(resume_path: str) -> str:
    """Return the plain text of a PDF or DOCX résumé.

    PDFs (and any other extension) go through pymupdf. DOCX files go through
    python-docx, because pymupdf silently opens the ZIP container and returns
    reordered, garbled text instead of failing.
    """
    if resume_path.lower().endswith(".docx"):
        try:
            from engine.docx import docx_text

            return docx_text(resume_path)
        except ImportError:
            log.warning(
                "python-docx is not installed; cannot read DOCX resume %r", resume_path
            )
            return ""
    doc = pymupdf.open(resume_path)
    try:
        pages = []
        for page in doc:
            blocks = []
            for block in page.get_text("dict", sort=True)["blocks"]:
                lines = block.get("lines")
                if not lines:
                    continue
                blocks.append(_flow_pdf_block(lines))
            pages.append("\n".join(blocks))
        return "\n".join(pages)
    finally:
        doc.close()


def _flow_pdf_block(lines: list) -> str:
    """Join visual wraps inside one PDF text block without merging list items."""
    flowed_lines = []
    previous = None
    for line in lines:
        spans = line.get("spans", [])
        text = "".join(span.get("text", "") for span in spans).strip()
        if not text:
            continue

        bbox = line.get("bbox", (0, 0, 0, 0))
        font_size = max((float(span.get("size", 0)) for span in spans), default=0.0)
        bullet_start = text.startswith(tuple(_BULLETS))
        continues = False
        if previous is not None:
            prev_text, prev_bbox, prev_size = previous
            line_height = max(font_size, prev_size, 1.0)
            vertical_gap = bbox[1] - prev_bbox[3]
            tolerance = max(2.0, line_height * 0.75)
            prev_bullet = prev_text.startswith(tuple(_BULLETS))
            same_indent = abs(bbox[0] - prev_bbox[0]) <= max(2.0, line_height * 0.25)
            if prev_bullet and not bullet_start:
                same_indent = 0 <= bbox[0] - prev_bbox[0] <= line_height * 2.5
            has_separator = prev_text.rstrip().endswith((",", ";", "|", "•", "●", "▪", "‣"))
            ends_sentence = prev_text.rstrip().endswith((".", "!", "?"))
            continues = (
                same_indent
                and -1 <= vertical_gap <= tolerance
                and not bullet_start
                and not has_separator
                and not ends_sentence
            )

        if continues:
            flowed_lines[-1] = f"{flowed_lines[-1]} {text}"
        else:
            flowed_lines.append(text)
        previous = (text, bbox, font_size)

    return "\n".join(flowed_lines)


def _flow_text(text: str) -> str:
    """Join hard-wrapped lines so a phrase split across a line break stays whole.

    PDF extractors emit a newline at every visual line end, so 'First Aid' becomes
    'First\\nAid' and multi-word keywords fragment into 'first' and 'aid'. The
    DOCX reader keeps the paragraph on one line, which made the same résumé score
    differently as PDF and DOCX. Line structure still matters for section
    detection, so callers keep the raw text for that and use this flowed copy for
    token and phrase tiers.
    """
    return re.sub(r"\s*\n\s*", " ", text or "")


def _frequent_terms(full_text_lower: str, limit: int = 20) -> list:
    """Return the most frequent non-stopword tokens as proxy skills."""
    words = _WORD_RE.findall(full_text_lower)
    counts = Counter(w for w in words if w not in _STOPWORDS and len(w) >= 3)
    return [w for w, _ in counts.most_common(limit)]


def _extract_phrases(full_text: str, limit: int = 20) -> list:
    """Return capitalized multi-word phrases (e.g. 'Technical Writer')."""
    phrases = set()
    for match in _CAPITALIZED_PHRASE_RE.findall(full_text or ""):
        phrase = match.strip()
        if len(phrase) >= 4:
            phrases.add(phrase)
    return list(phrases)[:limit]


def extract_resume_keywords(resume_path: str, must_have_skills: List[str]) -> List[str]:
    """Extract scoring keywords from a PDF or DOCX résumé.

    Reads the résumé as PDF (pymupdf) or DOCX (python-docx) and merges
    ``must_have_skills`` with four tiers of evidence, highest signal first:
    the Skills section, COMMON_DOMAIN_KEYWORDS present in the text, frequent
    non-stopword terms, and capitalized phrases already vouched for by one of
    those tiers. The list is capped at ``_MAX_KEYWORDS``, so the cap drops the
    weakest tier rather than the alphabetically last term.
    """
    keywords, _ = _resume_signals(resume_path, must_have_skills)
    return keywords


def _resume_signals(resume_path: str, must_have_skills: List[str]) -> Tuple[List[str], str]:
    """Return the résumé's keywords and its lower-cased text from one file read.

    The text drives posting-side coverage, so callers that need both get them
    from a single parse of the résumé.
    """
    keywords: Dict[str, str] = {}

    for skill in must_have_skills or []:
        _add_keyword(keywords, skill)

    if not resume_path:
        return list(keywords.values()), ""

    resume_text = ""
    try:
        full_text = _read_resume_text(resume_path)
        resume_text = full_text.lower()
        full_text_lower = resume_text
        flowed_lower = _flow_text(resume_text)

        for term in _extract_skills_section(full_text_lower):
            _add_keyword(keywords, term, max_len=_MAX_SKILL_LEN)

        for term in _domain_terms(flowed_lower):
            _add_keyword(keywords, term)

        for term in _frequent_terms(flowed_lower):
            _add_keyword(keywords, term)

        # Capitalized phrases count as keywords only when a higher tier already
        # vouches for them. Everything else is a résumé-specific proper noun - a
        # school, employer, or program name - that no job posting will contain,
        # and each one permanently deflates every match score. A term-frequency
        # proxy (drop a proper noun seen once) is deliberately absent: résumé
        # tokens mostly appear once, so that rule would delete real skills.
        confirmed = set(keywords)
        for phrase in _extract_phrases(_flow_text(full_text)):
            if phrase.lower() in confirmed:
                _add_keyword(keywords, phrase)
    except Exception as e:
        log.warning("Could not parse resume %r: %s", resume_path, e)
        resume_text = ""

    return list(keywords.values())[:_MAX_KEYWORDS], resume_text


def _add_keyword(keywords: Dict[str, str], term: str, max_len: int = 60) -> None:
    """Merge one candidate term into ``keywords``, keyed by its lower-cased form.

    One form per lower-cased keyword, so no case-duplicate pair survives
    (Docker/docker, Javascript/javascript). The highest-signal tier that
    contributed the term wins, except that a short all-caps form always upgrades
    a lowercase twin: CSS, GIT, and API keep their capitals.
    """
    cleaned = _clean_keyword(term, max_len=max_len)
    if cleaned is None:
        return
    key = cleaned.lower()
    existing = keywords.get(key)
    if existing is None:
        keywords[key] = cleaned
        return
    if cleaned.isupper() and len(cleaned) <= 5 and not existing.isupper():
        keywords[key] = cleaned


def _job_text(job: Dict) -> str:
    """Return the posting as plain lines of text, one block per line.

    Titles and descriptions arrive as markdown or HTML depending on the source.
    Block tags become newlines before the shared strippers run, so the
    requirements/qualifications structure survives for section detection.
    """
    title = _strip_html(_strip_md(str(job.get("title") or ""))).strip()
    description = str(job.get("description") or "")
    description = _BLOCK_TAG_RE.sub("\n", description)
    lines = [
        _strip_html(_strip_md(line))
        for line in description.splitlines()
        if line.strip()
    ]
    return "\n".join(part for part in [title, *lines] if part)


def _job_requirement_text(text: str) -> str:
    """Return the posting's requirements block, or "" when it labels none."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _heading_key(line) not in _JOB_SECTION_STARTS:
            continue
        body = []
        for following in lines[i + 1 :]:
            if _heading_key(following) in _JOB_SECTION_BREAKS:
                break
            body.append(following)
        if body:
            return "\n".join(body)
    # A labeled heading that shares a line with its list, e.g. "Requirements: 5+ years".
    inline = re.search(
        r"(?im)^\s*(?:requirements|qualifications|required skills)\s*:\s*(.+)$", text
    )
    return inline.group(1).strip() if inline else ""


def _job_priority_keywords(job: Dict) -> Tuple[List[str], List[str]]:
    """Extract keywords from explicitly required and preferred posting sections."""
    required_lines = []
    preferred_lines = []
    current = None

    for line in _job_text(job).splitlines():
        heading_text, separator, inline_text = line.partition(":")
        heading = _heading_key(heading_text if separator else line)
        if heading in _REQUIRED_JOB_HEADINGS:
            current = required_lines
            content = inline_text
        elif heading in _PREFERRED_JOB_HEADINGS:
            current = preferred_lines
            content = inline_text
        elif heading in _JOB_SECTION_STARTS or heading in _JOB_SECTION_BREAKS:
            current = None
            content = ""
        else:
            content = line

        if current is not None and content.strip():
            current.append(content.strip())

    def collect(lines: List[str]) -> List[str]:
        text = "\n".join(lines).lower()
        keywords: Dict[str, str] = {}
        for term in _domain_terms(text):
            _add_keyword(keywords, term)
        for term in _section_terms(text):
            _add_keyword(keywords, term)
        for term in _frequent_terms(text, limit=_MAX_JOB_KEYWORDS):
            _add_keyword(keywords, term)
        return list(keywords.values())

    return collect(required_lines), collect(preferred_lines)


def extract_job_keywords(job: Dict) -> List[str]:
    """Extract what a posting asks for, strongest signal first.

    Explicit required and preferred sections outrank surrounding marketing copy.
    Without a labeled section, the posting's most frequent non-stopword terms
    stand in. Returns an empty list when the posting carries no usable text.
    """
    text = _job_text(job)
    if not text:
        return []
    text_lower = text.lower()

    section = _job_requirement_text(text)
    section_lower = section.lower()

    keywords: Dict[str, str] = {}
    required_keywords, preferred_keywords = _job_priority_keywords(job)
    for term in required_keywords:
        _add_keyword(keywords, term)
    for term in preferred_keywords:
        _add_keyword(keywords, term)
    for term in _domain_terms(text_lower):
        _add_keyword(keywords, term)
    for term in _section_terms(section_lower):
        _add_keyword(keywords, term)
    frequent_source = section_lower or text_lower
    for term in _frequent_terms(frequent_source, limit=_MAX_JOB_KEYWORDS):
        _add_keyword(keywords, term)

    return list(keywords.values())[:_MAX_JOB_KEYWORDS]


def determine_badge(job_desc: str) -> str:
    """Determine if application demands extended writing (Amber) or standard quick apply (Slate)."""
    if not job_desc:
        return "Slate"
    desc_lower = job_desc.lower()
    for kw in AMBER_KEYWORDS:
        if re.search(kw, desc_lower):
            return "Amber"
    return "Slate"


def normalize_synonyms(raw) -> Dict[str, Tuple[str, ...]]:
    """Return a term -> interchangeable-terms map from a profile's synonym groups.

    Accepts either a mapping (``{"docs-as-code": ["documentation as code"]}``) or
    a list of groups (``[["docs-as-code", "documentation as code"]]``). Every
    member of a group maps to the rest of the group, so matching works in both
    directions: a posting keyword and a résumé phrase meet in the middle even
    when only one of them appears in the group.
    """
    groups: List[List[str]] = []
    if isinstance(raw, dict):
        for term, equivalents in raw.items():
            members = equivalents if isinstance(equivalents, (list, tuple, set)) else [equivalents]
            groups.append([str(term), *(str(m) for m in members)])
    elif isinstance(raw, (list, tuple, set)):
        for entry in raw:
            if isinstance(entry, (list, tuple, set)):
                groups.append([str(member) for member in entry])
            else:
                groups.append([str(entry)])

    synonyms: Dict[str, Tuple[str, ...]] = {}
    for group in groups:
        cleaned = []
        for member in group:
            term = re.sub(r"\s+", " ", str(member)).strip().lower()
            if term and term not in cleaned:
                cleaned.append(term)
        if len(cleaned) < 2:
            continue
        for term in cleaned:
            others = tuple(other for other in cleaned if other != term)
            synonyms[term] = tuple(dict.fromkeys([*synonyms.get(term, ()), *others]))
    return synonyms


def _keyword_aliases(
    keyword: str, synonyms: Optional[Dict[str, Tuple[str, ...]]]
) -> Tuple[str, ...]:
    """Return the built-in and profile-supplied equivalents for one keyword."""
    built_in = _KEYWORD_ALIASES.get(keyword, ())
    if not synonyms:
        return built_in
    supplied = synonyms.get(keyword, ())
    if not supplied:
        return built_in
    return tuple(dict.fromkeys([*supplied, *built_in]))


def _job_cover(
    job_keywords: List[str],
    resume_text: str,
    required_keywords: Optional[List[str]] = None,
    preferred_keywords: Optional[List[str]] = None,
    synonyms: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> float:
    """Weighted share of the posting's keywords that the résumé text already shows.

    Coverage runs against the résumé text a single résumé read produced, so a
    sweep never re-parses the résumé per posting. Explicitly required terms
    carry twice the weight of unlabelled terms; preferred terms carry half.
    """
    if not job_keywords or not resume_text:
        return 0.0
    required = {kw.lower() for kw in required_keywords or []}
    preferred = {kw.lower() for kw in preferred_keywords or []} - required
    total_weight = 0.0
    matched_weight = 0.0
    for keyword in job_keywords:
        lowered = keyword.lower()
        weight = 2.0 if lowered in required else 0.5 if lowered in preferred else 1.0
        total_weight += weight
        if _keyword_in_text(keyword, resume_text, synonyms):
            matched_weight += weight
    return matched_weight / total_weight if total_weight else 0.0


def _keyword_in_text(
    keyword: str,
    text: str,
    synonyms: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> bool:
    """Match a keyword as a phrase, allowing regular inflections and known aliases."""
    keyword = keyword.lower().strip()
    text = text.lower()
    candidates = [keyword, *_keyword_aliases(keyword, synonyms)]
    for candidate in candidates:
        words = candidate.split()
        if not words:
            continue
        final = words[-1]
        forms = {final}
        if final.endswith("ies") and len(final) > 4:
            forms.add(f"{final[:-3]}y")
        elif final.endswith(("ches", "shes", "xes", "zes", "sses")):
            forms.add(final[:-2])
        elif final.endswith("s") and not final.endswith(("ss", "us", "is")):
            forms.add(final[:-1])
        elif final.endswith(("s", "x", "z", "ch", "sh")):
            forms.add(f"{final}es")
        else:
            forms.add(f"{final}s")

        for form in forms:
            phrase = " ".join([*words[:-1], form])
            pattern = re.escape(phrase).replace(r"\ ", r"\s+")
            if re.search(r"\b" + pattern + r"\b", text):
                return True
    return False


def _score_job_against_keywords(
    job: Dict,
    keywords: List[str],
    keywords_weight: float,
    resume_text: str = "",
    synonyms: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> None:
    """Set match_score, coverage, badge, key_matches, and playbook on a job dict.

    The score blends two directions: how much of the résumé's vocabulary the
    posting repeats (``resume_cover``) and how much of the posting's requirements
    the résumé already shows (``job_cover``). The posting side carries the larger
    weight, because the ad defines what the match means.
    """
    haystack = f"{job.get('title', '')} {job.get('description', '')}".lower()
    matched = []
    missing = []

    for kw in keywords:
        if _keyword_in_text(kw, haystack, synonyms):
            matched.append(kw)
        else:
            missing.append(kw)

    resume_cover = len(matched) / len(keywords) if keywords else None
    job_keywords = extract_job_keywords(job)
    required_keywords, preferred_keywords = _job_priority_keywords(job)
    job_cover = _job_cover(
        job_keywords,
        resume_text,
        required_keywords=required_keywords,
        preferred_keywords=preferred_keywords,
        synonyms=synonyms,
    )
    # The posting side needs both an extractable posting and a readable résumé.
    # Without one of them, the blend degrades to the résumé-side overlap.
    job_side = bool(job_keywords) and bool(resume_text)

    if resume_cover is None and not job_side:
        score = 75
    elif resume_cover is None:
        score = max(0, min(100, int(job_cover * 100 * keywords_weight)))
    elif not job_side:
        score = max(0, min(100, int(resume_cover * 100 * keywords_weight)))
    else:
        raw = 0.4 * resume_cover + 0.6 * job_cover
        score = max(0, min(100, int(raw * 100 * keywords_weight)))

    top_matches = matched[:3]
    if top_matches:
        playbook = f"Highlight your {', '.join(top_matches)} experience in your application."
    else:
        playbook = "Tailor your cover letter to the core responsibilities listed in the role."

    job["match_score"] = score
    job["job_coverage"] = int(job_cover * 100)
    job["job_keywords"] = job_keywords
    job["badge"] = determine_badge(job.get("description", ""))
    job["key_matches"] = matched[:6]
    job["missing_skills"] = missing[:3]
    job["playbook"] = playbook


def score_jobs(
    jobs: List[Dict],
    resume_path: str,
    must_have_skills: List[str],
    keywords_weight: float = 1.0,
    progress: Optional[Callable[[int, int, str], None]] = None,
    synonyms: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> Tuple[List[Dict], List[str]]:
    """Score jobs against resume keywords and attach badge, matches, and playbook."""
    keywords, resume_text = _resume_signals(resume_path, must_have_skills)

    scored_jobs = []

    for idx, job in enumerate(jobs):
        _score_job_against_keywords(job, keywords, keywords_weight, resume_text, synonyms)
        scored_jobs.append(job)

        if progress is not None and (idx + 1) % 25 == 0:
            progress(idx + 1, len(jobs), "Scoring roles")

    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored_jobs, keywords


def score_jobs_by_track(
    jobs: List[Dict],
    tracks: List[Dict],
    default_resume_path: str,
    must_have_skills: List[str],
    keywords_weight: float = 1.0,
    progress: Optional[Callable[[int, int, str], None]] = None,
    synonyms: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> Tuple[List[Dict], List[str]]:
    """Score each job against the resume for the track it routes to."""
    signal_cache: Dict[str, Tuple[List[str], str]] = {}
    for track in tracks:
        path = track.get("path") or default_resume_path
        if path not in signal_cache:
            # One résumé read per unique path, keywords and coverage text alike.
            signal_cache[path] = _resume_signals(path, must_have_skills)

    all_keywords: set = set()
    for keywords, _ in signal_cache.values():
        all_keywords.update(keywords)

    scored_jobs = []

    for idx, job in enumerate(jobs):
        track = route_track(job.get("title", ""), job.get("description", ""), tracks)
        path = track.get("path") or default_resume_path
        keywords, resume_text = signal_cache[path]
        _score_job_against_keywords(job, keywords, keywords_weight, resume_text, synonyms)
        job["resume_track"] = track.get("name", "")
        job["resume_color"] = track.get("color", "#1D4ED8")

        scored_jobs.append(job)

        if progress is not None and (idx + 1) % 25 == 0:
            progress(idx + 1, len(jobs), "Scoring roles")

    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored_jobs, sorted(list(all_keywords), key=lambda x: x.lower())
