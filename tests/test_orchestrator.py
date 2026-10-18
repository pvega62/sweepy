import threading
import time

import pandas as pd
import pytest

from engine.adapters.base import ScraperAdapter
from engine.cache import ResultCache
from engine.circuit_breaker import CircuitBreaker
from engine.discovery import scrape_all, scrape_all_sync


class _Fast(ScraperAdapter):
    name = "fast"

    def scrape(self, query, config):
        return pd.DataFrame([{"title": "Writer", "url": "https://example.com/1"}])


class _Other(ScraperAdapter):
    name = "other"

    def scrape(self, query, config):
        return pd.DataFrame([{"title": "Editor", "url": "https://example.com/2"}])


class _Slow(ScraperAdapter):
    name = "slow"

    def scrape(self, query, config):
        time.sleep(2)
        return pd.DataFrame([{"title": "Late", "url": "https://example.com/3"}])


class _Broken(ScraperAdapter):
    name = "broken"

    def scrape(self, query, config):
        raise RuntimeError("endpoint exploded")


@pytest.fixture
def registry(monkeypatch):
    import engine.discovery as discovery

    adapters = {
        "fast": _Fast(),
        "other": _Other(),
        "slow": _Slow(),
        "broken": _Broken(),
    }
    monkeypatch.setattr(discovery, "ADAPTERS", adapters)
    return adapters


def test_timeout_isolates_one_hanging_engine(registry):
    frame, skipped = scrape_all_sync(
        {"keywords": "writer"},
        ["fast", "other", "slow"],
        {},
        timeout_per_source=0.3,
        use_cache=False,
        circuit=CircuitBreaker(),
    )
    assert len(frame) == 2
    assert skipped == [{"name": "slow", "reason": "timeout"}]


def test_failure_is_reported_without_losing_other_results(registry):
    frame, skipped = scrape_all_sync(
        {"keywords": "writer"},
        ["fast", "broken"],
        {},
        use_cache=False,
        circuit=CircuitBreaker(),
    )
    assert len(frame) == 1
    assert skipped[0]["name"] == "broken"
    assert "exploded" in skipped[0]["reason"]


def test_circuit_opens_after_repeated_failures(registry):
    circuit = CircuitBreaker(failure_threshold=2, cooldown=30)
    for _ in range(2):
        scrape_all_sync(
            {"keywords": "writer"}, ["broken"], {}, use_cache=False, circuit=circuit
        )

    frame, skipped = scrape_all_sync(
        {"keywords": "writer"}, ["broken"], {}, use_cache=False, circuit=circuit
    )
    assert frame.empty
    assert skipped == [{"name": "broken", "reason": "circuit_open"}]


def test_circuit_breaker_resets_after_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, cooldown=0.01)
    breaker.record_failure("jobspy")
    assert breaker.is_open("jobspy") is True
    time.sleep(0.02)
    assert breaker.is_open("jobspy") is False
    assert breaker.failure_count("jobspy") == 0


def test_cache_hit_skips_scrape(registry, tmp_path, monkeypatch):
    calls = []

    class Counting(_Fast):
        def scrape(self, query, config):
            calls.append(query)
            return super().scrape(query, config)

    monkeypatch.setitem(registry, "fast", Counting())
    cache = ResultCache(path=str(tmp_path / "cache.db"), ttl=60)
    query = {"keywords": "writer"}

    first, _ = scrape_all_sync(query, ["fast"], {}, cache=cache)
    second, _ = scrape_all_sync(query, ["fast"], {}, cache=cache)

    assert len(calls) == 1
    pd.testing.assert_frame_equal(first, second)


def test_cache_key_changes_with_engine_config(registry, tmp_path, monkeypatch):
    calls = []

    class Counting(_Fast):
        def scrape(self, query, config):
            calls.append(config)
            return super().scrape(query, config)

    monkeypatch.setitem(registry, "fast", Counting())
    cache = ResultCache(path=str(tmp_path / "cache.db"), ttl=60)

    scrape_all_sync({"keywords": "writer"}, ["fast"], {"fast": {"sites": ["a"]}}, cache=cache)
    scrape_all_sync({"keywords": "writer"}, ["fast"], {"fast": {"sites": ["b"]}}, cache=cache)
    assert len(calls) == 2


def test_unknown_source_is_skipped(registry):
    frame, skipped = scrape_all_sync(
        {"keywords": "writer"}, ["mystery"], {}, use_cache=False, circuit=CircuitBreaker()
    )
    assert frame.empty
    assert skipped == [{"name": "mystery", "reason": "unknown source"}]


def test_duplicate_urls_collapse_across_engines(registry):
    class Clone(_Other):
        name = "clone"

        def scrape(self, query, config):
            return pd.DataFrame([{"title": "Writer", "url": "https://example.com/1"}])

    registry["clone"] = Clone()
    frame, _ = scrape_all_sync(
        {"keywords": "writer"},
        ["fast", "clone"],
        {},
        use_cache=False,
        circuit=CircuitBreaker(),
    )
    assert len(frame) == 1
    assert set(frame["source"]) == {"fast"}


def test_frame_to_jobs_labels_platforms_per_engine():
    from engine.discovery import _frame_to_jobs

    frame = pd.DataFrame(
        [
            {"title": "W", "url": "https://www.linkedin.com/jobs/view/1", "source": "jobspy", "site": "linkedin"},
            {"title": "W", "url": "https://jobs.lever.co/x/3", "source": "openroles", "board": "greenhouse:figma"},
            {"title": "W", "url": "https://example.com/4", "source": "apify"},
        ]
    )
    platforms = [job["platform"] for job in _frame_to_jobs(frame, location="NYC")]
    assert platforms == ["Linkedin", "Lever", "Apify"]


def test_normalized_frame_keeps_common_columns(registry):
    frame, _ = scrape_all_sync(
        {"keywords": "writer"}, ["fast"], {}, use_cache=False, circuit=CircuitBreaker()
    )
    from engine.normalize import COMMON_COLUMNS

    assert list(frame.columns)[: len(COMMON_COLUMNS)] == COMMON_COLUMNS


def test_async_entry_point_runs(registry):
    import asyncio

    frame, skipped = asyncio.run(
        scrape_all(
            {"keywords": "writer"},
            ["fast"],
            {},
            use_cache=False,
            circuit=CircuitBreaker(),
        )
    )
    assert len(frame) == 1
    assert skipped == []


def test_concurrency_semaphore_limits_parallel_calls():
    active = {"count": 0, "peak": 0}
    lock = threading.Lock()

    class Narrow(ScraperAdapter):
        name = "narrow"
        default_concurrency = 1

        def scrape(self, query, config):
            with lock:
                active["count"] += 1
                active["peak"] = max(active["peak"], active["count"])
            time.sleep(0.1)
            with lock:
                active["count"] -= 1
            return pd.DataFrame([{"title": "x", "url": "https://example.com/x"}])

    import engine.discovery as discovery

    original = discovery.ADAPTERS
    discovery.ADAPTERS = {"narrow": Narrow()}
    try:
        for _ in range(3):
            scrape_all_sync(
                {"keywords": "writer"}, ["narrow"], {}, use_cache=False, circuit=CircuitBreaker()
            )
    finally:
        discovery.ADAPTERS = original

    assert active["peak"] == 1
