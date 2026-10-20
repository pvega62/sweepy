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
