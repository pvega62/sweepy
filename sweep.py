import argparse
import sys
import os

from engine.config import run_wizard, load_config
from engine.discovery import discover_jobs
from engine.validator import filter_valid_jobs
from engine.scorer import score_jobs
from engine.pdf_builder import build_pdf
from engine.exporter import export_to_csv, export_to_json

def main():
    parser = argparse.ArgumentParser(description="Career Sweep Engine - Automated Job Board Aggregator")
    parser.add_argument("--setup", action="store_true", help="Run the interactive configuration wizard")
    parser.add_argument("--profile", type=str, help="Path to the YAML profile configuration to use")
    
    args = parser.parse_args()

    print("==========================================================")
    print("                CAREER SWEEP ENGINE")
    print("==========================================================\n")

    if args.setup:
        profile_path = run_wizard()
        print(f"To run your sweep, execute: python sweep.py --profile {profile_path}")
        sys.exit(0)

    # Determine which profile to use
    profile_path = args.profile
    if not profile_path:
        # Check if a custom one exists, or use config.sample.yaml
        if os.path.exists("profiles/custom_profile.yaml"):
            profile_path = "profiles/custom_profile.yaml"
        elif os.path.exists("config.sample.yaml"):
            profile_path = "config.sample.yaml"
            print("Notice: No profile specified. Using config.sample.yaml by default.")
            print("For a tailored search, run: python sweep.py --setup")
        else:
            print("Error: No profile provided and config.sample.yaml not found.")
            print("Please run: python sweep.py --setup")
            sys.exit(1)

    print(f"Loading configuration from {profile_path}...")
    try:
        config = load_config(profile_path)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

    # 1. Extraction from Config
    name = config.get("name", "Job Seeker")
    search = config.get("search", {})
    titles = search.get("titles", [])
    location = search.get("location", "")
    remote_only = search.get("remote_only", False)

    resume = config.get("resume", {})
    resume_path = resume.get("path", "")
    must_have_skills = resume.get("must_have_skills", [])

    export = config.get("export", {})
    formats = export.get("format", "pdf").lower().split(",")
    output_dir = export.get("output_dir", "results")

    # 2. Discover Jobs
    print("\n[1/4] Discovering jobs across multiple platforms...")
    jobs = discover_jobs(titles, location, remote_only)
    if not jobs:
        print("No jobs found matching your criteria. Try expanding your search.")
        sys.exit(0)

    # 3. Validate Links (Check for 404s and soft-404s)
    print("\n[2/4] Validating URLs and removing dead links...")
    valid_jobs = filter_valid_jobs(jobs)
    print(f"  * {len(valid_jobs)} out of {len(jobs)} URLs are active.")

    if not valid_jobs:
        print("All discovered jobs had invalid or dead links. Exiting.")
        sys.exit(0)

    # 4. Score Jobs & Assign Badges
    print("\n[3/4] Analyzing job descriptions and assigning match scores...")
    scored_jobs = score_jobs(valid_jobs, resume_path, must_have_skills)
    print("  * Analysis complete.")

    # 5. Export Results
    print("\n[4/4] Generating outputs...")
    safe_name = name.lower().replace(" ", "_")
    base_output_path = os.path.join(output_dir, f"{safe_name}_sweep")

    if "pdf" in formats:
        build_pdf(scored_jobs, f"{base_output_path}.pdf", name)
    
    if "csv" in formats:
        export_to_csv(scored_jobs, f"{base_output_path}.csv")
        
    if "json" in formats:
        export_to_json(scored_jobs, f"{base_output_path}.json")

    print("\n==========================================================")
    print("                 SWEEP COMPLETE")
    print("==========================================================")

if __name__ == "__main__":
    main()
