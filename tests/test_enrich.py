from engine.enrich import enrich_jobs, get_tracks, route_track


def _job(**overrides):
    job = {
        "title": "Technical Writer",
        "company": "Acme",
        "platform": "Ashby",
        "url": "https://jobs.ashbyhq.com/acme/abc",
        "location": "New York",
        "description": "Write API docs. Requirements: Python and REST experience.",
        "min_amount": 100000,
        "max_amount": 120000,
        "currency": "USD",
        "match_score": 87,
        "badge": "Slate",
        "playbook": "Highlight your Python experience.",
        "department": "Engineering",
    }
    job.update(overrides)
    return job


def _profile():
    return {
        "name": "Test",
        "resume": {
            "tracks": [
                {"name": "Tech Writer", "color": "#1D4ED8", "route_keywords": ["api", "python"]},
                {"name": "UX Writer", "color": "#7E22CE", "route_keywords": ["ux", "figma"]},
            ]
        },
    }


def test_enrich_populates_card_schema():
    cards = enrich_jobs([_job()], _profile())
    card = cards[0]
    assert card["id"]
    assert card["rank"] == 1
    assert card["match_value"] == 87
    assert card["match_kind"] == "overlap"
    assert card["resume_track"] == "Tech Writer"
    assert card["resume_color"] == "#1D4ED8"
    assert card["has_extended_response"] is False
    assert card["domain"] == "Engineering"
    assert card["benefits"] == "Not disclosed"
    assert card["comp"].startswith("$100K")
    assert card["summary"]
    assert card["requirements"]
    assert card["alignment"] == "Highlight your Python experience."


def test_enrich_extended_response_from_amber_badge():
    cards = enrich_jobs([_job(badge="Amber")], _profile())
    assert cards[0]["has_extended_response"] is True


def test_enrich_track_routing_ux():
    job = _job(description="UX writing with Figma microcopy")
    cards = enrich_jobs([job], _profile())
    assert cards[0]["resume_track"] == "UX Writer"
    assert cards[0]["resume_color"] == "#7E22CE"


def test_enrich_ranks_descending():
    cards = enrich_jobs([_job(match_score=50), _job(match_score=90), _job(match_score=70)], _profile())
    assert [c["match_value"] for c in cards] == [90, 70, 50]
    assert [c["rank"] for c in cards] == [1, 2, 3]


def test_enrich_no_department_yields_empty_domain():
    cards = enrich_jobs([_job(department="")], _profile())
    assert cards[0]["domain"] == ""


def test_enrich_comp_not_disclosed():
    cards = enrich_jobs([_job(min_amount=0, max_amount=0)], _profile())
    assert cards[0]["comp"] == "Not disclosed"


def test_enrich_comp_keeps_hourly_unit():
    cards = enrich_jobs([_job(min_amount=45, max_amount=55, salary_period="hour")], _profile())
    assert cards[0]["comp"] == "$45 - $55 / hour"
    assert cards[0]["salary_period"] == "hour"


def test_enrich_comp_keeps_monthly_unit():
    cards = enrich_jobs([_job(min_amount=8000, max_amount=10000, salary_period="month")], _profile())
    assert cards[0]["comp"] == "$8K - $10K / month"


def test_enrich_comp_collapses_equal_bounds():
    cards = enrich_jobs([_job(min_amount=95000, max_amount=95000)], _profile())
    assert cards[0]["comp"] == "$95K"


def test_route_track_ties_resolve_to_first():
    tracks = [
        {"name": "A", "color": "#111", "route_keywords": ["x"]},
        {"name": "B", "color": "#222", "route_keywords": ["x"]},
    ]
    assert route_track("x", "", tracks)["name"] == "A"


def test_get_tracks_implicit_single_track():
    profile = {"resume": {"path": "C:/resumes/Tech Writer.pdf"}}
    tracks = get_tracks(profile)
    assert len(tracks) == 1
    assert tracks[0]["name"] == "Tech Writer"


def test_enrich_truncates_description_to_the_default_limit():
    card = enrich_jobs([_job(description="alpha " * 400)], _profile())[0]
    assert len(card["description"]) <= 1000
    assert card["description"].endswith("…")


def test_enrich_reads_description_chars_from_the_export_settings():
    profile = _profile()
    profile["export"] = {"description_chars": 60}
    card = enrich_jobs([_job(description="alpha beta gamma delta. " * 20)], profile)[0]
    assert len(card["description"]) <= 61


def test_enrich_zero_description_chars_keeps_the_whole_posting():
    profile = _profile()
    profile["export"] = {"description_chars": 0}
    text = "alpha beta gamma delta. " * 20
    card = enrich_jobs([_job(description=text)], profile)[0]
    assert card["description"] == text.strip()


def test_enrich_strips_html_from_the_description_excerpt():
    card = enrich_jobs([_job(description="<p>Write <b>API</b> docs.</p>")], _profile())[0]
    assert card["description"] == "Write API docs."


def test_enrich_carries_the_scored_fields_the_csv_exports():
    job = _job(
        key_matches=["python", "docs"],
        missing_skills=["figma"],
        unverified=True,
        currency="EUR",
    )
    card = enrich_jobs([job], _profile())[0]
    assert card["match_score"] == card["match_value"] == 87
    assert card["badge"] == "Slate"
    assert card["unverified"] is True
    assert card["min_amount"] == 100000
    assert card["max_amount"] == 120000
    assert card["currency"] == "EUR"
    assert card["key_matches"] == ["python", "docs"]
    assert card["missing_skills"] == ["figma"]
    assert card["playbook"] == "Highlight your Python experience."


def test_export_fills_every_column_from_a_scored_job(tmp_path):
    import csv

    from engine.exporter import EXPORT_COLUMNS, export_to_csv

    job = _job(key_matches=["python", "docs"], missing_skills=["figma"])
    path = tmp_path / "sweep.csv"
    export_to_csv(enrich_jobs([job], _profile()), str(path), tracking=True)
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert [col for col in EXPORT_COLUMNS if not str(row[col]).strip()] == []
    assert row["key_matches"] == "python, docs"
    assert row["match_score"] == "87"
