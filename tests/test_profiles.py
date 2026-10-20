import copy
import pathlib

import pytest
import yaml

from engine.config import _answers_from_profile, _merge_answers
from engine.sweep_config import legacy_profile_notice, normalize_sources, validate_sources

PROFILES = sorted(pathlib.Path("profiles").glob("*.y*ml"))


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@pytest.mark.skipif(not PROFILES, reason="no profiles on disk")
@pytest.mark.parametrize("path", PROFILES, ids=[p.name for p in PROFILES])
def test_shipped_profile_resolves_and_validates(path):
    data = _load(path)
    runtime = normalize_sources(data)
    errors = validate_sources({name: runtime["engines"][name] for name in runtime["enabled"]})

    assert errors == []
    assert runtime["enabled"], f"{path.name} enables no engine"
    assert legacy_profile_notice(data) is None


@pytest.mark.skipif(not PROFILES, reason="no profiles on disk")
@pytest.mark.parametrize("path", PROFILES, ids=[p.name for p in PROFILES])
def test_wizard_edit_round_trip_keeps_every_section(path):
    data = _load(path)
    merged = _merge_answers(copy.deepcopy(data), _answers_from_profile(data))

    assert set(data) <= set(merged)
    for key in ("platforms", "sources", "report", "export"):
        if key in data:
            assert merged[key].keys() >= data[key].keys()


@pytest.mark.skipif(not PROFILES, reason="no profiles on disk")
@pytest.mark.parametrize("path", PROFILES, ids=[p.name for p in PROFILES])
def test_profile_cache_and_timeout_settings_are_sane(path):
    runtime = normalize_sources(_load(path))
    cache = runtime["cache"]
    orchestrator = runtime["orchestrator"]

    assert isinstance(cache["enabled"], bool)
    assert int(cache["ttl_seconds"]) >= 0
    assert float(orchestrator["timeout_per_source_seconds"]) > 0
    assert int(orchestrator["circuit_breaker"]["failure_threshold"]) >= 1
