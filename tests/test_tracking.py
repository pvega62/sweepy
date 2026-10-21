import csv
import os

import engine.exporter as exporter
from engine.tracking import (
    TRACKING_COLUMNS,
    backfill,
    carried_count,
    load_previous,
    tracking_enabled,
)


def _jobs():
    return [
        {
            "title": "Technical Writer",
            "company": "Acme",
            "location": "New York, NY",
            "url": "https://example.com/jobs/1?utm_source=x",
            "match_score": 80,
        },
        {
            "title": "UX Writer",
            "company": "Globex",
            "location": "Remote",
            "url": "https://example.com/jobs/2",
            "match_score": 70,
        },
    ]


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_tracking_defaults_on_and_honors_explicit_off():
    assert tracking_enabled(None) is True
    assert tracking_enabled({}) is True
    assert tracking_enabled({"tracking": False}) is False
    assert tracking_enabled({"tracking": "false"}) is False
    assert tracking_enabled({"tracking": "yes"}) is True


def test_export_appends_tracking_columns_when_enabled(tmp_path):
    path = str(tmp_path / "sweep.csv")

    rows, cols = exporter.export_to_csv(_jobs(), path, tracking=True)

    header = list(_read_csv(path)[0].keys())
    assert (rows, cols) == (2, len(header))
    assert header[-len(TRACKING_COLUMNS):] == TRACKING_COLUMNS
    assert header[header.index("description") + 1] == TRACKING_COLUMNS[0]
    assert all(_read_csv(path)[0][col] == "" for col in TRACKING_COLUMNS)


def test_export_keeps_raw_columns_when_disabled(tmp_path):
    path = str(tmp_path / "sweep.csv")

    exporter.export_to_csv(_jobs(), path)

    header = list(_read_csv(path)[0].keys())
    assert header == exporter.EXPORT_COLUMNS
    assert "date_applied" not in header


def test_previous_values_carry_into_the_next_export(tmp_path):
    first = str(tmp_path / "profile_2026-10-19-101010.csv")
    exporter.export_to_csv(_jobs(), first, tracking=True)

    with open(first, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["status"] = "Applied"
    rows[0]["date_applied"] = "2026-10-19"
    rows[0]["notes"] = "Recruiter reached out"
    with open(first, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    previous = load_previous(str(tmp_path), "profile")
    second = str(tmp_path / "profile_2026-10-20-101010.csv")
    exporter.export_to_csv(_jobs(), second, tracking=True, previous=previous)

    filled = _read_csv(second)
    assert filled[0]["status"] == "Applied"
    assert filled[0]["date_applied"] == "2026-10-19"
    assert filled[0]["notes"] == "Recruiter reached out"
    assert filled[1]["status"] == ""


def test_newest_export_wins_and_url_tracking_params_still_match(tmp_path):
    newer = str(tmp_path / "profile_2026-10-20-090000.csv")
    older = str(tmp_path / "profile_2026-10-19-090000.csv")
    header = exporter.EXPORT_COLUMNS + TRACKING_COLUMNS

    def _write(path, status, mtime):
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerow(
                {
                    "title": "Technical Writer",
                    "company": "Acme",
                    "location": "New York, NY",
                    "url": "https://example.com/jobs/1?utm_campaign=fall",
                    "status": status,
                }
            )
        os.utime(path, (mtime, mtime))

    _write(older, "Applied", 1_700_000_000)
    _write(newer, "Interviewing", 1_700_100_000)

    previous = load_previous(str(tmp_path), "profile")

    assert previous
    rows = _jobs()
    assert backfill(rows, previous) == 1
    assert rows[0]["status"] == "Interviewing"
    assert carried_count(rows, previous) == 1


def test_role_key_fallback_matches_a_changed_url(tmp_path):
    old = str(tmp_path / "profile_2026-10-19-090000.csv")
    header = exporter.EXPORT_COLUMNS + TRACKING_COLUMNS
    with open(old, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerow(
            {
                "title": "Technical Writer",
                "company": "Acme",
                "location": "New York, NY",
                "url": "https://old.example.com/posting",
                "status": "Applied",
            }
        )

    previous = load_previous(str(tmp_path), "profile")
    jobs = _jobs()

    assert backfill(jobs, previous) == 1
    assert jobs[0]["status"] == "Applied"


def test_export_without_previous_leaves_tracking_blank(tmp_path):
    path = str(tmp_path / "sweep.csv")

    exporter.export_to_csv(_jobs(), path, tracking=True, previous={})

    assert _read_csv(path)[0]["status"] == ""


def test_empty_job_list_short_circuits(tmp_path):
    assert exporter.export_to_csv([], str(tmp_path / "empty.csv"), tracking=True) == (0, 0)
    assert not (tmp_path / "empty.csv").exists()
