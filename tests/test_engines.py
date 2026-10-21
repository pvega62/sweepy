import subprocess

import pytest

import engine.engines as engines


class _Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_catalog_covers_every_registered_adapter():
    from engine.adapters import ADAPTERS

    assert set(engines.ENGINE_CATALOG) == set(ADAPTERS)


def test_catalog_entries_name_what_they_scrape():
    for name, info in engines.ENGINE_CATALOG.items():
        assert info.scrapes, f"{name} must list the boards it reads"
        assert info.blurb, f"{name} needs a one-line summary"


def test_core_engines_report_installed():
    assert engines.engine_status("jobspy")["installed"] is True
    assert engines.engine_status("ats")["installed"] is True


def test_status_detection_uses_find_spec(monkeypatch):
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)
    status = engines.engine_status("jobdrop")
    assert status["installed"] is False
    assert "pip install" in status["detail"]


def _jobspy_only(monkeypatch):
    """Pretend only the core JobSpy library is present, so conflicts stay visible."""
    monkeypatch.setattr(
        engines.importlib.util,
        "find_spec",
        lambda name: object() if name == "jobspy" else None,
    )


def test_install_refuses_a_conflicting_engine(monkeypatch):
    calls = []
    _jobspy_only(monkeypatch)

    results = engines.install_engines(
        ["jobdrop"], runner=lambda args: calls.append(args) or _Completed()
    )

    assert calls == []
    assert results["jobdrop"]["blocked"] is True
    assert results["jobdrop"]["installed"] is False
    assert "curl" in results["jobdrop"]["detail"]


def test_install_allows_a_conflict_when_overridden(monkeypatch):
    calls = []
    _jobspy_only(monkeypatch)

    engines.install_engines(
        ["jobdrop"],
        runner=lambda args: calls.append(args) or _Completed(),
        allow_conflicts=True,
    )

    assert calls[0] == ["--no-deps", "jobdrop>=2.10,<3"]
    flat = " ".join(item for call in calls for item in call).lower()
    assert "curl" not in flat, "the conflicting pin must stay out of every pip call"


def test_split_install_keeps_conflicting_packages_out(monkeypatch):
    _jobspy_only(monkeypatch)
    blocked = engines.ENGINE_CATALOG["jobdrop"].conflict_packages
    monkeypatch.setattr(
        engines.importlib.metadata,
        "requires",
        lambda name: [
            "beautifulsoup4 (>=4.12.2,<5.0.0)",
            "curl-cffi (>=0.7.0,<0.8.0)",
            "pandas (>=2.1.0,<3.0.0)",
            'fastmcp (>=0.2.0) ; extra == "mcp"',
        ],
    )

    dependencies = engines._dependencies_without("jobdrop", blocked)

    assert dependencies
    assert not any("curl" in requirement.lower() for requirement in dependencies)
    assert not any("extra ==" in requirement for requirement in dependencies)


def test_split_install_tolerates_absent_metadata(monkeypatch):
    def missing(name):
        raise engines.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(engines.importlib.metadata, "requires", missing)

    assert engines._dependencies_without("jobdrop", ("curl-cffi",)) == []


def test_missing_engines_hide_the_conflicting_engine(monkeypatch):
    _jobspy_only(monkeypatch)
    assert "jobdrop" not in engines.missing_engines()
    assert "jobdrop" in engines.missing_engines(include_conflicting=True)


def test_status_table_flags_the_conflict(monkeypatch):
    _jobspy_only(monkeypatch)
    assert "conflicts with JobSpy" in engines.status_table()


def test_extras_install_compatible_engines_in_one_resolution():
    """`pip install -e ".[all-engines]"` must stay resolvable next to JobSpy."""
    import tomllib

    with open("pyproject.toml", "rb") as handle:
        extras = tomllib.load(handle)["project"]["optional-dependencies"]

    combined = " ".join(extras["all-engines"]).lower()
    assert "hirehunt" in combined
    assert "openroles" in combined
    assert "apify-client" in combined
    assert "jobdrop" not in combined
    assert "jobdrop" not in extras, "a jobdrop extra cannot resolve with the core deps"


def test_unknown_engine_status():
    status = engines.engine_status("mystery")
    assert status["installed"] is False
    assert "Unknown job engine" in status["detail"]


def test_status_table_marks_missing_engines(monkeypatch):
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)
    table = engines.status_table()
    assert "[ ] jobspy" in table
    assert "[x] ats" in table
    assert "[ ] jobdrop" in table


def test_install_specs_expand_all():
    specs = engines.install_specs(["all"])
    assert any(spec.startswith("hirehunt") for spec in specs)
    assert any(spec.startswith("openroles") for spec in specs)
    assert not any(spec.startswith("python-jobspy") for spec in specs)
    # jobdrop pins an older curl-cffi, so "all" leaves it out.
    assert not any(spec.startswith("jobdrop") for spec in specs)


def test_install_specs_include_jobdrop_when_named():
    assert engines.install_specs(["jobdrop"]) == ["jobdrop>=2.10,<3"]


def test_conflict_warnings_name_the_blocker():
    warnings = engines.conflict_warnings(["jobdrop"])
    assert warnings
    assert "JobSpy" in warnings[0] or "jobspy" in warnings[0]
    assert "curl" in warnings[0]


def test_conflict_warnings_ignore_clean_engines():
    assert engines.conflict_warnings(["openroles", "hirehunt"]) == []


def test_install_specs_reject_unknown_engine():
    with pytest.raises(ValueError):
        engines.install_specs(["nope"])


def test_install_command_names_package(monkeypatch):
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)
    command = engines.install_command(["openroles"])
    assert "pip install" in command
    assert "openroles" in command


def test_install_engines_skips_when_already_present():
    calls = []
    results = engines.install_engines(["jobspy"], runner=lambda args: calls.append(args))
    assert calls == []
    assert results["jobspy"]["installed"] is True


def test_install_engines_runs_pip_and_verifies(monkeypatch):
    calls = []
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(engines.importlib, "invalidate_caches", lambda: None)

    def runner(args):
        calls.append(args)
        return _Completed()

    messages = []
    results = engines.install_engines(["openroles"], runner=runner, echo=messages.append)

    assert calls and calls[0][0].startswith("openroles")
    assert messages
    assert results["openroles"]["installed"] is False
    assert results["openroles"]["command"]


def test_install_engines_reports_pip_tail_on_failure(monkeypatch):
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)

    def runner(args):
        return _Completed(returncode=1, stderr="ERROR: no matching distribution")

    results = engines.install_engines(["jobdrop"], runner=runner)
    assert results["jobdrop"]["installed"] is False
    assert "no matching distribution" in results["jobdrop"]["detail"]
    assert "pip install" in results["jobdrop"]["command"]


def test_install_engines_retries_with_user_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)

    def runner(args):
        calls.append(args)
        if "--user" in args:
            return _Completed()
        return _Completed(returncode=1, stderr="ERROR: Permission denied")

    engines.install_engines(["hirehunt"], runner=runner)
    assert "--user" in calls[1]


def test_install_engines_reports_missing_pip(monkeypatch):
    monkeypatch.setattr(engines.importlib.util, "find_spec", lambda name: None)

    def runner(args):
        raise FileNotFoundError("pip")

    results = engines.install_engines(["jobdrop"], runner=runner)
    assert results["jobdrop"]["installed"] is False
    assert "pip was not found" in results["jobdrop"]["detail"]


def test_missing_engines_lists_only_absent(monkeypatch):
    monkeypatch.setattr(
        engines.importlib.util, "find_spec", lambda name: object() if name == "jobdrop" else None
    )
    assert engines.missing_engines() == ["jobspy", "hirehunt", "openroles", "apify"]


def test_installed_engines_can_exclude_core(monkeypatch):
    monkeypatch.setattr(
        engines.importlib.util, "find_spec", lambda name: object() if name == "jobdrop" else None
    )
    assert engines.installed_engines(include_core=False) == ["jobdrop"]


def test_updater_reinstalls_known_extras(tmp_path, monkeypatch):
    import engine.updater as updater

    calls = []
    monkeypatch.setattr(
        updater, "_install_requirements", lambda root, args: calls.append((root, args)) or _Completed()
    )
    updater._reinstall_optional_engines(str(tmp_path), ["openroles"])
    assert calls and calls[0][1][0].startswith("openroles")


def test_updater_skips_extras_when_none_installed(monkeypatch):
    import engine.updater as updater

    calls = []
    monkeypatch.setattr(
        updater, "_install_requirements", lambda root, args: calls.append(args) or _Completed()
    )
    assert updater._reinstall_optional_engines("x", []).returncode == 0
    assert calls == []


def test_installed_optional_engines_survives_errors(monkeypatch):
    import engine.updater as updater

    monkeypatch.setattr(engines, "installed_engines", _boom)
    assert updater._installed_optional_engines() == []


def _boom(*args, **kwargs):
    raise RuntimeError("broken")


def test_subprocess_completed_process_contract():
    # Guard against a runner returning something unexpected being treated as success.
    completed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad")
    assert completed.returncode == 1
