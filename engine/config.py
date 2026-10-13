from __future__ import annotations

import logging
import os
import re
from typing import Optional

import questionary
import yaml

log = logging.getLogger("sweepy.engine.config")


def _parse_salary(text: str) -> Optional[int]:
    """Parse a salary string like '65000', '65,000', '$65,000', or '65k'. Returns None on failure."""
    s = text.strip().lower().replace("$", "").replace(",", "")
    if not s:
        return 0
    multiplier = 1
    if s.endswith("k"):
        s = s[:-1].strip()
        multiplier = 1000
    try:
        value = int(float(s) * multiplier)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def run_wizard():
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║            Sweepy — Profile Setup Wizard         ║")
    log.info("╚══════════════════════════════════════════════════╝")

    name = questionary.text("What is your name?").ask()

    titles_str = questionary.text(
        "What job titles are you looking for?\n  (Separate multiple titles with a comma)"
    ).ask()
    titles = [t.strip() for t in titles_str.split(",") if t.strip()]

    location = questionary.text("Where do you want to work? (City, State):").ask()

    remote_only = questionary.confirm("Do you want to see remote-only roles?").ask()
    include_hybrid = questionary.confirm("Do you want to include hybrid roles?").ask()

    resume_path = questionary.text("What is the path to your resume PDF?").ask()

    min_salary = 0
    while True:
        min_salary_str = questionary.text("What is your minimum target salary? (Leave blank to skip):").ask()
        parsed = _parse_salary(min_salary_str or "")
        if parsed is not None:
            min_salary = parsed
            break
        log.warning("Could not parse salary %r. Enter a number like 65000, 65,000, or 65k.", min_salary_str)

    platform_choices = questionary.checkbox(
        "Which platforms do you want to search?",
        choices=[
            questionary.Choice("Greenhouse", value="greenhouse", checked=True),
            questionary.Choice("Ashby", value="ashby", checked=True),
            questionary.Choice("Lever", value="lever", checked=True),
            questionary.Choice("Workable", value="workable", checked=True),
            questionary.Choice("Aggregator feeds (Remotive, Adzuna)", value="aggregators", checked=False),
        ]
    ).ask() or ["greenhouse", "ashby", "lever", "workable"]

    add_custom = questionary.confirm("Do you want to add custom platforms or ATS domains?").ask()
    custom_platforms = []
    if add_custom:
        custom_input = questionary.text(
            "Enter custom platform names and domains (format: Name:domain.com, comma-separated):\n  e.g. SmartRecruiters:smartrecruiters.com, Breezy HR:breezy.hr"
        ).ask()
        if custom_input:
            for item in custom_input.split(","):
                item = item.strip()
                if ":" in item:
                    c_name, c_domain = item.split(":", 1)
                    custom_platforms.append({
                        "name": c_name.strip(),
                        "domain": c_domain.strip().lower(),
                        "enabled": True
                    })

    skills_str = questionary.text(
        "Enter must-have skills or keywords to prioritize (comma-separated, leave blank to extract from resume):"
    ).ask()
    must_have_skills = [s.strip() for s in skills_str.split(",") if s.strip()]

    formats = questionary.checkbox(
        "What export formats do you want?",
        choices=[
            questionary.Choice("PDF Report", value="pdf", checked=True),
            questionary.Choice("CSV Spreadsheet", value="csv", checked=True),
            questionary.Choice("JSON Data", value="json")
        ]
    ).ask() or ["pdf", "csv"]

    tracks = []
    add_tracks = questionary.confirm(
        "Do you want to configure multiple resume tracks (e.g. Tech Writer vs UX Writer)?"
    ).ask()
    if add_tracks:
        while True:
            track_name = questionary.text("Track name (leave blank to finish):").ask()
            if not track_name or not track_name.strip():
                break
            track_color = questionary.text(
                f"Track color (hex, e.g. #1D4ED8) for {track_name.strip()}:"
            ).ask() or "#1D4ED8"
            keywords_str = questionary.text(
                f"Routing keywords for {track_name.strip()} (comma-separated):"
            ).ask()
            tracks.append({
                "name": track_name.strip(),
                "color": track_color.strip() or "#1D4ED8",
                "route_keywords": [k.strip() for k in (keywords_str or "").split(",") if k.strip()],
            })

    platforms_dict = {
        "greenhouse": "greenhouse" in platform_choices,
        "ashby": "ashby" in platform_choices,
        "lever": "lever" in platform_choices,
        "workable": "workable" in platform_choices,
        "aggregators": "aggregators" in platform_choices,
    }
    if custom_platforms:
        platforms_dict["custom"] = custom_platforms

    profile_data = {
        "name": name or "Job Seeker",
        "search": {
            "titles": titles or ["Paralegal"],
            "location": location or "New York, NY",
            "remote_only": bool(remote_only),
            "include_hybrid": bool(include_hybrid),
            "min_salary": min_salary
        },
        "resume": {
            "path": resume_path.strip().strip('"').replace("\\", "/"),
            "must_have_skills": must_have_skills,
            "keywords_weight": 1.5
        },
        "platforms": platforms_dict,
        "export": {
            "format": ",".join(formats),
            "output_dir": "results"
        }
    }

    if tracks:
        profile_data["resume"]["tracks"] = tracks

    first_title_slug = re.sub(r'[^a-zA-Z0-9]+', '_', (titles[0] if titles else "custom")).strip('_').lower()
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', (name or "user")).strip('_').lower()
    file_path = f"profiles/{safe_name}_{first_title_slug}.yaml"

    return save_profile(profile_data, file_path)


def save_profile(profile_data: dict, file_path: Optional[str] = None) -> str:
    """Saves a profile configuration dict to YAML."""
    if not file_path:
        name = profile_data.get("name", "user")
        titles = profile_data.get("search", {}).get("titles", ["custom"])
        first_title = titles[0] if titles else "custom"
        safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
        safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', first_title).strip('_').lower()
        file_path = f"profiles/{safe_name}_{safe_title}.yaml"

    os.makedirs(os.path.dirname(file_path) or "profiles", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, sort_keys=False, default_flow_style=False)

    log.info("Profile saved to: %s", file_path)
    return file_path


def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
