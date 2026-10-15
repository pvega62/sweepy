from __future__ import annotations

import logging
import os
import re
from typing import Callable, Optional

import questionary
import yaml

log = logging.getLogger("sweepy.engine.config")

try:
    from reportlab.lib.colors import getAllNamedColors as _named_colors

    _COLOR_NAMES = set(_named_colors())
except Exception:  # pragma: no cover - reportlab is a core dependency
    _COLOR_NAMES = {
        "black", "white", "red", "green", "blue", "navy", "gray", "grey",
        "purple", "orange", "yellow", "teal", "maroon", "olive", "silver",
        "aqua", "fuchsia", "lime", "brown", "cyan", "magenta", "gold",
    }

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


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


def is_valid_color(value: str) -> bool:
    """Return True when ``value`` is a #RGB/#RRGGBB hex code or a known color name."""
    v = (value or "").strip()
    if not v:
        return False
    if _HEX_COLOR_RE.match(v):
        return True
    return v.lower() in _COLOR_NAMES


def _ask_color(track_name: str) -> str:
    while True:
        value = (
            questionary.text(
                f"Track color (hex code or color name, e.g. #1D4ED8 or navy) for {track_name}:"
            ).ask()
            or "#1D4ED8"
        ).strip()
        if is_valid_color(value):
            return value
        log.warning(
            "Invalid color %r. Enter a valid hex code (#RGB or #RRGGBB) or a color name.",
            value,
        )


class _Step:
    """One wizard question: a stable key, a human label, and the ask callable."""

    def __init__(self, key: str, label: str, ask: Callable):
        self.key = key
        self.label = label
        self.ask = ask


def _ask_name():
    return questionary.text("What is your name?").ask()


def _ask_titles():
    raw = questionary.text(
        "What job titles are you looking for?\n  (Separate multiple titles with a comma)"
    ).ask()
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def _ask_location():
    return questionary.text("Where do you want to work? (City, State):").ask()


def _ask_remote_only():
    return questionary.confirm("Do you want to see remote-only roles?").ask()


def _ask_include_hybrid():
    return questionary.confirm("Do you want to include hybrid roles?").ask()


def _ask_resume_path():
    return questionary.text("What is the path to your resume PDF?").ask()


def _ask_min_salary():
    while True:
        raw = questionary.text("What is your minimum target salary? (Leave blank to skip):").ask()
        parsed = _parse_salary(raw or "")
        if parsed is not None:
            return parsed
        log.warning("Could not parse salary %r. Enter a number like 65000, 65,000, or 65k.", raw)


def _ask_platforms():
    return questionary.checkbox(
        "Which platforms do you want to search?",
        choices=[
            questionary.Choice("Greenhouse", value="greenhouse", checked=True),
            questionary.Choice("Ashby", value="ashby", checked=True),
            questionary.Choice("Lever", value="lever", checked=True),
            questionary.Choice("Workable", value="workable", checked=True),
            questionary.Choice("Aggregator feeds (Remotive, Adzuna)", value="aggregators", checked=False),
        ],
    ).ask() or ["greenhouse", "ashby", "lever", "workable"]


def _ask_custom_platforms():
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
                        "enabled": True,
                    })
    return custom_platforms


def _ask_skills():
    raw = questionary.text(
        "Enter must-have skills or keywords to prioritize (comma-separated, leave blank to extract from resume):"
    ).ask()
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def _ask_formats():
    return questionary.checkbox(
        "What export formats do you want?",
        choices=[
            questionary.Choice("PDF Report", value="pdf", checked=True),
            questionary.Choice("CSV Spreadsheet", value="csv", checked=True),
            questionary.Choice("JSON Data", value="json"),
        ],
    ).ask() or ["pdf", "csv"]


def _ask_tracks():
    tracks = []
    add_tracks = questionary.confirm(
        "Do you want to configure multiple resume tracks (e.g. Tech Writer vs UX Writer)?"
    ).ask()
    if add_tracks:
        while True:
            track_name = questionary.text("Track name (leave blank to finish):").ask()
            if not track_name or not track_name.strip():
                break
            track_color = _ask_color(track_name.strip())
            keywords_str = questionary.text(
                f"Routing keywords for {track_name.strip()} (comma-separated):"
            ).ask()
            tracks.append({
                "name": track_name.strip(),
                "color": track_color,
                "route_keywords": [k.strip() for k in (keywords_str or "").split(",") if k.strip()],
            })
    return tracks


def _ask_debug():
    return questionary.confirm(
        "Enable debug logging? (Logs are saved under logs/ in the application directory):"
    ).ask()


def _build_steps():
    return [
        _Step("name", "Your name", _ask_name),
        _Step("titles", "Job titles", _ask_titles),
        _Step("location", "Location", _ask_location),
        _Step("remote_only", "Remote-only roles", _ask_remote_only),
        _Step("include_hybrid", "Hybrid roles", _ask_include_hybrid),
        _Step("resume_path", "Resume path", _ask_resume_path),
        _Step("min_salary", "Minimum salary", _ask_min_salary),
        _Step("platforms", "Platforms", _ask_platforms),
        _Step("custom_platforms", "Custom platforms", _ask_custom_platforms),
        _Step("must_have_skills", "Must-have skills", _ask_skills),
        _Step("formats", "Export formats", _ask_formats),
        _Step("tracks", "Resume tracks", _ask_tracks),
        _Step("debug", "Debug logging", _ask_debug),
    ]


def _collect(steps):
    answers = {}
    for step in steps:
        answers[step.key] = step.ask()
    return answers


def _format_answer(step, value):
    if step.key == "platforms":
        return ", ".join(value) if value else "(none)"
    if step.key == "custom_platforms":
        return ", ".join(c["name"] for c in value) if value else "(none)"
    if step.key == "tracks":
        return ", ".join(t["name"] for t in value) if value else "(none)"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value in (None, ""):
        return "(blank)"
    return str(value)


def _print_summary(answers, steps):
    log.info("──────────────────────────────────────────────────")
    log.info("Review your answers before submitting:")
    for step in steps:
        log.info("  %s: %s", step.label, _format_answer(step, answers.get(step.key)))
    log.info("──────────────────────────────────────────────────")


def _build_profile(answers):
    custom_platforms = answers.get("custom_platforms") or []
    platforms_dict = {
        "greenhouse": "greenhouse" in answers["platforms"],
        "ashby": "ashby" in answers["platforms"],
        "lever": "lever" in answers["platforms"],
        "workable": "workable" in answers["platforms"],
        "aggregators": "aggregators" in answers["platforms"],
    }
    if custom_platforms:
        platforms_dict["custom"] = custom_platforms

    resume_path = (answers.get("resume_path") or "").strip().strip('"').replace("\\", "/")
    titles = answers.get("titles") or []
    profile_data = {
        "name": answers.get("name") or "Job Seeker",
        "search": {
            "titles": titles or ["Paralegal"],
            "location": answers.get("location") or "New York, NY",
            "remote_only": bool(answers.get("remote_only")),
            "include_hybrid": bool(answers.get("include_hybrid")),
            "min_salary": answers.get("min_salary", 0),
        },
        "resume": {
            "path": resume_path,
            "must_have_skills": answers.get("must_have_skills") or [],
            "keywords_weight": 1.5,
        },
        "platforms": platforms_dict,
        "export": {
            "format": ",".join(answers.get("formats") or ["pdf", "csv"]),
            "output_dir": "results",
        },
        "debug": bool(answers.get("debug")),
    }

    tracks = answers.get("tracks") or []
    if tracks:
        profile_data["resume"]["tracks"] = tracks

    return profile_data


def _profile_path(profile_data):
    titles = profile_data["search"]["titles"]
    first_title_slug = re.sub(r'[^a-zA-Z0-9]+', '_', (titles[0] if titles else "custom")).strip('_').lower()
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', profile_data["name"]).strip('_').lower()
    return f"profiles/{safe_name}_{first_title_slug}.yaml"


def run_wizard():
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║            Sweepy — Profile Setup Wizard         ║")
    log.info("╚══════════════════════════════════════════════════╝")

    steps = _build_steps()
    answers = _collect(steps)

    while True:
        _print_summary(answers, steps)
        action = questionary.select(
            "What would you like to do?",
            choices=["Submit profile", "Edit an answer", "Start over"],
        ).ask()
        if action == "Submit profile":
            break
        if action == "Start over":
            answers = _collect(steps)
            continue

        label = questionary.select(
            "Which answer do you want to edit?",
            choices=[step.label for step in steps],
        ).ask()
        step = next(s for s in steps if s.label == label)
        answers[step.key] = step.ask()

    profile_data = _build_profile(answers)
    return save_profile(profile_data, _profile_path(profile_data))


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
