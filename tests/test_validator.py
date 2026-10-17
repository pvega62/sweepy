import logging
from unittest.mock import patch

import pytest
import requests

from engine import validator


class FakeResponse:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def test_soft_404_ashby():
    head = FakeResponse(200, "", {})
    body = FakeResponse(200, "window.__appData.posting = null; render", {})
    with patch("requests.head", return_value=head), patch("requests.get", return_value=body):
        assert validator.is_valid_url("https://jobs.ashbyhq.com/x/123") is False


def test_dead_link_404():
    with patch("requests.head", return_value=FakeResponse(404, "", {})):
        assert validator.is_valid_url("https://example.com/job/1") is False


def test_valid_url():
    with patch("requests.head", return_value=FakeResponse(200, "", {"content-length": "4321"})):
        assert validator.is_valid_url("https://example.com/job/2") is True


def test_timeout_keeps_job_as_unverified():
    jobs = [{"url": "https://example.com/job/1", "title": "T"}]
    with patch("requests.head", side_effect=requests.Timeout("timeout")):
        valid, expired = validator.filter_valid_jobs(jobs)
    assert expired == 0
    assert valid[0]["unverified"] is True


def test_connection_error_prunes_job():
    jobs = [{"url": "https://example.com/job/1", "title": "T"}]
    with patch("requests.head", side_effect=requests.ConnectionError("boom")):
        valid, expired = validator.filter_valid_jobs(jobs)
    assert expired == 1
    assert valid == []


def test_parallel_preserves_order_and_completes_quickly():
    jobs = [{"url": f"https://example.com/job/{i}", "title": str(i)} for i in range(200)]
    with patch("requests.head", return_value=FakeResponse(200, "", {"content-length": "10"})):
        valid, expired = validator.filter_valid_jobs(jobs)
    assert expired == 0
    assert [j["title"] for j in valid] == [str(i) for i in range(200)]


def test_rate_limited_head_is_kept_unverified(caplog):
    job = {"url": "https://www.linkedin.com/jobs/view/4012345", "title": "T"}
    with patch("requests.head", return_value=FakeResponse(429, "", {})):
        assert validator.check_url(job["url"]) == "unverified"
        assert validator.is_valid_url(job["url"]) is True
        with caplog.at_level(logging.INFO, logger="sweepy.engine.validator"):
            valid, expired = validator.filter_valid_jobs([job])
    assert expired == 0
    assert valid[0]["unverified"] is True
    assert "HTTP 429" in caplog.text
    assert job["url"] in caplog.text


def test_forbidden_is_kept_unverified():
    job = {"url": "https://www.indeed.com/viewjob?jk=abc123", "title": "T"}
    with patch("requests.head", return_value=FakeResponse(403, "", {})):
        assert validator.check_url(job["url"]) == "unverified"
        assert validator.is_valid_url(job["url"]) is True
        valid, expired = validator.filter_valid_jobs([job])
    assert expired == 0
    assert valid[0]["unverified"] is True


def test_server_error_is_kept_unverified():
    job = {"url": "https://www.glassdoor.com/job-listing/x", "title": "T"}
    with patch("requests.head", return_value=FakeResponse(503, "", {})):
        assert validator.check_url(job["url"]) == "unverified"
        assert validator.is_valid_url(job["url"]) is True
        valid, expired = validator.filter_valid_jobs([job])
    assert expired == 0
    assert valid[0]["unverified"] is True


def test_genuine_404_is_dead():
    job = {"url": "https://example.com/job/gone", "title": "T"}
    with patch("requests.head", return_value=FakeResponse(404, "", {})):
        assert validator.check_url(job["url"]) == "dead"
        assert validator.is_valid_url(job["url"]) is False
        valid, expired = validator.filter_valid_jobs([job])
    assert expired == 1
    assert valid == []


def test_transient_statuses_cover_rate_limit_and_block_codes():
    assert validator._UNVERIFIED_STATUSES == {403, 408, 425, 429, 500, 502, 503, 504}
    assert 404 not in validator._UNVERIFIED_STATUSES
    assert 410 not in validator._UNVERIFIED_STATUSES


@pytest.mark.parametrize("status", sorted(validator._UNVERIFIED_STATUSES))
def test_every_unverified_status_keeps_the_posting(status):
    job = {"url": "https://boards.example.com/jobs/42", "title": "T"}
    with patch("requests.head", return_value=FakeResponse(status, "", {})):
        assert validator.check_url(job["url"]) == "unverified"
        assert validator.is_valid_url(job["url"]) is True
        valid, expired = validator.filter_valid_jobs([job])
    assert expired == 0
    assert valid[0]["unverified"] is True


@pytest.mark.parametrize("status", [404, 410, 451])
def test_definitely_gone_statuses_are_dead(status):
    job = {"url": "https://boards.example.com/jobs/43", "title": "T"}
    with patch("requests.head", return_value=FakeResponse(status, "", {})):
        assert validator.check_url(job["url"]) == "dead"
        assert validator.is_valid_url(job["url"]) is False
        valid, expired = validator.filter_valid_jobs([job])
    assert expired == 1
    assert valid == []
