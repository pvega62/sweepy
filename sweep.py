import argparse
import sys
import os
import datetime
import importlib.metadata

from engine.config import run_wizard, load_config
from engine.discovery import discover_jobs
from engine.validator import filter_valid_jobs
from engine.scorer import score_jobs
from engine.pdf_builder import build_pdf
from engine.exporter import export_to_csv, export_to_json

VERSION = "1.0.0"

def get_dependency_versions():
    import pymupdf
    import reportlab
    return f"Python {sys.version.split()[0]} | pymupdf {pymupdf.__version__} | reportlab {reportlab.__version__}"

def main():
    parser = argparse.ArgumentParser(description="Career Sweep Engine - Automated Job Board Aggregator")
    parser.add_argument("--version", action="store_true", help="Show engine version and dependencies")
    parser.add_argument("--setup", action="store_true", help="Run the interactive configuration wizard")
    parser.add_argument("--profile", type=str, help="Path to the YAML profile configuration to use")
    
    args = parser.parse_args()

    if args.version:
        print(f"Career Sweep Engine v{VERSION}")
        print(get_dependency_versions())
        print("Ready to sweep.")
        sys.exit(0)

    print("================================================================================")
    print(f"Career Sweep Engine v{VERSION}")

    if args.setup:
        print("================================================================================\n")
        profile_path = run_wizard()
        print(f"To run your sweep, execute: python sweep.py --profile {profile_path}")
        sys.exit(0)

    # Determine profile path
    profile_path = args.profile
    if not profile_path:
        if os.path.exists("profiles/custom_profile.yaml"):
            profile_path = "profiles/custom_profile.yaml"
        elif os.path.exists("profiles/paralegal_nyc.yaml"):
            profile_path = "profiles/paralegal_nyc.yaml"
        elif os.path.exists("config.sample.yaml"):
            profile_path = "config.sample.yaml"
            print("Notice: No profile specified. Using config.sample.yaml by default.")
        else:
            print("Error: No profile provided and default configuration not found.")
            print("Please run: python sweep.py --setup")
            sys.exit(1)

    try:
        config = load_config(profile_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    name = config.get("name", "Job Seeker")
    search = config.get("search", {})
    titles = search.get("titles", [])
    location = search.get("location", "")
    remote_only = search.get("remote_only", False)
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
        "aggregators": False
    })

    export = config.get("export", {})
    formats = [f.strip().lower() for f in export.get("format", "pdf,csv").split(",") if f.strip()]
    output_dir = export.get("output_dir", "results")

    titles_display = ", ".join(titles) if titles else "All Titles"
    location_display = f"{location} (including remote)" if not remote_only else f"{location} (remote only)"
    print(f"Profile: {name} — {titles_display} ({location})")
    print("================================================================================\n")

    # [1/5] Loading profile
    print("[1/5] Loading profile...")
    print(f"  * Profile loaded: {profile_path}")
    print(f"  * Search titles: {titles_display}")
    print(f"  * Location: {location_display}")

    # [2/5] Discovering roles
    print("\n[2/5] Discovering roles...")
    jobs, platform_counts = discover_jobs(titles, location, remote_only, min_salary, platforms)
    for plat_name, count in platform_counts.items():
        dots = "." * max(3, 25 - len(plat_name))
        print(f"  -> Searching {plat_name}{dots} Found {count} postings")
    print(f"  * Total discovered: {len(jobs)} postings")

    if not jobs:
        print("No jobs found matching your criteria. Try expanding your search.")
        sys.exit(0)

    # [3/5] Validating URLs
    print("\n[3/5] Validating URLs...")
    print(f"  -> Checking all {len(jobs)} links for active status...")
    valid_jobs, expired_count = filter_valid_jobs(jobs)
    if expired_count > 0:
        print(f"  [x] Removed {expired_count} expired postings (returned dead links or soft-404 redirects)")
    print(f"  * {len(valid_jobs)} verified active postings remain")

    if not valid_jobs:
        print("All discovered jobs had invalid or dead links. Exiting.")
        sys.exit(0)

    # [4/5] Scoring against resume
    print("\n[4/5] Scoring against resume...")
    scored_jobs, extracted_keywords = score_jobs(valid_jobs, resume_path, must_have_skills, keywords_weight)
    sample_keywords = ", ".join(extracted_keywords[:8])
    if len(extracted_keywords) > 8:
        sample_keywords += "..."
    print(f"  -> Parsing resume: {resume_path}")
    print(f"  -> Extracted {len(extracted_keywords)} keywords: {sample_keywords}")
    print(f"  -> Scoring {len(scored_jobs)} roles against keywords...")
    scores = [j.get("match_score", 0) for j in scored_jobs]
    min_score, max_score = min(scores) if scores else 0, max(scores) if scores else 0
    print(f"  * Scored all {len(scored_jobs)} roles (range: {min_score}% — {max_score}%)")

    # [5/5] Generating reports
    print("\n[5/5] Generating reports...")
    today_str = datetime.date.today().isoformat()
    profile_stem = os.path.splitext(os.path.basename(profile_path))[0]
    base_output_path = os.path.join(output_dir, f"{profile_stem}_{today_str}")
    os.makedirs(output_dir, exist_ok=True)

    pdf_file = f"{base_output_path}.pdf"
    csv_file = f"{base_output_path}.csv"
    json_file = f"{base_output_path}.json"

    if "pdf" in formats:
        total_pages = build_pdf(scored_jobs, pdf_file, name)
        print(f"  -> Building PDF: {total_pages} pages (4 cards per page, {len(scored_jobs)} roles)")
        print(f"  * PDF saved: {pdf_file}")

    if "csv" in formats:
        num_rows, num_cols = export_to_csv(scored_jobs, csv_file)
        print(f"  -> Building CSV: {num_rows} rows, {num_cols} columns")
        print(f"  * CSV saved: {csv_file}")

    if "json" in formats:
        export_to_json(scored_jobs, json_file)
        print(f"  * JSON saved: {json_file}")

    # Completion Banner
    top_role = scored_jobs[0] if scored_jobs else {}
    top_title = top_role.get("title", "Role")
    top_company = top_role.get("company", "Company")
    top_score = top_role.get("match_score", 0)

    print("\n================================================================================")
    print("Sweep Complete!")
    print(f"  Active roles found: {len(scored_jobs)}")
    print(f"  Top match: {top_title} at {top_company} ({top_score}%)")
    print(f"  Reports saved to: {output_dir}\\")
    print("================================================================================")

if __name__ == "__main__":
    main()
