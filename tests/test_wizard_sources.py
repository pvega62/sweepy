import copy
import types

import pytest
import yaml

import engine.config as config
from engine.sweep_config import normalize_sources


class _StubQuestion:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def promptless(monkeypatch):
    """Keep questionary from reaching for a real console during tests."""
    for name in ("confirm", "text", "checkbox", "password", "select"):
        monkeypatch.setattr(config.questionary, name, _StubQuestion)
    monkeypatch.setattr(config, "_ask", lambda question: None)


def _scripted(values):
    """Return an `_ask` replacement that answers from a list in order."""
    queue = list(values)

    def ask(_question):
        if not queue:
            raise AssertionError("wizard asked more questions than expected")
        return queue.pop(0)

    return ask


def test_engine_labels_show_install_state(monkeypatch):
    monkeypatch.setattr(config, "engine_status", lambda name: {"installed": False, "core": False})
    label = config._engine_choice_label("jobdrop")
    assert "jobdrop" in label
    assert "download" in label
    assert "wellfound" in config.ENGINE_CATALOG["jobdrop"].blurb.lower() or "33" in label


def test_engine_details_list_scraped_boards():
    details = config._engine_details("jobspy")
    assert "LinkedIn" in details
    assert "Glassdoor" in details


def test_ask_engines_prompts_only_selected(monkeypatch):
    prompted = []
    monkeypatch.setattr(config, "_ask", _scripted([["jobspy", "openroles"]]))
    monkeypatch.setattr(config, "_ensure_engine_available", lambda name: True)

    def fake_jobspy(current):
        prompted.append("jobspy")
        return {"sites": ["linkedin"]}

    def fake_openroles(current):
        prompted.append("openroles")
        return {"ats": ["greenhouse"], "companies": ["figma"]}

    monkeypatch.setitem(config._ENGINE_PROMPTS, "jobspy", fake_jobspy)
    monkeypatch.setitem(config._ENGINE_PROMPTS, "openroles", fake_openroles)

    answers = config._ask_engines({})
    assert prompted == ["jobspy", "openroles"]
    assert answers["enabled"] == ["jobspy", "openroles"]
    assert answers["openroles"]["companies"] == ["figma"]


def test_ask_engines_drops_declined_download(monkeypatch):
    monkeypatch.setattr(config, "_ask", _scripted([["jobspy", "jobdrop"]]))
    monkeypatch.setattr(config, "_ensure_engine_available", lambda name: name == "jobspy")
    monkeypatch.setitem(config._ENGINE_PROMPTS, "jobspy", lambda current: {})
    monkeypatch.setitem(
        config._ENGINE_PROMPTS,
        "jobdrop",
        lambda current: pytest.fail("prompts must not run for a declined download"),
    )

    answers = config._ask_engines({})
    assert answers["enabled"] == ["jobspy"]


def test_ask_engines_survives_invalid_engine_config(monkeypatch):
    monkeypatch.setattr(config, "_ask", _scripted([["jobspy", "openroles"]]))
    monkeypatch.setattr(config, "_ensure_engine_available", lambda name: True)
    monkeypatch.setitem(config._ENGINE_PROMPTS, "jobspy", lambda current: {})

    def reject(current):
        raise ValueError("companies required")

    monkeypatch.setitem(config._ENGINE_PROMPTS, "openroles", reject)
    answers = config._ask_engines({})
    assert answers["enabled"] == ["jobspy"]


def _record(seen, names):
    seen["names"] = list(names)
    return {names[0]: {"installed": True}}


def test_ensure_engine_available_installs_on_confirmation(monkeypatch):
    seen = {}
    monkeypatch.setattr(config, "engine_status", lambda name: {"installed": False, "core": False})
    monkeypatch.setattr(config, "_ask", lambda question: True)
    monkeypatch.setattr(
        config,
        "install_engines",
        lambda names, echo=None: _record(seen, names),
    )
    assert config._ensure_engine_available("jobdrop") is True
    assert seen["names"] == ["jobdrop"]


def test_ensure_engine_available_skips_when_declined(monkeypatch):
    monkeypatch.setattr(config, "engine_status", lambda name: {"installed": False, "core": False})
    monkeypatch.setattr(config, "_ask", lambda question: False)
    monkeypatch.setattr(
        config, "install_engines", lambda *a, **k: pytest.fail("must not install unasked")
    )
    assert config._ensure_engine_available("jobdrop") is False


def test_ensure_engine_available_reports_failed_install(monkeypatch):
    monkeypatch.setattr(config, "engine_status", lambda name: {"installed": False, "core": False})
    monkeypatch.setattr(config, "_ask", lambda question: True)
    monkeypatch.setattr(
        config,
        "install_engines",
        lambda names, echo=None: {names[0]: {"installed": False, "detail": "no wheels", "command": "pip"}},
    )
    assert config._ensure_engine_available("jobdrop") is False


def test_openroles_reprompts_until_companies_given(monkeypatch):
    monkeypatch.setattr(
        config, "_ask", _scripted([["greenhouse"], "", "figma, stripe"])
    )
    answers = config._ask_openroles({})
    assert answers == {"ats": ["greenhouse"], "companies": ["figma", "stripe"]}


def test_apify_requires_token(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    assert config._ask_apify({}) is None


def test_apify_reads_token_and_actor(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "secret")
    monkeypatch.setattr(config, "_ask", _scripted(["my/actor"]))
    answers = config._ask_apify({})
    assert answers["actor"] == "my/actor"
    assert answers["token"] is None


def test_hirehunt_reports_no_proxy_support(monkeypatch):
    monkeypatch.setattr(config, "_ask", _scripted([["linkedin"]]))
    answers = config._ask_hirehunt({"sources": ["linkedin"]})
    assert answers["sources"] == ["linkedin"]


def test_proxy_file_is_read_without_echo(tmp_path, monkeypatch, caplog):
    proxy_file = tmp_path / "proxies.txt"
    proxy_file.write_text("user:pw@host:1\nhost:2\n", encoding="utf-8")
    monkeypatch.setattr(config, "_ask", _scripted([True, True, str(proxy_file)]))

    proxies = config._ask_proxies([])
    assert proxies == ["user:pw@host:1", "host:2"]
    assert "pw@" not in caplog.text


def test_proxy_inline_prompts_for_password(monkeypatch):
    monkeypatch.setattr(
        config, "_ask", _scripted([True, False, "host:9000", "user", "secret"])
    )
    assert config._ask_proxies([]) == ["user:secret@host:9000"]


def test_proxy_declined_returns_empty(monkeypatch):
    monkeypatch.setattr(config, "_ask", _scripted([False]))
    assert config._ask_proxies([]) == []


def test_orchestrator_defaults_with_one_enter(monkeypatch):
    monkeypatch.setattr(config, "_ask", _scripted(["", True, "", "", ""]))
    answers = config._ask_orchestrator({})
    assert answers["timeout_per_source_seconds"] == 180
    assert answers["cache"] == {"enabled": True, "ttl_seconds": 3600}
    assert answers["circuit_breaker"]["failure_threshold"] == 5


def test_orchestrator_accepts_overrides(monkeypatch):
    monkeypatch.setattr(config, "_ask", _scripted(["90", False, "60", "3", "10"]))
    answers = config._ask_orchestrator({})
    assert answers["timeout_per_source_seconds"] == 90
    assert answers["cache"] == {"enabled": False, "ttl_seconds": 60}
    assert answers["circuit_breaker"] == {"failure_threshold": 3, "cooldown_seconds": 10}


def test_answers_include_engine_blocks():
    profile = {
        "sources": {
            "enabled": ["jobspy", "openroles"],
            "openroles": {"companies": ["figma"]},
        }
    }
    answers = config._answers_from_profile(profile)
    assert answers["sources"]["enabled"] == ["jobspy", "openroles"]
    assert answers["sources"]["openroles"]["companies"] == ["figma"]


def test_answers_default_legacy_profile():
    answers = config._answers_from_profile({"platforms": {"greenhouse": True}})
    assert answers["sources"]["enabled"] == ["jobspy", "ats"]


def test_merge_answers_writes_engine_blocks():
    merged = config._merge_answers(
        {},
        {
            "name": "Alex",
            "titles": ["Writer"],
            "location": "NYC",
            "platforms": ["greenhouse"],
            "sources": {
                "enabled": ["jobspy", "openroles"],
                "jobspy": {"sites": ["linkedin"], "fetch_descriptions": False},
                "openroles": {"companies": ["figma"]},
            },
            "sources_dirty": True,
            "orchestrator_dirty": True,
            "orchestrator": {
                "timeout_per_source_seconds": 45,
                "cache": {"enabled": False, "ttl_seconds": 30},
                "circuit_breaker": {"failure_threshold": 4, "cooldown_seconds": 12},
            },
        },
    )
    assert merged["sources"]["enabled"] == ["jobspy", "openroles"]
    assert merged["cache"] == {"enabled": False, "ttl_seconds": 30}
    assert merged["orchestrator"]["timeout_per_source_seconds"] == 45

    runtime = normalize_sources(merged)
    assert runtime["enabled"] == ["jobspy", "openroles"]
    assert runtime["engines"]["jobspy"]["fetch_descriptions"] is False


def test_merge_answers_preserves_native_source_blocks():
    original = {"sources": {"greenhouse": {"boards": ["gitlab"]}, "ashby": {"enabled": False}}}
    merged = config._merge_answers(
        copy.deepcopy(original), {"name": "A", "sources": {"enabled": ["ats"]}}
    )
    assert merged["sources"]["greenhouse"] == {"boards": ["gitlab"]}
    assert merged["sources"]["ashby"] == {"enabled": False}


def test_profile_survives_yaml_round_trip(tmp_path):
    profile = config._merge_answers(
        {},
        {
            "name": "Alex",
            "titles": ["Writer"],
            "location": "NYC",
            "sources": {
                "enabled": ["jobspy", "jobdrop"],
                "jobdrop": {"sites": ["wellfound"], "headless": True},
            },
            "sources_dirty": True,
        },
    )
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.dump(profile, sort_keys=False), encoding="utf-8")

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    runtime = normalize_sources(loaded)
    assert runtime["enabled"] == ["jobspy", "jobdrop"]
    assert runtime["engines"]["jobdrop"]["sites"] == ["wellfound"]


def test_format_answer_reports_engines():
    assert config._format_engines({"enabled": ["jobspy", "ats"]}) == "jobspy, ats"
    assert config._format_engines(None) == "(defaults: jobspy, ats)"
    assert config._format_orchestrator(None).startswith("(defaults")


def test_format_orchestrator_reports_cache_state():
    value = {
        "timeout_per_source_seconds": 90,
        "cache": {"enabled": False, "ttl_seconds": 60},
    }
    assert config._format_orchestrator(value) == "timeout 90s, cache off (60s)"


def test_legacy_notice_only_for_list_platforms():
    from engine.sweep_config import legacy_profile_notice

    assert legacy_profile_notice({"platforms": ["linkedin"]}) is not None
    assert legacy_profile_notice({"platforms": {"greenhouse": True}}) is None
    assert legacy_profile_notice({"sources": {"enabled": ["jobspy"]}}) is None


def test_manage_engines_shows_details(monkeypatch, capsys):
    monkeypatch.setattr(
        config, "_ask", _scripted(["Show engine details", "jobspy", config.BACK_LABEL])
    )
    config._manage_engines()
    out = capsys.readouterr().out
    assert "Job engines" in out
    assert "LinkedIn" in out


def test_manage_engines_installs_all_missing(monkeypatch):
    installed = []
    monkeypatch.setattr(config, "missing_engines", lambda: ["jobdrop"])
    monkeypatch.setattr(config, "_ask", _scripted(["Install all missing engines", True, config.BACK_LABEL]))
    monkeypatch.setattr(
        config,
        "install_engines",
        lambda names, echo=None: installed.append(list(names)) or {"jobdrop": {"installed": True}},
    )
    config._manage_engines()
    assert installed == [["jobdrop"]]


def test_manage_engines_installs_one(monkeypatch):
    installed = []
    monkeypatch.setattr(config, "missing_engines", lambda: ["jobdrop", "openroles"])
    monkeypatch.setattr(
        config,
        "_ask",
        _scripted(["Install one engine", "openroles", True, config.BACK_LABEL]),
    )
    monkeypatch.setattr(
        config,
        "install_engines",
        lambda names, echo=None: installed.append(list(names)) or {"openroles": {"installed": True}},
    )
    config._manage_engines()
    assert installed == [["openroles"]]


def test_manage_engines_prints_retry_command(monkeypatch, caplog):
    monkeypatch.setattr(config, "missing_engines", lambda: ["jobdrop"])
    monkeypatch.setattr(
        config, "_ask", _scripted(["Install all missing engines", True, config.BACK_LABEL])
    )
    monkeypatch.setattr(
        config,
        "install_engines",
        lambda names, echo=None: {
            "jobdrop": {"installed": False, "detail": "no wheels", "command": "pip install jobdrop"}
        },
    )
    with caplog.at_level("INFO", logger="sweepy.engine.config"):
        config._manage_engines()
    assert "pip install jobdrop" in caplog.text
    assert "no wheels" in caplog.text


def test_manage_engines_never_installs_without_confirmation(monkeypatch):
    monkeypatch.setattr(config, "missing_engines", lambda: ["jobdrop"])
    monkeypatch.setattr(config, "_ask", _scripted(["Install all missing engines", False, config.BACK_LABEL]))
    monkeypatch.setattr(
        config, "install_engines", lambda *a, **k: pytest.fail("must not install unasked")
    )
    config._manage_engines()


def test_review_screen_offers_engine_setup(monkeypatch):
    calls = {}
    monkeypatch.setattr(config, "_print_summary", lambda answers, steps: None)
    monkeypatch.setattr(config, "_manage_engines", lambda: calls.setdefault("downloads", True))
    monkeypatch.setattr(
        config, "_ask_engines", lambda current: calls.setdefault("sources", {"enabled": ["jobdrop"]})
    )
    performance = {
        "timeout_per_source_seconds": 30,
        "cache": {"enabled": False, "ttl_seconds": 1},
        "circuit_breaker": {"failure_threshold": 1, "cooldown_seconds": 1},
    }
    monkeypatch.setattr(config, "_ask_orchestrator", lambda current: calls.setdefault("perf", performance))
    monkeypatch.setattr(
        config,
        "_ask",
        _scripted([config.MENU_ENGINES, config.MENU_SOURCES, "Adjust engine performance", "Submit profile"]),
    )

    answers = {}
    config._review_answers(answers, [], lambda: {})

    assert calls["downloads"] is True
    assert answers["sources"] == {"enabled": ["jobdrop"]}
    assert answers["sources_dirty"] is True
    assert answers["orchestrator_dirty"] is True
    assert answers["orchestrator"] == performance


def test_toolbox_exposes_engine_management():
    choices = config._toolbox_choices()
    assert config.MENU_SOURCES in choices
    assert config.MENU_ENGINES in choices


def _headless_args(**overrides):
    base = {
        "profile": None,
        "name": "Alex",
        "titles": "Technical Writer,UX Writer",
        "location": "New York, NY",
        "resume": "C:/resume.pdf",
        "sources": "jobspy,ats",
        "jobspy_sites": "linkedin,indeed",
        "hirehunt_sources": None,
        "jobdrop_sites": None,
        "openroles_companies": None,
        "apify_actor": None,
        "timeout": 120,
        "cache_ttl": 60,
        "no_cache": True,
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


def _profile_from(monkeypatch, **overrides):
    """Rebuild the profile that _setup_headless handed to save_profile."""
    import swee

    captured = {}

    def fake_save(data, path):
        captured.update(data)
        return str(path)

    monkeypatch.setattr(swee, "save_profile", fake_save)
    swee._setup_headless(_headless_args(profile="captured", **overrides))
    return captured


def test_headless_setup_applies_flags(monkeypatch):
    profile = _profile_from(monkeypatch)
    assert profile["name"] == "Alex"
    assert profile["search"]["titles"] == ["Technical Writer", "UX Writer"]
    assert profile["sources"]["jobspy"]["sites"] == ["linkedin", "indeed"]
    assert profile["cache"]["enabled"] is False
    assert profile["orchestrator"]["timeout_per_source_seconds"] == 120

    runtime = normalize_sources(profile)
    assert runtime["enabled"] == ["jobspy", "ats"]


def test_headless_setup_requires_identity_fields(monkeypatch):
    import swee

    with pytest.raises(ValueError, match="--name"):
        swee._setup_headless(_headless_args(name=None))


def test_headless_setup_fails_fast_on_openroles_without_companies(monkeypatch):
    import swee

    monkeypatch.setattr(swee, "save_profile", lambda data, path: pytest.fail("must not save"))
    with pytest.raises(ValueError, match="companies"):
        swee._setup_headless(_headless_args(sources="jobspy,openroles"))


def test_headless_setup_updates_existing_profile(tmp_path, monkeypatch):
    import swee

    existing = tmp_path / "existing.yaml"
    existing.write_text(
        yaml.dump({"name": "Old", "search": {"titles": ["Writer"], "location": "LA"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        swee, "load_config", lambda path: yaml.safe_load(existing.read_text(encoding="utf-8"))
    )
    captured = {}
    monkeypatch.setattr(swee, "save_profile", lambda data, path: captured.update(data) or str(path))

    swee._setup_headless(
        _headless_args(profile=str(existing), name=None, titles=None, location=None, resume="C:/r.pdf")
    )
    assert captured["name"] == "Old"
    assert captured["search"]["titles"] == ["Writer"]
