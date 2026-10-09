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

if __name__ == "__main__":
    mcp.run()
