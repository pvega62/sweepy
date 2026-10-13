import engine.discovery as discovery
from engine.sources.ashby import normalize as normalize_ashby
from engine.sources.builtinnyc import parse_jobs
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
