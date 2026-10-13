from __future__ import annotations

import logging
import re
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


def extract_resume_keywords(pdf_path: str, must_have_skills: List[str]) -> List[str]:
    """Extract skills and keywords from resume PDF and merge with must-have skills."""
    extracted = set([s.strip() for s in must_have_skills if s.strip()])
    if not pdf_path:
        return sorted(list(extracted))

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

        tokens = re.findall(r'\b[A-Z][a-zA-Z0-9+#\.\-]{2,18}\b', full_text)
        for token in tokens:
            if token.lower() in COMMON_DOMAIN_KEYWORDS:
                extracted.add(token)

    except Exception as e:
        log.warning("Could not parse resume PDF at %r: %s", pdf_path, e)

    return sorted(list(extracted), key=lambda x: x.lower())


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
        desc = job.get("description", "").lower()
        matched = []
        missing = []

        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, desc):
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
        job["badge"] = determine_badge(desc)
        job["key_matches"] = matched[:6]
        job["missing_skills"] = missing[:3]
        job["playbook"] = playbook

        scored_jobs.append(job)

        if progress is not None and (idx + 1) % 25 == 0:
            progress(idx + 1, len(jobs), "Scoring roles")

    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored_jobs, keywords
