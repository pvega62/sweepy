import pandas as pd

from engine.engine_defaults import DEFAULT_JOBDROP_SITES, DEFAULT_JOBSPY_SITES
from engine.normalize import COMMON_COLUMNS, dedupe, normalize_all, to_common
from engine.sweep_config import (
    enabled_engine_names,
    migrate_legacy_platforms,
    normalize_sources,
    validate_sources,
)


def test_legacy_profile_defaults_to_jobspy_and_ats():
    profile = {
        "sources": {"jobspy": {"linkedin": True, "indeed": False}},
        "platforms": {"greenhouse": True, "ashby": True, "lever": True, "workable": True},
    }
    runtime = normalize_sources(profile)
    assert runtime["enabled"] == ["jobspy", "ats"]
    assert runtime["legacy_platforms"] is True
    assert runtime["engines"]["jobspy"]["sites"] == ["linkedin", "glassdoor", "zip_recruiter"]


def test_legacy_sites_list_is_preserved():
    runtime = normalize_sources({"sources": {"jobspy": {"sites": ["indeed"]}}})
    assert runtime["engines"]["jobspy"]["sites"] == ["indeed"]


def test_enabled_list_preserves_order():
    runtime = normalize_sources(
        {"sources": {"enabled": ["openroles", "jobspy"], "openroles": {"companies": ["figma"]}}}
    )
    assert runtime["enabled"] == ["jobspy", "openroles"]


def test_enabled_false_disables_an_engine():
    runtime = normalize_sources(
        {"sources": {"enabled": ["jobspy", "jobdrop"], "jobdrop": {"enabled": False}}}
    )
    assert runtime["enabled"] == ["jobspy"]


def test_unknown_engine_warns_and_is_dropped(caplog):
    runtime = normalize_sources({"sources": {"enabled": ["jobspy", "mystery"]}})
    assert runtime["enabled"] == ["jobspy"]
    assert "Unknown job engine" in caplog.text


def test_auto_enable_requires_optional_engine_inputs():
    runtime = normalize_sources({"sources": {"openroles": {"enabled": True}, "apify": {"enabled": True}}})
    assert "openroles" not in runtime["enabled"]
    assert "apify" not in runtime["enabled"]


def test_optional_engines_auto_enable_with_inputs(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "token")
    runtime = normalize_sources(
        {
            "sources": {
                "openroles": {"enabled": True, "companies": ["figma"]},
                "apify": {"enabled": True, "token": "token"},
            }
        }
    )
    assert "openroles" in runtime["enabled"]
    assert "apify" in runtime["enabled"]


def test_cache_and_orchestrator_defaults():
    runtime = normalize_sources({})
    assert runtime["cache"]["enabled"] is True
    assert runtime["cache"]["ttl_seconds"] == 3600
    assert runtime["orchestrator"]["timeout_per_source_seconds"] == 180
    assert runtime["orchestrator"]["circuit_breaker"]["failure_threshold"] == 5


def test_cache_and_orchestrator_overrides():
    runtime = normalize_sources(
        {
            "cache": {"enabled": False, "ttl_seconds": 60},
            "orchestrator": {"timeout_per_source_seconds": 30, "circuit_breaker": {"cooldown_seconds": 5}},
        }
    )
    assert runtime["cache"] == {"enabled": False, "ttl_seconds": 60, "path": None}
    assert runtime["orchestrator"]["timeout_per_source_seconds"] == 30
    assert runtime["orchestrator"]["circuit_breaker"]["failure_threshold"] == 5
    assert runtime["orchestrator"]["circuit_breaker"]["cooldown_seconds"] == 5


def test_migrate_legacy_platforms_list():
    migrated = migrate_legacy_platforms(["linkedin", "indeed"])
    assert migrated == {"enabled": ["jobspy"], "jobspy": {"sites": ["linkedin", "indeed"]}}


def test_migrate_legacy_platforms_empty_falls_back():
    assert migrate_legacy_platforms([])["jobspy"]["sites"] == DEFAULT_JOBSPY_SITES


def test_validate_sources_reports_openroles_companies():
    errors = validate_sources({"openroles": {"companies": []}})
    assert errors and "companies" in errors[0]


def test_validate_sources_accepts_valid_config():
    assert validate_sources({"jobdrop": {"sites": ["linkedin"]}}) == []


def test_enabled_engine_names_helper():
    assert enabled_engine_names({"sources": {"enabled": ["jobdrop"]}}) == ["jobdrop"]
    assert enabled_engine_names({}) == ["jobspy", "ats"]


def test_jobdrop_defaults_are_documented_sites():
    runtime = normalize_sources({"sources": {"enabled": ["jobdrop"]}})
    assert runtime["engines"]["jobdrop"]["sites"] == DEFAULT_JOBDROP_SITES


def test_to_common_maps_aliases_and_keeps_extras():
    frame = pd.DataFrame(
        [{"title": "Writer", "job_url": "https://x", "company_name": "Acme", "platform": "Assay"}]
    )
    common = to_common(frame, "jobspy")
    assert list(common.columns)[: len(COMMON_COLUMNS)] == COMMON_COLUMNS
    assert common.iloc[0]["url"] == "https://x"
    assert common.iloc[0]["company"] == "Acme"
    assert common.iloc[0]["platform"] == "Assay"
    assert common.iloc[0]["source"] == "jobspy"
    assert common.iloc[0]["raw"]["title"] == "Writer"


def test_normalize_all_merges_and_dedupes():
    a = pd.DataFrame(
        [{"title": "Writer", "company": "Acme", "url": "https://x", "location": "NYC"}]
    )
    b = pd.DataFrame(
        [{"title": "Writer", "company": "Acme", "url": "https://x", "location": "NYC", "salary_min": 1}]
    )
    c = pd.DataFrame([{"title": "Editor", "company": "Beta", "url": "https://y"}])
    merged = normalize_all([("jobspy", a, None), ("jobdrop", b, None), ("openroles", c, None)])
    assert len(merged) == 2
    assert set(merged["source"]) == {"jobspy", "openroles"}


def test_normalize_all_skips_failures():
    merged = normalize_all([("jobspy", None, "timeout")])
    assert merged.empty
    assert list(merged.columns) == COMMON_COLUMNS


def test_dedupe_matches_repeated_urls():
    frame = pd.DataFrame(
        [
            {"title": "Writer", "company": "Acme", "location": "NYC", "url": "https://x"},
            {"title": "Writer", "company": "Acme", "location": "NYC", "url": "https://x"},
        ]
    )
    assert len(dedupe(frame)) == 1


def test_dedupe_matches_details_when_url_is_empty():
    frame = pd.DataFrame(
        [
            {"title": "Writer", "company": "Acme", "location": "NYC", "url": ""},
            {"title": "writer", "company": "acme", "location": "nyc", "url": ""},
            {"title": "Writer", "company": "Acme", "location": "NYC", "url": "https://x"},
            {"title": "Writer", "company": "Acme", "location": "NYC", "url": "https://y"},
        ]
    )
    assert len(dedupe(frame)) == 3
