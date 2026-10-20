"""Enabling a newly installed engine in an existing profile."""

import pytest
import yaml

import engine.config as config
from engine.sweep_config import normalize_sources


class _Answer:
    def __init__(self, value):
        self.value = value

    def unsafe_ask(self):
        return self.value


@pytest.fixture(autouse=True)
def promptless(monkeypatch):
    """Keep questionary from reaching for a real console; `_ask` supplies the answers."""
    for name in ("confirm", "text", "checkbox", "password", "select"):
        monkeypatch.setattr(config.questionary, name, lambda *a, **k: _Answer(None))


def _scripted(values):
    queue = list(values)

    def ask(_question):
        if not queue:
            raise AssertionError("wizard asked more questions than expected")
        return queue.pop(0)

    return ask


def _profile(tmp_path):
    path = tmp_path / "profiles" / "alex.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.dump(
            {
                "name": "Alex",
                "search": {"titles": ["Technical Writer"], "location": "New York, NY"},
                "resume": {"path": "C:/resume.pdf"},
                "sources": {"jobspy": {"linkedin": True}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path, yaml.safe_load(path.read_text(encoding="utf-8"))


def test_newly_installed_engine_lands_in_the_profile(tmp_path, monkeypatch):
    path, profile = _profile(tmp_path)

    # A fresh install: the library reports as present, and the profile predates it.
    monkeypatch.setattr(
        config, "engine_status", lambda name: {"installed": True, "core": False}
    )
    monkeypatch.setitem(
        config._ENGINE_PROMPTS, "jobspy", lambda current: current
    )
    monkeypatch.setitem(
        config._ENGINE_PROMPTS,
        "jobdrop",
        lambda current: {"sites": ["wellfound"], "headless": True, "proxies": []},
    )
    monkeypatch.setattr(
        config,
        "_ask",
        _scripted(["Choose engines and settings", ["jobspy", "ats", "jobdrop"], config.BACK_LABEL]),
    )

    assert config._edit_sources(profile) is True
    config.save_profile(profile, str(path))

    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    runtime = normalize_sources(saved)

    assert saved["sources"]["enabled"] == ["jobspy", "ats", "jobdrop"]
    assert saved["sources"]["jobdrop"]["sites"] == ["wellfound"]
    assert runtime["enabled"] == ["jobspy", "ats", "jobdrop"]
    assert runtime["engines"]["jobdrop"]["sites"] == ["wellfound"]
    assert config.validate_sources({"jobdrop": runtime["engines"]["jobdrop"]}) == []


def test_existing_engine_settings_survive_adding_a_new_one(monkeypatch):
    profile = {
        "sources": {
            "enabled": ["jobspy"],
            "jobspy": {"sites": ["linkedin"], "fetch_descriptions": False},
        }
    }
    monkeypatch.setattr(
        config, "engine_status", lambda name: {"installed": True, "core": False}
    )
    monkeypatch.setitem(config._ENGINE_PROMPTS, "jobspy", lambda current: current)
    monkeypatch.setitem(
        config._ENGINE_PROMPTS, "openroles", lambda current: {"companies": ["figma"]}
    )
    monkeypatch.setattr(
        config,
        "_ask",
        _scripted(["Choose engines and settings", ["jobspy", "openroles"], config.BACK_LABEL]),
    )

    config._edit_sources(profile)

    assert profile["sources"]["enabled"] == ["jobspy", "openroles"]
    assert profile["sources"]["jobspy"]["fetch_descriptions"] is False
    assert profile["sources"]["jobspy"]["sites"] == ["linkedin"]
    assert profile["sources"]["openroles"]["companies"] == ["figma"]


def test_installing_an_engine_does_not_silently_enable_it(monkeypatch, caplog):
    """Downloading is separate from enabling, so a sweep's source list stays deliberate."""
    monkeypatch.setattr(config, "missing_engines", lambda **kwargs: ["jobdrop"])
    monkeypatch.setattr(
        config, "_ask", _scripted(["Install all missing engines", True, config.BACK_LABEL])
    )
    monkeypatch.setattr(
        config,
        "install_engines",
        lambda names, echo=None: {names[0]: {"installed": True}},
    )
    profile = {"sources": {"enabled": ["jobspy"]}}

    with caplog.at_level("INFO", logger="sweepy.engine.config"):
        config._manage_engines()

    assert profile["sources"]["enabled"] == ["jobspy"]
    assert "Manage job engines" in caplog.text


def test_engine_choice_label_marks_an_installed_engine(monkeypatch):
    monkeypatch.setattr(
        config, "engine_status", lambda name: {"installed": True, "core": False}
    )
    label = config._engine_choice_label("jobdrop")
    assert "[installed]" in label
    assert "download" not in label


def test_validation_flags_an_engine_whose_library_is_missing(monkeypatch):
    import engine.engines as engines

    monkeypatch.setattr(
        engines,
        "engine_status",
        lambda name: {
            "name": name,
            "installed": False,
            "core": False,
            "package": name,
            "detail": f'Run: pip install "{name}"',
        },
    )
    errors = config.validate_sources({"jobdrop": {"sites": ["linkedin"]}}, check_installed=True)
    assert errors and "pip install" in errors[0]
