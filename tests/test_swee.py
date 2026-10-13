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


def _jobs(n=2):
    return [
        {"title": f"T{i}", "company": "C", "location": "L", "match_score": 90 - i, "url": f"u{i}", "playbook": "p"}
        for i in range(n)
    ]


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
