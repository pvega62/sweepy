import asyncio
import json
import os

import pytest
import yaml

import server


def test_every_tool_declares_complete_behavior_annotations():
    expected = {
        "create_profile": (False, True, True, False),
        "run_sweep": (False, True, False, True),
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


@pytest.fixture
def reset_session(monkeypatch):
    monkeypatch.setattr(server, "_session", server.SweepSession())
    monkeypatch.setattr(server, "_session_profile", {})
    monkeypatch.setattr(server, "_session_dir", None)


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
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    out = server.create_profile(name="Alice", titles=["Writer"], location="NYC", resume_path=str(pdf))
    data = json.loads(out)
    assert data["status"] == "ok"
    assert os.path.exists(data["profile_path"])


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
