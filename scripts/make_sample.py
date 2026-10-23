"""Regenerate docs/sample_report.{pdf,png} from the latest real sweep result.

Reads the most recent `results/*_*.json` file (excluding `_export.json`) and
renders the top cards as a single-page sample. Run from the repo root:

    python scripts/make_sample.py [--results results] [--profile paralegal_nyc]
                                  [--count 6] [--complete-only] [--renumber]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.exporter import export_to_png
from engine.report import build_report

SAMPLE_PROFILE = {
    "name": "Alex Rivera",
    "search": {"titles": ["Paralegal", "Legal Assistant", "Litigation Support Specialist", "Legal Secretary"],
               "location": "New York, NY"},
    "resume": {"path": "C:/path/to/alex_paralegal_resume.pdf",
               "must_have_skills": ["Westlaw", "LexisNexis", "e-discovery",
                                    "Contract Review", "Legal Research", "Litigation Support"]},
    "platforms": {"greenhouse": True, "ashby": True, "lever": True, "workable": True,
                  "aggregators": False,
                  "custom": [{"name": "SmartRecruiters", "domain": "smartrecruiters.com", "enabled": True},
                             {"name": "Breezy HR", "domain": "breezy.hr", "enabled": True}]},
    "sources": {"jobspy": {"linkedin": True, "indeed": True, "glassdoor": True, "zip_recruiter": True},
                "ashby": {"orgs": []}, "workable": {"slugs": []},
                "builtinnyc": {"enabled": True, "categories": []}},
    "report": {"cards_per_page": 6, "max_cards": 6, "style": "cards", "destinations": []},
    "export": {"format": "pdf,csv,json", "output_dir": "results"},
}


def _latest_results(results_dir: str, profile_stem: str | None) -> str | None:
    pattern = os.path.join(results_dir, f"{profile_stem}_*.json" if profile_stem else "*.json")
    matches = [p for p in glob.glob(pattern) if not p.endswith("_export.json")]
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="results")
    ap.add_argument("--profile", default="paralegal_nyc")
    ap.add_argument("--count", type=int, default=6, help="cards to render (default 6)")
    ap.add_argument(
        "--complete-only",
        action="store_true",
        help="render only cards that carry a company and posting text",
    )
    ap.add_argument(
        "--renumber",
        action="store_true",
        help="number the rendered cards 1..N instead of keeping sweep ranks",
    )
    args = ap.parse_args()

    src = _latest_results(args.results, args.profile)
    if src is None:
        print(f"No sweep result JSON found in {args.results!r} for profile {args.profile!r}", file=sys.stderr)
        sys.exit(1)

    with open(src, encoding="utf-8") as f:
        cards = json.load(f)

    if isinstance(cards, dict):
        cards = cards.get("roles", cards.get("cards", []))

    if args.complete_only:
        cards = [
            c
            for c in cards
            if str(c.get("company") or "").strip() and str(c.get("description") or "").strip()
        ]

    cards = cards[: args.count]
    if args.renumber:
        for position, card in enumerate(cards, start=1):
            card["rank"] = position
    for c in cards:
        c["page"] = 1
        c["page_theme"] = f"Page 1: Ranks 1-{len(cards)}"

    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(out_dir, "docs")
    pdf_path = os.path.join(docs_dir, "sample_report.pdf")

    pages = build_report(cards, pdf_path, SAMPLE_PROFILE)
    print(f"Wrote {pdf_path} ({pages} page(s), {len(cards)} cards) from {src}")

    png_paths = export_to_png(pdf_path, os.path.join(docs_dir, "sample_report"))
    for png_path in png_paths:
        print(f"Wrote {png_path}")


if __name__ == "__main__":
    main()