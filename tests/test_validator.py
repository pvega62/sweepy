from unittest.mock import patch

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
