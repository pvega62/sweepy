import sqlite3
import time

from engine.history import (
    MATCH_URL,
    MATCH_URL_OR_ROLE,
    SweepHistory,
    canonical_url,
    history_scope,
    role_key,
    url_key,
)


def _job(
    title="Technical Writer",
    company="Acme",
    location="Remote",
    url="https://boards.greenhouse.io/acme/jobs/123",
):
    return {"title": title, "company": company, "location": location, "url": url}


def _history(tmp_path, **kwargs):
    return SweepHistory(path=str(tmp_path / "history.db"), **kwargs)


def test_canonical_url_drops_tracking_and_fragment():
    canonical = canonical_url(
        "HTTPS://WWW.Example.com/Jobs/123/?utm_source=linkedin&gh_src=abc#apply"
    )

    assert canonical == "https://example.com/Jobs/123"


def test_canonical_url_keeps_meaningful_query_and_sorts():
    canonical = canonical_url("https://example.com/jobs?b=2&a=1&utm_medium=email")

    assert canonical == "https://example.com/jobs?a=1&b=2"


def test_canonical_url_handles_urls_without_a_scheme():
    assert canonical_url("example.com/jobs/1") == "https://example.com/jobs/1"
    assert canonical_url("") == ""


def test_url_key_ignores_tracking_parameters():
    assert url_key("https://example.com/jobs/1") == url_key(
        "https://www.example.com/jobs/1/?utm_source=newsletter"
    )


def test_role_key_normalizes_punctuation_and_case():
    assert role_key("Sr. Technical Writer", "Acme, Inc.", "New York, NY") == role_key(
        "sr technical writer", "acme inc", "new york ny"
    )
    assert role_key("Writer", "", "NYC") == ""


def test_history_scope_normalizes_a_profile_stem():
    assert history_scope("Pedro Vega Resume") == "pedro_vega_resume"
    assert history_scope("") == "default"


def test_filter_new_skips_reported_postings(tmp_path):
    history = _history(tmp_path)
    job = _job()

    fresh, seen = history.filter_new([job], "profile")

    assert fresh == [job]
    assert seen == []

    history.record([job], "profile", sweep_id="s1")
    fresh, seen = history.filter_new([job], "profile")

    assert fresh == []
    assert seen == [job]


def test_tracking_parameters_do_not_defeat_matching(tmp_path):
    history = _history(tmp_path)
    history.record([_job(url="https://example.com/jobs/1")], "profile")

    noisy = _job(url="https://www.example.com/jobs/1/?utm_source=newsletter")
    fresh, seen = history.filter_new([noisy], "profile")

    assert fresh == []
    assert seen == [noisy]


def test_url_mode_ignores_role_matches(tmp_path):
    history = _history(tmp_path, match=MATCH_URL)
    history.record([_job(url="https://boards.greenhouse.io/acme/jobs/123")], "profile")

    repost = _job(url="https://boards.greenhouse.io/acme/jobs/999")
    fresh, seen = history.filter_new([repost], "profile")

    assert fresh == [repost]
    assert seen == []


def test_role_mode_matches_a_repost_with_a_new_url(tmp_path):
    history = _history(tmp_path, match=MATCH_URL_OR_ROLE)
    history.record([_job(url="https://boards.greenhouse.io/acme/jobs/123")], "profile")

    repost = _job(url="https://boards.greenhouse.io/acme/jobs/999")
    fresh, seen = history.filter_new([repost], "profile")

    assert fresh == []
    assert seen == [repost]


def test_record_preserves_first_seen_and_refreshes_reported(tmp_path):
    path = str(tmp_path / "history.db")
    history = SweepHistory(path=path)
    job = _job()

    history.record([job], "profile", sweep_id="s1")
    with sqlite3.connect(path) as conn:
        first_seen = conn.execute("SELECT first_seen_at FROM seen_jobs").fetchone()[0]

    time.sleep(0.01)
    history.record([job], "profile", sweep_id="s2")
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT first_seen_at, last_reported_at, sweep_id FROM seen_jobs"
        ).fetchone()

    assert row[0] == first_seen
    assert row[1] > first_seen
    assert row[2] == "s2"


def test_prune_drops_rows_outside_the_retention_window(tmp_path):
    path = str(tmp_path / "history.db")
    history = SweepHistory(path=path, retention_days=1)
    history.record([_job()], "profile")

    stale = time.time() - 3 * 86400
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE seen_jobs SET last_seen_at = ?", (stale,))
        conn.commit()

    assert history.prune() == 1
    assert history.stats("profile")["count"] == 0


def test_clear_only_touches_the_requested_scope(tmp_path):
    history = _history(tmp_path)
    history.record([_job()], "one")
    history.record([_job(company="Other")], "two")

    assert history.clear("one") == 1
    assert history.stats("one")["count"] == 0
    assert history.stats("two")["count"] == 1


def test_zero_retention_reports_everything(tmp_path):
    history = _history(tmp_path, retention_days=0)
    job = _job()
    history.record([job], "profile")

    fresh, seen = history.filter_new([job], "profile")

    assert fresh == [job]
    assert seen == []


def test_unreadable_database_degrades_to_no_history(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    history = SweepHistory(path=str(blocker / "history.db"))
    job = _job()

    assert history.filter_new([job], "profile") == ([job], [])
    assert history.record([job], "profile") == 0
    assert history.prune() == 0
    assert history.clear("profile") == 0
    assert history.stats("profile")["count"] == 0
