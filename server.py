"""
Sweepy MCP Server

Provides standard MCP tools (stdio transport) for LLMs (Claude, Antigravity, etc.)
to automate job board discovery, profile generation, and match scoring.

Stream discipline: the MCP protocol travels over stdout, so nothing in this module or
the engine may write to stdout. All engine output uses the `logging` module. This server
does not attach a handler to the "sweepy" logger, so engine INFO records are silently
dropped; only "sweepy.server" logs (startup + expected warnings) go to stderr. A
`_quiet_stdout()` guard wraps engine calls that historically used `print()`, as a redundant safeguard.

Sandbox: `create_profile` and `export_report` write only inside `_WORKSPACE` (set via the
`SWEEPY_WORKSPACE` env var, defaulting to this file's directory). Set
`SWEEPY_ALLOW_EXTERNAL_WRITES=1` (or `true`/`yes`/`on`) to disable the boundary check.
"""

import contextlib
import glob
import json
import logging
import os
import re
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from typing import List, Optional

try:
    from mcp.server.fastmcp import Context, FastMCP  # mcp 1.x
    _MCP_MODULE = "mcp.server.fastmcp"
except ImportError:
    from mcp.server.mcpserver import Context  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_MODULE = "mcp.server.mcpserver"

try:
    _MCP_VERSION = _dist_version("mcp")
except PackageNotFoundError:
    _MCP_VERSION = "unknown"

log = logging.getLogger("sweepy.server")

# Import engine modules under a stdout redirect so any stray print() at import time
# cannot corrupt the JSON-RPC stream before mcp.run() starts.
with contextlib.redirect_stdout(sys.stderr):
    import anyio

    from engine.config import save_profile
    from engine.docx import convert_docx_to_pdf
    from engine.exporter import export_to_csv, export_to_json, export_to_png
    from engine.pdf_builder import build_pdf
    from engine.report import build_report
    from engine.session import SweepSession, stable_id
    from swee import run_sweep_pipeline

mcp = FastMCP("sweepy")

_WORKSPACE = os.path.realpath(
    os.environ.get("SWEEPY_WORKSPACE", os.path.dirname(os.path.abspath(__file__)))
)

_EXPECTED = (FileNotFoundError, ValueError, IsADirectoryError, PermissionError)

# The hybrid stateful session: populated by run_sweep, extended by import_jobs, and
# overridden by submit_judgments. Persisted to report_session.json in the output dir.
_session = SweepSession()
_session_profile: dict = {}
_session_dir: Optional[str] = None

_SESSION_FILENAME = "report_session.json"


def _allow_external_writes() -> bool:
    return os.environ.get("SWEEPY_ALLOW_EXTERNAL_WRITES", "").strip().lower() in ("1", "true", "yes", "on")


def _safe_output_path(candidate: str) -> str:
    """Resolve a write destination and enforce it stays inside _WORKSPACE."""
    expanded = os.path.expanduser(candidate)
    if not os.path.isabs(expanded):
        expanded = os.path.join(_WORKSPACE, expanded)
    target = os.path.realpath(expanded)

    if _allow_external_writes():
        return target

    try:
        if os.path.commonpath([_WORKSPACE, target]) != _WORKSPACE:
            raise ValueError(f"Refusing to write outside workspace: {candidate!r}")
    except ValueError:
        raise ValueError(f"Refusing to write outside workspace: {candidate!r}")
    return target


def _resolve_read_path(candidate: str, must_exist: bool = True) -> str:
    """Resolve a read path without enforcing the workspace boundary."""
    expanded = os.path.expanduser(candidate)
    if not os.path.isabs(expanded):
        expanded = os.path.join(_WORKSPACE, expanded)
    target = os.path.realpath(expanded)
    if must_exist and not os.path.exists(target):
        raise FileNotFoundError(f"File not found: {candidate!r}")
    return target


def _default_profile_path(profile_data: dict) -> str:
    name = profile_data.get("name", "user")
    titles = profile_data.get("search", {}).get("titles", ["custom"])
    first_title = titles[0] if titles else "custom"
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', first_title).strip('_').lower()
    return os.path.join("profiles", f"{safe_name}_{safe_title}.yaml")


def _latest_sweep_json(results_dir: str, profile_stem: Optional[str]) -> Optional[str]:
    pattern = os.path.join(results_dir, f"{profile_stem}_*.json" if profile_stem else "*.json")
    matches = [p for p in glob.glob(pattern) if not p.endswith("_export.json")]
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


@contextlib.contextmanager
def _quiet_stdout():
    with contextlib.redirect_stdout(sys.stderr):
        yield


def _session_path(results_dir: str) -> str:
    return os.path.join(results_dir, _SESSION_FILENAME)


def _persist_session(results_dir: Optional[str]) -> None:
    if not results_dir:
        return
    path = _session_path(results_dir)
    try:
        payload = {"profile": _session_profile, "jobs": _session.all()}
        os.makedirs(results_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    except OSError:
        log.warning("Could not persist session to %s", path)


def _load_session(results_dir: str) -> bool:
    """Load a persisted session into the in-memory store. Returns False if absent."""
    global _session, _session_profile
    path = _session_path(results_dir)
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        _session = SweepSession()
        _session.set_many(payload.get("jobs", []) or [])
        _session_profile = payload.get("profile", {}) or {}
        return True
    except (OSError, ValueError):
        log.warning("Could not load session from %s", path)
        return False


def _resolve_session(results_dir: str, profile_stem: Optional[str]) -> None:
    """Ensure the in-memory session reflects the request, loading from disk only when needed."""
    global _session_dir
    if profile_stem is None and _session.all():
        return
    resolved_dir = _resolve_read_path(results_dir, must_exist=True)
    _load_session(resolved_dir)
    _session_dir = resolved_dir


def _sorted_cards() -> List[dict]:
    cards = _session.all()
    cards.sort(key=lambda c: (c.get("rank", 0) if c.get("rank") else float("inf")))
    return cards


def _ok(**fields) -> str:
    payload = {"status": "ok"}
    payload.update(fields)
    return json.dumps(payload, default=str)


def _err(message: str, **fields) -> str:
    payload = {"status": "error", "message": message}
    payload.update(fields)
    return json.dumps(payload, default=str)


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
        platforms: Optional dictionary configuring platforms to sweep.
        output_filename: Optional custom YAML path (defaults to profiles/{name}_{title}.yaml).

    Returns:
        JSON string with the saved profile path.
    """
    try:
        if not name or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not titles:
            raise ValueError("titles must be a non-empty list")

        resolved_resume = _resolve_read_path(resume_path, must_exist=True)
        if not resolved_resume.lower().endswith(".pdf"):
            raise ValueError(f"resume_path must point to a .pdf file: {resume_path!r}")

        platforms_config = {
            "greenhouse": True,
            "ashby": True,
            "lever": True,
            "workable": True,
            "aggregators": False,
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
                "min_salary": min_salary,
            },
            "resume": {
                "path": resolved_resume,
                "must_have_skills": must_have_skills or [],
                "keywords_weight": 1.5,
            },
            "platforms": platforms_config,
            "export": {
                "format": "pdf,csv,json",
                "output_dir": "results",
            },
        }

        target_path = (
            _safe_output_path(output_filename)
            if output_filename
            else _safe_output_path(_default_profile_path(profile_data))
        )
        with _quiet_stdout():
            saved_path = save_profile(profile_data, target_path)
        return _ok(profile_path=saved_path)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("create_profile failed")
        return _err(str(exc))


@mcp.tool()
async def run_sweep(
    profile_path: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Executes a 5-stage job sweep pipeline using a specified profile or the default profile.

    This call may take several minutes: live board scraping and uptime verification run in
    a worker thread while progress notifications are forwarded to the client.

    Args:
        profile_path: Optional path to the profile YAML. If omitted, uses default profile or config.sample.yaml.

    Returns:
        JSON string summarizing active roles found, top matches, and generated report paths.
    """
    def _progress(current: int, total: int, label: str) -> None:
        if ctx is not None:
            anyio.from_thread.run(ctx.report_progress, float(current), float(total), label)

    try:
        resolved = _resolve_read_path(profile_path, must_exist=True) if profile_path else None

        def _worker() -> dict:
            return run_sweep_pipeline(profile_path=resolved, verbose=False, progress=_progress)

        with _quiet_stdout():
            results = await anyio.to_thread.run_sync(_worker)

        global _session, _session_profile, _session_dir
        cards = results.get("cards", []) or []
        _session = SweepSession()
        _session.set_many(cards)
        _session_profile = results.get("profile", {}) or {}
        output_dir = results.get("output_dir")
        _session_dir = output_dir
        if output_dir:
            _persist_session(output_dir)

        summary = {
            "discovered_count": results.get("discovered_count"),
            "active_count": results.get("active_count"),
            "top_match": results.get("top_match"),
            "reports": results.get("reports"),
            "top_roles": results.get("top_roles", [])[:5],
            "job_ids": [c["id"] for c in _sorted_cards()],
            "card_count": len(cards),
        }
        return _ok(**summary)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("run_sweep failed")
        return _err(str(exc))


@mcp.tool()
def get_results(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    limit: int = 10,
) -> str:
    """
    Retrieves the latest sweep results and report artifacts.

    Args:
        profile_stem: Optional profile identifier to filter results (e.g. 'pedro_writer'). If omitted, retrieves latest.
        results_dir: Results directory (default 'results').
        limit: Number of top scored roles to return in the list (default 10, clamped to 1..100).

    Returns:
        JSON string containing the latest sweep report metadata and top scored roles.
    """
    try:
        resolved_dir = _resolve_read_path(results_dir, must_exist=True)
        effective_limit = max(1, min(int(limit), 100))
        latest_json = _latest_sweep_json(resolved_dir, profile_stem)
        if latest_json is None:
            return _err("No sweep result JSON files found.")

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
                    "match_score": r.get("match_score", r.get("match_value")),
                    "match_kind": r.get("match_kind"),
                    "resume_track": r.get("resume_track"),
                    "domain": r.get("domain"),
                    "url": r.get("url"),
                    "playbook": r.get("playbook", ""),
                }
                for r in roles[:effective_limit]
            ],
        }
        return _ok(**summary)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("get_results failed")
        return _err(str(exc))


@mcp.tool()
def export_report(
    json_source: Optional[str] = None,
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    formats: Optional[List[str]] = None,
    candidate_name: str = "Job Seeker",
    output_dir: Optional[str] = None,
) -> str:
    """
    Rebuilds report files (PDF, PNG, CSV, or JSON) from an existing sweep result without re-running discovery or scoring.

    Args:
        json_source: Absolute path to the existing sweep JSON result file. Takes priority over profile_stem.
        profile_stem: Profile identifier used to find the latest matching JSON (e.g. 'pedro_writer').
        results_dir: Directory containing result files (default 'results').
        formats: List of output formats to generate. Options: 'pdf', 'csv', 'json', 'png'. Defaults to ['pdf'].
        candidate_name: Name displayed in the PDF report header (default 'Job Seeker').
        output_dir: Directory to save regenerated reports. Defaults to same directory as the source JSON.

    Returns:
        JSON string with the status and absolute paths to all generated report files.
    """
    try:
        if not formats:
            formats = ["pdf"]
        formats = [f.lower() for f in formats]

        if json_source:
            source_json = _resolve_read_path(json_source, must_exist=True)
        else:
            resolved_dir = _resolve_read_path(results_dir, must_exist=True)
            source_json = _latest_sweep_json(resolved_dir, profile_stem)
            if source_json is None:
                return _err("No JSON result files found matching the criteria.")

        with open(source_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        roles = data if isinstance(data, list) else data.get("roles", [])

        if not roles:
            return _err("Source JSON contains no roles to export.")

        base_name = os.path.splitext(source_json)[0]
        if output_dir is not None:
            target_dir = _safe_output_path(output_dir)
        else:
            target_dir = os.path.dirname(source_json)
        os.makedirs(target_dir, exist_ok=True)
        stem = os.path.basename(base_name)
        base_out = os.path.join(target_dir, stem)

        generated = {}
        errors = []

        pdf_path = f"{base_out}.pdf"

        if "pdf" in formats or "png" in formats:
            try:
                with _quiet_stdout():
                    if roles and "match_value" in roles[0]:
                        pages = build_report(roles, pdf_path, {"name": candidate_name})
                    else:
                        pages = build_pdf(roles, pdf_path, candidate_name)
                generated["pdf"] = os.path.realpath(pdf_path)
                generated["pdf_pages"] = pages
            except Exception as e:
                errors.append(f"PDF: {e}")

        if "png" in formats:
            try:
                if not os.path.exists(pdf_path):
                    raise FileNotFoundError(f"PNG export needs a rendered PDF at {pdf_path!r}")
                with _quiet_stdout():
                    png_paths = export_to_png(pdf_path, base_out)
                generated["png"] = png_paths
            except Exception as e:
                errors.append(f"PNG: {e}")

        if "csv" in formats:
            try:
                csv_path = f"{base_out}.csv"
                with _quiet_stdout():
                    num_rows, num_cols = export_to_csv(roles, csv_path)
                generated["csv"] = os.path.realpath(csv_path)
                generated["csv_rows"] = num_rows
            except Exception as e:
                errors.append(f"CSV: {e}")

        if "json" in formats:
            try:
                json_path = f"{base_out}_export.json"
                with _quiet_stdout():
                    export_to_json(roles, json_path)
                generated["json"] = os.path.realpath(json_path)
            except Exception as e:
                errors.append(f"JSON: {e}")

        if not generated:
            return _err("Failed to generate any report formats.", errors=errors)

        return _ok(source_file=source_json, roles_exported=len(roles), generated=generated, errors=errors)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("export_report failed")
        return _err(str(exc))


@mcp.tool()
def convert_docx(
    docx_path: str,
    pdf_path: Optional[str] = None,
) -> str:
    """
    Converts a DOCX file to PDF.

    Uses python-docx + reportlab first, falling back to Microsoft Word via
    docx2pdf when Word is installed. A blank pdf_path saves the PDF next to the
    DOCX. The output path must stay inside the workspace sandbox unless
    SWEEPY_ALLOW_EXTERNAL_WRITES is set.

    Args:
        docx_path: Absolute or relative path to the .docx file to convert.
        pdf_path: Optional output PDF path. Defaults to the DOCX directory.

    Returns:
        JSON string with the resolved output PDF path.
    """
    try:
        resolved_docx = _resolve_read_path(docx_path, must_exist=True)
        target = (
            _safe_output_path(pdf_path)
            if pdf_path
            else _safe_output_path(os.path.splitext(resolved_docx)[0] + ".pdf")
        )
        with _quiet_stdout():
            out_path = convert_docx_to_pdf(resolved_docx, target)
        return _ok(pdf_path=os.path.realpath(out_path))
    except (*_EXPECTED, RuntimeError) as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("convert_docx failed")
        return _err(str(exc))


@mcp.tool()
def get_jobs(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    limit: Optional[int] = None,
) -> str:
    """
    Returns the card records held in the current sweep session, ranked by match.

    Args:
        profile_stem: Optional profile identifier to load a persisted session from disk.
        results_dir: Results directory holding report_session.json (default 'results').
        limit: Optional number of cards to return (None returns all).

    Returns:
        JSON string with the list of card records.
    """
    try:
        _resolve_session(results_dir, profile_stem)
        cards = _sorted_cards()
        if limit is not None:
            cards = cards[: max(1, int(limit))]
        return _ok(count=len(cards), jobs=cards)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("get_jobs failed")
        return _err(str(exc))


@mcp.tool()
def submit_judgments(
    job_id: str,
    match_pct: Optional[int] = None,
    resume_track: Optional[str] = None,
    resume_color: Optional[str] = None,
    domain: Optional[str] = None,
    summary: Optional[str] = None,
    requirements: Optional[str] = None,
    alignment: Optional[str] = None,
    has_extended_response: Optional[bool] = None,
    app_format: Optional[str] = None,
    comp: Optional[str] = None,
    benefits: Optional[str] = None,
    page_theme: Optional[str] = None,
) -> str:
    """
    Overrides a job's deterministic card fields with LLM-supplied judgments.

    Supplying match_pct upgrades the match label provenance to "match"; otherwise the
    deterministic keyword-overlap value is retained. Only non-null fields are merged.

    Args:
        job_id: Stable job id (from run_sweep or get_jobs).
        match_pct: Optional LLM match percentage (0-100).
        resume_track, resume_color, domain, summary, requirements, alignment,
        has_extended_response, app_format, comp, benefits, page_theme: Optional overrides.

    Returns:
        JSON string with the merged card record.
    """
    try:
        fields: dict = {}
        if match_pct is not None:
            fields["match_value"] = int(match_pct)
            fields["match_kind"] = "match"
        for key, value in {
            "resume_track": resume_track,
            "resume_color": resume_color,
            "domain": domain,
            "summary": summary,
            "requirements": requirements,
            "alignment": alignment,
            "has_extended_response": has_extended_response,
            "app_format": app_format,
            "comp": comp,
            "benefits": benefits,
            "page_theme": page_theme,
        }.items():
            if value is not None:
                fields[key] = value

        if not fields:
            return _err("No judgment fields supplied.")

        try:
            card = _session.apply_judgments(job_id, **fields)
        except KeyError as exc:
            return _err(str(exc))

        _persist_session(_session_dir)
        return _ok(job=card)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("submit_judgments failed")
        return _err(str(exc))


@mcp.tool()
def import_jobs(
    jobs_json: str,
    validate: bool = False,
) -> str:
    """
    Appends agent-found jobs (canonical card schema) into the current session.

    URLs are skipped validation by default because the agent already vetted them; pass
    validate=True to run each URL through the validator.

    Args:
        jobs_json: JSON string encoding a list of card records.
        validate: Optional; when True, run URL validation before importing.

    Returns:
        JSON string with the number of imported jobs.
    """
    try:
        try:
            jobs = json.loads(jobs_json)
        except ValueError as exc:
            return _err(f"jobs_json must be valid JSON: {exc}")
        if not isinstance(jobs, list):
            return _err("jobs_json must encode a JSON list.")

        imported = 0
        skipped = 0
        for raw in jobs:
            job = dict(raw)
            job["id"] = job.get("id") or stable_id(job.get("url", ""))
            if validate and job.get("url"):
                from engine.validator import is_valid_url

                try:
                    if not is_valid_url(job["url"]):
                        skipped += 1
                        continue
                except Exception:
                    skipped += 1
                    continue
            _session.upsert(job)
            imported += 1

        _persist_session(_session_dir)
        return _ok(imported=imported, skipped=skipped)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("import_jobs failed")
        return _err(str(exc))


@mcp.tool()
def render_report(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    output_filename: Optional[str] = None,
    playbook: str = "",
) -> str:
    """
    Renders the cards PDF from the current session and writes it through the sandbox.

    Args:
        profile_stem: Optional profile identifier to load a persisted session from disk.
        results_dir: Results directory (default 'results').
        output_filename: Optional explicit output PDF path (must stay inside the workspace).
        playbook: Optional playbook text; when empty, a deterministic playbook is generated.

    Returns:
        JSON string with the output path and page count.
    """
    try:
        _resolve_session(results_dir, profile_stem)
        cards = _sorted_cards()
        if not cards:
            return _err("No jobs in the session to render.")

        profile = _session_profile or {"name": "Job Seeker"}

        if output_filename:
            pdf_path = _safe_output_path(output_filename)
        else:
            base = os.path.join(
                _session_dir or _resolve_read_path(results_dir, must_exist=True),
                "report",
            )
            pdf_path = _safe_output_path(base + ".pdf")

        os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
        with _quiet_stdout():
            pages = build_report(cards, pdf_path, profile, playbook=playbook)

        return _ok(pdf_report=os.path.realpath(pdf_path), pages=pages, card_count=len(cards))
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("render_report failed")
        return _err(str(exc))


if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    log.info("Sweepy MCP starting; mcp=%s (module %s)", _MCP_VERSION, _MCP_MODULE)
    mcp.run()
