import pandas as pd
import pytest

from engine import discovery, resolve


@pytest.fixture(autouse=True)
def _clear_resolver_cache():
    resolve.reset_cache()
    yield
    resolve.reset_cache()


def test_search_url_detection():
    assert resolve.is_search_url("https://www.google.com/search?q=Technical+Writer&udm=8")
    assert resolve.is_search_url("https://www.bing.com/search?q=technical+writer")
    assert not resolve.is_search_url("https://boards.greenhouse.io/figma/jobs/6207950004")
    assert not resolve.is_search_url("https://www.google.com/about/careers/applications/jobs/results/1")
    assert not resolve.is_search_url("")


def test_finds_the_posting_on_the_employers_board(monkeypatch):
    board = [
        ("Senior Software Engineer", "https://boards.greenhouse.io/acme/jobs/1"),
        ("Senior Content Strategist - Freelance", "https://boards.greenhouse.io/acme/jobs/2"),
    ]
    monkeypatch.setattr(resolve, "READERS", (("greenhouse", lambda slug: board),))

    resolved = resolve.resolve_posting_url("Senior Content Strategist", "Acme Media")

    assert resolved == "https://boards.greenhouse.io/acme/jobs/2"


def test_finds_the_posting_under_a_name_inside_the_title(monkeypatch):
    # Google and jobdrop sometimes file a posting under an agency name while the
    # employer appears inside the title.
    board = [("Senior Content Strategist - Freelance", "https://www.akqa.com/jobs/8304891/")]

    def _reader(slug):
        return board if slug == "akqa" else []

    monkeypatch.setattr(resolve, "READERS", (("greenhouse", _reader),))

    resolved = resolve.resolve_posting_url(
        "Senior Content Strategist - Freelance AKQA , NY, US", "Content Creators"
    )

    assert resolved == "https://www.akqa.com/jobs/8304891/"


def test_returns_none_and_caches_a_miss(monkeypatch):
    calls = []

    def _empty(slug):
        calls.append(slug)
        return []

    monkeypatch.setattr(resolve, "READERS", (("greenhouse", _empty),))
    assert resolve.resolve_posting_url("Technical Writer", "No Such Company") is None
    first_round = len(calls)
    assert first_round >= 1

    assert resolve.resolve_posting_url("Technical Writer", "No Such Company") is None
    assert len(calls) == first_round


def test_frame_to_jobs_replaces_a_search_url_with_the_posting(monkeypatch):
    monkeypatch.setattr(
        discovery, "resolve_posting_url",
        lambda title, company: "https://apply.workable.com/j/ABC123",
    )
    frame = pd.DataFrame([{
        "id": "go-1",
        "site": "google",
        "job_url": "https://www.google.com/search?q=Technical+Writer+Acme+job&udm=8",
        "title": "Technical Writer",
        "company": "Acme",
        "location": "New York, NY",
        "description": "",
    }])

    jobs = discovery._frame_to_jobs(frame, location="New York, NY", titles=["Technical Writer"],
                                    filter_titles=True)

    assert jobs[0]["url"] == "https://apply.workable.com/j/ABC123"
    assert jobs[0]["url_unresolved"] is False


def test_frame_to_jobs_keeps_a_search_url_and_flags_it(monkeypatch):
    monkeypatch.setattr(discovery, "resolve_posting_url", lambda title, company: None)
    frame = pd.DataFrame([{
        "id": "go-2",
        "site": "google",
        "job_url": "https://www.google.com/search?q=Technical+Writer+Unknown+Co+job&udm=8",
        "title": "Technical Writer",
        "company": "Unknown Co",
        "location": "New York, NY",
        "description": "",
    }])

    jobs = discovery._frame_to_jobs(frame, location="New York, NY", titles=["Technical Writer"],
                                    filter_titles=True)

    assert jobs[0]["url"].startswith("https://www.google.com/search?q=")
    assert jobs[0]["url_unresolved"] is True


def test_skipped_titles_never_reach_the_resolver(monkeypatch):
    calls = []
    monkeypatch.setattr(discovery, "resolve_posting_url",
                        lambda title, company: calls.append(title) or "https://example.com/job")
    frame = pd.DataFrame([{
        "id": "go-3",
        "site": "google",
        "job_url": "https://www.google.com/search?q=Software+Engineer&udm=8",
        "title": "Software Engineer",
        "company": "Acme",
        "location": "New York, NY",
        "description": "",
    }])

    jobs = discovery._frame_to_jobs(frame, location="New York, NY", titles=["Technical Writer"],
                                    filter_titles=True)

    assert jobs == []
    assert calls == []
