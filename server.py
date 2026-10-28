"""
Sweepy MCP Server

Provides standard MCP tools (stdio transport) for LLMs (Claude, Antigravity, etc.)
to automate job board discovery, profile generation, and match scoring.

Stream discipline: the MCP protocol travels over stdout, so nothing in this module or
the engine may write to stdout. All engine output uses the `logging` module. The `run_sweep`
tool attaches a debug file handler to the "sweepy" logger, so pipeline records go to a
timestamped log without writing to the MCP stdout stream. Other engine INFO records remain
silent; only "sweepy.server" logs (startup + expected warnings) go to stderr. A
`_quiet_stdout()` guard wraps engine calls that historically used `print()`, as a redundant safeguard.

Sandbox: `create_profile` and `export_report` write only inside `_WORKSPACE` (set via the
`SWEEPY_WORKSPACE` env var, defaulting to this file's directory). Set
`SWEEPY_ALLOW_EXTERNAL_WRITES=1` (or `true`/`yes`/`on`) to disable the boundary check.
"""

import asyncio
import contextlib
import glob
import json
import logging
import os
import queue
import re
import sys
import threading
import time
import uuid
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from typing import List, Optional

try:
    from mcp.server.fastmcp import Context, FastMCP  # mcp 1.x
    from mcp.types import ToolAnnotations
    _MCP_MODULE = "mcp.server.fastmcp"
except ImportError:
    from mcp.server.mcpserver import Context  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
    from mcp.types import ToolAnnotations
    _MCP_MODULE = "mcp.server.mcpserver"

try:
    _MCP_VERSION = _dist_version("mcp")
except PackageNotFoundError:
    _MCP_VERSION = "unknown"

log = logging.getLogger("sweepy.server")

# Import engine modules under a stdout redirect so any stray print() at import time
# cannot corrupt the JSON-RPC stream before mcp.run() starts.
with contextlib.redirect_stdout(sys.stderr):
    from engine.config import is_valid_color, load_config, save_profile
    from engine.documents import convert_to_pdf
    from engine.docx import convert_docx_to_pdf
    from engine.engine_defaults import DEFAULT_HISTORY
    from engine.engines import ENGINE_CATALOG, engine_status
    from engine.exporter import export_to_csv, export_to_json, export_to_png
    from engine.history import SweepHistory, history_scope
    from engine.logging import enable_debug_logging
    from engine.pdf_builder import build_pdf
    from engine.portfolio import normalize_portfolio, portfolio_summary
    from engine.report import build_report
    from engine.scorer import read_document_text
    from engine.session import SweepSession, stable_id
    from engine.sweep_config import default_engine_config, normalize_sources, validate_sources
    from engine.timefmt import normalize_stamp
    from engine.tracking import load_previous, tracking_enabled
    from swee import result_stem, run_sweep_pipeline

_SERVER_INSTRUCTIONS = (
    "Sweepy matches job postings against a candidate's resume and portfolio. "
    "Before create_profile, ask the candidate for a portfolio: an online URL, a local PDF, "
    "DOCX, Markdown, text, or HTML file, or none. Pass what they give you as `portfolios`, "
    "one entry per resume track when the candidate targets more than one role family, and "
    "pass `resume_tracks` when they keep a separate resume for each track. For an existing "
    "profile, call set_portfolio instead. Every card reports the portfolio for its track "
    "plus `portfolio_pieces`. Choose the pieces that best fit each role and submit them with "
    "submit_judgments(portfolio_highlight=...) before render_report, so the report and the "
    "exports name the pieces to send. A card with no portfolio carries empty portfolio "
    "fields, and that is not a failure. Score each role against the candidate's actual "
    "resume, not the profile's keyword list: get_jobs returns `resume_documents` with the "
    "parsed text of every resume track, so read that text, weigh transferable skills the "
    "way a recruiter would, and score match_pct the way the posting's ATS parses the file. "
    "A term a parser can read in a standard Experience or Skills section outranks the same "
    "term buried in a table, header, or sidebar. State the resulting obstacle in concerns. "
    "Stamp the artifacts with the user's clock: pass `timestamp` as YYYY-MM-DD-HHMMSS to "
    "run_sweep and render_report, using the local time you already know from the "
    "conversation, so each filename carries the user's date and time instead of the "
    "server's."
)

mcp = FastMCP("sweepy", instructions=_SERVER_INSTRUCTIONS)

_WORKSPACE = os.path.realpath(
    os.environ.get("SWEEPY_WORKSPACE", os.path.dirname(os.path.abspath(__file__)))
)

_EXPECTED = (FileNotFoundError, ValueError, IsADirectoryError, PermissionError)

# The hybrid stateful session: populated by run_sweep, extended by import_jobs, and
# overridden by submit_judgments. Persisted to report_session.json in the output dir.
_session = SweepSession()
_session_profile: dict = {}
_session_dir: Optional[str] = None
# The stem of the profile behind the session, so a rendered report keeps the sweep's name.
_session_stem: Optional[str] = None
# The agent's strategy text, kept with the session so a re-render does not drop it.
_session_playbook: str = ""
# Remembers the history bucket of the last sweep so clear_history() needs no arguments.
_last_history: dict = {"scope": None, "config": {}}

_SESSION_FILENAME = "report_session.json"


def _default_mcp_sources_config() -> tuple[dict, dict]:
    enabled = [name for name, info in ENGINE_CATALOG.items() if info.core]
    not_enabled = {}
    for name, info in ENGINE_CATALOG.items():
        if info.core:
            continue
        if name == "apify":
            not_enabled[name] = "Requires explicit opt-in because the service may incur charges."
            continue
        status = engine_status(name)
        if not status["installed"]:
            not_enabled[name] = status["detail"]
            continue
        errors = validate_sources({name: default_engine_config(name)})
        if errors:
            not_enabled[name] = "; ".join(errors)
            continue
        enabled.append(name)
    return {"enabled": enabled}, not_enabled


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


_RESULT_STAMP = re.compile(r"(?:_mcp)?_\d{4}-\d{2}-\d{2}-\d{6}$")


def _profile_stem_from_result(stem: str) -> str:
    """Drop the ``_YYYY-MM-DD-HHMMSS`` stamp, and any ``_mcp`` marker, from a result stem."""
    return _RESULT_STAMP.sub("", stem)


def _profile_tracking_setting(profile_stem: Optional[str]) -> bool:
    """Read ``export.tracking`` from the profile behind a sweep. Off when unresolvable."""
    if not profile_stem:
        return False
    for suffix in (".yaml", ".yml"):
        path = os.path.join(_WORKSPACE, "profiles", f"{profile_stem}{suffix}")
        if os.path.exists(path):
            try:
                with _quiet_stdout():
                    profile = load_config(path)
            except (OSError, ValueError):
                return False
            return tracking_enabled(profile.get("export") or {})
    return False


def _validate_runtime_config(
    cache_config: Optional[dict],
    orchestrator_config: Optional[dict],
    history_config: Optional[dict] = None,
) -> None:
    if history_config is not None:
        if not isinstance(history_config, dict):
            raise ValueError("history_config must be an object")
        unknown = set(history_config) - {"enabled", "retention_days", "match", "path"}
        if unknown:
            raise ValueError(
                "Unsupported history_config field(s): " + ", ".join(sorted(unknown))
            )
        if "enabled" in history_config and type(history_config["enabled"]) is not bool:
            raise ValueError("history_config.enabled must be a boolean")
        days = history_config.get("retention_days")
        if days is not None and (type(days) is not int or days < 0):
            raise ValueError(
                "history_config.retention_days must be a non-negative integer"
            )
        match = history_config.get("match")
        if match is not None and match not in ("url", "url+role"):
            raise ValueError("history_config.match must be 'url' or 'url+role'")
        path = history_config.get("path")
        if path is not None and (not isinstance(path, str) or not path.strip()):
            raise ValueError("history_config.path must be a non-empty string or null")

    if cache_config is not None:
        if not isinstance(cache_config, dict):
            raise ValueError("cache_config must be an object")
        unknown = set(cache_config) - {"enabled", "ttl_seconds"}
        if unknown:
            raise ValueError(
                "Unsupported cache_config field(s): " + ", ".join(sorted(unknown))
            )
        if "enabled" in cache_config and type(cache_config["enabled"]) is not bool:
            raise ValueError("cache_config.enabled must be a boolean")
        ttl = cache_config.get("ttl_seconds")
        if ttl is not None and (type(ttl) is not int or ttl < 0):
            raise ValueError("cache_config.ttl_seconds must be a non-negative integer")

    if orchestrator_config is not None:
        if not isinstance(orchestrator_config, dict):
            raise ValueError("orchestrator_config must be an object")
        unknown = set(orchestrator_config) - {
            "timeout_per_source_seconds",
            "circuit_breaker",
        }
        if unknown:
            raise ValueError(
                "Unsupported orchestrator_config field(s): "
                + ", ".join(sorted(unknown))
            )
        timeout = orchestrator_config.get("timeout_per_source_seconds")
        if timeout is not None and (type(timeout) is not int or timeout < 1):
            raise ValueError(
                "orchestrator_config.timeout_per_source_seconds must be a positive integer"
            )

        breaker = orchestrator_config.get("circuit_breaker")
        if breaker is not None:
            if not isinstance(breaker, dict):
                raise ValueError("orchestrator_config.circuit_breaker must be an object")
            unknown = set(breaker) - {"failure_threshold", "cooldown_seconds"}
            if unknown:
                raise ValueError(
                    "Unsupported circuit_breaker field(s): "
                    + ", ".join(sorted(unknown))
                )
            threshold = breaker.get("failure_threshold")
            if threshold is not None and (type(threshold) is not int or threshold < 1):
                raise ValueError(
                    "circuit_breaker.failure_threshold must be a positive integer"
                )
            cooldown = breaker.get("cooldown_seconds")
            if cooldown is not None and (type(cooldown) is not int or cooldown < 0):
                raise ValueError(
                    "circuit_breaker.cooldown_seconds must be a non-negative integer"
                )


def _normalize_resume_tracks(tracks: Optional[List[dict]]) -> List[dict]:
    """Validate the resume tracks an MCP caller supplies and resolve their paths."""
    if tracks is None:
        return []
    if not isinstance(tracks, list):
        raise ValueError("resume_tracks must be a list of objects")

    normalized = []
    seen = set()
    for index, track in enumerate(tracks, start=1):
        label = f"resume_tracks[{index}]"
        if not isinstance(track, dict):
            raise ValueError(f"{label} must be an object")
        unknown = set(track) - {"name", "path", "color", "route_keywords"}
        if unknown:
            raise ValueError(
                f"{label} has unsupported field(s): " + ", ".join(sorted(unknown))
            )

        name = str(track.get("name") or "").strip()
        if not name:
            raise ValueError(f"{label}.name must be a non-empty string")
        if name.lower() in seen:
            raise ValueError(f"{label}.name repeats an earlier track: {name!r}")
        seen.add(name.lower())

        path = str(track.get("path") or "").strip()
        if path:
            resolved = _resolve_read_path(path, must_exist=True)
            if not resolved.lower().endswith((".pdf", ".docx")):
                raise ValueError(
                    f"{label}.path must point to a .pdf or .docx file: {path!r}"
                )
            path = resolved

        color = str(track.get("color") or "").strip() or "#1D4ED8"
        if not is_valid_color(color):
            raise ValueError(
                f"{label}.color must be a hex code or a color name: {color!r}"
            )

        keywords = track.get("route_keywords") or []
        if not isinstance(keywords, list):
            raise ValueError(f"{label}.route_keywords must be a list")

        normalized.append(
            {
                "name": name,
                "color": color,
                "path": path,
                "route_keywords": [
                    str(keyword).strip() for keyword in keywords if str(keyword).strip()
                ],
            }
        )
    return normalized


def _portfolio_prompt() -> str:
    """Tell the agent how to collect a portfolio when the profile holds none."""
    return (
        "Ask the user whether they have a portfolio to submit: an online URL, a local "
        "PDF, DOCX, Markdown, text, or HTML file, or none. Call set_portfolio with what "
        "they give you, one entry per resume track when they target more than one role "
        "family. Skip this when the user has no portfolio."
    )


def _portfolio_payload(profile: Optional[dict] = None) -> dict:
    """Describe the portfolio setup for get_jobs and create_profile payloads."""
    summary = portfolio_summary(profile if profile is not None else _session_profile)
    payload = {
        "portfolio_configured": summary["configured"],
        "portfolio_sources": summary["sources"],
        "portfolio_pieces_per_card": summary["pieces_per_card"],
    }
    payload["portfolio_guidance"] = (
        "Each card lists portfolio_pieces from the portfolio for its resume track. Pick the "
        "pieces that best fit the posting, then pass them to submit_judgments as "
        "portfolio_highlight."
        if summary["configured"]
        else _portfolio_prompt()
    )
    return payload


def _normalize_portfolio_block(
    portfolios: Optional[List[dict]],
    track_names: Optional[List[str]] = None,
    pieces_per_card: Optional[int] = None,
) -> dict:
    """Validate a portfolio list from an MCP caller and return the profile block."""
    raw: dict = {"sources": portfolios or []}
    if pieces_per_card is not None:
        raw["pieces_per_card"] = pieces_per_card
    return normalize_portfolio(raw, track_names)


# One parsed resume per file, keyed by (path, mtime), so calling get_jobs twice does
# not re-parse the same PDF.
_RESUME_TEXT_CACHE: dict = {}
# A resume runs two pages at most; the cap only guards against a mislabeled document.
_RESUME_TEXT_LIMIT = 12000

_RESUME_GUIDANCE = (
    "Read `resume_documents[].text`, the parsed resume, before you score anything. The "
    "profile's `must_have_skills` and `synonyms` only drive the deterministic keyword "
    "pass, so judging from them measures the YAML instead of the candidate. Judge the "
    "document a recruiter reads: transferable skills, the scope and seniority behind each "
    "bullet, domain, tools, and the outcome every line proves. Then score it the way the "
    "posting's applicant tracking system parses it. A term the parser can read inside a "
    "standard Experience or Skills section counts as evidence; the same term inside a "
    "header, footer, image, table, or two-column sidebar may never reach a person, so "
    "weigh it lower. Name the ATS family when the apply URL reveals it (Workday, "
    "Greenhouse, Lever, Ashby, iCIMS, Taleo, Workable, SmartRecruiters) and say in "
    "`concerns` when a parser would lose part of the resume."
)


def _resume_text(path: str) -> str:
    """Return the plain text of a resume file, cached by path and modification time."""
    if not path:
        return ""
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return ""
    cached = _RESUME_TEXT_CACHE.get(path)
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        text = read_document_text(path)
    except Exception as exc:
        log.warning("Could not read resume %r: %s", path, exc)
        text = ""
    text = (text or "").strip()
    if len(text) > _RESUME_TEXT_LIMIT:
        text = text[:_RESUME_TEXT_LIMIT].rstrip() + "\n[...truncated...]"
    _RESUME_TEXT_CACHE[path] = (stamp, text)
    return text


def _resume_payload(profile: Optional[dict] = None, include_text: bool = True) -> dict:
    """Hand the agent the resume files, so judgment reads the document itself.

    Tracks that share a file share one entry. Sending the parsed text keeps the
    assessment grounded in the real candidate document even when the caller has no
    PDF reader of its own.
    """
    block = ((profile if profile is not None else _session_profile) or {}).get("resume") or {}
    default_path = str(block.get("path") or "")
    documents: dict = {}
    for track in block.get("tracks") or []:
        path = str(track.get("path") or default_path)
        if not path:
            continue
        document = documents.setdefault(path, {"path": path, "tracks": []})
        name = str(track.get("name") or "").strip()
        if name and name not in document["tracks"]:
            document["tracks"].append(name)
    if not documents and default_path:
        documents[default_path] = {"path": default_path, "tracks": []}

    entries = []
    for document in documents.values():
        entry = dict(document)
        if include_text:
            entry["text"] = _resume_text(document["path"])
        entries.append(entry)

    return {
        "resume_configured": bool(entries),
        "resume_default_path": default_path,
        "resume_documents": entries,
        "resume_guidance": _RESUME_GUIDANCE,
    }


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
        payload = {
            "profile": _session_profile,
            "profile_stem": _session_stem,
            "jobs": _session.all(),
            "playbook": _session_playbook,
        }
        os.makedirs(results_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    except OSError:
        log.warning("Could not persist session to %s", path)


def _load_session(results_dir: str) -> bool:
    """Load a persisted session into the in-memory store. Returns False if absent."""
    global _session, _session_profile, _session_playbook
    global _session_stem
    path = _session_path(results_dir)
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        _session = SweepSession()
        _session.set_many(payload.get("jobs", []) or [])
        _session_profile = payload.get("profile", {}) or {}
        _session_playbook = str(payload.get("playbook") or "")
        _session_stem = payload.get("profile_stem") or None
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


def _report_cards(cards: List[dict], profile: Optional[dict]) -> List[dict]:
    """Return the cards a rendered report prints, honoring ``report.max_cards``.

    ``build_report`` caps its story at ``max_cards`` (24 by default, no cap at zero),
    so an assessment gate that counted every card would demand judgments for roles the
    report never prints.
    """
    raw = ((profile or {}).get("report") or {}).get("max_cards")
    try:
        limit = 24 if raw in (None, "") else int(raw)
    except (TypeError, ValueError):
        limit = 24
    return list(cards) if limit <= 0 else list(cards)[:limit]


_ASSESSMENT_MODES = ("agent", "keyword")


def _assessment_mode(profile: Optional[dict]) -> str:
    """Return the profile's reporting mode: ``agent`` (default) or ``keyword``."""
    report = (profile or {}).get("report") or {}
    raw = report.get("assessment")
    if raw is None or str(raw).strip() == "":
        return "agent"
    mode = str(raw).strip().lower()
    if mode not in _ASSESSMENT_MODES:
        log.warning("Ignoring unknown report.assessment %r; using 'agent'", raw)
        return "agent"
    return mode


def _judgments_required() -> bool:
    """True when SWEEPY_REQUIRE_JUDGMENTS asks the server to refuse unassessed reports."""
    return os.environ.get("SWEEPY_REQUIRE_JUDGMENTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _unassessed(cards: List[dict]) -> List[dict]:
    return [card for card in cards if card.get("match_kind") != "match"]


def _needs_description(card: dict) -> bool:
    """True when the card carries no posting text for the caller to read."""
    if "needs_description" in card:
        return bool(card.get("needs_description"))
    return not str(card.get("description") or "").strip()


def _assessment_error(cards: List[dict], tool_name: str) -> Optional[str]:
    """Return an error payload when unassessed cards block a report."""
    pending = _unassessed(cards)
    if not pending:
        return None
    return _err(
        f"{tool_name} needs an agent assessment first. {len(pending)} of {len(cards)} report cards "
        "still carry keyword overlap, not a match score. Call get_jobs, assess each role "
        "against the resume, then submit_judgments before rendering. Set "
        "report.assessment: keyword in the profile to keep keyword-only reports.",
        unassessed_count=len(pending),
        unassessed_job_ids=[card.get("id") for card in pending],
        unassessed_titles=[
            f"{card.get('company') or card.get('title')}: {card.get('title')}" for card in pending
        ],
    )


# ---------------------------------------------------------------------------
# Background sweep jobs
#
# A live sweep needs minutes of board scraping, which outlives many client tool
# timeouts. The pipeline therefore runs on its own thread, and tool calls only
# ever wait for a bounded slice of it. A disconnected client cannot cancel the
# work, and a later call picks the job back up from the registry.
# ---------------------------------------------------------------------------

_SWEEP_JOBS: dict[str, "_SweepJob"] = {}
_SWEEP_JOB_HISTORY = 5
_SWEEP_POLL_SECONDS = 0.1
# Hosts abort long tool calls, so no request waits longer than this by default.
_DEFAULT_WAIT_SECONDS = 45.0
_MAX_WAIT_SECONDS = 600.0


class _SweepJob:
    """Mutable state for one pipeline run shared by a worker thread and tool calls."""

    def __init__(
        self,
        profile_path: Optional[str],
        deduplicate: bool,
        include_seen: bool,
        debug_log: Optional[str],
        timestamp: Optional[str] = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self.profile_path = profile_path
        self.deduplicate = deduplicate
        self.include_seen = include_seen
        self.debug_log = debug_log
        self.timestamp = timestamp
        self.status = "running"
        self.result: Optional[dict] = None
        self.error: Optional[str] = None
        self.progress = {"step": 0, "total": 0, "label": "Starting"}
        self.started_at = time.monotonic()
        self.finished_at: Optional[float] = None
        self._updates: "queue.Queue[tuple]" = queue.Queue()

    def record_progress(self, current: int, total: int, label: str) -> None:
        self._updates.put((current, total, label))

    def drain_progress(self) -> List[tuple]:
        updates = []
        while True:
            try:
                updates.append(self._updates.get_nowait())
            except queue.Empty:
                return updates

    @property
    def elapsed_seconds(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.monotonic()
        return round(end - self.started_at, 1)


def _prune_sweep_jobs() -> None:
    finished = [job for job in _SWEEP_JOBS.values() if job.status != "running"]
    finished.sort(key=lambda job: job.finished_at or 0.0)
    for job in finished[: max(0, len(finished) - _SWEEP_JOB_HISTORY)]:
        _SWEEP_JOBS.pop(job.id, None)


def _apply_sweep_result(job: "_SweepJob") -> None:
    """Adopt a finished job's cards as the live session so later tools see them."""
    global _session, _session_profile, _session_dir, _last_history, _session_playbook
    global _session_stem
    results = job.result or {}
    _session = SweepSession()
    _session.set_many(results.get("cards", []) or [])
    _session_profile = results.get("profile", {}) or {}
    _session_dir = results.get("output_dir")
    _session_stem = results.get("profile_stem")
    # A new sweep replaces every card, so the previous strategy text no longer applies.
    _session_playbook = ""
    scope = results.get("history_scope")
    if scope:
        _last_history = {
            "scope": scope,
            "config": dict((results.get("profile") or {}).get("history") or {}),
        }
    _persist_session(_session_dir)


def _run_sweep_job(job: "_SweepJob") -> None:
    """Worker-thread body: run the pipeline and publish its outcome on the job."""
    try:
        with _quiet_stdout():
            job.result = run_sweep_pipeline(
                profile_path=job.profile_path,
                verbose=True,
                progress=job.record_progress,
                deduplicate=job.deduplicate,
                include_seen=job.include_seen,
                execution_method="mcp",
                timestamp=job.timestamp,
            )
        # Adopt the cards before announcing completion so a waiting tool call
        # never reads an empty session.
        _apply_sweep_result(job)
        job.status = "completed"
        log.info("MCP run_sweep completed (job=%s)", job.id)
    except _EXPECTED as exc:
        job.error = str(exc)
        job.status = "failed"
        log.warning("%s: %s", type(exc).__name__, exc)
    except BaseException as exc:  # a broken sweep must not strand the job
        job.error = str(exc)
        job.status = "failed"
        log.exception("run_sweep job %s failed", job.id)
    finally:
        job.finished_at = time.monotonic()


def _start_sweep_job(
    profile_path: Optional[str],
    deduplicate: bool,
    include_seen: bool,
    debug_log: Optional[str],
    timestamp: Optional[str] = None,
) -> "_SweepJob":
    for job in _SWEEP_JOBS.values():
        if (
            job.status == "running"
            and job.profile_path == profile_path
            and job.deduplicate == deduplicate
            and job.include_seen == include_seen
            and job.timestamp == timestamp
        ):
            log.info("Reusing running sweep job %s", job.id)
            return job
    job = _SweepJob(profile_path, deduplicate, include_seen, debug_log, timestamp)
    _SWEEP_JOBS[job.id] = job
    _prune_sweep_jobs()
    log.info("MCP run_sweep started (job=%s, profile=%s, debug_log=%s)",
             job.id, profile_path or "default profile", debug_log)
    threading.Thread(
        target=_run_sweep_job, args=(job,), name=f"sweepy-{job.id}", daemon=True
    ).start()
    return job


async def _await_sweep_job(job: "_SweepJob", wait_seconds: float, ctx: Context) -> None:
    """Wait at most ``wait_seconds`` for the job, forwarding progress notifications."""
    deadline = time.monotonic() + max(0.0, float(wait_seconds))
    while True:
        for step, total, label in job.drain_progress():
            job.progress = {"step": step, "total": total, "label": label}
            if ctx is not None:
                try:
                    await ctx.report_progress(float(step), float(total), label)
                except Exception:  # progress is advisory only
                    log.debug("Progress notification failed", exc_info=True)
        if job.status != "running":
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        await asyncio.sleep(min(_SWEEP_POLL_SECONDS, remaining))


def _clamp_wait(wait_seconds) -> float:
    """Bound a tool-call wait so no request outlives the client's timeout.

    ``SWEEPY_MCP_WAIT_SECONDS`` lowers the ceiling for hosts with tighter limits.
    """
    try:
        value = _DEFAULT_WAIT_SECONDS if wait_seconds is None else float(wait_seconds)
    except (TypeError, ValueError):
        value = _DEFAULT_WAIT_SECONDS
    ceiling = _MAX_WAIT_SECONDS
    configured = os.environ.get("SWEEPY_MCP_WAIT_SECONDS", "").strip()
    if configured:
        try:
            parsed = float(configured)
        except ValueError:
            parsed = 0.0
        if parsed > 0:
            ceiling = min(ceiling, parsed)
    return max(0.0, min(value, ceiling))


def _latest_sweep_job() -> Optional["_SweepJob"]:
    running = [job for job in _SWEEP_JOBS.values() if job.status == "running"]
    if running:
        return max(running, key=lambda job: job.started_at)
    if not _SWEEP_JOBS:
        return None
    return max(
        _SWEEP_JOBS.values(),
        key=lambda job: job.finished_at if job.finished_at is not None else job.started_at,
    )


def _sweep_payload(job: "_SweepJob") -> str:
    """Render a job as the run_sweep status payload for any wait duration."""
    if job.status == "failed":
        return _err(job.error or "The sweep failed.", job_id=job.id, sweep_status="failed")
    if job.status == "running":
        return _ok(
            sweep_status="running",
            job_id=job.id,
            progress=job.progress,
            elapsed_seconds=job.elapsed_seconds,
            debug_log=job.debug_log,
            message=(
                "The sweep is still running. Call get_sweep_status to wait for it, "
                "then continue with get_jobs."
            ),
        )
    results = job.result or {}
    previously_seen = results.get("previously_seen_count") or 0
    message = results.get("message")
    if not message and previously_seen and not results.get("active_count"):
        message = (
            f"No new postings since the last sweep ({previously_seen} already reported). "
            "Call run_sweep with include_seen=true to review them."
        )
    cards = _sorted_cards()
    mode = _assessment_mode(_session_profile)
    return _ok(
        sweep_status="completed",
        job_id=job.id,
        discovered_count=results.get("discovered_count"),
        new_count=results.get("new_count"),
        previously_seen_count=previously_seen,
        active_count=results.get("active_count"),
        top_match=results.get("top_match"),
        reports=results.get("reports"),
        debug_log=job.debug_log,
        top_roles=results.get("top_roles", [])[:5],
        job_ids=[c["id"] for c in cards],
        card_count=len(results.get("cards", []) or []),
        assessed_count=len(cards) - len(_unassessed(cards)),
        # Boards that return no body leave these cards unreadable until the caller
        # fetches them; report the count so the assessment step can plan for it.
        needs_description_count=sum(1 for c in cards if _needs_description(c)),
        assessment_mode=mode,
        assessment_required=mode == "agent" or _judgments_required(),
        skipped_sources=results.get("skipped_sources", []),
        elapsed_seconds=job.elapsed_seconds,
        message=message,
        **_portfolio_payload(),
    )


def _ok(**fields) -> str:
    payload = {"status": "ok"}
    payload.update(fields)
    return json.dumps(payload, default=str)


def _err(message: str, **fields) -> str:
    payload = {"status": "error", "message": message}
    payload.update(fields)
    return json.dumps(payload, default=str)


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def create_profile(
    name: str,
    titles: List[str],
    location: str,
    resume_path: str,
    remote_only: bool = False,
    include_hybrid: bool = True,
    min_salary: int = 0,
    must_have_skills: Optional[List[str]] = None,
    synonyms: Optional[list] = None,
    platforms: Optional[dict] = None,
    sources_config: Optional[dict] = None,
    cache_config: Optional[dict] = None,
    orchestrator_config: Optional[dict] = None,
    history_config: Optional[dict] = None,
    resume_tracks: Optional[List[dict]] = None,
    portfolios: Optional[List[dict]] = None,
    pieces_per_card: Optional[int] = None,
    job_tracking: bool = True,
    assessment: str = "agent",
    output_filename: Optional[str] = None
) -> str:
    """
    Creates or updates a Sweepy search profile YAML file.

    Ask the user for a portfolio before you call this tool, then pass it as ``portfolios``.
    A candidate who targets more than one role family usually keeps one resume and one
    portfolio per track, so pass ``resume_tracks`` too and name the track on each portfolio
    entry.

    Args:
        name: Full name of the candidate.
        titles: List of target job titles (e.g. ['Technical Writer', 'UX Writer']).
        location: Target location (e.g. 'New York, NY').
        resume_path: Absolute or relative path to the candidate's PDF or DOCX resume.
        remote_only: True to restrict to 100% remote positions.
        include_hybrid: True to include hybrid positions (default True).
        min_salary: Minimum target annual base salary (0 if unconstrained).
        must_have_skills: Optional list of required skill keywords to boost matching.
        synonyms: Optional list of interchangeable-term groups, such as
            [['docs-as-code', 'documentation as code']]. Matching then treats every
            member of a group as equivalent in both directions.
        platforms: Optional dictionary configuring platforms to sweep.
        sources_config: Optional dictionary merged into the profile's ``sources`` block,
            such as {"enabled": ["jobspy", "openroles"], "openroles": {"companies": ["figma"]}}.
            Every enabled engine passes validation before the file is written.
        cache_config: Optional cache settings: ``enabled`` and ``ttl_seconds``.
        orchestrator_config: Optional orchestration settings: ``timeout_per_source_seconds``
            and ``circuit_breaker`` with ``failure_threshold`` and ``cooldown_seconds``.
        history_config: Optional cross-run settings: ``enabled``, ``retention_days``
            (default 4), ``match`` (``url`` or ``url+role``), and ``path`` (default
            ``~/.sweepy/history.db``). Controls whether a sweep skips postings the user
            already received.
        resume_tracks: Optional list of resume tracks, each with ``name``, an optional
            ``path`` to that track's PDF or DOCX, an optional ``color``, and optional
            ``route_keywords``. Sweepy routes each posting to the best track.
        portfolios: Optional list of portfolios, each with an optional ``track`` naming
            the resume track it belongs to, an optional ``url`` for an online portfolio, an
            optional ``path`` to a local PDF, DOCX, Markdown, text, or HTML file, and an
            optional ``pieces`` list of ``{title, url, tags}``. An entry without ``track``
            serves every track. Sweepy lists each portfolio's pieces on the cards, and the
            report names the pieces the agent chooses.
        pieces_per_card: How many portfolio pieces a card lists (1-10, default 3).
        job_tracking: True (default) appends job-tracking columns to the CSV export
            (``date_applied``, ``status``, ``interview_stage``, ``offer_amount``,
            ``offer_date``, ``follow_up_date``, ``contact``, ``notes``) and carries
            earlier values forward into later sweeps.
        assessment: ``agent`` (default) makes render_report refuse keyword-only cards
            until the agent submits judgments. ``keyword`` keeps keyword-overlap
            reports available for callers that want them.
        output_filename: Optional custom YAML path (defaults to profiles/{name}_{title}.yaml).

    Returns:
        JSON string with the saved profile path, the resume documents the profile points
        at, the portfolio state, and, when the candidate gave no portfolio, a prompt
        asking how to collect one.
    """
    try:
        if not name or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not titles:
            raise ValueError("titles must be a non-empty list")

        _validate_runtime_config(cache_config, orchestrator_config, history_config)

        assessment_value = str(assessment or "").strip().lower()
        if assessment_value not in _ASSESSMENT_MODES:
            raise ValueError(
                "assessment must be 'agent' or 'keyword': " + repr(assessment)
            )

        resolved_resume = _resolve_read_path(resume_path, must_exist=True)
        if not resolved_resume.lower().endswith((".pdf", ".docx")):
            raise ValueError(
                f"resume_path must point to a .pdf or .docx file: {resume_path!r}"
            )

        tracks = _normalize_resume_tracks(resume_tracks)
        portfolio_block = _normalize_portfolio_block(
            portfolios, [track["name"] for track in tracks], pieces_per_card
        )

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
            "report": {"assessment": assessment_value},
            "export": {
                "format": "pdf,csv,json",
                "output_dir": "results",
                "tracking": bool(job_tracking),
            },
        }
        if tracks:
            profile_data["resume"]["tracks"] = tracks
        if portfolio_block["sources"]:
            profile_data["portfolio"] = portfolio_block
        if synonyms:
            profile_data["resume"]["synonyms"] = synonyms
        if cache_config is not None:
            profile_data["cache"] = dict(cache_config)
        if orchestrator_config is not None:
            profile_data["orchestrator"] = dict(orchestrator_config)
        if history_config is not None:
            profile_data["history"] = dict(history_config)
        engine_notes = {}
        if sources_config:
            profile_data["sources"] = dict(sources_config)
            runtime = normalize_sources(profile_data)
            errors = validate_sources(
                {engine: runtime["engines"][engine] for engine in runtime["enabled"]}
            )
            if errors:
                raise ValueError("Invalid sources_config: " + "; ".join(errors))
        else:
            profile_data["sources"], engine_notes = _default_mcp_sources_config()
            runtime = normalize_sources(profile_data)

        target_path = (
            _safe_output_path(output_filename)
            if output_filename
            else _safe_output_path(_default_profile_path(profile_data))
        )
        with _quiet_stdout():
            saved_path = save_profile(profile_data, target_path)
        return _ok(
            profile_path=saved_path,
            enabled_engines=runtime["enabled"],
            engines_not_enabled=engine_notes,
            resume_tracks=[track["name"] for track in tracks],
            **_resume_payload(profile_data, include_text=False),
            **_portfolio_payload(profile_data),
        )
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("create_profile failed")
        return _err(str(exc))


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def set_portfolio(
    profile_path: str,
    portfolios: Optional[List[dict]] = None,
    replace: bool = False,
    pieces_per_card: Optional[int] = None,
) -> str:
    """
    Adds or updates the portfolios a saved profile submits.

    Call this after the user names a portfolio. Accept an online URL, a local PDF, DOCX,
    Markdown, text, or HTML file, or a list of pieces they want to use. One entry per
    resume track keeps a separate portfolio for each track. Sweepy reads each portfolio
    once per sweep and lists its pieces on the cards, so the agent can choose the pieces
    that fit a role and pass them to submit_judgments as ``portfolio_highlight``.

    Args:
        profile_path: Path to an existing profile YAML file.
        portfolios: List of entries, each with an optional ``track`` naming a resume track,
            an optional ``url``, an optional ``path`` to a local file, and an optional
            ``pieces`` list of ``{title, url, tags}``. An entry without ``track`` serves
            every track. Pass an empty list with ``replace`` to remove every portfolio.
        replace: True drops the saved portfolios before adding these. False keeps the
            saved entries whose track no new entry names.
        pieces_per_card: How many portfolio pieces a card lists (1-10). Leave unset to
            keep the saved value, which defaults to 3.

    Returns:
        JSON string with the profile path, the resume tracks the profile defines, and the
        portfolio state.
    """
    try:
        profile_file = _resolve_read_path(profile_path, must_exist=True)
        target = _safe_output_path(profile_file)
        with _quiet_stdout():
            profile = load_config(profile_file)

        tracks = [
            str(track.get("name") or "")
            for track in (profile.get("resume") or {}).get("tracks") or []
            if str(track.get("name") or "").strip()
        ]

        prior = profile.get("portfolio")
        prior = prior if isinstance(prior, dict) else {}
        if portfolios is None and pieces_per_card is None:
            raise ValueError("Provide portfolios, pieces_per_card, or both.")
        if pieces_per_card is None:
            pieces_per_card = prior.get("pieces_per_card")

        sources = [] if replace else [
            dict(entry) for entry in (prior.get("sources") or []) if isinstance(entry, dict)
        ]
        incoming = list(portfolios or [])
        if not replace:
            named = {
                str(entry.get("track") or "").strip().lower()
                for entry in incoming
                if isinstance(entry, dict)
            }
            sources = [
                entry
                for entry in sources
                if str(entry.get("track") or "").strip().lower() not in named
            ]

        block = _normalize_portfolio_block(sources + incoming, tracks, pieces_per_card)
        if block["sources"]:
            profile["portfolio"] = block
        else:
            profile.pop("portfolio", None)

        with _quiet_stdout():
            save_profile(profile, target)
        return _ok(
            profile_path=target,
            resume_tracks=tracks,
            **_portfolio_payload(profile),
        )
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("set_portfolio failed")
        return _err(str(exc))


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
))
async def run_sweep(
    profile_path: Optional[str] = None,
    ctx: Context = None,
    deduplicate: bool = True,
    include_seen: bool = False,
    wait_seconds: int = 45,
    timestamp: Optional[str] = None,
) -> str:
    """
    Executes a 5-stage job sweep pipeline using a specified profile or the default profile.

    This produces deterministic keyword-overlap scores; it does not invoke LLM judgment.
    For a normal job-search request, continue with get_jobs, assess the roles against the
    candidate's resume and available job evidence, submit_judgments for each assessed
    role, and render_report. Stop after this tool only when the user asks for keyword-only
    results or the available evidence does not support responsible LLM assessment.

    Treat the results as a useful but non-exhaustive candidate set. Inspect
    skipped_sources and report failures. A URL check blocked by rate limiting or
    bot protection does not prove a posting is dead. When search tools are available,
    verify promising listings against employer or ATS pages and add verified omissions
    with import_jobs; never invent postings or claim exhaustive coverage.

    A live sweep takes minutes, so it runs in the background. This tool waits at most
    `wait_seconds`, which keeps the request inside the client's tool timeout. When the
    sweep needs longer it returns `sweep_status: "running"` with a `job_id`; call
    get_sweep_status until it reports `sweep_status: "completed"`. The sweep keeps going
    even if the client disconnects.

    By default the sweep reports only postings the user has not received before.
    Postings recorded in an earlier sweep stay hidden for the profile's
    `history.retention_days` (4 by default). When every discovered posting is a
    repeat, the payload reports `previously_seen_count` and no new cards.

    Args:
        profile_path: Optional path to the profile YAML. If omitted, uses the last saved
            profile, then the first conventional profile on disk.
        deduplicate: Remove repeated URLs and matching postings from different boards for this run. Defaults to True.
        include_seen: Report previously seen postings too, refreshing their history. Defaults to False.
        wait_seconds: Longest time to block before returning progress (default 45, clamped to 0..600).
            Hosts with tighter limits can set `SWEEPY_MCP_WAIT_SECONDS` to lower the cap.
        timestamp: The user's local time for the report filenames, as `YYYY-MM-DD-HHMMSS`
            or ISO 8601 (`2026-10-27T23:55:10`). Pass the clock you already know from the
            conversation so artifacts carry the user's date and time instead of the
            server's. Leave it empty to use the profile's `export.timezone`.

    Returns:
        JSON string reporting `sweep_status`, plus the active role count, the number of
        new and previously seen postings, top matches, generated report paths, and the
        debug log path once the sweep completes.
    """
    try:
        resolved = _resolve_read_path(profile_path, must_exist=True) if profile_path else None
        stamp = normalize_stamp(timestamp)
        debug_log = enable_debug_logging()
        job = _start_sweep_job(
            resolved, bool(deduplicate), bool(include_seen), debug_log, stamp
        )
        await _await_sweep_job(job, _clamp_wait(wait_seconds), ctx)
        return _sweep_payload(job)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("run_sweep failed")
        return _err(str(exc))


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
))
async def get_sweep_status(
    job_id: Optional[str] = None,
    wait_seconds: int = 45,
    ctx: Context = None,
) -> str:
    """
    Reports or waits on a sweep started by run_sweep.

    Call this when run_sweep returned `sweep_status: "running"`. Repeat it until it
    returns `sweep_status: "completed"`, then inspect the roles with get_jobs. Each call
    blocks for at most `wait_seconds`, so no single request outlives the client timeout.

    Args:
        job_id: Job id from run_sweep. Defaults to the most recent sweep job.
        wait_seconds: Longest time to block before returning progress (default 45, clamped to 0..600).

    Returns:
        JSON string with `sweep_status` and, once the sweep finishes, the same summary
        fields run_sweep reports.
    """
    try:
        job = _SWEEP_JOBS.get(job_id) if job_id else _latest_sweep_job()
        if job is None:
            if job_id:
                return _err(f"Unknown sweep job {job_id!r}. Start one with run_sweep.")
            return _err("No sweep job found. Start one with run_sweep.")
        await _await_sweep_job(job, _clamp_wait(wait_seconds), ctx)
        return _sweep_payload(job)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("get_sweep_status failed")
        return _err(str(exc))


def _history_config_for_stem(profile_stem: str) -> dict:
    """Read a profile's history settings from profiles/, when the file exists."""
    for suffix in (".yaml", ".yml"):
        candidate = _resolve_read_path(
            os.path.join("profiles", f"{profile_stem}{suffix}"), must_exist=False
        )
        if os.path.exists(candidate):
            return normalize_sources(load_config(candidate)).get("history") or {}
    return {}


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def clear_history(
    profile_path: Optional[str] = None,
    profile_stem: Optional[str] = None,
) -> str:
    """
    Forgets the postings Sweepy already reported so the next sweep can report them again.

    Histories are per profile. Pass `profile_path` or `profile_stem` to clear a specific
    profile, or call with neither after a sweep to clear the profile that sweep used.

    Args:
        profile_path: Optional path to the profile YAML.
        profile_stem: Optional profile identifier, such as 'pedro_writer'.

    Returns:
        JSON string with the cleared scope, the number of forgotten postings, and how
        many remain.
    """
    try:
        if profile_path:
            resolved = _resolve_read_path(profile_path, must_exist=True)
            scope = history_scope(os.path.splitext(os.path.basename(resolved))[0])
            config = normalize_sources(load_config(resolved)).get("history") or {}
        elif profile_stem:
            scope = history_scope(profile_stem)
            config = _history_config_for_stem(profile_stem)
        else:
            scope = _last_history.get("scope")
            config = dict(_last_history.get("config") or {})
            if not scope:
                return _err(
                    "No sweep history is loaded. Pass profile_path or profile_stem."
                )

        store = SweepHistory(
            path=config.get("path"),
            retention_days=config.get(
                "retention_days", DEFAULT_HISTORY["retention_days"]
            ),
            match=config.get("match", DEFAULT_HISTORY["match"]),
        )
        cleared = store.clear(scope)
        return _ok(scope=scope, cleared=cleared, remaining=store.stats(scope)["count"])
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("clear_history failed")
        return _err(str(exc))


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
))
def get_results(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    limit: int = 10,
) -> str:
    """
    Retrieves the latest sweep results and report artifacts. Scores labeled KEYWORD
    OVERLAP are deterministic first-pass scores, not LLM-assessed matches. For a normal
    job-search request, use get_jobs and submit LLM judgments before presenting results.

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


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def export_report(
    json_source: Optional[str] = None,
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    formats: Optional[List[str]] = None,
    candidate_name: str = "Job Seeker",
    output_dir: Optional[str] = None,
    job_tracking: Optional[bool] = None,
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
        job_tracking: Add the job-tracking columns to a CSV export and carry earlier values
            forward. Leave unset to follow the profile's ``export.tracking`` setting.

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

        if _judgments_required():
            blocked = _assessment_error(roles, "export_report")
            if blocked:
                return blocked

        base_name = os.path.splitext(source_json)[0]
        if output_dir is not None:
            target_dir = _safe_output_path(output_dir)
        else:
            target_dir = os.path.dirname(source_json)
        os.makedirs(target_dir, exist_ok=True)
        stem = os.path.basename(base_name)
        base_out = os.path.join(target_dir, stem)

        tracking_stem = profile_stem or _profile_stem_from_result(stem)
        tracking = (
            job_tracking
            if job_tracking is not None
            else _profile_tracking_setting(tracking_stem)
        )

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
                # Do not exclude ``csv_path``: a re-export overwrites the same file, so
                # its current contents are the newest tracking edits to keep.
                previous = (
                    load_previous(os.path.dirname(source_json), tracking_stem)
                    if tracking
                    else None
                )
                with _quiet_stdout():
                    num_rows, num_cols = export_to_csv(
                        roles, csv_path, tracking=tracking, previous=previous
                    )
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


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def convert_docx(
    docx_path: str,
    pdf_path: Optional[str] = None,
) -> str:
    """
    Converts a DOCX file to PDF.

    Uses python-docx + reportlab first, falling back to Microsoft Word via
    docx2pdf when Word is installed. A blank pdf_path saves the PDF next to the
    DOCX. The output path must stay inside the workspace sandbox unless
    SWEEPY_ALLOW_EXTERNAL_WRITES is set. Use convert_document when the file may
    not be a DOCX; it handles .doc, .txt, .md, and .pdf as well.

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


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def convert_document(
    document_path: str,
    pdf_path: Optional[str] = None,
) -> str:
    """
    Converts a supported document to PDF.

    Accepts `.docx`, `.doc`, `.txt`, `.md`, and `.pdf`. DOCX files rebuild clean
    text through python-docx and reportlab, then fall back to Microsoft Word via
    docx2pdf. Legacy `.doc` files need Microsoft Word. Plain text and Markdown
    render with headings and bullets. A `.pdf` source passes through unchanged.
    A blank pdf_path saves the PDF next to the source file. The output path must
    stay inside the workspace sandbox unless SWEEPY_ALLOW_EXTERNAL_WRITES is set.

    Args:
        document_path: Absolute or relative path to the file to convert.
        pdf_path: Optional output PDF path. Defaults to the source directory.

    Returns:
        JSON string with the resolved output PDF path.
    """
    try:
        source = _resolve_read_path(document_path, must_exist=True)
        target = _safe_output_path(pdf_path or os.path.splitext(source)[0] + ".pdf")
        with _quiet_stdout():
            out_path = convert_to_pdf(source, target)
        return _ok(pdf_path=os.path.realpath(out_path), source_path=source)
    except (*_EXPECTED, RuntimeError) as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("convert_document failed")
        return _err(str(exc))


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
))
def get_jobs(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    limit: Optional[int] = None,
    needs_description: Optional[bool] = None,
) -> str:
    """
    Returns the card records held in the current sweep session, ranked by deterministic
    keyword overlap or submitted match score. For a normal job-search request, inspect
    the available evidence and assess relevant cards against the candidate's resume;
    then submit an independent LLM judgment for each assessed card. A judgment states
    both the highlight that favors the candidate and the obstacle that works against
    them, so no card reads as a one-sided pitch.

    Some boards (Built In, Google Jobs, Apple) return a title and URL with no posting
    body. Those cards carry ``needs_description: true``, score low on overlap because a
    title cannot state requirements, and sort last. Fetch such a posting yourself, then
    pass its text as ``description`` to ``submit_judgments`` along with your match. Call
    ``get_jobs`` with ``needs_description=True`` to list them on their own. That is the
    supported way to judge a role the sweep could not read.

    Each card also carries ``portfolio_url``, ``portfolio_path``, ``portfolio_pieces``,
    and ``portfolio_highlight``. ``portfolio_pieces`` comes from the portfolio for the
    card's resume track. Choose the pieces that fit the posting and pass them to
    ``submit_judgments`` as ``portfolio_highlight``.

    The payload also carries ``resume_documents``: the parsed text of each resume file,
    with the tracks that use it. Judge from that text, never from the profile's
    ``must_have_skills`` or ``synonyms``, which only feed the deterministic keyword pass.
    Read the document the way a recruiter does, including transferable skills, scope,
    seniority, domain, and the outcome behind each bullet. Then score it the way the
    posting's applicant tracking system parses it: evidence in a standard Experience or
    Skills section counts, while the same term inside a table, header, footer, image, or
    two-column sidebar may never reach a person and weighs less. ``resume_guidance``
    restates these rules.

    Args:
        profile_stem: Optional profile identifier to load a persisted session from disk.
        results_dir: Results directory holding report_session.json (default 'results').
        limit: Optional number of cards to return (None returns all).
        needs_description: Optional filter. ``True`` returns only cards whose posting body
            is missing, ``False`` only cards that carry one, and ``None`` returns both.

    Returns:
        JSON string with the list of card records, the resume documents for the profile,
        the portfolio setup, and guidance for the portfolio step. When a sweep is still
        running, the payload also reports `sweep_status`, `running_job_id`, and its
        progress, because the cards predate that sweep.
    """
    try:
        _resolve_session(results_dir, profile_stem)
        cards = _sorted_cards()
        total = len(cards)
        missing = sum(1 for card in cards if _needs_description(card))
        if needs_description is not None:
            wanted = bool(needs_description)
            cards = [card for card in cards if _needs_description(card) is wanted]
        if limit is not None:
            cards = cards[: max(1, int(limit))]
        portfolio = _portfolio_payload()
        resume = _resume_payload()
        counts = {"count": len(cards), "session_count": total, "needs_description_count": missing}
        running = [job for job in _SWEEP_JOBS.values() if job.status == "running"]
        if running:
            # These cards predate the sweep in flight; say so rather than letting
            # the caller present stale matches.
            newest = max(running, key=lambda job: job.started_at)
            return _ok(
                **counts,
                jobs=cards,
                **resume,
                sweep_status="running",
                running_job_id=newest.id,
                progress=newest.progress,
                message="A sweep is still running. Call get_sweep_status before using these cards.",
                **portfolio,
            )
        return _ok(**counts, jobs=cards, **resume, **portfolio)
    except _EXPECTED as exc:
        log.warning("%s: %s", type(exc).__name__, exc)
        return _err(str(exc))
    except Exception as exc:
        log.exception("get_jobs failed")
        return _err(str(exc))


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def submit_judgments(
    job_id: Optional[str] = None,
    match_pct: Optional[int] = None,
    portfolio_fit: Optional[int] = None,
    resume_track: Optional[str] = None,
    resume_color: Optional[str] = None,
    domain: Optional[str] = None,
    summary: Optional[str] = None,
    requirements: Optional[str] = None,
    alignment: Optional[str] = None,
    concerns: Optional[str] = None,
    has_extended_response: Optional[bool] = None,
    app_format: Optional[str] = None,
    comp: Optional[str] = None,
    benefits: Optional[str] = None,
    page_theme: Optional[str] = None,
    portfolio_highlight: Optional[str] = None,
    description: Optional[str] = None,
    judgments: Optional[List[dict]] = None,
) -> str:
    """
    Overrides a job's deterministic card fields with LLM-supplied judgments.

    Supplying match_pct upgrades the match label provenance to "match"; otherwise the
    deterministic keyword-overlap value is retained. Only non-null fields are merged.
    Assess the candidate-to-role fit from the resume and available job evidence. Do not
    copy the deterministic overlap score into match_pct or invent unsupported details.
    In the standard job-search workflow, submit judgments for all roles you assessed.

    Judge the resume file, not the profile. ``get_jobs`` returns ``resume_documents``
    with the parsed text of every track; read that text before scoring, because the
    profile's ``must_have_skills`` and ``synonyms`` only feed the deterministic keyword
    pass. Weigh the evidence a recruiter weighs, including transferable skills that do
    not repeat the posting's wording, scope, seniority, domain, and outcomes. Then score
    the document the way the posting's applicant tracking system parses it: a term a
    parser reads inside a standard Experience or Skills section counts, while the same
    term inside a table, header, footer, image, or two-column sidebar may never reach a
    person and weighs less. Match the tracker to the apply URL when it is visible
    (Workday, Greenhouse, Lever, Ashby, iCIMS, Taleo, Workable, SmartRecruiters) and name
    in ``concerns`` what that parser would lose, such as text set inside a graphic.

    Every assessed card carries both sides of the case. ``alignment`` holds the
    highlight: the strongest evidence that the candidate fits, plus the move that uses
    it. ``concerns`` holds what works against the candidate: unmet requirements,
    seniority or tenure gaps, domain mismatches, on-site expectations, or pay below the
    floor. Name the specific obstacle and cite the posting text. Write "None identified"
    only when the posting states no real obstacle.

    Pass ``judgments`` to assess many roles in one call. Each entry needs a ``job_id``
    plus any of the single-card fields, which keeps a 24-role assessment to one request.

    Args:
        job_id: Stable job id (from run_sweep or get_jobs).
        match_pct: Optional LLM match percentage (0-100), scored against the parsed
            resume text and the ATS read described above. Leave unset when the evidence
            supports only keyword overlap.
        resume_track, resume_color, domain, summary, requirements, alignment,
        concerns, has_extended_response, app_format, comp, benefits, page_theme:
            Optional overrides.
        portfolio_fit: How well the track's portfolio covers what the posting asks
            for, as a 0-100 score. Report it beside ``match_pct`` so the résumé case
            and the sample case stay separate and auditable. Leave unset when the
            card has no portfolio.
        portfolio_highlight: The portfolio pieces to send with this application, named in
            plain text. Read ``portfolio_pieces`` from the card and name the one to three
            pieces that match the posting. Leave unset when the card has no portfolio or
            the posting asks for none.
        description: The posting body you read from the card's URL, for a card the sweep
            could not read (``needs_description: true``). Supplying it clears the flag and
            gives the report real requirement text to print. Pass ``summary`` and
            ``requirements`` too when you want those rows to match what you read.
        judgments: Optional list of judgment objects, each with a ``job_id`` key. Do not
            combine with the single-card fields.

    Returns:
        JSON string with the merged card, or with ``applied`` and ``jobs`` for a batch.
    """
    try:
        if judgments is not None:
            if job_id is not None:
                return _err("Pass either job_id or judgments, not both.")
            return _submit_judgment_batch(judgments)

        if not job_id:
            return _err("Provide job_id or a judgments list.")

        fields: dict = {}
        if match_pct is not None:
            fields["match_value"] = int(match_pct)
            fields["match_kind"] = "match"
        for key, value in {
            "resume_track": resume_track,
            "resume_color": resume_color,
            "portfolio_fit": portfolio_fit,
            "domain": domain,
            "summary": summary,
            "requirements": requirements,
            "alignment": alignment,
            "concerns": concerns,
            "has_extended_response": has_extended_response,
            "app_format": app_format,
            "comp": comp,
            "benefits": benefits,
            "page_theme": page_theme,
            "portfolio_highlight": portfolio_highlight,
            "description": description,
        }.items():
            if value is not None:
                fields[key] = value

        if "description" in fields and str(fields["description"]).strip():
            fields["needs_description"] = False

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


def _submit_judgment_batch(judgments: List[dict]) -> str:
    """Apply a list of judgments, reporting any entry that cannot be stored."""
    applied = []
    rejected = []
    for entry in judgments:
        if not isinstance(entry, dict):
            rejected.append({"job_id": None, "reason": "entry is not an object"})
            continue
        target = entry.get("job_id") or entry.get("id")
        if not target:
            rejected.append({"job_id": None, "reason": "missing job_id"})
            continue
        fields = {k: v for k, v in entry.items() if k not in ("job_id", "id") and v is not None}
        if "match_pct" in fields:
            fields["match_value"] = int(fields.pop("match_pct"))
            fields["match_kind"] = "match"
        if "description" in fields and str(fields["description"]).strip():
            fields["needs_description"] = False
        try:
            applied.append(_session.apply_judgments(target, **fields))
        except KeyError:
            rejected.append({"job_id": target, "reason": "no job with that id in the session"})

    if applied:
        _persist_session(_session_dir)
    return _ok(applied=len(applied), jobs=applied, rejected=rejected)


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=True,
))
def import_jobs(
    jobs_json: str,
    validate: bool = False,
) -> str:
    """
    Appends agent-found jobs (canonical card schema) into the current session.

    Use this to add roles that independent research found and verified but Sweepy missed.
    Confirm each posting from an employer or ATS source when possible, avoid duplicates,
    and do not invent missing fields. URLs skip validation by default; pass validate=True
    for an additional check. A rate limit or bot-protection response is treated as
    unverified, not as proof that the posting is dead.

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


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
))
def render_report(
    profile_stem: Optional[str] = None,
    results_dir: str = "results",
    output_filename: Optional[str] = None,
    playbook: str = "",
    timestamp: Optional[str] = None,
) -> str:
    """
    Renders the cards PDF from the current session and writes it through the sandbox.
    In the standard LLM-assisted workflow, call this after submitting judgments so the
    report reflects assessed matches instead of only deterministic keyword overlap.
    Cards show the portfolio for their resume track. A card with a submitted
    ``portfolio_highlight`` names the pieces to send, and a card without one lists the
    pieces Sweepy found.

    Args:
        profile_stem: Optional profile identifier to load a persisted session from disk.
        results_dir: Results directory (default 'results').
        output_filename: Optional explicit output PDF path (must stay inside the workspace).
            When omitted, Sweepy writes ``{profile_stem}_mcp_{YYYY-MM-DD-HHMMSS}.pdf``
            into the results directory, mirroring the CLI's dated report names with an
            ``mcp`` marker.
        playbook: Optional plain-text strategy note. Ampersands, angle brackets, and
            newlines are handled as text, and ``**bold**`` adds emphasis. The text is
            saved with the session, so a later render keeps it. When empty, Sweepy
            reuses the saved playbook, then falls back to a generated one.
        timestamp: The user's local time for the default filename, as
            ``YYYY-MM-DD-HHMMSS`` or ISO 8601. Pass the clock you know from the
            conversation so the report carries the user's date and time.

    Returns:
        JSON string with the output path, page count, and the playbook it used.
    """
    global _session_playbook
    try:
        _resolve_session(results_dir, profile_stem)
        cards = _sorted_cards()
        if not cards:
            return _err("No jobs in the session to render.")

        if _assessment_mode(_session_profile) == "agent" or _judgments_required():
            blocked = _assessment_error(_report_cards(cards, _session_profile), "render_report")
            if blocked:
                return blocked

        profile = _session_profile or {"name": "Job Seeker"}
        if playbook.strip():
            _session_playbook = playbook
        elif _session_playbook:
            playbook = _session_playbook

        if output_filename:
            pdf_path = _safe_output_path(output_filename)
        else:
            base_dir = _session_dir or _resolve_read_path(results_dir, must_exist=True)
            stem = profile_stem or _session_stem or "report"
            stamp = normalize_stamp(timestamp)
            pdf_path = _safe_output_path(
                os.path.join(base_dir, f"{result_stem(stem, 'mcp', timestamp=stamp)}.pdf")
            )

        os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
        with _quiet_stdout():
            pages = build_report(cards, pdf_path, profile, playbook=playbook)

        _persist_session(_session_dir)
        return _ok(
            pdf_report=os.path.realpath(pdf_path),
            pages=pages,
            card_count=len(cards),
            playbook_saved=bool(_session_playbook),
        )
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
