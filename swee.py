from __future__ import annotations

import argparse
import datetime
import logging
import os
import re
import shutil
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from typing import Callable, Optional

from engine.config import load_config, run_wizard
from engine.discovery import discover_jobs, discover_sources
from engine.enrich import enrich_jobs
from engine.exporter import export_to_csv, export_to_json
from engine.pdf_builder import build_pdf
from engine.report import build_report
from engine.scorer import score_jobs
from engine.validator import filter_valid_jobs

log = logging.getLogger("sweepy")


def _read_version() -> str:
    version_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "VERSION")
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


VERSION = _read_version()

_DEFAULT_JOBSPY_SITES = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]


def get_dependency_versions() -> str:
    parts = [f"Python {sys.version.split()[0]}"]
    for pkg in ("pymupdf", "reportlab"):
        try:
            parts.append(f"{pkg} {_dist_version(pkg)}")
        except PackageNotFoundError:
            parts.append(f"{pkg} MISSING")
    return " | ".join(parts)


def _configure_logging() -> None:
    root = logging.getLogger("sweepy")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweepy - Automated Job Board Aggregator")
    parser.add_argument("--version", action="store_true", help="Show engine version and dependencies")
    parser.add_argument("--setup", action="store_true", help="Run the interactive configuration wizard")
    parser.add_argument("--profile", type=str, help="Path to the YAML profile configuration to use")

    args = parser.parse_args()

    _configure_logging()

    if args.version:
        print(f"Sweepy v{VERSION}")
        print(get_dependency_versions())
        print("Ready to sweep.")
        sys.exit(0)

    print("================================================================================")
    print(f"Sweepy v{VERSION}")

    if args.setup:
        print("================================================================================\n")
        profile_path = run_wizard()
        print(f"To run your sweep, execute: python swee.py --profile {profile_path}")
        sys.exit(0)

    try:
        run_sweep_pipeline(profile_path=args.profile)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        if not args.profile:
            print("Please run: python swee.py --setup")
        sys.exit(1)


def _project_role(role: dict) -> dict:
    return {
        "title": role.get("title"),
        "company": role.get("company"),
        "location": role.get("location"),
        "match_score": role.get("match_score"),
        "url": role.get("url"),
        "playbook": role.get("playbook", ""),
    }


def run_sweep_pipeline(
    profile_path: Optional[str] = None,
    profile_dict: Optional[dict] = None,
    *,
    verbose: bool = True,
    progress: Optional[Callable[[int, int, str], None]] = None,
    include_roles: bool = False,
) -> dict:
    """
    Executes the Sweepy 5-stage pipeline.
    Accepts either a path to a profile YAML or a pre-loaded/in-memory configuration dictionary.
    Returns a dictionary summarizing the sweep results, output paths, and top roles.
    """
    log_fn = log.info if verbose else (lambda *_: None)

    def _progress(step: int, total: int, label: str) -> None:
        if progress is not None:
            progress(step, total, label)

    if profile_dict is not None:
        config = profile_dict
        profile_stem = re.sub(r'[^a-zA-Z0-9]+', '_', config.get("name", "profile")).strip('_').lower()
    else:
        if not profile_path:
            if os.path.exists("profiles/custom_profile.yaml"):
                profile_path = "profiles/custom_profile.yaml"
            elif os.path.exists("profiles/paralegal_nyc.yaml"):
                profile_path = "profiles/paralegal_nyc.yaml"
            elif os.path.exists("config.sample.yaml"):
                profile_path = "config.sample.yaml"
                log_fn("Notice: No profile specified. Using config.sample.yaml by default.")
            else:
                raise FileNotFoundError("No profile provided and default configuration not found.")

        config = load_config(profile_path)
        profile_stem = os.path.splitext(os.path.basename(profile_path))[0]

    name = config.get("name", "Job Seeker")
    search = config.get("search", {})
    titles = search.get("titles", [])
    location = search.get("location", "")
    remote_only = search.get("remote_only", False)
    include_hybrid = search.get("include_hybrid", True)
    min_salary = search.get("min_salary", 0)

    resume = config.get("resume", {})
    resume_path = resume.get("path", "")
    must_have_skills = resume.get("must_have_skills", [])
    keywords_weight = resume.get("keywords_weight", 1.0)

    platforms = config.get("platforms", {
        "greenhouse": True,
        "ashby": True,
        "lever": True,
        "workable": True,
        "aggregators": False,
    })

    sources = config.get("sources", {}) or {}
    jobspy_cfg = sources.get("jobspy", {}) or {}
    jobspy_sites = [s for s in _DEFAULT_JOBSPY_SITES if jobspy_cfg.get(s, True)]

    report = config.get("report", {}) or {}
    report_style = report.get("style", "cards")
    report_destinations = list(report.get("destinations", []) or [])

    export = config.get("export", {})
    formats = [f.strip().lower() for f in export.get("format", "pdf,csv").split(",") if f.strip()]
    output_dir = export.get("output_dir", "results")

    titles_display = ", ".join(titles) if titles else "All Titles"
    location_suffix = []
    if remote_only:
        location_suffix.append("remote only")
    else:
        location_suffix.append("including remote")
    if not include_hybrid:
        location_suffix.append("no hybrid")
    location_display = f"{location} ({', '.join(location_suffix)})"
    log_fn(f"Profile: {name} — {titles_display} ({location})")
    log_fn("================================================================================")

    # [1/5] Loading profile
    _progress(1, 5, "Loading profile")
    log_fn("[1/5] Loading profile...")
    if profile_path:
        log_fn(f"  * Profile loaded: {profile_path}")
    else:
        log_fn("  * Profile loaded from in-memory configuration")
    log_fn(f"  * Search titles: {titles_display}")
    log_fn(f"  * Location: {location_display}")

    # [2/5] Discovering roles
    _progress(2, 5, "Discovering roles")
    log_fn("\n[2/5] Discovering roles...")
    jobs, platform_counts = discover_jobs(
        titles, location, remote_only, include_hybrid, min_salary, platforms,
        sites=jobspy_sites, progress=progress
    )
    source_jobs, source_counts = discover_sources(
        sources, titles, location, remote_only, include_hybrid, min_salary, progress=progress
    )
    jobs = jobs + source_jobs
    for plat_name, count in source_counts.items():
        platform_counts[plat_name] = platform_counts.get(plat_name, 0) + count
    jobs = list({j["url"]: j for j in jobs if j.get("url")}.values())
    for plat_name, count in platform_counts.items():
        dots = "." * max(3, 25 - len(plat_name))
        log_fn(f"  -> Searching {plat_name}{dots} Found {count} postings")
    log_fn(f"  * Total discovered: {len(jobs)} postings")

    if not jobs:
        log_fn("No jobs found matching your criteria. Try expanding your search.")
        return {
            "status": "completed",
            "discovered_count": 0,
            "active_count": 0,
            "top_match": None,
            "roles": [],
            "top_roles": [],
            "reports": {},
        }

    # [3/5] Validating URLs
    _progress(3, 5, "Validating URLs")
    log_fn("\n[3/5] Validating URLs...")
    log_fn(f"  -> Checking all {len(jobs)} links for active status...")
    valid_jobs, expired_count = filter_valid_jobs(jobs, progress=progress)
    if expired_count > 0:
        log_fn(f"  [x] Removed {expired_count} expired postings (returned dead links or soft-404 redirects)")
    log_fn(f"  * {len(valid_jobs)} verified active postings remain")

    if not valid_jobs:
        log_fn("All discovered jobs had invalid or dead links.")
        return {
            "status": "completed",
            "discovered_count": len(jobs),
            "active_count": 0,
            "top_match": None,
            "roles": [],
            "top_roles": [],
            "reports": {},
        }

    # [4/5] Scoring against resume
    _progress(4, 5, "Scoring against resume")
    log_fn("\n[4/5] Scoring against resume...")
    scored_jobs, extracted_keywords = score_jobs(
        valid_jobs, resume_path, must_have_skills, keywords_weight, progress=progress
    )
    sample_keywords = ", ".join(extracted_keywords[:8])
    if len(extracted_keywords) > 8:
        sample_keywords += "..."
    log_fn(f"  -> Parsing resume: {resume_path}")
    log_fn(f"  -> Extracted {len(extracted_keywords)} keywords: {sample_keywords}")
    log_fn(f"  -> Scoring {len(scored_jobs)} roles against keywords...")
    scores = [j.get("match_score", 0) for j in scored_jobs]
    min_score, max_score = min(scores) if scores else 0, max(scores) if scores else 0
    log_fn(f"  * Scored all {len(scored_jobs)} roles (range: {min_score}% — {max_score}%)")

    # [5/5] Generating reports
    _progress(5, 5, "Generating reports")
    log_fn("\n[5/5] Generating reports...")
    today_str = datetime.date.today().isoformat()
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    time_str = utc_now.strftime("%H%M%S")
    base_output_path = os.path.join(output_dir, f"{profile_stem}_{today_str}-{time_str}")
    os.makedirs(output_dir, exist_ok=True)

    pdf_file = f"{base_output_path}.pdf"
    csv_file = f"{base_output_path}.csv"
    json_file = f"{base_output_path}.json"

    generated_reports = {}

    cards = enrich_jobs(scored_jobs, config)

    if "pdf" in formats:
        if report_style == "legacy":
            total_pages = build_pdf(scored_jobs, pdf_file, name)
        else:
            total_pages = build_report(cards, pdf_file, config)
        log_fn(f"  -> Building PDF: {total_pages} pages ({len(cards)} roles)")
        log_fn(f"  * PDF saved: {pdf_file}")
        generated_reports["pdf"] = os.path.realpath(pdf_file)
        for dest in report_destinations:
            try:
                dest_dir = os.path.expanduser(dest)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copyfile(pdf_file, os.path.join(dest_dir, os.path.basename(pdf_file)))
                log_fn(f"  * PDF copied to: {dest_dir}")
            except Exception as e:
                log_fn(f"  [x] Could not copy PDF to {dest!r}: {e}")

    if "csv" in formats:
        export_rows = cards if report_style != "legacy" else scored_jobs
        num_rows, num_cols = export_to_csv(export_rows, csv_file)
        log_fn(f"  -> Building CSV: {num_rows} rows, {num_cols} columns")
        log_fn(f"  * CSV saved: {csv_file}")
        generated_reports["csv"] = os.path.realpath(csv_file)

    if "json" in formats:
        export_rows = cards if report_style != "legacy" else scored_jobs
        export_to_json(export_rows, json_file)
        log_fn(f"  * JSON saved: {json_file}")
        generated_reports["json"] = os.path.realpath(json_file)

    top_role = scored_jobs[0] if scored_jobs else {}
    top_title = top_role.get("title", "Role")
    top_company = top_role.get("company", "Company")
    top_score = top_role.get("match_score", 0)

    log_fn("\n================================================================================")
    log_fn("Sweep Complete!")
    log_fn(f"  Active roles found: {len(scored_jobs)}")
    log_fn(f"  Top match: {top_title} at {top_company} ({top_score}%)")
    log_fn(f"  Reports saved to: {output_dir}")
    log_fn("================================================================================")

    return {
        "status": "completed",
        "discovered_count": len(jobs),
        "active_count": len(scored_jobs),
        "top_match": {
            "title": top_title,
            "company": top_company,
            "match_score": top_score,
            "url": top_role.get("url", ""),
        } if scored_jobs else None,
        "roles": scored_jobs if include_roles else [],
        "top_roles": [_project_role(r) for r in scored_jobs[:25]],
        "cards": cards,
        "output_dir": os.path.realpath(output_dir),
        "profile": config,
        "reports": generated_reports,
    }


if __name__ == "__main__":
    main()
