import sys
import types

import pandas as pd
import pytest

from engine.adapters import ADAPTERS
from engine.adapters.base import ScraperAdapter, supported_kwargs
from engine.adapters.hirehunt_adapter import HireHuntAdapter
from engine.adapters.jobspy_adapter import JobSpyAdapter
from engine.adapters.openroles_adapter import OpenRolesAdapter


class _Dummy(ScraperAdapter):
    name = "dummy"

    def scrape(self, query, config):
        return pd.DataFrame([{"title": query["keywords"]}])


def test_registry_exposes_every_engine():
    assert list(ADAPTERS) == ["jobspy", "ats", "hirehunt", "openroles", "jobdrop", "apify"]
    assert all(isinstance(adapter, ScraperAdapter) for adapter in ADAPTERS.values())


def test_base_preflight_drops_unsupported_proxies():
    cfg = _Dummy().preflight({"proxies": ["host:1"], "user_agent": "UA"})
    assert cfg["proxies"] == []
    assert "user_agent" not in cfg


def test_jobspy_preflight_rejects_non_list_proxies():
    with pytest.raises(ValueError):
        JobSpyAdapter().preflight({"proxies": "host:1"})


def test_jobspy_preflight_defaults_descriptions_on():
    cfg = JobSpyAdapter().preflight({})
    assert cfg["fetch_descriptions"] is True
    assert cfg["sites"] == ["linkedin", "indeed", "glassdoor", "zip_recruiter"]


def test_jobspy_accepts_legacy_board_booleans():
    cfg = JobSpyAdapter().preflight({"linkedin": True, "indeed": False})
    assert cfg["sites"] == ["linkedin", "glassdoor", "zip_recruiter"]


def test_openroles_requires_companies():
    with pytest.raises(ValueError, match="companies"):
        OpenRolesAdapter().preflight({"companies": []})
    assert OpenRolesAdapter().preflight({"companies": ["figma"]})["companies"] == ["figma"]


def test_hirehunt_declares_no_proxy_support():
    adapter = HireHuntAdapter()
    assert adapter.supports_proxies is False
    assert adapter.preflight({"proxies": ["host:1"]})["proxies"] == []


def test_missing_library_raises_actionable_error(monkeypatch):
    adapter = HireHuntAdapter()
    monkeypatch.setattr("importlib.import_module", _raise_import_error)
    with pytest.raises(ValueError, match="pip install"):
        adapter.require_library()


def _raise_import_error(name):
    raise ImportError(name)


def test_supported_kwargs_filters_unknown_keys():
    def scrape(a, b=1):
        return a, b

    assert supported_kwargs(scrape, {"a": 1, "b": 2, "c": 3}) == {"a": 1, "b": 2}


def test_supported_kwargs_keeps_everything_for_var_kwargs():
    def scrape(**kwargs):
        return kwargs

    assert supported_kwargs(scrape, {"a": None, "b": 2}) == {"b": 2}


def _install_fake_module(monkeypatch, name, module):
    monkeypatch.setitem(sys.modules, name, module)


def test_hirehunt_scrape_flattens_jobs(monkeypatch):
    job = types.SimpleNamespace(
        title="Technical Writer",
        company="Acme",
        location="Remote",
        job_url="https://example.com/1",
        description="Write docs",
        date_posted="2026-10-01",
        work_mode="remote",
        salary=types.SimpleNamespace(min_amount=1, max_amount=2, currency="USD"),
        source="linkedin",
    )
    result = types.SimpleNamespace(jobs=[job], errors=[])
    fake = types.SimpleNamespace(
        scrape_jobs=lambda **kwargs: result,
    )
    _install_fake_module(monkeypatch, "hirehunt", fake)

    frame = HireHuntAdapter().scrape({"keywords": "writer", "limit": 5}, {})
    assert list(frame.columns)[:4] == ["title", "company", "location", "job_url"]
    assert bool(frame.iloc[0]["is_remote"]) is True


def test_openroles_scrape_reads_each_board(monkeypatch):
    class Job:
        def to_dict(self):
            return {"title": "Writer", "url": "https://example.com/x", "location": "NYC"}

    seen = []

    def fetch(board, **kwargs):
        seen.append(board)
        return [Job()]

    _install_fake_module(monkeypatch, "openroles", types.SimpleNamespace(fetch=fetch))
    frame = OpenRolesAdapter().scrape(
        {"keywords": "writer"}, {"ats": ["greenhouse"], "companies": ["figma"]}
    )
    assert seen == ["greenhouse:figma"]
    assert frame.iloc[0]["board"] == "greenhouse:figma"


def test_openroles_isolates_a_broken_board(monkeypatch):
    def fetch(board, **kwargs):
        raise RuntimeError("board unavailable")

    _install_fake_module(monkeypatch, "openroles", types.SimpleNamespace(fetch=fetch))
    frame = OpenRolesAdapter().scrape(
        {"keywords": "writer"}, {"ats": ["lever"], "companies": ["nope"]}
    )
    assert frame.empty
