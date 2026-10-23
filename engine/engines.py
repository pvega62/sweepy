from __future__ import annotations

import importlib
import importlib.metadata
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
    conflicts: tuple = ()
    conflict_note: str = ""
    conflict_packages: tuple = ()


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
            "Google Jobs",
            "Bayt",
            "Naukri",
            "BDJobs",
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
        notes="Requires company slugs when enabled; reads only the boards you name. No key needed.",
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
        conflicts=("jobspy",),
        conflict_note=(
            "jobdrop pins curl-cffi<0.8, while JobSpy needs curl_cffi>=0.16.2, so pip "
            "refuses to resolve both. The pin is stale: jobdrop runs on the newer "
            "curl_cffi. Installing anyway skips that pin and keeps JobSpy's version."
        ),
        conflict_packages=("curl-cffi",),
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


# Every board Sweepy can search, keyed by the engine that reads it. The wizard's
# platform picker and each engine's own prompt both read this list, so adding a
# board here makes it selectable everywhere.
BOARD_CATALOG: Dict[str, Dict[str, str]] = {
    "jobspy": {
        "linkedin": "LinkedIn",
        "indeed": "Indeed",
        "glassdoor": "Glassdoor",
        "zip_recruiter": "ZipRecruiter",
        "google": "Google Jobs",
        "bayt": "Bayt",
        "naukri": "Naukri",
        "bdjobs": "BDJobs",
    },
    "ats": {
        "greenhouse": "Greenhouse",
        "ashby": "Ashby",
        "lever": "Lever",
        "workable": "Workable",
        "builtinnyc": "Built In NYC",
    },
    "hirehunt": {
        "linkedin": "LinkedIn",
        "indeed": "Indeed",
        "naukri": "Naukri",
        "shine": "Shine",
        "internshala": "Internshala",
        "unstop": "Unstop",
        "google_careers": "Google Careers",
        "amazon": "Amazon",
        "meta": "Meta",
        "apple": "Apple",
        "netflix": "Netflix",
        "microsoft": "Microsoft",
    },
    "openroles": {
        "greenhouse": "Greenhouse",
        "lever": "Lever",
        "ashby": "Ashby",
        "workday": "Workday",
    },
    "jobdrop": {
        "linkedin": "LinkedIn",
        "indeed": "Indeed",
        "glassdoor": "Glassdoor",
        "google": "Google Jobs",
        "zip_recruiter": "ZipRecruiter",
        "hiring_cafe": "Hiring Cafe",
        "wellfound": "Wellfound",
        "collab_work": "CollabWork",
        "trueup": "TrueUp",
        "greenhouse": "Greenhouse",
        "ashby": "Ashby",
        "workday": "Workday",
        "lever": "Lever",
        "remoteok": "RemoteOK",
        "weworkremotely": "We Work Remotely",
        "governmentjobs": "GovernmentJobs",
        "builtin": "Built In",
        "icims": "iCIMS",
        "bayt": "Bayt",
        "naukri": "Naukri",
        "usajobs": "USAJobs",
        "adzuna": "Adzuna",
        "jooble": "Jooble",
        "findwork": "Findwork",
        "the_muse": "The Muse",
        "insight_global": "Insight Global",
        "clearance_jobs": "ClearanceJobs",
        "kforce": "Kforce",
        "snagajob": "Snagajob",
        "dice": "Dice",
        "idealist": "Idealist",
        "careerbuilder": "CareerBuilder",
        "handshake": "Handshake",
    },
    "apify": {
        "actor": "LinkedIn via Apify actor",
    },
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
                "conflict": info.conflict_note if _conflicts_present(info) else "",
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
        suffix = "  (conflicts with JobSpy)" if row["conflict"] else ""
        lines.append(
            f"  {mark} {row['name']:<{width}}{origin:<10}{row['blurb']}{suffix}"
        )
    return "\n".join(lines)


def board_summary(engine: str) -> str:
    """Return 'engine · note' text used to group the platform picker."""
    info = ENGINE_CATALOG[engine]
    parts = []
    if info.core:
        parts.append("built in")
    else:
        parts.append("installed" if engine_status(engine)["installed"] else "needs download")
    if info.needs:
        parts.append("needs " + ", ".join(info.needs))
    if info.conflicts:
        parts.append("conflicts with JobSpy")
    return " · ".join(parts)


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


def _conflicts_present(info: EngineInfo) -> bool:
    """Report whether anything this engine clashes with already sits in the environment."""
    return any(engine_status(other)["installed"] for other in info.conflicts)


def conflict_warnings(names: Optional[Sequence[str]]) -> List[str]:
    """Explain each requested engine that cannot share an environment with an installed one."""
    warnings: List[str] = []
    for name in names or []:
        info = ENGINE_CATALOG.get(str(name).strip().lower())
        if info is None or not _conflicts_present(info):
            continue
        blockers = [other for other in info.conflicts if engine_status(other)["installed"]]
        warnings.append(f"{info.name} conflicts with {', '.join(blockers)}: {info.conflict_note}")
    return warnings


def missing_engines(include_conflicting: bool = False) -> List[str]:
    """Name the engines without a library, minus the ones pip cannot resolve."""
    missing = [name for name in ENGINE_CATALOG if not engine_status(name)["installed"]]
    if include_conflicting:
        return missing
    return [name for name in missing if not _conflicts_present(ENGINE_CATALOG[name])]


def _expand(names: Optional[Sequence[str]]) -> List[str]:
    """Resolve names, expanding "all" to the engines pip can actually install together."""
    if not names:
        return []
    requested: List[str] = []
    for name in names:
        key = str(name).strip().lower()
        if key in ("all", "all-engines"):
            requested.extend(
                name
                for name in ENGINE_CATALOG
                if not ENGINE_CATALOG[name].core and not _conflicts_present(ENGINE_CATALOG[name])
            )
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


def _run_pip(
    args: List[str],
    run: Callable[[List[str]], subprocess.CompletedProcess],
    echo: Callable[[str], None],
) -> subprocess.CompletedProcess:
    """Run pip, retrying once for the current user when permissions block it."""
    completed = run(args)
    output = f"{completed.stdout or ''}\n{completed.stderr or ''}".lower()
    if completed.returncode != 0 and any(
        marker in output for marker in ("permission denied", "access is denied", "errno 13")
    ):
        echo("The install needs elevated permissions; retrying for the current user.")
        completed = run(["--user", *args])
    return completed


def _dependencies_without(name: str, conflict_packages: Sequence[str]) -> List[str]:
    """List an engine's requirements, minus the packages whose pins start the fight.

    A stale upper bound in a package's metadata blocks pip even when the installed
    version works. Installing the package with ``--no-deps`` and then resolving the
    rest of its requirements keeps the conflicting pin out of the command entirely.
    """
    try:
        requirements = list(importlib.metadata.requires(name) or [])
    except importlib.metadata.PackageNotFoundError:
        return []

    blocked = {package.lower().replace("_", "-") for package in conflict_packages}
    keep: List[str] = []
    for requirement in requirements:
        marker = requirement.split(";", 1)[1] if ";" in requirement else ""
        if "extra ==" in marker:
            continue
        package = requirement.split(";")[0].split("[")[0].split("(")[0].strip()
        for separator in (" ", "<", ">", "=", "!", "~"):
            package = package.split(separator)[0]
        if package.strip().lower().replace("_", "-") in blocked:
            continue
        keep.append(requirement.split(";")[0].strip())
    return keep


def install_engines(
    names: Optional[Sequence[str]],
    *,
    echo: Optional[Callable[[str], None]] = None,
    runner: Optional[Callable[[List[str]], subprocess.CompletedProcess]] = None,
    allow_conflicts: bool = False,
) -> Dict[str, dict]:
    """Install the requested optional engines into the running interpreter.

    ``runner`` exists for tests. Nothing runs unless a caller asks for it, and a
    failure reports pip's tail plus the exact command a user can retry. An engine
    that pip cannot resolve alongside an installed one is refused unless
    ``allow_conflicts`` is set, because pip would otherwise fail the whole install.
    """
    echo = echo or (lambda message: None)
    targets = _expand(names)
    results: Dict[str, dict] = {}

    to_install = [name for name in targets if not engine_status(name)["installed"]]

    if not allow_conflicts:
        for name in list(to_install):
            warnings = conflict_warnings([name])
            if not warnings:
                continue
            to_install.remove(name)
            results[name] = {
                "installed": False,
                "blocked": True,
                "detail": warnings[0],
                "command": install_command([name]),
            }

    for name in targets:
        if name not in to_install:
            if name in results:
                continue
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
    conflicted = [name for name in to_install if conflict_warnings([name])]
    plain = [name for name in to_install if name not in conflicted]

    plain_specs = install_specs(plain)
    output = ""
    if plain_specs:
        echo(f"Installing: {', '.join(plain_specs)}")
        try:
            completed = _run_pip(plain_specs, run, echo)
            output = f"{completed.stdout or ''}\n{completed.stderr or ''}".strip()
        except FileNotFoundError:
            for name in plain:
                results[name] = {
                    "installed": False,
                    "detail": "pip was not found for the running interpreter",
                    "command": install_command([name]),
                }

    for name in conflicted:
        info = ENGINE_CATALOG[name]
        spec = info.spec or info.name
        echo(f"Installing {name} without its stale pin:")
        echo(f"  pip install --no-deps {spec}")
        try:
            first = _run_pip(["--no-deps", spec], run, echo)
            if first.returncode != 0:
                output = f"{first.stdout or ''}\n{first.stderr or ''}".strip()
                continue
            importlib.invalidate_caches()
            dependencies = _dependencies_without(name, info.conflict_packages)
            if dependencies:
                echo(f"  pip install {' '.join(dependencies)}")
                second = _run_pip(dependencies, run, echo)
                output = f"{second.stdout or ''}\n{second.stderr or ''}".strip()
        except FileNotFoundError:
            results[name] = {
                "installed": False,
                "detail": "pip was not found for the running interpreter",
                "command": install_command([name]),
            }

    importlib.invalidate_caches()
    tail = output.strip().splitlines()[-1] if output.strip() else "pip reported no output"
    for name in to_install:
        if name in results:
            continue
        status = engine_status(name)
        detail = status["detail"] if status["installed"] else tail
        if status["installed"] and conflict_warnings([name]):
            detail = (
                f"{detail}; installed alongside {', '.join(ENGINE_CATALOG[name].conflicts)} "
                "by skipping its curl-cffi pin, which pip check still reports"
            )
        results[name] = {
            "installed": status["installed"],
            "detail": detail,
            "command": None if status["installed"] else install_command([name]),
        }
    return results
