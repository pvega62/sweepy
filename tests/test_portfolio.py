import logging

import pytest

from engine.portfolio import (
    DEFAULT_PIECES_PER_CARD,
    MAX_PIECES_PER_SOURCE,
    PortfolioError,
    card_portfolio_fields,
    extract_pieces,
    get_portfolio,
    normalize_portfolio,
    portfolio_errors,
    portfolio_for_track,
    portfolio_summary,
)


def _markdown(path, text="# Case Study One\n\nBody.\n\n## Case Study Two\n"):
    path.write_text(text, encoding="utf-8")
    return str(path)


def _profile(sources, pieces_per_card=None):
    block = {"sources": sources}
    if pieces_per_card is not None:
        block["pieces_per_card"] = pieces_per_card
    return {"name": "Test", "portfolio": block}


def test_empty_portfolio_is_usable():
    assert portfolio_errors(None) == []
    assert portfolio_errors({}) == []
    assert normalize_portfolio(None)["sources"] == []


def test_url_entry_needs_no_extraction_setup():
    assert portfolio_errors({"sources": [{"url": "https://example.com/work"}]}) == []


def test_shorthand_block_is_one_default_source():
    block = normalize_portfolio({"url": "https://example.com/work"})
    assert block["sources"][0]["url"] == "https://example.com/work"
    assert "track" not in block["sources"][0]


def test_entry_without_a_target_is_rejected():
    errors = portfolio_errors({"sources": [{"track": "Tech"}]})
    assert errors == ["portfolio.sources[1] needs a url, a path, or pieces"]


def test_unknown_entry_field_is_rejected():
    errors = portfolio_errors({"sources": [{"url": "https://example.com", "colour": "red"}]})
    assert "unsupported field(s): colour" in errors[0]


def test_non_http_url_is_rejected():
    errors = portfolio_errors({"sources": [{"url": "example.com/work"}]})
    assert "must start with http:// or https://" in errors[0]


def test_missing_file_is_rejected(tmp_path):
    errors = portfolio_errors({"sources": [{"path": str(tmp_path / "gone.pdf")}]})
    assert "not found" in errors[0]


def test_unsupported_file_type_is_rejected(tmp_path):
    path = tmp_path / "portfolio.psd"
    path.write_text("x", encoding="utf-8")
    errors = portfolio_errors({"sources": [{"path": str(path)}]})
    assert "must be one of" in errors[0]


def test_track_must_match_a_resume_track():
    raw = {"sources": [{"track": "Ghost Track", "url": "https://example.com"}]}
    errors = portfolio_errors(raw, ["Tech Writer", "UX Writer"])
    assert errors == [
        "portfolio.sources[1].track 'Ghost Track' matches no resume track "
        "(Tech Writer, UX Writer)"
    ]


def test_track_match_ignores_case():
    raw = {"sources": [{"track": "ux writer", "url": "https://example.com"}]}
    assert portfolio_errors(raw, ["Tech Writer", "UX Writer"]) == []


def test_pieces_per_card_is_bounded():
    errors = portfolio_errors({"url": "https://example.com", "pieces_per_card": 11})
    assert "pieces_per_card must be an integer from 1 to 10" in errors[0]


def test_piece_strings_become_titles():
    block = normalize_portfolio({"url": "https://example.com", "pieces": ["Launch notes"]})
    assert block["sources"][0]["pieces"] == [
        {"title": "Launch notes", "url": "", "tags": []}
    ]


def test_piece_without_a_title_is_rejected():
    raw = {"sources": [{"pieces": [{"url": "https://example.com/a"}]}]}
    errors = portfolio_errors(raw)
    assert "pieces[1].title must be a non-empty string" in errors[0]


def test_normalize_reports_every_problem():
    raw = {"sources": [{"url": "ftp://example.com"}, {"track": "Ghost"}]}
    with pytest.raises(PortfolioError) as excinfo:
        normalize_portfolio(raw, ["Tech Writer"])
    message = str(excinfo.value)
    assert "must start with http:// or https://" in message
    assert "needs a url, a path, or pieces" in message


def test_get_portfolio_drops_an_unusable_entry(tmp_path, caplog):
    good = _markdown(tmp_path / "portfolio.md")
    profile = _profile(
        [
            {"path": good},
            {"path": str(tmp_path / "missing.pdf")},
        ]
    )
    with caplog.at_level(logging.WARNING, logger="sweepy.engine.portfolio"):
        block = get_portfolio(profile)

    assert len(block["sources"]) == 1
    assert block["sources"][0]["path"] == good
    assert "Skipping portfolio source 2" in caplog.text


def test_markdown_headings_become_pieces(tmp_path):
    path = _markdown(tmp_path / "portfolio.md")
    pieces = extract_pieces({"path": path})
    assert [piece["title"] for piece in pieces] == ["Case Study One", "Case Study Two"]


def test_short_lines_stand_in_for_headings(tmp_path):
    path = tmp_path / "portfolio.txt"
    path.write_text(
        "Selected Work\n"
        "Rewrote the onboarding guide for a payments API.\n"
        "Release Notes Program\n",
        encoding="utf-8",
    )
    pieces = extract_pieces({"path": str(path)})
    assert [piece["title"] for piece in pieces] == [
        "Selected Work",
        "Release Notes Program",
    ]


def test_html_portfolio_lists_headings_and_links(tmp_path):
    path = tmp_path / "portfolio.html"
    path.write_text(
        '<h1>Writing</h1>'
        '<h2>API Reference</h2><a href="/work/api">REST docs rebuild</a>',
        encoding="utf-8",
    )
    pieces = extract_pieces({"path": str(path)})
    assert [piece["title"] for piece in pieces] == [
        "Writing",
        "API Reference",
        "REST docs rebuild",
    ]


def test_online_portfolio_is_fetched_once(monkeypatch):
    calls = []

    class Response:
        text = '<h2>Design System Docs</h2><a href="/work/ux">Checkout copy</a>'

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr("requests.get", fake_get)
    pieces = extract_pieces({"url": "https://example.com/portfolio"})

    assert calls == ["https://example.com/portfolio"]
    assert [piece["title"] for piece in pieces] == ["Design System Docs", "Checkout copy"]
    assert pieces[1]["url"] == "https://example.com/work/ux"


def test_failed_fetch_keeps_the_card_working(monkeypatch, caplog):
    def fake_get(url, **kwargs):
        raise OSError("connection reset")

    monkeypatch.setattr("requests.get", fake_get)
    with caplog.at_level(logging.WARNING, logger="sweepy.engine.portfolio"):
        pieces = extract_pieces({"url": "https://example.com/portfolio"})

    assert pieces == []
    assert "Could not read portfolio URL" in caplog.text


def test_explicit_pieces_skip_extraction(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("extraction should not run")

    monkeypatch.setattr("requests.get", fail)
    pieces = extract_pieces(
        {
            "url": "https://example.com/portfolio",
            "path": str(tmp_path / "missing.mp4"),
            "pieces": [{"title": "Case Study A", "tags": ["api"]}],
        }
    )
    assert pieces == [{"title": "Case Study A", "url": "", "tags": ["api"]}]


def test_pieces_are_deduped_and_capped(tmp_path):
    headings = "\n".join(f"## Case {index}" for index in range(20))
    path = tmp_path / "portfolio.md"
    path.write_text(headings + "\n## Case 0\n", encoding="utf-8")
    pieces = extract_pieces({"path": str(path)})
    assert len(pieces) == MAX_PIECES_PER_SOURCE
    assert len({piece["title"] for piece in pieces}) == MAX_PIECES_PER_SOURCE


def test_portfolio_for_track_prefers_the_named_track(tmp_path):
    tech = _markdown(tmp_path / "tech.md")
    ux = _markdown(tmp_path / "ux.md")
    profile = _profile(
        [
            {"track": "Tech Writer", "path": tech},
            {"url": "https://example.com/all"},
            {"track": "UX Writer", "path": ux},
        ]
    )
    assert portfolio_for_track(profile, "UX Writer")["path"] == ux
    assert portfolio_for_track(profile, "Tech Writer")["path"] == tech
    assert portfolio_for_track(profile, "Other")["url"] == "https://example.com/all"


def test_portfolio_for_track_returns_none_when_nothing_matches(tmp_path):
    profile = _profile([{"track": "Tech Writer", "path": _markdown(tmp_path / "t.md")}])
    assert portfolio_for_track(profile, "UX Writer") is None
    assert portfolio_for_track({}, "UX Writer") is None


def test_card_fields_follow_the_resume_track(tmp_path):
    tech = _markdown(tmp_path / "tech.md")
    profile = _profile([{"track": "Tech Writer", "path": tech, "url": "https://example.com/t"}])

    card = card_portfolio_fields(profile, "Tech Writer")
    assert card["portfolio_url"] == "https://example.com/t"
    assert card["portfolio_path"] == tech
    assert card["portfolio_pieces"] == ["Case Study One", "Case Study Two"]
    assert card["portfolio_highlight"] == ""

    other = card_portfolio_fields(profile, "UX Writer")
    assert other == {
        "portfolio_url": "",
        "portfolio_path": "",
        "portfolio_pieces": [],
        "portfolio_highlight": "",
    }


def test_card_fields_respect_the_piece_limit(tmp_path):
    path = _markdown(
        tmp_path / "portfolio.md",
        "# One\n## Two\n## Three\n## Four\n",
    )
    profile = _profile([{"path": path}])
    card = card_portfolio_fields(profile, "", limit=2)
    assert card["portfolio_pieces"] == ["One", "Two"]


def test_card_fields_extract_each_portfolio_once(tmp_path, monkeypatch):
    path = _markdown(tmp_path / "portfolio.md")
    profile = _profile([{"path": path}])
    calls = []

    monkeypatch.setattr(
        "engine.portfolio.extract_pieces",
        lambda entry, fetch=True: calls.append(entry) or [{"title": "Only", "url": "", "tags": []}],
    )
    cache = {}
    for _ in range(3):
        card = card_portfolio_fields(profile, "", cache)
        assert card["portfolio_pieces"] == ["Only"]

    assert len(calls) == 1


def test_card_fields_without_a_portfolio_stay_blank():
    assert card_portfolio_fields({"name": "Test"}, "Tech Writer")["portfolio_pieces"] == []
    assert DEFAULT_PIECES_PER_CARD == 3


def test_portfolio_summary_describes_every_source(tmp_path):
    path = _markdown(tmp_path / "portfolio.md")
    summary = portfolio_summary(
        _profile(
            [
                {"track": "Tech Writer", "path": path, "pieces": ["One", "Two"]},
                {"url": "https://example.com/all"},
            ],
            pieces_per_card=2,
        )
    )
    assert summary["configured"] is True
    assert summary["pieces_per_card"] == 2
    assert summary["sources"][0] == {
        "track": "Tech Writer",
        "url": "",
        "path": path,
        "pieces_declared": 2,
    }
    assert summary["sources"][1]["url"] == "https://example.com/all"


def test_summary_reports_no_portfolio():
    summary = portfolio_summary({"name": "Test"})
    assert summary == {
        "configured": False,
        "pieces_per_card": DEFAULT_PIECES_PER_CARD,
        "sources": [],
    }
