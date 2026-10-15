from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple

import pymupdf

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

_SKILLS_HEADINGS = {
    "skills", "core skills", "technical skills", "key skills", "competencies",
    "technologies", "tools",
}

_CAPITALIZED_PHRASE_RE = re.compile(r"\b[A-Z][a-z]+(?:[ -][A-Z][a-z]+){1,2}\b")
_WORD_RE = re.compile(r"[a-z][a-z0-9+#.-]{1,20}")

_MAX_KEYWORDS = 60


def _extract_skills_section(full_text_lower: str) -> set:
    """Pull comma/bullet-separated terms from a dedicated Skills section."""
    skills: set = set()
    lines = full_text_lower.splitlines()
    for i, line in enumerate(lines):
        heading = line.strip().rstrip(":")
        if heading in _SKILLS_HEADINGS:
            for following in lines[i + 1 : i + 14]:
                for part in re.split(r"[•|,;·\t]+", following):
                    term = part.strip().strip("•-* ").strip()
                    if 2 <= len(term) <= 40 and not term.startswith(("http", "www")):
                        skills.add(term)
            break
    return skills


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


def extract_resume_keywords(pdf_path: str, must_have_skills: List[str]) -> List[str]:
    """Extract skills and keywords from resume PDF and merge with must-have skills.

    Combines the profile's ``must_have_skills`` with three deterministic signals
    pulled from the résumé text: a dedicated Skills section, frequent non-stopword
    tokens, and capitalized multi-word phrases. The merged list is capped so a long
    résumé cannot dilute the overlap denominator.
    """
    extracted = set(s.strip() for s in must_have_skills if s.strip())
    if not pdf_path:
        return sorted(list(extracted), key=lambda x: x.lower())

    try:
        doc = pymupdf.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " "
        doc.close()

        full_text_lower = full_text.lower()
        for kw in COMMON_DOMAIN_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', full_text_lower):
                extracted.add(kw.title() if len(kw) > 3 else kw.upper())

        extracted.update(_extract_skills_section(full_text_lower))
        extracted.update(_frequent_terms(full_text_lower))
        for phrase in _extract_phrases(full_text):
            extracted.add(phrase.lower())

    except Exception as e:
        log.warning("Could not parse resume PDF at %r: %s", pdf_path, e)

    return sorted(list(extracted), key=lambda x: x.lower())[:_MAX_KEYWORDS]


def determine_badge(job_desc: str) -> str:
    """Determine if application demands extended writing (Amber) or standard quick apply (Slate)."""
    if not job_desc:
        return "Slate"
    desc_lower = job_desc.lower()
    for kw in AMBER_KEYWORDS:
        if re.search(kw, desc_lower):
            return "Amber"
    return "Slate"


def score_jobs(
    jobs: List[Dict],
    resume_path: str,
    must_have_skills: List[str],
    keywords_weight: float = 1.0,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[List[Dict], List[str]]:
    """Score jobs against resume keywords and attach badge, matches, and playbook."""
    keywords = extract_resume_keywords(resume_path, must_have_skills)

    scored_jobs = []

    for idx, job in enumerate(jobs):
        haystack = f"{job.get('title', '')} {job.get('description', '')}".lower()
        matched = []
        missing = []

        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, haystack):
                matched.append(kw)
            else:
                missing.append(kw)

        if keywords:
            raw_pct = (len(matched) / len(keywords)) * 100
            score = max(0, min(100, int(raw_pct * keywords_weight)))
        else:
            score = 75

        top_matches = matched[:3]
        if top_matches:
            playbook = f"Highlight your {', '.join(top_matches)} experience in your application."
        else:
            playbook = "Tailor your cover letter to the core responsibilities listed in the role."

        job["match_score"] = score
        job["badge"] = determine_badge(job.get("description", ""))
        job["key_matches"] = matched[:6]
        job["missing_skills"] = missing[:3]
        job["playbook"] = playbook

        scored_jobs.append(job)

        if progress is not None and (idx + 1) % 25 == 0:
            progress(idx + 1, len(jobs), "Scoring roles")

    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored_jobs, keywords
