import asyncio
import csv
import json
import os
import threading

import pytest
import yaml

import server
from engine.sweep_config import normalize_sources


def test_every_tool_declares_complete_behavior_annotations():
    expected = {
        "create_profile": (False, True, True, False),
        "set_portfolio": (False, True, True, False),
        "run_sweep": (False, True, False, True),
        "get_sweep_status": (False, False, True, False),
        "clear_history": (False, True, True, False),
        "get_results": (True, False, True, False),
        "export_report": (False, True, True, False),
        "convert_docx": (False, True, True, False),
        "convert_document": (False, True, True, False),
        "get_jobs": (False, False, True, False),
        "submit_judgments": (False, True, True, False),
        "import_jobs": (False, True, True, True),
        "render_report": (False, True, True, False),
    }
    hint_names = (
        "readOnlyHint",
        "destructiveHint",
        "idempotentHint",
        "openWorldHint",
    )

    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    assert set(tools) == set(expected)

    for name, expected_hints in expected.items():
        annotations = tools[name].annotations
        assert annotations is not None
        actual_hints = tuple(getattr(annotations, hint) for hint in hint_names)
        assert actual_hints == expected_hints
        assert all(type(hint) is bool for hint in actual_hints)


def test_create_profile_exposes_current_engine_settings():
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    properties = tools["create_profile"].inputSchema["properties"]

    assert {
        "sources_config",
        "cache_config",
        "orchestrator_config",
        "history_config",
    } <= set(properties)


@pytest.fixture
def reset_session(monkeypatch):
    monkeypatch.setattr(server, "_session", server.SweepSession())
    monkeypatch.setattr(server, "_session_profile", {})
    monkeypatch.setattr(server, "_session_dir", None)
    monkeypatch.setattr(server, "_session_playbook", "")
    monkeypatch.setattr(server, "_SWEEP_JOBS", {})
    monkeypatch.setattr(server, "_last_history", {"scope": None, "config": {}})
    monkeypatch.setattr(server, "enable_debug_logging", lambda: "test-debug.log")


def _card():
    return {
        "id": "abc123",
        "rank": 1,
        "title": "Technical Writer",
        "company": "Modal",
        "platform": "Ashby",
        "url": "https://jobs.ashbyhq.com/modal/1",
        "location": "Remote - US",
        "match_value": 87,
        "match_kind": "overlap",
        "resume_track": "Tech Writer Resume",
        "resume_color": "#1D4ED8",
        "has_extended_response": False,
        "app_format": "Standard Application (Resume upload).",
        "domain": "Cloud",
        "summary": "S",
        "requirements": "R",
        "alignment": "A",
        "concerns": "C",
        "comp": "$100K",
        "benefits": "Not disclosed",
        "page": 0,
        "page_theme": "",
    }



def test_safe_output_path_rejects_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    with pytest.raises(ValueError):
        server._safe_output_path("../../etc/passwd")


def test_safe_output_path_under_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    assert server._safe_output_path("results/foo.pdf") == os.path.join(str(tmp_path), "results", "foo.pdf")


def test_safe_output_path_rejects_absolute_outside(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    outside = str(tmp_path.parent / "outside.pdf")
    with pytest.raises(ValueError):
        server._safe_output_path(outside)


def test_safe_output_path_allows_external_with_escape_hatch(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SWEEPY_ALLOW_EXTERNAL_WRITES", "1")
    outside = str(tmp_path.parent / "outside.pdf")
    assert server._safe_output_path(outside) == os.path.realpath(outside)


def test_resolve_read_path_does_not_enforce_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    outside = tmp_path.parent / "resume.pdf"
    outside.write_bytes(b"x")
    assert server._resolve_read_path(str(outside)) == os.path.realpath(str(outside))


def test_create_profile_rejects_empty_name(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    out = server.create_profile(name=" ", titles=["Writer"], location="NYC", resume_path="r.pdf")
    data = json.loads(out)
    assert data["status"] == "error"


def test_create_profile_rejects_empty_titles(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    out = server.create_profile(name="Alice", titles=[], location="NYC", resume_path="r.pdf")
    assert json.loads(out)["status"] == "error"


def test_create_profile_rejects_non_pdf_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    txt = tmp_path / "resume.txt"
    txt.write_text("not a pdf")
    out = server.create_profile(name="Alice", titles=["Writer"], location="NYC", resume_path=str(txt))
    assert json.loads(out)["status"] == "error"


def test_create_profile_accepts_docx_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    docx = tmp_path / "resume.docx"
    docx.write_bytes(b"PK\x03\x04 fake")
    out = server.create_profile(name="Alice", titles=["Writer"], location="NYC", resume_path=str(docx))
    data = json.loads(out)
    assert data["status"] == "ok"
    assert os.path.exists(data["profile_path"])


def test_create_profile_success(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "engine_status",
        lambda name: {
            "name": name,
            "installed": name in {"hirehunt", "jobdrop"},
            "detail": f"{name} is not installed",
        },
    )
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    out = server.create_profile(name="Alice", titles=["Writer"], location="NYC", resume_path=str(pdf))
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["enabled_engines"] == ["jobspy", "ats", "hirehunt", "jobdrop"]
    assert "openroles" in data["engines_not_enabled"]
    assert "apify" in data["engines_not_enabled"]
    assert os.path.exists(data["profile_path"])
    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    assert saved["sources"]["enabled"] == data["enabled_engines"]


def test_create_profile_reports_uninstalled_optional_engines(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "engine_status",
        lambda name: {"name": name, "installed": False, "detail": f"Install {name}"},
    )
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    data = json.loads(
        server.create_profile(name="Alice", titles=["Writer"], location="NYC", resume_path=str(pdf))
    )

    assert data["status"] == "ok"
    assert data["enabled_engines"] == ["jobspy", "ats"]
    assert data["engines_not_enabled"]["hirehunt"] == "Install hirehunt"
    assert data["engines_not_enabled"]["jobdrop"] == "Install jobdrop"


def test_create_profile_writes_synonym_groups(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    groups = [["docs-as-code", "documentation as code"]]

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        synonyms=groups,
    )
    data = json.loads(out)

    assert data["status"] == "ok"
    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    assert saved["resume"]["synonyms"] == groups


def test_create_profile_writes_sources_config(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "engine_status",
        lambda name: (_ for _ in ()).throw(AssertionError("explicit config must be preserved")),
    )
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        sources_config={"enabled": ["jobspy", "openroles"], "openroles": {"companies": ["figma"]}},
    )
    data = json.loads(out)

    assert data["status"] == "ok"
    assert data["enabled_engines"] == ["jobspy", "openroles"]
    assert data["engines_not_enabled"] == {}
    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    assert saved["sources"]["enabled"] == ["jobspy", "openroles"]
    assert saved["sources"]["openroles"]["companies"] == ["figma"]


def test_create_profile_writes_engine_runtime_config(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        sources_config={"enabled": ["jobspy"], "jobspy": {"sites": ["indeed"]}},
        cache_config={"enabled": False, "ttl_seconds": 60},
        orchestrator_config={
            "timeout_per_source_seconds": 45,
            "circuit_breaker": {"failure_threshold": 2, "cooldown_seconds": 10},
        },
    )
    data = json.loads(out)

    assert data["status"] == "ok"
    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    runtime = normalize_sources(saved)
    assert runtime["enabled"] == ["jobspy"]
    assert runtime["engines"]["jobspy"]["sites"] == ["indeed"]
    assert runtime["cache"]["enabled"] is False
    assert runtime["cache"]["ttl_seconds"] == 60
    assert runtime["orchestrator"]["timeout_per_source_seconds"] == 45
    assert runtime["orchestrator"]["circuit_breaker"] == {
        "failure_threshold": 2,
        "cooldown_seconds": 10,
    }


def test_create_profile_writes_history_config(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        sources_config={"enabled": ["jobspy"], "jobspy": {"sites": ["indeed"]}},
        history_config={"retention_days": 10, "match": "url"},
    )
    data = json.loads(out)

    assert data["status"] == "ok"
    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    runtime = normalize_sources(saved)
    assert runtime["history"]["retention_days"] == 10
    assert runtime["history"]["match"] == "url"
    assert runtime["history"]["enabled"] is True


@pytest.mark.parametrize(
    ("history_config", "message"),
    [
        ({"retention_days": -1}, "retention_days must be a non-negative integer"),
        ({"match": "title"}, "match must be 'url' or 'url+role'"),
        ({"unknown": True}, "Unsupported history_config field"),
    ],
)
def test_create_profile_rejects_invalid_history_config(
    tmp_path, monkeypatch, history_config, message
):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        history_config=history_config,
    )

    assert json.loads(out)["status"] == "error"
    assert message in json.loads(out)["message"]


@pytest.mark.parametrize(
    ("cache_config", "orchestrator_config", "message"),
    [
        ({"ttl_seconds": -1}, None, "ttl_seconds must be a non-negative integer"),
        (None, {"timeout_per_source_seconds": 0}, "timeout_per_source_seconds must be a positive integer"),
        (None, {"circuit_breaker": {"failure_threshold": 0}}, "failure_threshold must be a positive integer"),
        ({"path": "outside.db"}, None, "Unsupported cache_config field"),
    ],
)
def test_create_profile_rejects_invalid_runtime_config(
    tmp_path, monkeypatch, cache_config, orchestrator_config, message
):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        cache_config=cache_config,
        orchestrator_config=orchestrator_config,
    )

    assert json.loads(out)["status"] == "error"
    assert message in json.loads(out)["message"]


def test_create_profile_rejects_invalid_sources_config(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        sources_config={"enabled": ["openroles"], "openroles": {"companies": []}},
    )
    assert json.loads(out)["status"] == "error"


def test_get_results_excludes_export_files(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    (results / "foo_2026-01-01.json").write_text(json.dumps([{"title": "A"}]))
    (results / "foo_2026-01-02_export.json").write_text(json.dumps([{"title": "B"}]))
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    out = server.get_results(profile_stem="foo", results_dir="results")
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["result_file"].endswith("foo_2026-01-01.json")


def test_get_results_clamps_limit(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    (results / "foo_2026-01-01.json").write_text(
        json.dumps([{"title": f"r{i}"} for i in range(200)])
    )
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    zero = json.loads(server.get_results(profile_stem="foo", results_dir="results", limit=0))
    assert len(zero["top_roles"]) == 1

    huge = json.loads(server.get_results(profile_stem="foo", results_dir="results", limit=1000))
    assert len(huge["top_roles"]) == 100


def test_every_return_has_status(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    calls = [
        server.create_profile(name="", titles=["x"], location="l", resume_path="r.pdf"),
        server.get_results(results_dir=str(tmp_path)),
    ]
    for out in calls:
        assert "status" in json.loads(out)


def _job():
    return {
        "title": "T",
        "company": "C",
        "location": "L",
        "match_score": 90,
        "badge": "Slate",
        "url": "https://example.com/job",
        "playbook": "p",
        "key_matches": ["python"],
        "missing_skills": [],
        "min_amount": 0,
        "max_amount": 0,
        "currency": "USD",
    }


def test_run_sweep_reports_progress(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    fake_result = {
        "status": "completed",
        "discovered_count": 1,
        "active_count": 1,
        "top_match": {"title": "T", "company": "C", "match_score": 90, "url": "u"},
        "reports": {},
        "top_roles": [_job()],
    }

    def fake_pipeline(**kwargs):
        progress = kwargs.get("progress")
        for i in range(1, 6):
            if progress:
                progress(i, 5, f"step {i}")
        return fake_result

    monkeypatch.setattr(server, "run_sweep_pipeline", fake_pipeline)

    class FakeCtx:
        def __init__(self):
            self.calls = []

        async def report_progress(self, progress, total=None, message=None):
            self.calls.append((progress, total, message))

    ctx = FakeCtx()
    out = asyncio.run(server.run_sweep(ctx=ctx))
    data = json.loads(out)

    assert data["status"] == "ok"
    assert data["active_count"] == 1
    assert len(ctx.calls) >= 5


def test_export_report_generates_all_formats(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    src = tmp_path / "foo_2026-01-01.json"
    src.write_text(json.dumps([_job()]))

    out = server.export_report(json_source=str(src), formats=["pdf", "csv", "json"])
    data = json.loads(out)

    assert data["status"] == "ok"
    assert os.path.exists(data["generated"]["pdf"])
    assert os.path.exists(data["generated"]["csv"])
    assert os.path.exists(data["generated"]["json"])


def test_export_report_generates_png(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    src = tmp_path / "foo_2026-01-01.json"
    src.write_text(json.dumps([_job()]))

    out = server.export_report(json_source=str(src), formats=["png"])
    data = json.loads(out)

    assert data["status"] == "ok"
    assert data["generated"]["png"]
    for png_path in data["generated"]["png"]:
        assert os.path.exists(png_path)
        assert png_path.endswith(".png")


def test_export_report_carries_tracking_values(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "foo.yaml").write_text(
        "name: Foo\nexport:\n  format: csv\n  tracking: true\n", encoding="utf-8"
    )
    src = tmp_path / "foo_2026-01-01-101010.json"
    src.write_text(json.dumps([_job()]))

    first = json.loads(server.export_report(json_source=str(src), formats=["csv"]))
    csv_path = first["generated"]["csv"]
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert "status" in rows[0]
    rows[0]["status"] = "Applied"
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    server.export_report(json_source=str(src), formats=["csv"])

    with open(csv_path, newline="", encoding="utf-8") as handle:
        carried = list(csv.DictReader(handle))
    assert carried[0]["status"] == "Applied"


def test_export_report_no_roles(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    src = tmp_path / "foo_2026-01-01.json"
    src.write_text(json.dumps([]))

    out = server.export_report(json_source=str(src), formats=["pdf"])
    assert json.loads(out)["status"] == "error"


def test_run_sweep_populates_session(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    fake_result = {
        "status": "completed",
        "discovered_count": 1,
        "active_count": 1,
        "top_match": {"title": "T", "company": "C", "match_score": 87, "url": "u"},
        "reports": {},
        "top_roles": [],
        "cards": [_card()],
        "output_dir": str(tmp_path),
        "profile": {"name": "Test"},
    }
    monkeypatch.setattr(server, "run_sweep_pipeline", lambda **kwargs: fake_result)

    out = asyncio.run(server.run_sweep(ctx=None))
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["job_ids"] == ["abc123"]
    assert data["card_count"] == 1


def test_run_sweep_reports_skipped_sources(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    fake_result = {
        "status": "completed",
        "discovered_count": 1,
        "active_count": 1,
        "top_match": None,
        "reports": {},
        "top_roles": [],
        "cards": [_card()],
        "output_dir": str(tmp_path),
        "profile": {"name": "Test"},
        "skipped_sources": [{"name": "jobdrop", "reason": "timeout"}],
    }
    monkeypatch.setattr(server, "run_sweep_pipeline", lambda **kwargs: fake_result)

    data = json.loads(asyncio.run(server.run_sweep(ctx=None)))
    assert data["skipped_sources"] == [{"name": "jobdrop", "reason": "timeout"}]


def test_run_sweep_defaults_skipped_sources_to_empty(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: {"status": "completed", "cards": [], "reports": {}},
    )
    data = json.loads(asyncio.run(server.run_sweep(ctx=None)))
    assert data["skipped_sources"] == []


def test_run_sweep_forwards_deduplicate_option(monkeypatch, tmp_path, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    captured = {}
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: captured.update(kwargs) or {"status": "completed", "cards": []},
    )

    asyncio.run(server.run_sweep(deduplicate=False, ctx=None))

    assert captured["deduplicate"] is False
    assert captured["execution_method"] == "mcp"


def test_run_sweep_forwards_include_seen_option(monkeypatch, tmp_path, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    captured = {}
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: captured.update(kwargs) or {"status": "completed", "cards": []},
    )

    asyncio.run(server.run_sweep(include_seen=True, ctx=None))

    assert captured["include_seen"] is True


def test_run_sweep_payload_reports_previously_seen(monkeypatch, tmp_path, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: {
            "status": "completed",
            "cards": [],
            "reports": {},
            "discovered_count": 5,
            "new_count": 0,
            "previously_seen_count": 5,
            "active_count": 0,
            "history_scope": "pedro",
            "profile": {"name": "Pedro", "history": {"retention_days": 4}},
        },
    )

    data = json.loads(asyncio.run(server.run_sweep(ctx=None)))

    assert data["previously_seen_count"] == 5
    assert data["new_count"] == 0
    assert "include_seen=true" in data["message"]


def test_clear_history_forgets_the_last_sweep_scope(tmp_path, monkeypatch, reset_session):
    from engine.history import SweepHistory

    db_path = str(tmp_path / "history.db")
    monkeypatch.setattr(
        server,
        "_last_history",
        {"scope": "pedro", "config": {"path": db_path}},
    )
    SweepHistory(path=db_path).record(
        [{"title": "T", "company": "C", "location": "L", "url": "https://x.example/1"}],
        "pedro",
    )

    data = json.loads(server.clear_history())

    assert data["status"] == "ok"
    assert data["scope"] == "pedro"
    assert data["cleared"] == 1
    assert data["remaining"] == 0


def test_clear_history_requires_a_known_scope(reset_session):
    data = json.loads(server.clear_history())

    assert data["status"] == "error"
    assert "profile_path" in data["message"]


def test_clear_history_reads_a_profile_file(tmp_path, monkeypatch, reset_session):
    from engine.history import SweepHistory

    db_path = str(tmp_path / "history.db").replace("\\", "/")
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "pedro_writer.yaml").write_text(
        "name: Pedro\n"
        "search:\n"
        "  titles: [Writer]\n"
        "  location: Remote\n"
        f"history:\n"
        f"  path: {db_path}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    SweepHistory(path=str(tmp_path / "history.db")).record(
        [{"title": "T", "company": "C", "location": "L", "url": "https://x.example/1"}],
        "pedro_writer",
    )

    data = json.loads(server.clear_history(profile_stem="pedro_writer"))

    assert data["status"] == "ok"
    assert data["scope"] == "pedro_writer"
    assert data["cleared"] == 1


def test_run_sweep_enables_debug_logging_and_returns_log_path(
    monkeypatch, tmp_path, reset_session, caplog
):
    debug_log = str(tmp_path / "sweepy_mcp.log")
    captured = {}
    monkeypatch.setattr(server, "enable_debug_logging", lambda: debug_log)
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: captured.update(kwargs)
        or {"status": "completed", "cards": [], "active_count": 0},
    )

    data = json.loads(asyncio.run(server.run_sweep(ctx=None)))

    assert captured["verbose"] is True
    assert data["debug_log"] == debug_log
    assert "MCP run_sweep started" in caplog.text
    assert "MCP run_sweep completed" in caplog.text


def test_run_sweep_returns_running_when_the_wait_budget_expires(
    tmp_path, monkeypatch, reset_session
):
    """A slow sweep must answer with a job id instead of blocking the client."""
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    release = threading.Event()
    fake_result = {
        "status": "completed",
        "active_count": 1,
        "cards": [_card()],
        "output_dir": str(tmp_path),
        "profile": {"name": "Test"},
    }

    def slow_pipeline(**kwargs):
        release.wait(5)
        return fake_result

    monkeypatch.setattr(server, "run_sweep_pipeline", slow_pipeline)

    first = json.loads(asyncio.run(server.run_sweep(ctx=None, wait_seconds=0)))
    assert first["status"] == "ok"
    assert first["sweep_status"] == "running"
    assert first["job_id"]
    assert "get_sweep_status" in first["message"]

    release.set()
    second = json.loads(
        asyncio.run(server.get_sweep_status(job_id=first["job_id"], wait_seconds=5))
    )
    assert second["status"] == "ok"
    assert second["sweep_status"] == "completed"
    assert second["card_count"] == 1
    assert second["job_ids"] == ["abc123"]


def test_get_sweep_status_defaults_to_the_latest_job(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: {"status": "completed", "cards": [_card()], "output_dir": str(tmp_path)},
    )

    started = json.loads(asyncio.run(server.run_sweep(ctx=None, wait_seconds=5)))
    assert started["sweep_status"] == "completed"

    data = json.loads(asyncio.run(server.get_sweep_status(wait_seconds=5)))
    assert data["job_id"] == started["job_id"]
    assert data["sweep_status"] == "completed"


def test_get_sweep_status_without_a_job_reports_an_error(reset_session):
    data = json.loads(asyncio.run(server.get_sweep_status(ctx=None)))
    assert data["status"] == "error"
    assert "run_sweep" in data["message"]

    unknown = json.loads(asyncio.run(server.get_sweep_status(job_id="missing", ctx=None)))
    assert unknown["status"] == "error"
    assert "missing" in unknown["message"]


def test_run_sweep_reuses_a_running_job(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    release = threading.Event()
    calls = []

    def slow_pipeline(**kwargs):
        calls.append(kwargs)
        release.wait(5)
        return {"status": "completed", "cards": [], "output_dir": str(tmp_path)}

    monkeypatch.setattr(server, "run_sweep_pipeline", slow_pipeline)

    first = json.loads(asyncio.run(server.run_sweep(ctx=None, wait_seconds=0)))
    second = json.loads(asyncio.run(server.run_sweep(ctx=None, wait_seconds=0)))

    release.set()
    assert first["job_id"] == second["job_id"]
    asyncio.run(server.get_sweep_status(job_id=first["job_id"], wait_seconds=5))
    assert len(calls) == 1


def test_run_sweep_surfaces_pipeline_failure(monkeypatch, tmp_path, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    def boom(**kwargs):
        raise ValueError("profile is unusable")

    monkeypatch.setattr(server, "run_sweep_pipeline", boom)

    data = json.loads(asyncio.run(server.run_sweep(ctx=None, wait_seconds=5)))
    assert data["status"] == "error"
    assert data["sweep_status"] == "failed"
    assert "profile is unusable" in data["message"]


def test_wait_budget_is_bounded_and_configurable(monkeypatch):
    assert server._clamp_wait(None) == 45.0
    assert server._clamp_wait(10) == 10.0
    assert server._clamp_wait(-5) == 0.0
    assert server._clamp_wait(10_000) == 600.0
    assert server._clamp_wait("nonsense") == 45.0

    monkeypatch.setenv("SWEEPY_MCP_WAIT_SECONDS", "15")
    assert server._clamp_wait(120) == 15.0
    assert server._clamp_wait(5) == 5.0

    monkeypatch.setenv("SWEEPY_MCP_WAIT_SECONDS", "0")
    assert server._clamp_wait(120) == 120.0


def test_run_sweep_progress_reaches_the_client(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    def pipeline(**kwargs):
        progress = kwargs["progress"]
        for step in range(1, 6):
            progress(step, 5, f"step {step}")
        return {"status": "completed", "cards": [], "output_dir": str(tmp_path)}

    monkeypatch.setattr(server, "run_sweep_pipeline", pipeline)

    calls = []

    class FakeCtx:
        async def report_progress(self, progress, total=None, message=None):
            calls.append((progress, total, message))

    asyncio.run(server.run_sweep(ctx=FakeCtx(), wait_seconds=5))

    assert [call[0] for call in calls] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert calls[-1][2] == "step 5"


def test_get_jobs_flags_a_running_sweep(tmp_path, monkeypatch, reset_session):
    """Cards from the previous sweep must not look current while one is in flight."""
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    server._session.upsert(_card())
    release = threading.Event()
    monkeypatch.setattr(
        server,
        "run_sweep_pipeline",
        lambda **kwargs: release.wait(5) or {"status": "completed", "cards": []},
    )

    started = json.loads(asyncio.run(server.run_sweep(ctx=None, wait_seconds=0)))
    assert started["sweep_status"] == "running"

    data = json.loads(server.get_jobs(results_dir=str(tmp_path)))
    release.set()
    assert data["sweep_status"] == "running"
    assert data["running_job_id"] == started["job_id"]
    assert "get_sweep_status" in data["message"]
    assert data["count"] == 1
    asyncio.run(server.get_sweep_status(job_id=started["job_id"], wait_seconds=5))


def test_get_jobs_omits_sweep_fields_when_idle(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.get_jobs(results_dir=str(tmp_path)))
    assert data["count"] == 1
    assert "running_job_id" not in data


def test_submit_judgments_and_get_jobs_roundtrip(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    server._session.upsert(_card())

    out = server.submit_judgments("abc123", match_pct=95, domain="Cloud Compute")
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["job"]["match_value"] == 95
    assert data["job"]["match_kind"] == "match"

    jobs = json.loads(server.get_jobs())
    assert jobs["jobs"][0]["match_value"] == 95
    assert jobs["jobs"][0]["match_kind"] == "match"
    assert jobs["jobs"][0]["domain"] == "Cloud Compute"


def test_render_report_shows_match_for_judged_job(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test"})
    server._session.upsert(_card())
    server.submit_judgments("abc123", match_pct=95)

    out = server.render_report(output_filename=str(tmp_path / "report.pdf"))
    data = json.loads(out)
    assert data["status"] == "ok"
    assert os.path.exists(data["pdf_report"])
    assert data["pages"] == 1

    import pymupdf

    doc = pymupdf.open(data["pdf_report"])
    text = doc[0].get_text()
    doc.close()
    assert "95% MATCH" in text


def test_import_jobs_appends(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    server._session.upsert(_card())

    new_job = _card()
    new_job["id"] = "xyz789"
    new_job["url"] = "https://jobs.ashbyhq.com/modal/2"
    out = server.import_jobs(json.dumps([new_job]))
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["imported"] == 1

    ids = [j["id"] for j in json.loads(server.get_jobs())["jobs"]]
    assert "xyz789" in ids


def test_import_jobs_rejects_invalid_json(reset_session):
    out = server.import_jobs("not json")
    assert json.loads(out)["status"] == "error"


def test_convert_document_writes_pdf_next_to_source(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    source = tmp_path / "notes.md"
    source.write_text("# Alex Rivera\n\n- Westlaw\n", encoding="utf-8")

    data = json.loads(server.convert_document(str(source)))

    expected = os.path.realpath(str(tmp_path / "notes.pdf"))
    assert data["status"] == "ok"
    assert data["pdf_path"] == expected
    assert os.path.exists(expected)


def test_convert_document_accepts_explicit_target(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    source = tmp_path / "notes.txt"
    source.write_text("Alex Rivera\n", encoding="utf-8")
    target = tmp_path / "out" / "notes.pdf"

    data = json.loads(server.convert_document(str(source), pdf_path=str(target)))

    assert data["status"] == "ok"
    assert data["pdf_path"] == os.path.realpath(str(target))
    assert target.exists()


def test_convert_document_rejects_unsupported_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    source = tmp_path / "image.png"
    source.write_bytes(b"\x89PNG")

    data = json.loads(server.convert_document(str(source)))

    assert data["status"] == "error"
    assert "Unsupported file type" in data["message"]


def test_convert_document_reports_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    data = json.loads(server.convert_document(str(tmp_path / "gone.docx")))

    assert data["status"] == "error"
    assert "File not found" in data["message"]


def test_create_profile_records_assessment_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        assessment="keyword",
    )
    data = json.loads(out)

    assert data["status"] == "ok"
    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    assert saved["report"]["assessment"] == "keyword"


def test_create_profile_defaults_to_agent_assessment(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(name="Alice", titles=["Writer"], location="NYC", resume_path=str(pdf))
    data = json.loads(out)

    with open(data["profile_path"], encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)
    assert saved["report"]["assessment"] == "agent"


def test_create_profile_rejects_unknown_assessment(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    out = server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(pdf),
        assessment="sometimes",
    )

    assert json.loads(out)["status"] == "error"


def test_assessment_mode_defaults_to_agent():
    assert server._assessment_mode({}) == "agent"
    assert server._assessment_mode({"report": {}}) == "agent"
    assert server._assessment_mode({"report": {"assessment": "KEYWORD"}}) == "keyword"


def test_assessment_mode_ignores_unknown_value(caplog):
    with caplog.at_level("WARNING", logger="sweepy.server"):
        assert server._assessment_mode({"report": {"assessment": "vibes"}}) == "agent"
    assert "unknown report.assessment" in caplog.text


def test_submit_judgments_accepts_batch(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    for suffix in ("a", "b"):
        card = _card()
        card["id"] = f"abc{suffix}"
        card["url"] = f"https://example.com/{suffix}"
        server._session.upsert(card)

    out = server.submit_judgments(
        judgments=[
            {"job_id": "abca", "match_pct": 91, "domain": "Docs"},
            {"job_id": "abcb", "match_value": 40, "alignment": "Tenure gap", "concerns": "Six years asked, four shown"},
        ]
    )
    data = json.loads(out)

    assert data["status"] == "ok"
    assert data["applied"] == 2
    assert data["rejected"] == []
    assert {job["id"]: job["match_value"] for job in data["jobs"]} == {"abca": 91, "abcb": 40}
    assert server._session.get("abca")["match_kind"] == "match"


def test_submit_judgments_stores_the_concern_beside_the_highlight(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.submit_judgments(
        "abc123",
        alignment="Lead with the docs-as-code pipeline.",
        concerns="Posting asks for 7 years; the resume shows 4.",
    ))

    assert data["status"] == "ok"
    assert data["job"]["alignment"] == "Lead with the docs-as-code pipeline."
    assert data["job"]["concerns"] == "Posting asks for 7 years; the resume shows 4."


def test_submit_judgments_stores_portfolio_fit_apart_from_match(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.submit_judgments(
        "abc123",
        match_pct=74,
        portfolio_fit=85,
    ))

    assert data["status"] == "ok"
    assert data["job"]["match_value"] == 74
    assert data["job"]["portfolio_fit"] == 85


def test_submit_judgments_batch_stores_portfolio_fit(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.submit_judgments(judgments=[
        {"job_id": "abc123", "match_pct": 61, "portfolio_fit": 40},
    ]))

    assert data["status"] == "ok"
    assert data["jobs"][0]["portfolio_fit"] == 40
    assert data["jobs"][0]["match_value"] == 61


def test_submit_judgments_batch_reports_unknown_ids(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.submit_judgments(judgments=[{"job_id": "nope", "match_pct": 50}]))

    assert data["applied"] == 0
    assert data["rejected"][0]["job_id"] == "nope"


def test_submit_judgments_rejects_mixed_calls(reset_session):
    data = json.loads(server.submit_judgments("abc123", match_pct=50, judgments=[]))
    assert data["status"] == "error"


def test_render_report_blocks_unassessed_cards_in_agent_mode(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test", "report": {"assessment": "agent"}})
    server._session.upsert(_card())

    data = json.loads(server.render_report(output_filename=str(tmp_path / "report.pdf")))

    assert data["status"] == "error"
    assert data["unassessed_job_ids"] == ["abc123"]
    assert "submit_judgments" in data["message"]
    assert not (tmp_path / "report.pdf").exists()


def test_render_report_allows_unassessed_cards_in_keyword_mode(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test", "report": {"assessment": "keyword"}})
    server._session.upsert(_card())

    data = json.loads(server.render_report(output_filename=str(tmp_path / "report.pdf")))

    assert data["status"] == "ok"
    assert data["card_count"] == 1


def test_require_judgments_env_blocks_keyword_mode(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test", "report": {"assessment": "keyword"}})
    monkeypatch.setenv("SWEEPY_REQUIRE_JUDGMENTS", "1")
    server._session.upsert(_card())

    data = json.loads(server.render_report(output_filename=str(tmp_path / "report.pdf")))

    assert data["status"] == "error"
    assert data["unassessed_count"] == 1


def test_require_judgments_env_blocks_export(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SWEEPY_REQUIRE_JUDGMENTS", "true")
    src = tmp_path / "foo_2026-01-01.json"
    src.write_text(json.dumps([_job()]))

    data = json.loads(server.export_report(json_source=str(src), formats=["csv"]))

    assert data["status"] == "error"
    assert "export_report needs an agent assessment" in data["message"]


def test_render_report_saves_playbook_with_the_session(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test", "report": {"assessment": "agent"}})
    server._session.upsert(_card())
    server.submit_judgments("abc123", match_pct=95)

    out = server.render_report(
        output_filename=str(tmp_path / "report.pdf"), playbook="R&D first"
    )
    assert json.loads(out)["playbook_saved"] is True

    with open(tmp_path / "report_session.json", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["playbook"] == "R&D first"


def test_render_report_reuses_saved_playbook(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test", "report": {"assessment": "agent"}})
    server._session.upsert(_card())
    server.submit_judgments("abc123", match_pct=95)
    server.render_report(output_filename=str(tmp_path / "report.pdf"), playbook="Keep this line")

    # A fresh process reloads the session from disk, where the playbook now lives.
    server._session_playbook = ""
    assert server._load_session(str(tmp_path)) is True
    assert server._session_playbook == "Keep this line"

    data = json.loads(server.render_report(output_filename=str(tmp_path / "again.pdf")))

    assert data["status"] == "ok"
    assert data["playbook_saved"] is True
    import pymupdf

    with pymupdf.open(data["pdf_report"]) as doc:
        assert "Keep this line" in doc[-1].get_text()


def test_new_sweep_result_clears_the_saved_playbook(monkeypatch, reset_session):
    monkeypatch.setattr(server, "_session_playbook", "stale strategy")
    job = server._SweepJob(None, True, False, None)
    job.result = {"cards": [_card()], "profile": {"name": "Test"}, "output_dir": None}

    server._apply_sweep_result(job)

    assert server._session_playbook == ""


def _profile_with_portfolio(tmp_path, monkeypatch, portfolio_text="# Case Study A\n## Case Study B\n"):
    """Save a profile with one resume track and one portfolio, then return its path."""
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    portfolio = tmp_path / "portfolio.md"
    portfolio.write_text(portfolio_text, encoding="utf-8")

    data = json.loads(server.create_profile(
        name="Alice",
        titles=["UX Writer"],
        location="NYC",
        resume_path=str(pdf),
        resume_tracks=[
            {"name": "UX Writer", "path": str(pdf), "color": "navy", "route_keywords": ["ux"]}
        ],
        portfolios=[{"track": "UX Writer", "path": str(portfolio)}],
        pieces_per_card=2,
        sources_config={"enabled": []},
    ))
    assert data["status"] == "ok"
    return data["profile_path"], portfolio


def test_create_profile_writes_resume_tracks_and_portfolio(tmp_path, monkeypatch):
    path, portfolio = _profile_with_portfolio(tmp_path, monkeypatch)

    with open(path, encoding="utf-8") as handle:
        saved = yaml.safe_load(handle)

    assert saved["resume"]["tracks"][0]["name"] == "UX Writer"
    assert saved["resume"]["tracks"][0]["color"] == "navy"
    assert saved["portfolio"]["pieces_per_card"] == 2
    assert saved["portfolio"]["sources"] == [
        {"track": "UX Writer", "path": str(portfolio)}
    ]


def test_create_profile_reports_the_portfolio_state(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    data = json.loads(server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(_resume_file(tmp_path)),
        portfolios=[{"url": "https://example.com/work"}],
        sources_config={"enabled": []},
    ))

    assert data["status"] == "ok"
    assert data["portfolio_configured"] is True
    assert data["portfolio_sources"] == [
        {"track": "", "url": "https://example.com/work", "path": "", "pieces_declared": 0}
    ]
    assert "submit_judgments" in data["portfolio_guidance"]


def test_create_profile_asks_for_a_portfolio_when_none_is_given(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    data = json.loads(server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(_resume_file(tmp_path)),
        sources_config={"enabled": []},
    ))

    assert data["portfolio_configured"] is False
    assert "set_portfolio" in data["portfolio_guidance"]
    assert "portfolio" not in yaml.safe_load(open(data["profile_path"], encoding="utf-8"))


def _resume_file(tmp_path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    return path


def test_create_profile_rejects_a_portfolio_track_without_tracks(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    data = json.loads(server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(_resume_file(tmp_path)),
        portfolios=[{"track": "UX Writer", "url": "https://example.com/work"}],
        sources_config={"enabled": []},
    ))

    assert data["status"] == "error"
    assert "matches no resume track" in data["message"]


def test_create_profile_rejects_a_missing_portfolio_file(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    data = json.loads(server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(_resume_file(tmp_path)),
        portfolios=[{"path": str(tmp_path / "gone.pdf")}],
        sources_config={"enabled": []},
    ))

    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_create_profile_rejects_duplicate_resume_track_names(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    data = json.loads(server.create_profile(
        name="Alice",
        titles=["Writer"],
        location="NYC",
        resume_path=str(_resume_file(tmp_path)),
        resume_tracks=[{"name": "Writer"}, {"name": "writer"}],
        sources_config={"enabled": []},
    ))

    assert data["status"] == "error"
    assert "repeats an earlier track" in data["message"]


def test_set_portfolio_merges_a_new_track_entry(tmp_path, monkeypatch):
    path, portfolio = _profile_with_portfolio(tmp_path, monkeypatch)

    data = json.loads(server.set_portfolio(
        path, portfolios=[{"url": "https://example.com/all"}]
    ))

    assert data["status"] == "ok"
    assert [(source["track"], source["url"]) for source in data["portfolio_sources"]] == [
        ("UX Writer", ""),
        ("", "https://example.com/all"),
    ]
    saved = yaml.safe_load(open(path, encoding="utf-8"))
    assert saved["portfolio"]["sources"][0]["path"] == str(portfolio)


def test_set_portfolio_replaces_every_source(tmp_path, monkeypatch):
    path, _ = _profile_with_portfolio(tmp_path, monkeypatch)

    data = json.loads(server.set_portfolio(
        path,
        portfolios=[{"track": "UX Writer", "url": "https://example.com/ux"}],
        replace=True,
    ))

    assert data["status"] == "ok"
    assert data["portfolio_sources"] == [
        {"track": "UX Writer", "url": "https://example.com/ux", "path": "", "pieces_declared": 0}
    ]


def test_set_portfolio_removes_every_source(tmp_path, monkeypatch):
    path, _ = _profile_with_portfolio(tmp_path, monkeypatch)

    data = json.loads(server.set_portfolio(path, portfolios=[], replace=True))

    assert data["status"] == "ok"
    assert data["portfolio_configured"] is False
    assert "portfolio" not in yaml.safe_load(open(path, encoding="utf-8"))


def test_set_portfolio_needs_input(tmp_path, monkeypatch):
    path, _ = _profile_with_portfolio(tmp_path, monkeypatch)

    data = json.loads(server.set_portfolio(path))

    assert data["status"] == "error"
    assert "Provide portfolios" in data["message"]


def test_set_portfolio_reports_an_unknown_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))

    data = json.loads(server.set_portfolio(str(tmp_path / "nope.yaml"), portfolios=[]))

    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_get_jobs_reports_the_portfolio_setup(tmp_path, monkeypatch, reset_session):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        server,
        "_session_profile",
        {"name": "Test", "portfolio": {"sources": [{"url": "https://example.com/work"}]}},
    )
    server._session.upsert(_card())

    data = json.loads(server.get_jobs(results_dir=str(tmp_path)))

    assert data["portfolio_configured"] is True
    assert data["portfolio_sources"][0]["url"] == "https://example.com/work"
    assert "portfolio_highlight" in data["portfolio_guidance"]


def test_get_jobs_asks_for_a_portfolio_when_none_is_configured(
    tmp_path, monkeypatch, reset_session
):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_profile", {"name": "Test"})
    server._session.upsert(_card())

    data = json.loads(server.get_jobs(results_dir=str(tmp_path)))

    assert data["portfolio_configured"] is False
    assert "set_portfolio" in data["portfolio_guidance"]


def test_submit_judgments_stores_the_portfolio_highlight(
    tmp_path, monkeypatch, reset_session
):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.submit_judgments(
        "abc123",
        match_pct=91,
        portfolio_highlight="API Reference Rebuild and the Docs-as-Code migration",
    ))

    assert data["status"] == "ok"
    assert data["job"]["portfolio_highlight"] == (
        "API Reference Rebuild and the Docs-as-Code migration"
    )


def test_submit_judgments_batch_accepts_portfolio_highlights(
    tmp_path, monkeypatch, reset_session
):
    monkeypatch.setattr(server, "_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server, "_session_dir", str(tmp_path))
    server._session.upsert(_card())

    data = json.loads(server.submit_judgments(
        judgments=[{"job_id": "abc123", "portfolio_highlight": "Case Study A"}]
    ))

    assert data["applied"] == 1
    assert data["jobs"][0]["portfolio_highlight"] == "Case Study A"
