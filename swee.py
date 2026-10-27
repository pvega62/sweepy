from __future__ import annotations

import argparse
import copy
import datetime
import logging
import os
import re
import shutil
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from typing import Callable, Optional

from engine.config import (
    DOCS_URL,
    last_profile_path,
    load_config,
    record_last_profile,
    run_wizard,
    save_profile,
)
from engine.discovery import (
    build_cache,
    build_circuit,
    dedupe_jobs,
    discover_engines,
    discover_jobs,
    discover_sources,
)
from engine.documents import convert_to_pdf
from engine.docx import convert_docx_to_pdf
from engine.engines import install_engines, status_table
from engine.enrich import enrich_jobs, get_tracks
from engine.exporter import export_to_csv, export_to_json, export_to_png
from engine.history import SweepHistory, build_history, history_scope
from engine.logging import enable_debug_logging, recent_log_lines
from engine.pdf_builder import build_pdf
from engine.portfolio import PORTFOLIO_SUFFIXES, looks_like_url, normalize_portfolio
from engine.report import build_report
from engine.scorer import normalize_synonyms, score_jobs, score_jobs_by_track
from engine.sweep_config import normalize_sources, validate_sources
from engine.tracking import carried_count, load_previous, tracking_enabled
from engine.updater import check_for_updates, update_sweepy
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

_DEFAULT_PROFILE_CANDIDATES = (
    "profiles/custom_profile.yaml",
    "profiles/paralegal_nyc.yaml",
    "config.sample.yaml",
)


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


def _split_list(value: Optional[str]) -> list:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _portfolio_sources(
    values, track_names, default_track: str = ""
) -> list:
    """Turn ``--portfolio`` values into portfolio entries.

    A value may carry a ``TRACK=`` prefix that names the resume track it serves.
    Values without a prefix use ``--portfolio-track``, then fall back to every track.
    """
    entries = []
    track_lookup = {name.lower(): name for name in track_names if name}
    if default_track and default_track.lower() not in track_lookup:
        raise ValueError(
            f"--portfolio-track {default_track!r} matches no resume track "
            + (
                f"({', '.join(track_names)})"
                if track_names
                else "(this profile defines none)"
            )
        )
    for raw in values:
        text = str(raw or "").strip().strip('"')
        if not text:
            continue
        track = ""
        for name in track_lookup.values():
            prefix = f"{name}="
            if text.lower().startswith(prefix.lower()):
                track, text = name, text[len(prefix):].strip().strip('"')
                break
        if not text:
            raise ValueError(f"--portfolio {raw!r} names no URL or file")
        if "=" in text and not looks_like_url(text) and not os.path.exists(text):
            prefix = text.partition("=")[0]
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]*", prefix or ""):
                valid = ", ".join(track_lookup.values()) or "(none)"
                raise ValueError(
                    f"--portfolio {raw!r} names track {prefix!r}, which this profile does "
                    f"not define. Valid tracks: {valid}"
                )

        if looks_like_url(text):
            entry = {"url": text}
        else:
            resolved = os.path.abspath(os.path.expanduser(text))
            if not os.path.exists(resolved):
                raise ValueError(f"--portfolio file not found: {text!r}")
            if os.path.splitext(resolved)[1].lower() not in PORTFOLIO_SUFFIXES:
                raise ValueError(
                    f"--portfolio must be a URL or one of: {', '.join(PORTFOLIO_SUFFIXES)}"
                )
            entry = {"path": resolved}

        if track or default_track:
            entry["track"] = track or default_track
        entries.append(entry)
    return entries


def _setup_headless(args) -> None:
    """Build or update a profile from flags without opening the wizard."""
    base: dict = {}
    if args.profile and os.path.exists(args.profile):
        base = load_config(args.profile)

    search = dict(base.get("search") or {})
    resume = dict(base.get("resume") or {})

    name = args.name or base.get("name")
    titles = _split_list(args.titles) or list(search.get("titles") or [])
    location = args.location or search.get("location")
    resume_path = args.resume or resume.get("path")

    missing = [
        label
        for label, value in (
            ("--name", name),
            ("--titles", titles),
            ("--location", location),
            ("--resume", resume_path),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            "Non-interactive setup needs " + ", ".join(missing) + " (or an existing --profile)"
        )

    profile = copy.deepcopy(base)
    profile["name"] = name
    search.update({"titles": titles, "location": location})
    profile["search"] = search
    resume["path"] = resume_path
    profile["resume"] = resume

    sources = dict(profile.get("sources") or {})
    if args.sources:
        sources["enabled"] = _split_list(args.sources)
    if args.jobspy_sites:
        sources["jobspy"] = {**(sources.get("jobspy") or {}), "sites": _split_list(args.jobspy_sites)}
    if args.hirehunt_sources:
        sources["hirehunt"] = {
            **(sources.get("hirehunt") or {}),
            "sources": _split_list(args.hirehunt_sources),
        }
    if args.jobdrop_sites:
        sources["jobdrop"] = {**(sources.get("jobdrop") or {}), "sites": _split_list(args.jobdrop_sites)}
    if args.openroles_companies:
        sources["openroles"] = {
            **(sources.get("openroles") or {}),
            "companies": _split_list(args.openroles_companies),
        }
    if args.apify_actor:
        sources["apify"] = {**(sources.get("apify") or {}), "actor": args.apify_actor}
    if sources:
        profile["sources"] = sources

    if args.timeout or args.cache_ttl is not None or args.no_cache:
        orchestrator = dict(profile.get("orchestrator") or {})
        cache = dict(profile.get("cache") or {})
        if args.timeout:
            orchestrator["timeout_per_source_seconds"] = args.timeout
        if args.cache_ttl is not None:
            cache["ttl_seconds"] = args.cache_ttl
        if args.no_cache:
            cache["enabled"] = False
        profile["orchestrator"] = orchestrator
        profile["cache"] = cache

    history_days = getattr(args, "history_days", None)
    no_history = getattr(args, "no_history", False)
    if history_days is not None or no_history:
        history = dict(profile.get("history") or {})
        if history_days is not None:
            history["retention_days"] = max(0, history_days)
        if no_history:
            history["enabled"] = False
        profile["history"] = history

    job_tracking = getattr(args, "job_tracking", None)
    if job_tracking is not None:
        export = dict(profile.get("export") or {})
        export.setdefault("format", "pdf,csv")
        export.setdefault("output_dir", "results")
        export["tracking"] = job_tracking
        profile["export"] = export

    portfolio_values = getattr(args, "portfolio", None) or []
    if portfolio_values:
        track_names = [
            str(track.get("name") or "")
            for track in (profile.get("resume") or {}).get("tracks") or []
            if str(track.get("name") or "").strip()
        ]
        sources = _portfolio_sources(
            portfolio_values,
            track_names,
            str(getattr(args, "portfolio_track", "") or "").strip(),
        )
        block = normalize_portfolio({"sources": sources}, track_names)
        profile["portfolio"] = block
        print(f"Portfolio: {len(block['sources'])} source(s)")

    runtime = normalize_sources(profile)
    errors = validate_sources(
        {engine: runtime["engines"][engine] for engine in runtime["enabled"]},
        check_installed=True,
    )
    if errors:
        raise ValueError("; ".join(errors))

    target = args.profile if args.profile else None
    save_profile(profile, target)
    print(f"Engines: {', '.join(runtime['enabled']) or '(none)'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweepy - Automated Job Board Aggregator")
    parser.add_argument("--run", action="store_true", help="Run a sweep with the last saved profile")
    parser.add_argument("--version", action="store_true", help="Show engine version and dependencies")
    parser.add_argument("--setup", action="store_true", help="Run the interactive configuration wizard")
    parser.add_argument("--profile", type=str, help="Path to the YAML profile configuration to use")
    parser.add_argument("--docx", type=str, metavar="PATH", help="Convert a DOCX file to PDF and exit")
    parser.add_argument(
        "--convert",
        type=str,
        metavar="PATH",
        help="Convert a document to PDF beside the original file and exit",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging (saved under logs/)")
    parser.add_argument("--log-dir", type=str, metavar="DIR", help="Directory for debug logs (default: logs/)")
    parser.add_argument("--logs", action="store_true", help="Show the most recent debug log entries")
    parser.add_argument("--update", action="store_true", help="Pull the latest Sweepy code and reinstall dependencies")
    parser.add_argument("--check-update", action="store_true", help="Report whether a newer Sweepy version exists")
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="Show every job engine, what it scrapes, and whether it is installed",
    )
    parser.add_argument(
        "--install-engines",
        nargs="?",
        const="all",
        metavar="NAMES",
        help="Download optional engines: 'all' or a comma-separated list",
    )
    parser.add_argument(
        "--allow-engine-conflicts",
        action="store_true",
        help="Install an engine whose metadata conflicts, skipping the conflicting pin",
    )
    parser.add_argument(
        "--sources",
        metavar="NAMES",
        help="Enable these engines for a headless setup (comma-separated)",
    )
    parser.add_argument("--jobspy-sites", metavar="SITES", help="JobSpy boards for a headless setup")
    parser.add_argument("--hirehunt-sources", metavar="SOURCES", help="HireHunt sources for a headless setup")
    parser.add_argument("--jobdrop-sites", metavar="SITES", help="jobdrop boards for a headless setup")
    parser.add_argument(
        "--openroles-companies",
        metavar="SLUGS",
        help="Company slugs for openroles, comma-separated",
    )
    parser.add_argument("--apify-actor", metavar="ACTOR", help="Apify actor id for a headless setup")
    parser.add_argument("--timeout", type=int, metavar="SECONDS", help="Per-source timeout in seconds")
    parser.add_argument("--cache-ttl", type=int, metavar="SECONDS", help="Cache lifetime in seconds")
    parser.add_argument("--no-cache", action="store_true", help="Disable the discovery cache")
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Keep duplicate postings from separate boards for this sweep",
    )
    parser.add_argument(
        "--include-seen",
        action="store_true",
        help="Report postings seen in an earlier sweep too",
    )
    parser.add_argument(
        "--reset-history",
        action="store_true",
        help="Forget the postings already reported for this profile",
    )
    parser.add_argument(
        "--history-days",
        type=int,
        metavar="DAYS",
        help="Days before a reported posting can appear again (headless setup)",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Report every posting on every run (headless setup)",
    )
    parser.add_argument(
        "--job-tracking",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Add job-tracking columns to the CSV and carry earlier values forward (headless setup)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Build or update a profile from flags without opening the wizard",
    )
    parser.add_argument("--name", help="Candidate name for a headless setup")
    parser.add_argument("--titles", metavar="TITLES", help="Target titles, comma-separated")
    parser.add_argument("--location", help="Target location for a headless setup")
    parser.add_argument("--resume", metavar="PATH", help="Resume path for a headless setup")
    parser.add_argument(
        "--portfolio",
        action="append",
        metavar="VALUE",
        help=(
            "Portfolio URL or local PDF, DOCX, Markdown, text, or HTML file for a headless "
            "setup. Repeat for more sources, and prefix a value with TRACK= to attach it to "
            "one resume track"
        ),
    )
    parser.add_argument(
        "--portfolio-track",
        metavar="TRACK",
        help="Resume track for --portfolio values that carry no TRACK= prefix",
    )

    args = parser.parse_args()

    _configure_logging()
    debug_enabled = args.debug or os.environ.get("SWEEPY_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
    if debug_enabled:
        enable_debug_logging(args.log_dir)

    if args.logs:
        _print_recent_logs(args.log_dir)
        sys.exit(0)

    if args.version:
        print(f"Sweepy v{VERSION}")
        print(get_dependency_versions())
        print("Ready to sweep.")
        sys.exit(0)

    if args.update:
        print(update_sweepy())
        sys.exit(0)

    if args.check_update:
        print(check_for_updates())
        sys.exit(0)

    if args.list_engines:
        print(status_table())
        sys.exit(0)

    if args.install_engines:
        names = _split_list(args.install_engines) or ["all"]
        try:
            results = install_engines(
                names, echo=print, allow_conflicts=args.allow_engine_conflicts
            )
        except ValueError as exc:
            print(f"Error: {exc}")
            sys.exit(1)
        failed = False
        ready = []
        for engine, result in results.items():
            if result.get("installed"):
                ready.append(engine)
                print(f"{engine}: ready")
            elif result.get("blocked"):
                failed = True
                print(f"{engine}: not installed - {result.get('detail')}")
                print("  Override with: sweepy --install-engines "
                      f"{engine} --allow-engine-conflicts")
            else:
                failed = True
                print(f"{engine}: install failed - {result.get('detail')}")
                if result.get("command"):
                    print(f"  Retry with: {result['command']}")
        if ready:
            print("")
            print("Add an engine to a profile:")
            print("  sweepy                                  # Sweepy's Toolbox > Manage job engines")
            print(f"  sweepy --setup --non-interactive --profile FILE --sources {','.join(ready)}")
        sys.exit(1 if failed else 0)

    if args.convert:
        _print_banner()
        _convert_document(args.convert)
        sys.exit(0)

    if args.docx:
        _print_banner()
        _convert_docx(args.docx)
        sys.exit(0)

    if args.setup:
        if args.sources or args.non_interactive:
            try:
                _setup_headless(args)
            except (FileNotFoundError, ValueError) as exc:
                print(f"Error: {exc}")
                sys.exit(1)
        else:
            _open_wizard(args.profile)
        sys.exit(0)

    if args.reset_history and not (args.run or args.profile):
        _print_banner()
        _clear_history(None)
        sys.exit(0)

    if args.run or args.profile:
        _print_banner()
        _run_from_cli(
            args.profile,
            use_last=args.run,
            deduplicate=not args.no_dedupe,
            include_seen=args.include_seen,
            reset_history=args.reset_history,
        )
        sys.exit(0)

    _open_wizard(None)
    sys.exit(0)


def _print_banner() -> None:
    print("================================================================================")
    print(f"Sweepy v{VERSION}")


def _default_profile_path() -> Optional[str]:
    """Return the last saved profile, then the first conventional profile on disk."""
    saved = last_profile_path()
    if saved:
        return saved
    for candidate in _DEFAULT_PROFILE_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return None


def _run_wizard_sweep(profile_data: dict, profile_path: Optional[str]) -> None:
    """Run the pipeline from the menu and keep the menu alive when the sweep fails."""
    try:
        run_sweep_pipeline(
            profile_dict=profile_data,
            profile_path=profile_path,
            execution_method="wizard",
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}")
        return
    if profile_path:
        record_last_profile(profile_path)


def _open_wizard(profile_path: Optional[str]) -> None:
    """Open the wizard's main menu, which can also run a sweep in place."""
    saved_path = run_wizard(profile_path, run_sweep=_run_wizard_sweep)
    if not saved_path:
        return
    print("\nTo run your sweep with this profile, execute:")
    print("  python swee.py --run")
    print(f"  (or: python swee.py --profile {saved_path})")


def _history_for_profile(profile_path: str):
    """Return the history store and scope for a saved profile."""
    config = load_config(profile_path)
    runtime = normalize_sources(config)
    cfg = runtime.get("history") or {}
    store = SweepHistory(
        path=cfg.get("path"),
        retention_days=cfg.get("retention_days", 4),
        match=cfg.get("match", "url+role"),
    )
    scope = history_scope(os.path.splitext(os.path.basename(profile_path))[0])
    return store, scope


def _clear_history(profile_path: Optional[str]) -> None:
    """Delete the remembered postings for one profile."""
    if not profile_path:
        profile_path = _default_profile_path()
    if not profile_path:
        print("Error: no saved profile found. Create one with: python swee.py --setup")
        return
    try:
        store, scope = _history_for_profile(profile_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return
    deleted = store.clear(scope)
    print(f"Cleared {deleted} remembered posting(s) for {scope}.")


def _run_from_cli(
    profile_path: Optional[str],
    *,
    use_last: bool,
    deduplicate: bool = True,
    include_seen: bool = False,
    reset_history: bool = False,
) -> None:
    """Run the sweep pipeline, resolving the last saved profile when ``--run`` is set."""
    if not profile_path and use_last:
        profile_path = _default_profile_path()
        if not profile_path:
            print("Error: no saved profile found. Create one with: python swee.py --setup")
            print(f"Docs: {DOCS_URL}")
            sys.exit(1)
        print(f"Using the last saved profile: {profile_path}")

    if reset_history and profile_path:
        _clear_history(profile_path)

    try:
        run_sweep_pipeline(
            profile_path=profile_path,
            deduplicate=deduplicate,
            include_seen=include_seen,
            execution_method="cli",
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        if not profile_path:
            print("Please run: python swee.py --setup")
        sys.exit(1)

    if profile_path:
        record_last_profile(profile_path)


def _print_recent_logs(log_dir: Optional[str]) -> None:
    lines = recent_log_lines(log_dir, lines=50)
    if not lines:
        print("No debug logs found. Run Sweepy with --debug to enable logging.")
        return
    print("".join(lines), end="")


def _convert_document(source_path: str) -> None:
    """Convert a supported document to PDF beside its source, with no prompts."""
    source = os.path.realpath(os.path.expanduser(source_path.strip().strip('"')))
    try:
        out_path = convert_to_pdf(source)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    if os.path.realpath(out_path) == source:
        print(f"This file is already a PDF: {out_path}")
        return
    print(f"PDF saved: {out_path}")


def _convert_docx(docx_path: str) -> None:
    target = input("Where should the PDF go? (leave blank to save next to the DOCX): ").strip()
    try:
        out_path = convert_docx_to_pdf(docx_path, target or None)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    print(f"PDF saved: {out_path}")


def _project_role(role: dict) -> dict:
    return {
        "title": role.get("title"),
        "company": role.get("company"),
        "location": role.get("location"),
        "match_score": role.get("match_score"),
        "url": role.get("url"),
        "playbook": role.get("playbook", ""),
    }


def _copy_to_destinations(files: list, destinations: list, label: str, log_fn: Callable) -> None:
    for dest in destinations:
        try:
            dest_dir = os.path.expanduser(dest)
            os.makedirs(dest_dir, exist_ok=True)
            for path in files:
                shutil.copyfile(path, os.path.join(dest_dir, os.path.basename(path)))
            log_fn(f"  * {label} copied to: {dest_dir}")
        except Exception as e:
            log_fn(f"  [x] Could not copy {label} to {dest!r}: {e}")


def run_sweep_pipeline(
    profile_path: Optional[str] = None,
    profile_dict: Optional[dict] = None,
    *,
    verbose: bool = True,
    progress: Optional[Callable[[int, int, str], None]] = None,
    include_roles: bool = False,
    deduplicate: bool = True,
    include_seen: bool = False,
    execution_method: str = "direct",
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
        if profile_path:
            # An in-memory edit still belongs to the file it came from, so its
            # history bucket matches a later `sweepy --run` of that profile.
            profile_stem = os.path.splitext(os.path.basename(profile_path))[0]
        else:
            profile_stem = re.sub(
                r'[^a-zA-Z0-9]+', '_', config.get("name", "profile")
            ).strip('_').lower()
    else:
        if not profile_path:
            profile_path = _default_profile_path()
            if not profile_path:
                raise FileNotFoundError("No profile provided and default configuration not found.")
            if profile_path == "config.sample.yaml":
                log_fn("Notice: No profile specified. Using config.sample.yaml by default.")

        config = load_config(profile_path)
        profile_stem = os.path.splitext(os.path.basename(profile_path))[0]

    debug_enabled = os.environ.get("SWEEPY_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
    if config.get("debug") or debug_enabled:
        enable_debug_logging()

    name = config.get("name", "Job Seeker")
    search = config.get("search", {})
    titles = search.get("titles", [])
    location = search.get("location", "")
    remote_only = search.get("remote_only", False)
    include_hybrid = search.get("include_hybrid", True)
    min_salary = search.get("min_salary", 0)
    salary_from_description = bool(search.get("salary_from_description", True))

    resume = config.get("resume", {})
    resume_path = resume.get("path", "")
    must_have_skills = resume.get("must_have_skills", [])
    keywords_weight = resume.get("keywords_weight", 1.0)
    synonyms = normalize_synonyms(resume.get("synonyms"))

    platforms = config.get("platforms", {
        "greenhouse": True,
        "ashby": True,
        "lever": True,
        "workable": True,
        "aggregators": False,
    })

    sources = config.get("sources", {}) or {}
    runtime = normalize_sources(config)
    extra_engines = [e for e in runtime["enabled"] if e not in ("jobspy", "ats")]
    cache = build_cache(runtime)
    circuit = build_circuit(runtime)
    history = build_history(runtime)
    history_scope_key = history_scope(profile_stem)
    skipped_sources: list = []

    report = config.get("report", {}) or {}
    report_style = report.get("style", "cards")
    report_destinations = list(report.get("destinations", []) or [])

    export = config.get("export", {})
    formats = [f.strip().lower() for f in export.get("format", "pdf,csv").split(",") if f.strip()]
    output_dir = export.get("output_dir", "results")
    job_tracking = tracking_enabled(export)

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
    log_fn(f"Execution method: {execution_method}")
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
    log_fn(f"  * Cross-board duplicate checking: {'enabled' if deduplicate else 'disabled'}")
    jobs, platform_counts = discover_jobs(
        titles, location, remote_only, include_hybrid, min_salary, platforms,
        sources_config=sources, runtime=runtime, cache=cache, circuit=circuit,
        skipped=skipped_sources, progress=progress, deduplicate=deduplicate,
        salary_from_description=salary_from_description,
    )
    source_jobs, source_counts = discover_sources(
        sources, titles, location, remote_only, include_hybrid, min_salary,
        platforms=platforms, runtime=runtime, cache=cache, circuit=circuit,
        skipped=skipped_sources, progress=progress, deduplicate=deduplicate,
        salary_from_description=salary_from_description,
    )
    extra_jobs, extra_counts = (
        discover_engines(
            extra_engines, titles, location, remote_only, include_hybrid, min_salary,
            runtime=runtime, cache=cache, circuit=circuit,
            skipped=skipped_sources, progress=progress, deduplicate=deduplicate,
            salary_from_description=salary_from_description,
        )
        if extra_engines
        else ([], {})
    )
    jobs = jobs + source_jobs + extra_jobs
    for plat_name, count in {**source_counts, **extra_counts}.items():
        platform_counts[plat_name] = platform_counts.get(plat_name, 0) + count
    before_dedupe = len(jobs)
    jobs = dedupe_jobs(jobs, enabled=deduplicate)
    removed_duplicates = before_dedupe - len(jobs)
    if deduplicate and removed_duplicates:
        log_fn(f"  * Removed {removed_duplicates} redundant postings from other boards")
    for plat_name, count in platform_counts.items():
        dots = "." * max(3, 25 - len(plat_name))
        log_fn(f"  -> Searching {plat_name}{dots} Found {count} postings")
    log_fn(f"  * Total discovered: {len(jobs)} postings")
    discovered_total = len(jobs)
    previously_seen_count = 0

    if history is not None and not include_seen and jobs:
        history_mode = (runtime.get("history") or {}).get("match", "url+role")
        jobs, seen_jobs = history.filter_new(jobs, history_scope_key, match=history_mode)
        previously_seen_count = len(seen_jobs)
        if previously_seen_count:
            log_fn(
                f"  * Skipped {previously_seen_count} postings reported in an earlier sweep"
            )
        log_fn(f"  * New postings: {len(jobs)}")

    if not jobs:
        if previously_seen_count:
            message = (
                f"No new postings since your last sweep ({previously_seen_count} already "
                "reported). Run with --include-seen to review them."
            )
            log_fn(message)
            return {
                "status": "completed",
                "message": message,
                "discovered_count": discovered_total,
                "new_count": 0,
                "previously_seen_count": previously_seen_count,
                "history_scope": history_scope_key,
                "active_count": 0,
                "top_match": None,
                "roles": [],
                "top_roles": [],
                "reports": {},
                "skipped_sources": skipped_sources,
            }
        log_fn("No jobs found matching your criteria. Try expanding your search.")
        return {
            "status": "completed",
            "discovered_count": 0,
            "new_count": 0,
            "previously_seen_count": 0,
            "history_scope": history_scope_key,
            "active_count": 0,
            "top_match": None,
            "roles": [],
            "top_roles": [],
            "reports": {},
            "skipped_sources": skipped_sources,
        }

    # [3/5] Validating URLs
    _progress(3, 5, "Validating URLs")
    log_fn("\n[3/5] Validating URLs...")
    log_fn(f"  -> Checking all {len(jobs)} links for active status...")
    valid_jobs, expired_count = filter_valid_jobs(jobs, progress=progress)
    if expired_count > 0:
        log_fn(f"  [x] Removed {expired_count} expired postings (returned dead links or soft-404 redirects)")
    unverified_count = sum(1 for job in valid_jobs if job.get("unverified"))
    if unverified_count:
        log_fn(f"  * {len(valid_jobs)} active postings remain ({unverified_count} unverified)")
    else:
        log_fn(f"  * {len(valid_jobs)} verified active postings remain")

    if history is not None:
        sweep_id = (
            f"{profile_stem}-"
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
        history.record(valid_jobs, history_scope_key, sweep_id=sweep_id)
        history.prune()

    if not valid_jobs:
        log_fn("All discovered jobs had invalid or dead links.")
        return {
            "status": "completed",
            "discovered_count": discovered_total,
            "new_count": len(jobs),
            "previously_seen_count": previously_seen_count,
            "history_scope": history_scope_key,
            "active_count": 0,
            "top_match": None,
            "roles": [],
            "top_roles": [],
            "reports": {},
            "skipped_sources": skipped_sources,
        }

    # [4/5] Scoring against resume
    _progress(4, 5, "Scoring against resume")
    log_fn("\n[4/5] Scoring against resume...")
    scored_jobs, extracted_keywords = (
        score_jobs_by_track(
            valid_jobs,
            get_tracks(config),
            resume_path,
            must_have_skills,
            keywords_weight,
            progress=progress,
            synonyms=synonyms,
        )
        if resume.get("tracks")
        else score_jobs(
            valid_jobs,
            resume_path,
            must_have_skills,
            keywords_weight,
            progress=progress,
            synonyms=synonyms,
        )
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

    if "pdf" in formats or "png" in formats:
        if report_style == "legacy":
            total_pages = build_pdf(scored_jobs, pdf_file, name)
        else:
            total_pages = build_report(cards, pdf_file, config)
        log_fn(f"  -> Building PDF: {total_pages} pages ({len(cards)} roles)")
        log_fn(f"  * PDF saved: {pdf_file}")
        generated_reports["pdf"] = os.path.realpath(pdf_file)
        _copy_to_destinations([pdf_file], report_destinations, "PDF", log_fn)

    if "png" in formats:
        try:
            png_files = export_to_png(pdf_file, base_output_path)
            log_fn(f"  -> Building PNG: {len(png_files)} image(s)")
            for png_file in png_files:
                log_fn(f"  * PNG saved: {png_file}")
            generated_reports["png"] = png_files
            _copy_to_destinations(png_files, report_destinations, "PNG", log_fn)
        except Exception as e:
            log_fn(f"  [x] Could not build PNG: {e}")

    if "csv" in formats:
        export_rows = cards if report_style != "legacy" else scored_jobs
        previous = load_previous(output_dir, profile_stem, exclude=csv_file) if job_tracking else None
        num_rows, num_cols = export_to_csv(
            export_rows, csv_file, tracking=job_tracking, previous=previous
        )
        log_fn(f"  -> Building CSV: {num_rows} rows, {num_cols} columns")
        if job_tracking:
            carried_rows = carried_count(export_rows, previous)
            if carried_rows:
                log_fn(f"  * Tracking: carried earlier values into {carried_rows} row(s)")
            else:
                log_fn("  * Tracking: ready to fill in Excel, Sheets, or Notion")
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
        "discovered_count": discovered_total,
        "new_count": len(jobs),
        "previously_seen_count": previously_seen_count,
        "history_scope": history_scope_key,
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
        "skipped_sources": skipped_sources,
    }


if __name__ == "__main__":
    main()
