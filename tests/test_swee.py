import os
import sys
import time

import pytest
import yaml

import swee


def _profile(output_dir):
    return {
        "name": "Test",
        "search": {
            "titles": ["Writer"],
            "location": "NYC",
            "remote_only": False,
            "include_hybrid": True,
            "min_salary": 0,
        },
        "resume": {"path": "", "must_have_skills": [], "keywords_weight": 1.0},
        "platforms": {"greenhouse": True},
        "export": {"format": "json", "output_dir": output_dir},
    }


def _mock_engine(monkeypatch, jobs):
    scored = jobs
    monkeypatch.setattr(swee, "discover_jobs", lambda *a, **k: (list(jobs), {"Greenhouse": len(jobs)}))
    monkeypatch.setattr(swee, "discover_sources", lambda *a, **k: ([], {}))
    monkeypatch.setattr(swee, "filter_valid_jobs", lambda *a, **k: (list(jobs), 0))
    monkeypatch.setattr(swee, "score_jobs", lambda *a, **k: (scored, ["python"]))
    monkeypatch.setattr(swee, "enrich_jobs", lambda jobs, cfg: jobs)
    monkeypatch.setattr(swee, "build_report", lambda *a, **k: 1)
    monkeypatch.setattr(swee, "build_pdf", lambda *a, **k: 1)
    monkeypatch.setattr(swee, "export_to_csv", lambda *a, **k: (len(jobs), 5))
    monkeypatch.setattr(swee, "export_to_json", lambda *a, **k: None)
    monkeypatch.setattr(swee, "export_to_png", lambda *a, **k: [])


def _jobs(n=2):
    return [
        {"title": f"T{i}", "company": "C", "location": "L", "match_score": 90 - i, "url": f"u{i}", "playbook": "p"}
        for i in range(n)
    ]


def test_pipeline_forwards_profile_synonyms_to_scorer(tmp_path, monkeypatch):
    captured = {}

    def fake_score_jobs(
        jobs,
        resume_path,
        must_have_skills,
        keywords_weight=1.0,
        progress=None,
        synonyms=None,
    ):
        captured["synonyms"] = synonyms
        return jobs, ["python"]

    _mock_engine(monkeypatch, _jobs())
    monkeypatch.setattr(swee, "score_jobs", fake_score_jobs)

    profile = _profile(str(tmp_path))
    profile["resume"]["synonyms"] = [["docs-as-code", "documentation as code"]]
    swee.run_sweep_pipeline(profile_dict=profile)

    assert captured["synonyms"]["docs-as-code"] == ("documentation as code",)


def test_pipeline_fires_progress_monotonically(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs())
    calls = []

    def progress(cur, tot, label):
        calls.append((cur, tot, label))

    swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)), progress=progress)

    assert len(calls) >= 5
    currents = [c[0] for c in calls]
    assert currents == sorted(currents)


def test_pipeline_include_roles_flag(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(2))

    default_result = swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)))
    assert default_result["roles"] == []
    assert len(default_result["top_roles"]) == 2

    full_result = swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)), include_roles=True)
    assert len(full_result["roles"]) == 2


def test_pipeline_empty_jobs_returns_well_shaped_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(swee, "discover_jobs", lambda *a, **k: ([], {"Greenhouse": 0}))
    monkeypatch.setattr(swee, "discover_sources", lambda *a, **k: ([], {}))
    result = swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)))
    assert result["status"] == "completed"
    assert result["discovered_count"] == 0
    assert result["roles"] == []
    assert result["top_roles"] == []
    assert result["reports"] == {}


def test_pipeline_no_valid_jobs(tmp_path, monkeypatch):
    jobs = _jobs(1)
    monkeypatch.setattr(swee, "discover_jobs", lambda *a, **k: (list(jobs), {"Greenhouse": 1}))
    monkeypatch.setattr(swee, "discover_sources", lambda *a, **k: ([], {}))
    monkeypatch.setattr(swee, "filter_valid_jobs", lambda *a, **k: ([], 1))
    result = swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)))
    assert result["status"] == "completed"
    assert result["active_count"] == 0
    assert result["top_roles"] == []


def test_pipeline_all_formats(tmp_path, monkeypatch):
    jobs = _jobs(2)
    _mock_engine(monkeypatch, jobs)
    profile = _profile(str(tmp_path))
    profile["export"]["format"] = "pdf,csv,json"
    result = swee.run_sweep_pipeline(profile_dict=profile)
    assert set(result["reports"].keys()) == {"pdf", "csv", "json"}


def test_pipeline_uses_track_scoring_when_tracks_defined(tmp_path, monkeypatch):
    jobs = _jobs(2)
    _mock_engine(monkeypatch, jobs)
    calls = []

    def fake_score_jobs(*a, **k):
        calls.append("single")
        return (jobs, ["python"])

    def fake_score_jobs_by_track(*a, **k):
        calls.append("track")
        return (jobs, ["python"])

    monkeypatch.setattr(swee, "score_jobs", fake_score_jobs)
    monkeypatch.setattr(swee, "score_jobs_by_track", fake_score_jobs_by_track)

    profile = _profile(str(tmp_path))
    profile["resume"]["tracks"] = [{"name": "Tech", "color": "#111111", "route_keywords": ["python"]}]
    swee.run_sweep_pipeline(profile_dict=profile)
    assert calls == ["track"]


def test_pipeline_uses_single_scoring_without_tracks(tmp_path, monkeypatch):
    jobs = _jobs(2)
    _mock_engine(monkeypatch, jobs)
    calls = []

    def fake_score_jobs(*a, **k):
        calls.append("single")
        return (jobs, ["python"])

    def fake_score_jobs_by_track(*a, **k):
        calls.append("track")
        return (jobs, ["python"])

    monkeypatch.setattr(swee, "score_jobs", fake_score_jobs)
    monkeypatch.setattr(swee, "score_jobs_by_track", fake_score_jobs_by_track)

    swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)))
    assert calls == ["single"]


def test_pipeline_png_format(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(2))
    monkeypatch.setattr(swee, "export_to_png", lambda *a, **k: ["card.png"])
    profile = _profile(str(tmp_path))
    profile["export"]["format"] = "png"
    result = swee.run_sweep_pipeline(profile_dict=profile)
    assert result["reports"]["png"] == ["card.png"]
    assert "pdf" in result["reports"]


def test_pipeline_with_profile_path(tmp_path, monkeypatch):
    profile = {
        "name": "Pathy",
        "search": {"titles": ["Writer"], "location": "NYC", "remote_only": False, "include_hybrid": True, "min_salary": 0},
        "resume": {"path": "", "must_have_skills": [], "keywords_weight": 1.0},
        "platforms": {"greenhouse": True},
        "export": {"format": "json", "output_dir": str(tmp_path)},
    }
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(profile))

    jobs = _jobs(1)
    monkeypatch.setattr(swee, "discover_jobs", lambda *a, **k: (list(jobs), {"Greenhouse": 1}))
    monkeypatch.setattr(swee, "discover_sources", lambda *a, **k: ([], {}))
    monkeypatch.setattr(swee, "filter_valid_jobs", lambda *a, **k: (list(jobs), 0))
    monkeypatch.setattr(swee, "score_jobs", lambda *a, **k: (jobs, ["python"]))

    result = swee.run_sweep_pipeline(profile_path=str(path))
    assert result["status"] == "completed"
    assert result["active_count"] == 1


def test_pipeline_produces_timestamped_distinct_filenames(tmp_path, monkeypatch):
    jobs = _jobs(1)
    monkeypatch.setattr(swee, "discover_jobs", lambda *a, **k: (list(jobs), {"Greenhouse": 1}))
    monkeypatch.setattr(swee, "discover_sources", lambda *a, **k: ([], {}))
    monkeypatch.setattr(swee, "filter_valid_jobs", lambda *a, **k: (list(jobs), 0))
    monkeypatch.setattr(swee, "score_jobs", lambda *a, **k: (jobs, ["python"]))

    first = swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)))
    time.sleep(1.1)
    second = swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)))

    assert first["reports"]["json"] != second["reports"]["json"]
    assert os.path.exists(first["reports"]["json"])
    assert os.path.exists(second["reports"]["json"])


def test_get_dependency_versions_missing(monkeypatch):
    def fake_version(pkg):
        if pkg == "pymupdf":
            raise swee.PackageNotFoundError(pkg)
        return "9.9.9"

    monkeypatch.setattr(swee, "_dist_version", fake_version)
    out = swee.get_dependency_versions()
    assert "pymupdf MISSING" in out


def test_main_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--version"])
    with pytest.raises(SystemExit) as exc:
        swee.main()
    assert exc.value.code == 0
    assert "Sweepy v" in capsys.readouterr().out


def test_main_without_args_opens_wizard(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swee.py"])
    opened = []
    monkeypatch.setattr(swee, "run_wizard", lambda profile_path=None, **kwargs: opened.append(profile_path))
    monkeypatch.setattr(swee, "run_sweep_pipeline", lambda **k: pytest.fail("pipeline ran"))

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert opened == [None]


def test_open_wizard_hands_the_run_callback_to_the_menu(monkeypatch):
    seen = {}

    def fake_wizard(profile_path=None, run_sweep=None):
        seen["profile_path"] = profile_path
        seen["run_sweep"] = run_sweep
        return None

    monkeypatch.setattr(swee, "run_wizard", fake_wizard)

    swee._open_wizard("profiles/alex.yaml")

    assert seen["profile_path"] == "profiles/alex.yaml"
    assert seen["run_sweep"] is swee._run_wizard_sweep


def test_wizard_sweep_runs_the_pipeline_and_records_the_profile(monkeypatch):
    profile = {"name": "Alex"}
    captured = {}

    def fake_pipeline(profile_path=None, profile_dict=None, **kwargs):
        captured["profile_dict"] = profile_dict
        return {"status": "completed"}

    recorded = []
    monkeypatch.setattr(swee, "run_sweep_pipeline", fake_pipeline)
    monkeypatch.setattr(swee, "record_last_profile", recorded.append)

    swee._run_wizard_sweep(profile, "profiles/alex.yaml")

    assert captured["profile_dict"] is profile
    assert recorded == ["profiles/alex.yaml"]


def test_wizard_sweep_reports_errors_without_losing_the_profile(monkeypatch, capsys):
    def failing_pipeline(**kwargs):
        raise FileNotFoundError("resume.pdf not found")

    monkeypatch.setattr(swee, "run_sweep_pipeline", failing_pipeline)
    monkeypatch.setattr(swee, "record_last_profile", lambda path: pytest.fail("profile recorded"))

    swee._run_wizard_sweep({"name": "Alex"}, "profiles/alex.yaml")

    assert "Error: resume.pdf not found" in capsys.readouterr().out


def test_main_run_uses_last_profile(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--run"])
    monkeypatch.setattr(swee, "last_profile_path", lambda: "profiles/last.yaml")
    captured = {}

    def fake_pipeline(profile_path=None, **kwargs):
        captured["profile_path"] = profile_path
        return {"status": "completed"}

    recorded = []
    monkeypatch.setattr(swee, "run_sweep_pipeline", fake_pipeline)
    monkeypatch.setattr(swee, "record_last_profile", recorded.append)

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert captured["profile_path"] == "profiles/last.yaml"
    assert recorded == ["profiles/last.yaml"]
    assert "Using the last saved profile" in capsys.readouterr().out


def test_main_run_without_any_profile_errors(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--run"])
    monkeypatch.setattr(swee, "last_profile_path", lambda: None)
    monkeypatch.setattr(swee, "_default_profile_path", lambda: None)
    monkeypatch.setattr(swee, "run_sweep_pipeline", lambda **k: pytest.fail("pipeline ran"))

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 1
    assert "no saved profile found" in capsys.readouterr().out


def test_main_convert_saves_pdf_next_to_source(monkeypatch, capsys):
    called = []

    def fake_convert(path):
        called.append(path)
        return os.path.join(os.path.dirname(path), "resume.pdf")

    monkeypatch.setattr(swee, "convert_to_pdf", fake_convert)
    monkeypatch.setattr(sys, "argv", ["swee.py", "--convert", "resume.md"])

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert called == [os.path.realpath("resume.md")]
    assert "PDF saved:" in capsys.readouterr().out


def test_main_convert_writes_pdf_next_to_markdown(tmp_path, monkeypatch, capsys):
    source = tmp_path / "resume.md"
    source.write_text("# Alex Rivera\n\n- Westlaw\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["swee.py", "--convert", str(source)])

    with pytest.raises(SystemExit) as exc:
        swee.main()

    expected = os.path.realpath(str(tmp_path / "resume.pdf"))
    assert exc.value.code == 0
    assert os.path.exists(expected)
    assert f"PDF saved: {expected}" in capsys.readouterr().out


def test_main_convert_unsupported_file_exits(tmp_path, monkeypatch, capsys):
    source = tmp_path / "image.png"
    source.write_bytes(b"\x89PNG")
    monkeypatch.setattr(sys, "argv", ["swee.py", "--convert", str(source)])

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 1
    assert "Unsupported file type" in capsys.readouterr().out


def test_main_convert_missing_file_exits(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--convert", str(tmp_path / "gone.docx")])

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 1
    assert "File not found" in capsys.readouterr().out
