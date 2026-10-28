import csv
import datetime
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


def test_pipeline_logs_execution_method(tmp_path, monkeypatch, caplog):
    _mock_engine(monkeypatch, _jobs(1))
    caplog.set_level("INFO", logger="sweepy")

    swee.run_sweep_pipeline(
        profile_dict=_profile(str(tmp_path)),
        execution_method="mcp",
    )

    assert "Execution method: mcp" in caplog.text


def test_pipeline_enables_profile_debug_logging_when_not_verbose(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs())
    profile = _profile(str(tmp_path))
    profile["debug"] = True
    enabled = []
    monkeypatch.setattr(swee, "enable_debug_logging", lambda: enabled.append(True))

    swee.run_sweep_pipeline(profile_dict=profile, verbose=False)

    assert enabled == [True]


def test_pipeline_enables_environment_debug_logging_when_not_verbose(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs())
    monkeypatch.setenv("SWEEPY_DEBUG", "1")
    enabled = []
    monkeypatch.setattr(swee, "enable_debug_logging", lambda: enabled.append(True))

    swee.run_sweep_pipeline(profile_dict=_profile(str(tmp_path)), verbose=False)

    assert enabled == [True]


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
    profile = _profile(str(tmp_path))
    profile["history"] = {"enabled": False}

    default_result = swee.run_sweep_pipeline(profile_dict=profile)
    assert default_result["roles"] == []
    assert len(default_result["top_roles"]) == 2

    full_result = swee.run_sweep_pipeline(profile_dict=profile, include_roles=True)
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


def test_pipeline_merges_optional_engine_results(tmp_path, monkeypatch):
    jobs = _jobs(2)
    _mock_engine(monkeypatch, jobs)
    profile = _profile(str(tmp_path))
    profile["sources"] = {"enabled": ["jobdrop"], "jobdrop": {"sites": ["wellfound"]}}

    seen = {}

    def fake_engines(names, titles, *args, **kwargs):
        seen["names"] = names
        extra = {
            "title": "T9",
            "company": "C",
            "location": "L",
            "match_score": 80,
            "url": "u9",
            "platform": "Wellfound",
        }
        kwargs["skipped"].append({"name": "jobdrop", "reason": "timeout"})
        return [extra], {"Wellfound": 1}

    monkeypatch.setattr(swee, "discover_engines", fake_engines)
    result = swee.run_sweep_pipeline(profile_dict=profile)

    assert seen["names"] == ["jobdrop"]
    assert result["skipped_sources"] == [{"name": "jobdrop", "reason": "timeout"}]
    assert result["discovered_count"] >= 3


@pytest.mark.parametrize(("deduplicate", "expected_count"), [(True, 1), (False, 2)])
def test_pipeline_can_disable_cross_board_deduplication(
    tmp_path, monkeypatch, deduplicate, expected_count
):
    postings = [
        {
            "title": "Technical Writer",
            "company": "Acme",
            "location": "NYC",
            "match_score": 90,
            "url": "https://linkedin.example/jobs/1",
            "platform": "LinkedIn",
        },
        {
            "title": "Technical-Writer",
            "company": "ACME",
            "location": "N.Y.C.",
            "match_score": 88,
            "url": "https://jobs.example.com/technical-writer",
            "platform": "Greenhouse",
        },
    ]
    _mock_engine(monkeypatch, postings)

    result = swee.run_sweep_pipeline(
        profile_dict=_profile(str(tmp_path)),
        deduplicate=deduplicate,
    )

    assert result["discovered_count"] == expected_count


def test_pipeline_skips_postings_reported_in_earlier_sweep(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs())
    profile = _profile(str(tmp_path))

    first = swee.run_sweep_pipeline(profile_dict=profile)
    assert first["new_count"] == 2
    assert first["previously_seen_count"] == 0

    validated = []

    def record_validation(jobs, progress=None):
        validated.append(len(jobs))
        return list(jobs), 0

    monkeypatch.setattr(swee, "filter_valid_jobs", record_validation)

    second = swee.run_sweep_pipeline(profile_dict=profile)

    assert second["new_count"] == 0
    assert second["discovered_count"] == 2
    assert second["previously_seen_count"] == 2
    assert second["active_count"] == 0
    assert "No new postings" in second["message"]
    assert validated == []


def test_pipeline_include_seen_reports_everything(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs())
    profile = _profile(str(tmp_path))

    swee.run_sweep_pipeline(profile_dict=profile)
    result = swee.run_sweep_pipeline(profile_dict=profile, include_seen=True)

    assert result["new_count"] == 2
    assert result["previously_seen_count"] == 0
    assert result["active_count"] == 2


def test_pipeline_records_only_validated_postings(tmp_path, monkeypatch):
    jobs = _jobs()
    _mock_engine(monkeypatch, jobs)
    monkeypatch.setattr(swee, "filter_valid_jobs", lambda *a, **k: ([jobs[0]], 1))
    profile = _profile(str(tmp_path))

    swee.run_sweep_pipeline(profile_dict=profile)
    result = swee.run_sweep_pipeline(profile_dict=profile)

    assert result["previously_seen_count"] == 1
    assert result["new_count"] == 1


def test_pipeline_respects_disabled_history(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs())
    profile = _profile(str(tmp_path))
    profile["history"] = {"enabled": False}

    swee.run_sweep_pipeline(profile_dict=profile)
    result = swee.run_sweep_pipeline(profile_dict=profile)

    assert result["new_count"] == 2
    assert result["previously_seen_count"] == 0


def test_pipeline_uses_profile_file_stem_for_history_scope(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(1))
    profile = _profile(str(tmp_path))
    profile["name"] = "Different Name"

    result = swee.run_sweep_pipeline(
        profile_dict=profile,
        profile_path="profiles/pedro_writer.yaml",
    )

    assert result["history_scope"] == "pedro_writer"


def test_run_wizard_sweep_passes_profile_path(monkeypatch):
    captured = {}
    monkeypatch.setattr(swee, "run_sweep_pipeline", lambda **kwargs: captured.update(kwargs))

    swee._run_wizard_sweep({"name": "Alex"}, "profiles/alex.yaml")

    assert captured["profile_path"] == "profiles/alex.yaml"
    assert captured["profile_dict"] == {"name": "Alex"}


def test_pipeline_skips_disabled_engines(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(1))
    profile = _profile(str(tmp_path))
    profile["sources"] = {"enabled": ["jobspy"], "jobspy": {"sites": ["linkedin"]}}

    monkeypatch.setattr(
        swee,
        "discover_engines",
        lambda names, *a, **k: pytest.fail(f"unexpected engines: {names}"),
    )
    result = swee.run_sweep_pipeline(profile_dict=profile)
    assert result["status"] == "completed"
    assert result["skipped_sources"] == []


def test_pipeline_all_formats(tmp_path, monkeypatch):
    jobs = _jobs(2)
    _mock_engine(monkeypatch, jobs)
    profile = _profile(str(tmp_path))
    profile["export"]["format"] = "pdf,csv,json"
    result = swee.run_sweep_pipeline(profile_dict=profile)
    assert set(result["reports"].keys()) == {"pdf", "csv", "json"}


def test_pipeline_writes_tracking_columns_and_carries_values(tmp_path, monkeypatch):
    from engine.exporter import export_to_csv as real_export_to_csv

    jobs = _jobs(2)
    _mock_engine(monkeypatch, jobs)
    monkeypatch.setattr(swee, "export_to_csv", real_export_to_csv)

    profile = _profile(str(tmp_path))
    profile["export"]["format"] = "csv"
    profile["history"] = {"enabled": False}

    first = swee.run_sweep_pipeline(profile_dict=profile)
    csv_path = first["reports"]["csv"]
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert "date_applied" in rows[0] and "notes" in rows[0]

    rows[0]["status"] = "Applied"
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    time.sleep(1.1)
    second = swee.run_sweep_pipeline(profile_dict=profile)
    with open(second["reports"]["csv"], newline="", encoding="utf-8") as handle:
        carried = list(csv.DictReader(handle))
    assert carried[0]["status"] == "Applied"


def test_pipeline_omits_tracking_columns_when_disabled(tmp_path, monkeypatch):
    from engine.exporter import export_to_csv as real_export_to_csv

    _mock_engine(monkeypatch, _jobs(1))
    monkeypatch.setattr(swee, "export_to_csv", real_export_to_csv)

    profile = _profile(str(tmp_path))
    profile["export"]["format"] = "csv"
    profile["export"]["tracking"] = False

    result = swee.run_sweep_pipeline(profile_dict=profile)
    with open(result["reports"]["csv"], newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert "date_applied" not in header


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


def test_default_profile_prefers_last_saved(monkeypatch, tmp_path):
    saved = tmp_path / "saved.yaml"
    saved.write_text("name: Saved\n", encoding="utf-8")
    monkeypatch.setattr(swee, "last_profile_path", lambda: str(saved))

    assert swee._default_profile_path() == str(saved)


def test_default_profile_falls_back_to_conventional_candidate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(swee, "last_profile_path", lambda: None)
    (tmp_path / "config.sample.yaml").write_text("name: Sample\n", encoding="utf-8")

    assert swee._default_profile_path() == "config.sample.yaml"


def test_default_profile_returns_none_without_any_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(swee, "last_profile_path", lambda: None)

    assert swee._default_profile_path() is None


def test_pipeline_without_profile_path_uses_last_saved_profile(tmp_path, monkeypatch):
    profile = _profile(str(tmp_path))
    profile["name"] = "Last Saved"
    profile["history"] = {"enabled": False}
    path = tmp_path / "last_saved.yaml"
    path.write_text(yaml.safe_dump(profile), encoding="utf-8")

    _mock_engine(monkeypatch, _jobs(1))
    monkeypatch.setattr(swee, "last_profile_path", lambda: str(path))

    result = swee.run_sweep_pipeline(verbose=False)

    assert result["status"] == "completed"
    assert result["profile"]["name"] == "Last Saved"


def test_pipeline_produces_timestamped_distinct_filenames(tmp_path, monkeypatch):
    jobs = _jobs(1)
    monkeypatch.setattr(swee, "discover_jobs", lambda *a, **k: (list(jobs), {"Greenhouse": 1}))
    monkeypatch.setattr(swee, "discover_sources", lambda *a, **k: ([], {}))
    monkeypatch.setattr(swee, "filter_valid_jobs", lambda *a, **k: (list(jobs), 0))
    monkeypatch.setattr(swee, "score_jobs", lambda *a, **k: (jobs, ["python"]))
    profile = _profile(str(tmp_path))
    profile["history"] = {"enabled": False}

    first = swee.run_sweep_pipeline(profile_dict=profile)
    time.sleep(1.1)
    second = swee.run_sweep_pipeline(profile_dict=profile)

    assert first["reports"]["json"] != second["reports"]["json"]
    assert os.path.exists(first["reports"]["json"])
    assert os.path.exists(second["reports"]["json"])


def test_result_stem_marks_only_mcp_runs():
    plain = swee.result_stem("tech_writer")
    marked = swee.result_stem("tech_writer", "mcp")

    assert plain.startswith("tech_writer_")
    assert "_mcp_" not in plain
    assert marked.startswith("tech_writer_mcp_")


def test_result_stamp_shifts_with_the_timezone():
    utc = datetime.datetime.strptime(swee.result_stamp("UTC"), "%Y-%m-%d-%H%M%S")
    eastern = datetime.datetime.strptime(swee.result_stamp("-05:00"), "%Y-%m-%d-%H%M%S")

    assert datetime.timedelta(hours=4, minutes=59) <= utc - eastern <= datetime.timedelta(
        hours=5, minutes=1
    )


def test_result_stem_prefers_a_supplied_timestamp():
    assert swee.result_stem("tech_writer", "mcp", "UTC", "2026-10-27-235510") == (
        "tech_writer_mcp_2026-10-27-235510"
    )
    assert swee.result_stem("tech_writer", timestamp="2026-10-27T23:55:10") == (
        "tech_writer_2026-10-27-235510"
    )


def test_pipeline_stamps_reports_with_the_caller_timestamp(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(1))
    profile = _profile(str(tmp_path))
    profile["history"] = {"enabled": False}

    result = swee.run_sweep_pipeline(
        profile_dict=profile, execution_method="mcp", timestamp="2026-10-27-235510"
    )

    assert os.path.basename(result["reports"]["json"]) == "test_mcp_2026-10-27-235510.json"


def test_pipeline_rejects_an_unreadable_timestamp(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(1))

    with pytest.raises(ValueError) as excinfo:
        swee.run_sweep_pipeline(
            profile_dict=_profile(str(tmp_path)), timestamp="last tuesday"
        )

    assert "timestamp" in str(excinfo.value).lower()


def test_pipeline_rejects_an_unknown_timezone_before_discovering(tmp_path, monkeypatch):
    monkeypatch.setattr(
        swee, "discover_jobs", lambda *a, **k: pytest.fail("discovery should not run")
    )
    profile = _profile(str(tmp_path))
    profile["export"]["timezone"] = "Mars/Olympus"

    with pytest.raises(ValueError):
        swee.run_sweep_pipeline(profile_dict=profile)


def test_pipeline_marks_mcp_result_filenames(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(1))
    profile = _profile(str(tmp_path))
    profile["history"] = {"enabled": False}

    result = swee.run_sweep_pipeline(profile_dict=profile, execution_method="mcp")

    name = os.path.basename(result["reports"]["json"])
    assert name.startswith("test_mcp_")
    assert result["profile_stem"] == "test"


def test_pipeline_keeps_plain_filenames_for_cli_runs(tmp_path, monkeypatch):
    _mock_engine(monkeypatch, _jobs(1))
    profile = _profile(str(tmp_path))
    profile["history"] = {"enabled": False}

    result = swee.run_sweep_pipeline(profile_dict=profile, execution_method="cli")

    name = os.path.basename(result["reports"]["json"])
    assert name.startswith("test_")
    assert "_mcp_" not in name


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
        captured.update(kwargs)
        return {"status": "completed"}

    recorded = []
    monkeypatch.setattr(swee, "run_sweep_pipeline", fake_pipeline)
    monkeypatch.setattr(swee, "record_last_profile", recorded.append)

    swee._run_wizard_sweep(profile, "profiles/alex.yaml")

    assert captured["profile_dict"] is profile
    assert captured["execution_method"] == "wizard"
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
        captured.update(kwargs)
        return {"status": "completed"}

    recorded = []
    monkeypatch.setattr(swee, "run_sweep_pipeline", fake_pipeline)
    monkeypatch.setattr(swee, "record_last_profile", recorded.append)

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert captured["profile_path"] == "profiles/last.yaml"
    assert captured["execution_method"] == "cli"
    assert recorded == ["profiles/last.yaml"]
    assert "Using the last saved profile" in capsys.readouterr().out


def test_main_no_dedupe_flag_applies_to_one_run(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--run", "--no-dedupe"])
    monkeypatch.setattr(swee, "last_profile_path", lambda: "profiles/last.yaml")
    captured = {}
    monkeypatch.setattr(
        swee,
        "run_sweep_pipeline",
        lambda **kwargs: captured.update(kwargs) or {"status": "completed"},
    )

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert captured["deduplicate"] is False


def test_main_include_seen_flag_applies_to_one_run(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--run", "--include-seen"])
    monkeypatch.setattr(swee, "last_profile_path", lambda: "profiles/last.yaml")
    captured = {}
    monkeypatch.setattr(
        swee,
        "run_sweep_pipeline",
        lambda **kwargs: captured.update(kwargs) or {"status": "completed"},
    )

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert captured["include_seen"] is True


def test_main_reset_history_without_run_clears_and_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--reset-history"])
    called = []
    monkeypatch.setattr(swee, "_clear_history", called.append)
    monkeypatch.setattr(swee, "run_sweep_pipeline", lambda **k: pytest.fail("pipeline ran"))

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert called == [None]


def test_main_run_with_reset_history_clears_then_sweeps(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swee.py", "--run", "--reset-history"])
    monkeypatch.setattr(swee, "last_profile_path", lambda: "profiles/last.yaml")
    called = []
    monkeypatch.setattr(swee, "_clear_history", called.append)
    monkeypatch.setattr(
        swee, "run_sweep_pipeline", lambda **k: {"status": "completed"}
    )

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    assert called == ["profiles/last.yaml"]


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


def _portfolio_file(tmp_path, name="portfolio.md"):
    path = tmp_path / name
    path.write_text("# Case Study A\n", encoding="utf-8")
    return path


def test_portfolio_sources_attach_a_named_track(tmp_path):
    path = _portfolio_file(tmp_path)

    sources = swee._portfolio_sources([f"Tech Writer={path}"], ["Tech Writer"])

    assert sources == [{"path": str(path), "track": "Tech Writer"}]


def test_portfolio_sources_use_the_default_track(tmp_path):
    path = _portfolio_file(tmp_path)

    sources = swee._portfolio_sources([str(path)], ["Tech Writer"], "Tech Writer")

    assert sources == [{"path": str(path), "track": "Tech Writer"}]


def test_portfolio_sources_keep_urls_untouched():
    assert swee._portfolio_sources(["https://example.com/work"], []) == [
        {"url": "https://example.com/work"}
    ]


def test_portfolio_sources_reject_an_unknown_track(tmp_path):
    path = _portfolio_file(tmp_path)

    with pytest.raises(ValueError, match="matches no resume track"):
        swee._portfolio_sources([str(path)], ["Tech Writer"], "Ghost Track")


def test_portfolio_sources_reject_an_unknown_track_prefix():
    with pytest.raises(ValueError, match="names track 'Ghost'"):
        swee._portfolio_sources(["Ghost=https://example.com/work"], ["Tech Writer"])


def test_portfolio_sources_reject_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="file not found"):
        swee._portfolio_sources([str(tmp_path / "gone.md")], [])


def test_headless_setup_writes_the_portfolio(tmp_path, monkeypatch):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4 fake")
    portfolio = _portfolio_file(tmp_path)
    profile = tmp_path / "profile.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "swee.py",
            "--setup",
            "--non-interactive",
            "--profile",
            str(profile),
            "--name",
            "Alice",
            "--titles",
            "Writer",
            "--location",
            "NYC",
            "--resume",
            str(resume),
            "--sources",
            "ats",
            "--no-cache",
            "--portfolio",
            str(portfolio),
        ],
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        swee.main()

    assert exc.value.code == 0
    saved = yaml.safe_load(profile.read_text(encoding="utf-8"))
    assert saved["portfolio"]["sources"] == [{"path": str(portfolio)}]
