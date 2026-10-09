"""
Sweepy MCP Server
Provides standard MCP tools (stdio transport) for LLMs (Claude, Antigravity, etc.)
to automate job board discovery, profile generation, and match scoring.
"""

import os
import glob
import json
from typing import List, Optional
from mcp.server.fastmcp import FastMCP

from swee import run_sweep_pipeline
from engine.config import save_profile, load_config
from engine.pdf_builder import build_pdf
from engine.exporter import export_to_csv, export_to_json

# Initialize FastMCP Server
mcp = FastMCP("sweepy")

@mcp.tool()
def create_profile(
    name: str,
    titles: List[str],
    location: str,
    resume_path: str,
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    must_have_skills: Optional[List[str]] = None,
    platforms: Optional[dict] = None,
    output_filename: Optional[str] = None
) -> str:
    """
    Creates or updates a Sweepy search profile YAML file.
    
    Args:
        name: Full name of the candidate.
        titles: List of target job titles (e.g. ['Technical Writer', 'UX Writer']).
        location: Target location (e.g. 'New York, NY').
        resume_path: Absolute or relative path to the candidate's PDF resume.
        remote_only: True to restrict to 100% remote positions.
        include_hybrid: True to include hybrid positions (default True).
        min_salary: Minimum target annual base salary (0 if unconstrained).
        must_have_skills: Optional list of required skill keywords to boost matching.
        platforms: Optional dictionary configuring platforms to sweep (e.g. {'greenhouse': True, 'ashby': True, 'lever': True, 'workable': True, 'aggregators': False}).
        output_filename: Optional custom YAML path (defaults to profiles/{name}_{title}.yaml).
        
    Returns:
        The file path to the saved YAML profile.
    """
    platforms_config = {
        "greenhouse": True,
        "ashby": True,
        "lever": True,
        "workable": True,
        "aggregators": False
    }
    if platforms:
        platforms_config.update(platforms)

    profile_data = {
        "name": name,
        "search": {
            "titles": titles,
            "location": location,
            "remote_only": remote_only,
            "include_hybrid": include_hybrid,
            "min_salary": min_salary
        },
        "resume": {
            "path": resume_path.replace("\\", "/"),
            "must_have_skills": must_have_skills or [],
            "keywords_weight": 1.5
        },
        "platforms": platforms_config,
        "export": {
            "format": "pdf,csv,json",
            "output_dir": "results"
        }
    }

    target_path = output_filename if output_filename else None
    saved_path = save_profile(profile_data, target_path)
    return f"Profile successfully created and saved to {saved_path}"

@mcp.tool()
def run_sweep(profile_path: Optional[str] = None) -> str:
    """
    Executes a 5-stage job sweep pipeline using a specified profile or the default profile.
    
    Args:
        profile_path: Optional path to the profile YAML. If omitted, uses default profile or config.sample.yaml.
        
    Returns:
        JSON string summarizing active roles found, top match details, and generated report paths.
    """
    try:
        results = run_sweep_pipeline(profile_path=profile_path)
        # Summarize to keep response token-efficient
        summary = {
            "status": results.get("status"),
            "discovered_count": results.get("discovered_count"),
            "active_count": results.get("active_count"),
            "top_match": results.get("top_match"),
            "reports": results.get("reports"),
            "top_5_roles": [
                {
                    "title": r.get("title"),
                    "company": r.get("company"),
                    "location": r.get("location"),
                    "match_score": r.get("match_score"),
                    "url": r.get("url")
                }
                for r in results.get("roles", [])[:5]
            ]
        }
        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def get_results(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    limit: int = 10
) -> str:
    """
    Retrieves the latest sweep results and report artifacts.
    
    Args:
        profile_stem: Optional profile identifier to filter results (e.g. 'pedro_writer'). If omitted, retrieves latest.
        results_dir: Results directory (default 'results').
        limit: Number of top scored roles to return in the list (default 10).
        
    Returns:
        JSON string containing the latest sweep report metadata and top scored roles.
    """
    if not os.path.exists(results_dir):
        return json.dumps({"status": "error", "message": f"Directory '{results_dir}' does not exist."})

    pattern = os.path.join(results_dir, f"{profile_stem}_*.json" if profile_stem else "*.json")
    json_files = glob.glob(pattern)

    if not json_files:
        return json.dumps({"status": "error", "message": "No sweep result JSON files found."})

    # Pick the most recently modified JSON file
    latest_json = max(json_files, key=os.path.getmtime)
    
    try:
        with open(latest_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        roles = data if isinstance(data, list) else data.get("roles", [])
        base_name = os.path.splitext(latest_json)[0]

        summary = {
            "result_file": latest_json,
            "pdf_report": f"{base_name}.pdf" if os.path.exists(f"{base_name}.pdf") else None,
            "csv_report": f"{base_name}.csv" if os.path.exists(f"{base_name}.csv") else None,
            "total_roles": len(roles),
            "top_roles": [
                {
                    "title": r.get("title"),
                    "company": r.get("company"),
                    "location": r.get("location"),
                    "match_score": r.get("match_score"),
                    "url": r.get("url"),
                    "playbook": r.get("playbook", "")
                }
                for r in roles[:limit]
            ]
        }
        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to read result file: {e}"})

@mcp.tool()
def export_report(
    json_source: Optional[str] = None,
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    formats: Optional[List[str]] = None,
    candidate_name: str = "Job Seeker",
    output_dir: Optional[str] = None
) -> str:
    """
    Rebuilds report files (PDF, CSV, or JSON) from an existing sweep result without re-running discovery or scoring.
    Use this to regenerate a report in a different format after a sweep has already completed.

    Args:
        json_source: Absolute path to the existing sweep JSON result file. Takes priority over profile_stem.
        profile_stem: Profile identifier used to find the latest matching JSON (e.g. 'pedro_writer').
                      Ignored when json_source is provided.
        results_dir: Directory containing result files (default 'results').
        formats: List of output formats to generate. Options: 'pdf', 'csv', 'json'. Defaults to ['pdf'].
        candidate_name: Name displayed in the PDF report header (default 'Job Seeker').
        output_dir: Directory to save regenerated reports. Defaults to same directory as the source JSON.

    Returns:
        JSON string with the status and absolute paths to all generated report files.
    """
    import datetime

    if not formats:
        formats = ["pdf"]
    formats = [f.lower() for f in formats]

    # Resolve the source JSON
    source_json = None
    if json_source:
        source_json = json_source
    else:
        if not os.path.exists(results_dir):
            return json.dumps({"status": "error", "message": f"Directory '{results_dir}' does not exist."})
        pattern = os.path.join(results_dir, f"{profile_stem}_*.json" if profile_stem else "*.json")
        matches = glob.glob(pattern)
        if not matches:
            return json.dumps({"status": "error", "message": "No JSON result files found matching the criteria."})
        source_json = max(matches, key=os.path.getmtime)

    if not os.path.exists(source_json):
        return json.dumps({"status": "error", "message": f"Source file not found: {source_json}"})

    try:
        with open(source_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        roles = data if isinstance(data, list) else data.get("roles", [])
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to load JSON: {e}"})

    if not roles:
        return json.dumps({"status": "error", "message": "Source JSON contains no roles to export."})

    # Determine output paths
    base_name = os.path.splitext(source_json)[0]
    target_dir = output_dir or os.path.dirname(source_json)
    os.makedirs(target_dir, exist_ok=True)
    stem = os.path.basename(base_name)
    base_out = os.path.join(target_dir, stem)

    generated = {}
    errors = []

    if "pdf" in formats:
        try:
            pdf_path = f"{base_out}.pdf"
            pages = build_pdf(roles, pdf_path, candidate_name)
            generated["pdf"] = os.path.abspath(pdf_path)
            generated["pdf_pages"] = pages
        except Exception as e:
            errors.append(f"PDF: {e}")

    if "csv" in formats:
        try:
            csv_path = f"{base_out}.csv"
            num_rows, num_cols = export_to_csv(roles, csv_path)
            generated["csv"] = os.path.abspath(csv_path)
            generated["csv_rows"] = num_rows
        except Exception as e:
            errors.append(f"CSV: {e}")

    if "json" in formats:
        try:
            json_path = f"{base_out}_export.json"
            export_to_json(roles, json_path)
            generated["json"] = os.path.abspath(json_path)
        except Exception as e:
            errors.append(f"JSON: {e}")

    result = {
        "status": "completed" if generated else "error",
        "source_file": source_json,
        "roles_exported": len(roles),
        "generated": generated,
    }
    if errors:
        result["errors"] = errors

    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()
