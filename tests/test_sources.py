import os

import pandas as pd
import requests

import engine.discovery as discovery
import engine.sources as sources
import engine.sources.ashby as ashby
from engine.sources.ashby import fetch_ashby_org
from engine.sources.ashby import normalize as normalize_ashby
from engine.sources.builtinnyc import parse_jobs
from engine.sources.greenhouse import normalize as normalize_greenhouse
from engine.sources.lever import normalize as normalize_lever
from engine.sources.workable import normalize as normalize_workable


def _ashby_job(**overrides):
    job = {
        "id": "9b33ebe7",
        "title": "Technical Writer",
        "department": "Engineering",
        "employmentType": "FullTime",
        "location": "New York",
        "isRemote": False,
        "workplaceType": "OnSite",
        "publishedAt": "2024-10-23T20:10:46Z",
        "jobUrl": "https://jobs.ashbyhq.com/modal/9b33ebe7",
        "applyUrl": "https://jobs.ashbyhq.com/modal/9b33ebe7/application",
        "descriptionPlain": "About us.",
        "compensation": {
            "compensationTiers": [
                {"components": [
                    {"compensationType": "Salary", "currencyCode": "USD", "minValue": 100000, "maxValue": 120000},
                ]}
            ]
        },
    }
    job.update(overrides)
    return job


def test_ashby_normalize_fields():
    job = normalize_ashby(_ashby_job(), "modal")
    assert job["platform"] == "Ashby"
    assert job["title"] == "Technical Writer"
    assert job["company"] == "Modal"
    assert job["department"] == "Engineering"
    assert job["url"] == "https://jobs.ashbyhq.com/modal/9b33ebe7"
    assert job["min_amount"] == 100000.0
    assert job["max_amount"] == 120000.0
    assert job["currency"] == "USD"
    assert job["remote"] is False


def test_ashby_normalize_remote():
    job = normalize_ashby(_ashby_job(isRemote=True, workplaceType="Remote"), "modal")
    assert job["remote"] is True
    assert "(Remote)" in job["location"]


def test_ashby_normalize_skips_missing_url():
    assert normalize_ashby(_ashby_job(jobUrl=""), "modal") is None


def test_ashby_fetch_404_returns_empty(monkeypatch):
    class _Resp:
        status_code = 404

        def raise_for_status(self):
            raise requests.HTTPError("404 Not Found")

    monkeypatch.setattr(ashby.requests, "get", lambda *a, **k: _Resp())
    assert fetch_ashby_org("stale-org") == []


def test_ashby_seed_orgs_are_clean_and_drop_stale_slugs():
    path = os.path.join(sources.DATA_DIR, "ashby_orgs.txt")
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    assert raw_lines[0].startswith("#")
    tokens = [line.strip() for line in raw_lines if line.strip() and not line.strip().startswith("#")]
    assert tokens == sources.load_ashby_orgs()
    assert all(" " not in token for token in tokens)
    assert not {"stripe", "google-deepmind", "braze"} & set(tokens)


def _workable_job(**overrides):
    job = {
        "title": "UX Writer",
        "shortcode": "ABC123",
        "telecommuting": True,
        "department": "Design",
        "url": "https://apply.workable.com/j/ABC123",
        "application_url": "https://apply.workable.com/j/ABC123/apply",
        "published_on": "2026-08-27",
        "city": "New York",
        "state": "New York",
        "description": "<p>We are hiring.</p>",
    }
    job.update(overrides)
    return job


def test_workable_normalize_fields():
    job = normalize_workable(_workable_job(), "Acme")
    assert job["platform"] == "Workable"
    assert job["company"] == "Acme"
    assert job["department"] == "Design"
    assert job["url"] == "https://apply.workable.com/j/ABC123"
    assert job["remote"] is True
    assert "We are hiring." in job["description"]


def test_workable_normalize_skips_missing_url():
    assert normalize_workable(_workable_job(url="", shortcode=""), "Acme") is None


def test_builtin_parse_ashby_outbound_link():
    html = '<div><a href="https://jobs.ashbyhq.com/foo/123">Technical Writer</a></div>'
    jobs = parse_jobs(html)
    assert len(jobs) == 1
    assert jobs[0]["platform"] == "Ashby"
    assert jobs[0]["title"] == "Technical Writer"
    assert jobs[0]["url"] == "https://jobs.ashbyhq.com/foo/123"


def test_builtin_parse_relative_job_link():
    html = '<div><a href="/job/technical-writer">Technical Writer</a></div>'
    jobs = parse_jobs(html, "https://www.builtinnyc.com")
    assert jobs[0]["url"] == "https://www.builtinnyc.com/job/technical-writer"
    assert jobs[0]["platform"] == "Built In NYC"


def test_discover_sources_merges_and_dedupes(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    monkeypatch.setattr(discovery, "load_ashby_orgs", lambda: ["modal"])
    monkeypatch.setattr(discovery, "load_workable_slugs", lambda: [])
    monkeypatch.setattr(discovery, "load_greenhouse_boards", lambda: [])
    monkeypatch.setattr(discovery, "load_lever_companies", lambda: [])
    monkeypatch.setattr(discovery, "load_builtin_categories", lambda: [])
    monkeypatch.setattr(
        discovery, "fetch_ashby_org", lambda org: [normalize_ashby(_ashby_job(), org)]
    )

    jobs, counts = discovery.discover_sources(
        {"ashby": {"orgs": []}, "builtinnyc": {"enabled": False}},
        titles=["technical"],
        location="",
    )
    assert len(jobs) == 1
    assert counts.get("Ashby") == 1


def test_discover_sources_isolates_failures(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    monkeypatch.setattr(discovery, "load_ashby_orgs", lambda: ["good", "bad"])
    monkeypatch.setattr(discovery, "load_workable_slugs", lambda: [])
    monkeypatch.setattr(discovery, "load_greenhouse_boards", lambda: [])
    monkeypatch.setattr(discovery, "load_lever_companies", lambda: [])
    monkeypatch.setattr(discovery, "load_builtin_categories", lambda: [])

    def flaky(org):
        if org == "bad":
            raise RuntimeError("boom")
        return [normalize_ashby(_ashby_job(), org)]

    monkeypatch.setattr(discovery, "fetch_ashby_org", flaky)
    jobs, counts = discovery.discover_sources(
        {"builtinnyc": {"enabled": False}}, titles=["technical"], location=""
    )
    assert len(jobs) == 1


def _greenhouse_job(**overrides):
    job = {
        "id": 123,
        "title": "Technical Writer",
        "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/123",
        "company_name": "GitLab",
        "location": {"name": "Remote, France"},
        "first_published": "2026-10-02T11:31:50-04:00",
        "updated_at": "2026-10-03T00:00:00-04:00",
        "departments": [{"name": "Documentation"}],
        "content": "",
        "metadata": [],
    }
    job.update(overrides)
    return job


def test_greenhouse_normalize_fields():
    job = normalize_greenhouse(_greenhouse_job(), "gitlab")
    assert job["platform"] == "Greenhouse"
    assert job["title"] == "Technical Writer"
    assert job["company"] == "GitLab"
    assert job["department"] == "Documentation"
    assert job["url"] == "https://boards.greenhouse.io/gitlab/jobs/123"
    assert job["location"] == "Remote, France"
    assert job["remote"] is True
    assert job["workplace_type"] == "Remote"
    assert job["date_posted"] == "2026-10-02T11:31:50-04:00"


def test_greenhouse_company_falls_back_to_board():
    job = normalize_greenhouse(_greenhouse_job(company_name=""), "acme-corp")
    assert job["company"] == "Acme Corp"


def test_greenhouse_unescapes_and_strips_content():
    escaped = "&lt;p&gt;Write &amp; edit &lt;strong&gt;docs&lt;/strong&gt;.&lt;/p&gt;"
    job = normalize_greenhouse(_greenhouse_job(content=escaped), "gitlab")
    assert "Write & edit" in job["description"]
    assert "docs" in job["description"]
    assert "<p>" not in job["description"]
    assert "&lt;" not in job["description"]
    assert "&amp;" not in job["description"]


def test_greenhouse_parses_metadata_pay_range():
    job = normalize_greenhouse(
        _greenhouse_job(metadata=[{"name": "Salary Range", "value": "$100,000 - $120,000"}]),
        "gitlab",
    )
    assert job["min_amount"] == 100000.0
    assert job["max_amount"] == 120000.0
    assert job["currency"] == "USD"


def test_greenhouse_normalize_skips_missing_url():
    assert normalize_greenhouse(_greenhouse_job(absolute_url=""), "gitlab") is None


def _lever_job(**overrides):
    job = {
        "id": "abc123",
        "text": "UX Writer",
        "hostedUrl": "https://jobs.lever.co/leverdemo/abc123",
        "applyUrl": "https://jobs.lever.co/leverdemo/abc123/apply",
        "categories": {
            "location": "Atlanta, Georgia",
            "commitment": "Regular Full Time (Salary)",
            "department": "Customer Success",
            "team": "Customer Success Team",
        },
        "workplaceType": "hybrid",
        "createdAt": 1788199939703,
        "description": "<p>We are hiring.</p>",
        "descriptionPlain": "We are hiring.",
        "salaryRange": {"min": 85000, "max": 175000, "currency": "USD", "interval": "per-year-salary"},
    }
    job.update(overrides)
    return job


def test_lever_normalize_fields():
    job = normalize_lever(_lever_job(), "leverdemo")
    assert job["platform"] == "Lever"
    assert job["title"] == "UX Writer"
    assert job["company"] == "Lever"
    assert job["department"] == "Customer Success"
    assert job["location"] == "Atlanta, Georgia"
    assert job["job_type"] == "Regular Full Time (Salary)"
    assert job["workplace_type"] == "hybrid"
    assert job["remote"] is False
    assert job["date_posted"].startswith("2026-")
    assert job["date_posted"].endswith("Z")


def test_lever_normalize_remote_prefers_plain_description():
    job = normalize_lever(
        _lever_job(
            workplaceType="remote",
            categories={"location": "Austin", "commitment": "Full Time", "team": "Design"},
            descriptionPlain="Plain body.",
            description="<p>HTML body.</p>",
        ),
        "leverdemo",
    )
    assert job["remote"] is True
    assert job["workplace_type"] == "remote"
    assert job["location"] == "Austin (Remote)"
    assert job["department"] == "Design"
    assert job["description"] == "Plain body."


def test_lever_normalize_falls_back_to_html_description():
    job = normalize_lever(_lever_job(descriptionPlain="", description="<p>HTML body.</p>"), "leverdemo")
    assert "HTML body." in job["description"]


def test_lever_parses_salary_range():
    job = normalize_lever(_lever_job(), "leverdemo")
    assert job["min_amount"] == 85000.0
    assert job["max_amount"] == 175000.0
    assert job["currency"] == "USD"


def test_lever_company_falls_back_to_slug():
    job = normalize_lever(_lever_job(), "acme-corp")
    assert job["company"] == "Acme Corp"


def test_lever_normalize_skips_missing_url():
    assert normalize_lever(_lever_job(hostedUrl="", applyUrl=""), "leverdemo") is None


def _patch_seed_loaders(monkeypatch, **overrides):
    values = {
        "load_ashby_orgs": [],
        "load_workable_slugs": [],
        "load_greenhouse_boards": [],
        "load_lever_companies": [],
        "load_builtin_categories": [],
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setattr(discovery, name, lambda v=value: v)


def test_discover_sources_includes_greenhouse_and_lever(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    _patch_seed_loaders(
        monkeypatch,
        load_greenhouse_boards=["gitlab"],
        load_lever_companies=["leverdemo"],
    )
    seen = {}

    def fake_greenhouse(board, titles=None):
        seen["greenhouse"] = (board, titles)
        return [normalize_greenhouse(_greenhouse_job(), board)]

    def fake_lever(company, titles=None):
        seen["lever"] = (company, titles)
        return [normalize_lever(_lever_job(), company)]

    monkeypatch.setattr(discovery, "fetch_greenhouse_board", fake_greenhouse)
    monkeypatch.setattr(discovery, "fetch_lever_company", fake_lever)

    _, counts = discovery.discover_sources({}, titles=["writer"], platforms={})
    assert seen["greenhouse"] == ("gitlab", ["writer"])
    assert seen["lever"] == ("leverdemo", ["writer"])
    assert counts.get("Greenhouse") == 1
    assert counts.get("Lever") == 1


def test_discover_sources_empty_list_falls_back_to_seed(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    _patch_seed_loaders(monkeypatch, load_greenhouse_boards=["seedboard"])
    seen = []

    def fake_greenhouse(board, titles=None):
        seen.append(board)
        return [normalize_greenhouse(_greenhouse_job(), board)]

    monkeypatch.setattr(discovery, "fetch_greenhouse_board", fake_greenhouse)
    discovery.discover_sources({"greenhouse": {"boards": []}}, titles=["technical"])
    assert seen == ["seedboard"]


def test_discover_sources_explicit_list_replaces_seed(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    _patch_seed_loaders(monkeypatch, load_greenhouse_boards=["seedboard"])
    seen = []
    monkeypatch.setattr(
        discovery, "fetch_greenhouse_board", lambda board, titles=None: seen.append(board) or []
    )
    discovery.discover_sources({"greenhouse": {"boards": ["explicit"]}}, titles=["technical"])
    assert seen == ["explicit"]


def test_discover_sources_platform_flag_disables_source(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    _patch_seed_loaders(monkeypatch, load_greenhouse_boards=["gitlab"])
    calls = []
    monkeypatch.setattr(
        discovery, "fetch_greenhouse_board", lambda board, titles=None: calls.append(board) or []
    )
    _, counts = discovery.discover_sources(
        {}, titles=["technical"], platforms={"greenhouse": False}
    )
    assert calls == []
    assert "Greenhouse" not in counts


def test_discover_sources_enabled_false_disables_source(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    _patch_seed_loaders(monkeypatch, load_greenhouse_boards=["gitlab"])
    calls = []
    monkeypatch.setattr(
        discovery, "fetch_greenhouse_board", lambda board, titles=None: calls.append(board) or []
    )
    discovery.discover_sources({"greenhouse": {"enabled": False}}, titles=["technical"])
    assert calls == []


def test_builtin_source_ignores_platforms_key(monkeypatch):
    monkeypatch.setattr(discovery, "_REQUEST_DELAY", 0)
    _patch_seed_loaders(monkeypatch, load_builtin_categories=["jobs/legal"])
    calls = []
    monkeypatch.setattr(discovery, "fetch_builtin", lambda category: calls.append(category) or [])
    discovery.discover_sources({}, titles=["writer"], platforms={"builtinnyc": False})
    assert calls == ["jobs/legal"]


def _pay_frame(description: str, **overrides) -> pd.DataFrame:
    row = {
        "title": "Technical Writer",
        "company": "Acme",
        "location": "New York, NY",
        "url": "https://example.com/jobs/1",
        "description": description,
        "salary_min": 0,
        "salary_max": 0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_frame_to_jobs_reads_pay_from_description():
    jobs = discovery._frame_to_jobs(
        _pay_frame("Base salary: $90,000 - $110,000 per year."), location="New York, NY"
    )
    assert jobs[0]["min_amount"] == 90000.0
    assert jobs[0]["max_amount"] == 110000.0
    assert jobs[0]["currency"] == "USD"
    assert jobs[0]["salary_period"] == "year"


def test_frame_to_jobs_keeps_structured_pay_over_description():
    frame = _pay_frame("Pay: $20 - $25 per hour.", salary_min=100000, salary_max=120000)
    jobs = discovery._frame_to_jobs(frame, location="New York, NY")
    assert jobs[0]["min_amount"] == 100000.0
    assert jobs[0]["max_amount"] == 120000.0
    assert jobs[0]["salary_period"] == "year"


def test_frame_to_jobs_can_skip_description_pay():
    jobs = discovery._frame_to_jobs(
        _pay_frame("Base salary: $90,000 - $110,000 per year."),
        location="New York, NY",
        salary_from_description=False,
    )
    assert jobs[0]["min_amount"] == 0
    assert jobs[0]["max_amount"] == 0


def test_frame_to_jobs_maps_aggregator_interval():
    frame = _pay_frame("", salary_min=45, salary_max=55, interval="hourly")
    jobs = discovery._frame_to_jobs(frame, location="Remote", min_salary=65000)
    assert jobs[0]["salary_period"] == "hour"
    assert [job["title"] for job in jobs] == ["Technical Writer"]


def test_frame_to_jobs_filters_hourly_pay_by_annual_floor():
    kept = discovery._frame_to_jobs(
        _pay_frame("Hourly rate: $45 - $55 per hour."), location="Remote", min_salary=65000
    )
    dropped = discovery._frame_to_jobs(
        _pay_frame("Hourly rate: $20 - $25 per hour."), location="Remote", min_salary=65000
    )
    assert [job["title"] for job in kept] == ["Technical Writer"]
    assert dropped == []

