from __future__ import annotations

import importlib
import importlib.util
import logging
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from engine.adapters import ADAPTERS

log = logging.getLogger("sweepy.engine.engines")


@dataclass(frozen=True)
class EngineInfo:
    name: str
    package: Optional[str]
    module: Optional[str]
    spec: Optional[str]
    core: bool
    blurb: str
    scrapes: tuple = ()
    regions: str = ""
    needs: tuple = ()
    notes: str = ""
    capabilities: dict = field(default_factory=dict)


ENGINE_CATALOG: Dict[str, EngineInfo] = {
    "jobspy": EngineInfo(
        name="jobspy",
        package="python-jobspy",
        module="jobspy",
        spec=None,
        core=True,
        blurb="Fast multi-board search with proxies and User-Agent control",
        scrapes=(
            "LinkedIn",
            "Indeed",
            "Glassdoor",
            "ZipRecruiter",
            "Bayt",
            "Naukri",
            "BDJobs",
            "HelloWork",
        ),
        regions="US, Canada, Europe, India, Middle East",
        notes="Ships with Sweepy. LinkedIn detail pages are optional because they are slow.",
    ),
    "ats": EngineInfo(
        name="ats",
        package=None,
        module=None,
        spec=None,
        core=True,
        blurb="Employer boards read directly, no third-party library",
        scrapes=("Greenhouse", "Ashby", "Lever", "Workable", "Built In NYC"),
        regions="Global",
        notes="Ships with Sweepy. Uses the curated seed lists in data/sources/.",
    ),
    "hirehunt": EngineInfo(
        name="hirehunt",
        package="hirehunt",
        module="hirehunt",
        spec="hirehunt>=0.5,<0.6",
        core=False,
        blurb="India-first boards plus LinkedIn and Indeed through their APIs",
        scrapes=(
            "LinkedIn (guest HTML)",
            "Indeed (GraphQL)",
            "Naukri",
            "Shine",
            "Internshala",
            "Unstop",
            "Google Careers",
            "Amazon",
            "Meta",
            "Apple",
            "Netflix",
            "Microsoft",
        ),
        regions="India and global",
        notes="No proxy hook in the published API, so proxies are ignored with a warning.",
    ),
    "openroles": EngineInfo(
        name="openroles",
        package="openroles",
        module="openroles",
        spec="openroles>=0.1.2,<0.2",
        core=False,
        blurb="Reads public ATS JSON from boards you name",
        scrapes=("Greenhouse", "Lever", "Ashby", "Workday"),
        regions="Global",
        needs=("companies",),
        notes="Requires at least one company slug per ATS. No key needed.",
    ),
    "jobdrop": EngineInfo(
        name="jobdrop",
        package="jobdrop",
        module="jobdrop",
        spec="jobdrop>=2.10,<3",
        core=False,
        blurb="33 boards, including Google and Wellfound, with anti-bot handling",
        scrapes=(
            "LinkedIn",
            "Indeed",
            "Glassdoor",
            "Google",
            "ZipRecruiter",
            "Wellfound",
            "Hiring Cafe",
            "TrueUp",
            "Greenhouse",
            "Ashby",
            "Workday",
            "Lever",
            "iCIMS",
            "Built In",
            "RemoteOK",
            "WeWorkRemotely",
            "USAJobs",
            "GovernmentJobs",
            "Adzuna",
            "Jooble",
            "Findwork",
            "The Muse",
            "Insight Global",
            "ClearanceJobs",
            "Kforce",
            "CollabWork",
            "Naukri",
            "Bayt",
            "Snagajob",
            "Dice",
            "Idealist",
            "CareerBuilder",
            "Handshake",
        ),
        regions="US, Canada, Europe, India, Middle East",
        notes="Slower than JobSpy: Google and Glassdoor drive a browser.",
    ),
    "apify": EngineInfo(
        name="apify",
        package="apify-client",
        module="apify_client",
        spec="apify-client>=3.3,<4",
        core=False,
        blurb="Managed actors that handle proxies and CAPTCHAs for you",
        scrapes=("Actor-dependent; the default actor reads LinkedIn",),
        regions="Global",
        needs=("APIFY_TOKEN",),
        notes="Paid service. Set APIFY_TOKEN before enabling.",
    ),
}


def _capabilities(name: str) -> dict:
    adapter = ADAPTERS.get(name)
    if adapter is None:
        return {}
    return {
        "proxies": adapter.supports_proxies,
        "user_agent": adapter.supports_user_agent,
        "descriptions": adapter.supports_description_toggle,
    }


def catalog_names() -> List[str]:
    return list(ENGINE_CATALOG)


def engine_status(name: str) -> dict:
    """Report whether an engine's library imports, without importing it."""
    info = ENGINE_CATALOG.get(name)
    if info is None:
        return {
            "name": name,
            "installed": False,
            "core": False,
            "package": None,
            "detail": f"Unknown job engine: {name}",
        }
    if info.module is None:
        return {
            "name": name,
            "installed": True,
            "core": True,
            "package": None,
            "detail": "Built in",
        }
    importlib.invalidate_caches()
    installed = importlib.util.find_spec(info.module) is not None
    detail = (
        f"{info.package} installed"
        if installed
        else f"Run: {install_command([name])}"
    )
    return {
        "name": name,
        "installed": installed,
        "core": info.core,
        "package": info.package,
        "detail": detail,
    }


def status_rows() -> List[dict]:
    rows = []
    for name, info in ENGINE_CATALOG.items():
        status = engine_status(name)
        rows.append(
            {
                "name": name,
                "installed": status["installed"],
                "core": info.core,
                "package": info.package or "-",
                "blurb": info.blurb,
                "capabilities": _capabilities(name),
                "needs": list(info.needs),
            }
        )
    return rows


def status_table() -> str:
    rows = status_rows()
    width = max(len(row["name"]) for row in rows) + 2
    lines = []
    for row in rows:
        mark = "[x]" if row["installed"] else "[ ]"
        origin = "core" if row["core"] else "download"
        lines.append(f"  {mark} {row['name']:<{width}}{origin:<10}{row['blurb']}")
    return "\n".join(lines)


def scrapes_table(width: int = 74) -> str:
    """List every engine with the boards it reads, wrapped to the terminal width."""
    lines: List[str] = []
    for name, info in ENGINE_CATALOG.items():
        boards = ", ".join(info.scrapes)
        lines.extend(
            textwrap.wrap(
                f"{name}: {boards}",
                width=width,
                initial_indent="  ",
                subsequent_indent="    ",
            )
        )
    return "\n".join(lines)


def installed_engines(include_core: bool = True) -> List[str]:
    return [
        name
        for name in ENGINE_CATALOG
        if engine_status(name)["installed"] and (include_core or not ENGINE_CATALOG[name].core)
    ]


def missing_engines() -> List[str]:
    return [name for name in ENGINE_CATALOG if not engine_status(name)["installed"]]


def _expand(names: Optional[Sequence[str]]) -> List[str]:
    if not names:
        return []
    requested: List[str] = []
    for name in names:
        key = str(name).strip().lower()
        if key in ("all", "all-engines"):
            requested.extend(name for name in ENGINE_CATALOG if not ENGINE_CATALOG[name].core)
        elif key:
            requested.append(key)
    unique: List[str] = []
    for name in requested:
        if name not in ENGINE_CATALOG:
            raise ValueError(f"Unknown job engine: {name}")
        if name not in unique:
            unique.append(name)
    return unique


def install_specs(names: Optional[Sequence[str]]) -> List[str]:
    specs = []
    for name in _expand(names):
        info = ENGINE_CATALOG[name]
        if info.spec:
            specs.append(info.spec)
    return specs


def install_command(names: Optional[Sequence[str]]) -> str:
    specs = install_specs(names)
    if not specs:
        return "No download needed: every requested engine ships with Sweepy."
    return f'"{sys.executable}" -m pip install ' + " ".join(f'"{spec}"' for spec in specs)


def _pip(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pip", "install", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def install_engines(
    names: Optional[Sequence[str]],
    *,
    echo: Optional[Callable[[str], None]] = None,
    runner: Optional[Callable[[List[str]], subprocess.CompletedProcess]] = None,
) -> Dict[str, dict]:
    """Install the requested optional engines into the running interpreter.

    ``runner`` exists for tests. Nothing runs unless a caller asks for it, and a
    failure reports pip's tail plus the exact command a user can retry.
    """
    echo = echo or (lambda message: None)
    targets = _expand(names)
    results: Dict[str, dict] = {}

    to_install = [name for name in targets if not engine_status(name)["installed"]]
    for name in targets:
        if name not in to_install:
            results[name] = {
                "installed": True,
                "detail": "Already installed" if engine_status(name)["installed"] else "Built in",
            }
    if not to_install:
        return results

    specs = install_specs(to_install)
    if not specs:
        for name in to_install:
            results[name] = {"installed": True, "detail": "Built in"}
        return results

    run = runner or _pip
    echo(f"Installing: {', '.join(specs)}")
    try:
        completed = run(specs)
    except FileNotFoundError:
        for name in to_install:
            results[name] = {
                "installed": False,
                "detail": "pip was not found for the running interpreter",
                "command": install_command(to_install),
            }
        return results

    output = f"{completed.stdout or ''}\n{completed.stderr or ''}".strip()
    if completed.returncode != 0 and any(
        marker in output.lower()
        for marker in ("permission denied", "access is denied", "errno 13")
    ):
        echo("The install needs elevated permissions; retrying for the current user.")
        try:
            completed = run(["--user", *specs])
            output = f"{completed.stdout or ''}\n{completed.stderr or ''}".strip()
        except FileNotFoundError:
            pass

    importlib.invalidate_caches()
    tail = output.strip().splitlines()[-1] if output.strip() else "pip reported no output"
    for name in to_install:
        status = engine_status(name)
        results[name] = {
            "installed": status["installed"],
            "detail": status["detail"] if status["installed"] else tail,
            "command": None if status["installed"] else install_command([name]),
        }
    return results
